from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np

from .models import ProjectState

SORTING_SCHEMA = "neuroflow.sorting.v1"


def _normalized_spikes(
    spikes: dict[int, np.ndarray],
) -> dict[int, np.ndarray]:
    normalized: dict[int, np.ndarray] = {}
    for unit_id, values in spikes.items():
        times = np.asarray(values, dtype=np.float64).reshape(-1)
        times = times[np.isfinite(times)]
        normalized[int(unit_id)] = np.unique(np.sort(times))
    return normalized


def register_sorting_result(
    state: ProjectState,
    sorter_key: str,
    spikes: dict[int, np.ndarray],
    provenance: dict[str, Any],
    *,
    activate: bool = True,
) -> dict[int, np.ndarray]:
    """Store one sorter result behind NeuroFlow's stable, seconds-based interface."""
    normalized = _normalized_spikes(spikes)
    details = {
        "schema": SORTING_SCHEMA,
        "time_unit": "seconds",
        "sampling_rate_hz": float(state.sampling_rate),
        "sorter_key": sorter_key,
        "unit_count": len(normalized),
        "spike_count": int(sum(len(values) for values in normalized.values())),
        **provenance,
    }
    state.sorting_results[sorter_key] = normalized
    state.sorting_provenance[sorter_key] = details
    if activate:
        activate_sorting_result(state, sorter_key)
    return normalized


def activate_sorting_result(state: ProjectState, sorter_key: str) -> None:
    if sorter_key not in state.sorting_results:
        raise KeyError(f"No saved sorting result for {sorter_key}")
    state.active_sorter_key = sorter_key
    state.sorted_spikes = state.sorting_results[sorter_key]
    state.metadata["sorting"] = dict(
        state.sorting_provenance.get(
            sorter_key,
            {
                "schema": SORTING_SCHEMA,
                "time_unit": "seconds",
                "sorter_key": sorter_key,
            },
        )
    )


def ensure_sorting_registry(
    state: ProjectState,
    sorter_key: str | None = None,
) -> None:
    """Upgrade projects created before the multi-sorter result registry existed."""
    if state.sorting_results:
        if state.active_sorter_key not in state.sorting_results:
            state.active_sorter_key = next(iter(state.sorting_results))
        activate_sorting_result(state, str(state.active_sorter_key))
        return
    if not state.sorted_spikes:
        return
    metadata = dict(state.metadata.get("sorting", {}))
    key = sorter_key or metadata.get("sorter_key") or "imported_sorting"
    metadata.setdefault("sorter", metadata.get("sorter") or "Imported sorting")
    metadata.setdefault("backend", "Imported result")
    register_sorting_result(state, str(key), state.sorted_spikes, metadata)


def _to_si_sorting(spikes: dict[int, np.ndarray], sampling_rate: float):
    import spikeinterface as si

    samples = {
        int(unit_id): np.unique(
            np.rint(np.asarray(times, dtype=float) * sampling_rate).astype(np.int64)
        )
        for unit_id, times in spikes.items()
    }
    return si.NumpySorting.from_unit_dict([samples], sampling_rate)


def _matrix_payload(frame) -> dict[str, Any]:
    return {
        "rows": [int(value) for value in frame.index],
        "columns": [int(value) for value in frame.columns],
        "values": np.asarray(frame, dtype=float).tolist(),
    }


def _pairwise_payload(
    name_a: str,
    name_b: str,
    sorting_a,
    sorting_b,
    *,
    delta_time_ms: float,
    match_score: float,
) -> dict[str, Any]:
    from spikeinterface.comparison import compare_two_sorters

    comparison = compare_two_sorters(
        sorting_a,
        sorting_b,
        sorting1_name=name_a,
        sorting2_name=name_b,
        delta_time=delta_time_ms,
        match_score=match_score,
        verbose=False,
    )
    matrix = comparison.agreement_scores
    forward, _ = comparison.get_matching()
    matches: list[dict[str, Any]] = []
    for unit_a, unit_b in forward.items():
        if int(unit_b) < 0 or unit_b not in matrix.columns:
            continue
        score = float(matrix.loc[unit_a, unit_b])
        if score >= match_score:
            matches.append(
                {
                    "unit_a": int(unit_a),
                    "unit_b": int(unit_b),
                    "agreement": score,
                }
            )
    return {
        "sorter_a": name_a,
        "sorter_b": name_b,
        "agreement_matrix": _matrix_payload(matrix),
        "matched_pairs": matches,
        "matched_unit_count": len(matches),
        "mean_matched_agreement": (
            float(np.mean([item["agreement"] for item in matches]))
            if matches
            else 0.0
        ),
        "unique_units_a": int(len(sorting_a.unit_ids) - len(matches)),
        "unique_units_b": int(len(sorting_b.unit_ids) - len(matches)),
    }


def _ground_truth_payload(
    ground_truth,
    tested,
    sorter_key: str,
    *,
    delta_time_ms: float,
    match_score: float,
) -> dict[str, Any]:
    from spikeinterface.comparison import compare_sorter_to_ground_truth

    comparison = compare_sorter_to_ground_truth(
        ground_truth,
        tested,
        gt_name="ground_truth",
        tested_name=sorter_key,
        delta_time=delta_time_ms,
        match_score=match_score,
        verbose=False,
    )
    performance = comparison.get_performance(method="by_unit")
    rows = []
    for unit_id, row in performance.iterrows():
        precision = float(row["precision"])
        recall = float(row["recall"])
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        rows.append(
            {
                "truth_unit": int(unit_id),
                "accuracy": float(row["accuracy"]),
                "precision": precision,
                "recall": recall,
                "f1": float(f1),
                "false_discovery_rate": float(row["false_discovery_rate"]),
                "miss_rate": float(row["miss_rate"]),
            }
        )
    return {
        "sorter_key": sorter_key,
        "metrics_by_truth_unit": rows,
        "mean_accuracy": float(np.mean([row["accuracy"] for row in rows]))
        if rows
        else 0.0,
        "mean_precision": float(np.mean([row["precision"] for row in rows]))
        if rows
        else 0.0,
        "mean_recall": float(np.mean([row["recall"] for row in rows]))
        if rows
        else 0.0,
        "mean_f1": float(np.mean([row["f1"] for row in rows])) if rows else 0.0,
        "agreement_matrix": _matrix_payload(comparison.agreement_scores),
    }


def compare_sorting_results(
    state: ProjectState,
    *,
    delta_time_ms: float = 0.4,
    match_score: float = 0.5,
) -> dict[str, Any]:
    """Compare saved sorter outputs without treating agreement as ground truth."""
    ensure_sorting_registry(state)
    si_sortings = {
        key: _to_si_sorting(spikes, state.sampling_rate)
        for key, spikes in state.sorting_results.items()
        if spikes
    }
    summary: dict[str, Any] = {
        "schema": "neuroflow.sorting-comparison.v1",
        "time_unit": "seconds",
        "delta_time_ms": float(delta_time_ms),
        "match_score": float(match_score),
        "sorters": {
            key: {
                "unit_count": len(state.sorting_results[key]),
                "spike_count": int(
                    sum(len(values) for values in state.sorting_results[key].values())
                ),
                "provenance": state.sorting_provenance.get(key, {}),
            }
            for key in si_sortings
        },
        "pairwise": [],
        "ground_truth": {},
        "consensus": {},
        "interpretation": {
            "without_ground_truth": (
                "Agreement and consensus describe reproducibility between algorithms; "
                "they are not precision, recall, or proof of biological truth."
            ),
            "with_ground_truth": (
                "Precision, recall, accuracy, and F1 are reported only for data with "
                "known simulated or experimentally established ground truth."
            ),
        },
    }
    for key_a, key_b in combinations(si_sortings, 2):
        summary["pairwise"].append(
            _pairwise_payload(
                key_a,
                key_b,
                si_sortings[key_a],
                si_sortings[key_b],
                delta_time_ms=delta_time_ms,
                match_score=match_score,
            )
        )
    if state.ground_truth:
        truth = _to_si_sorting(state.ground_truth, state.sampling_rate)
        summary["ground_truth"] = {
            key: _ground_truth_payload(
                truth,
                sorting,
                key,
                delta_time_ms=delta_time_ms,
                match_score=match_score,
            )
            for key, sorting in si_sortings.items()
        }
    if len(si_sortings) >= 2:
        from spikeinterface.comparison import compare_multiple_sorters

        keys = list(si_sortings)
        multi = compare_multiple_sorters(
            [si_sortings[key] for key in keys],
            name_list=keys,
            delta_time=delta_time_ms,
            match_score=match_score,
            n_jobs=1,
            spiketrain_mode="intersection",
            verbose=False,
        )
        consensus = multi.get_agreement_sorting(minimum_agreement_count=2)
        summary["consensus"] = {
            "minimum_agreement_count": 2,
            "spiketrain_mode": "intersection",
            "unit_count": len(consensus.unit_ids),
            "spike_count": int(
                sum(
                    len(consensus.get_unit_spike_train(unit_id))
                    for unit_id in consensus.unit_ids
                )
            ),
        }
    state.sorting_comparison = summary
    state.log(
        "Sorter comparison updated: "
        f"{len(si_sortings)} result(s), {len(summary['pairwise'])} pair(s)"
    )
    return summary
