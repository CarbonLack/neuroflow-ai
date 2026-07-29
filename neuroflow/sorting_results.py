from __future__ import annotations

import csv
import json
from itertools import combinations
from pathlib import Path
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
    """Store a sorter result behind the stable seconds-based internal interface."""
    normalized = _normalized_spikes(spikes)
    replacing_existing = sorter_key in state.sorting_results
    replacing_active = replacing_existing and state.active_sorter_key == sorter_key
    if replacing_existing:
        # Unit QC is derived from the exact spike assignment. Reusing it after a
        # sorter rerun can silently mix old metrics with a new cluster registry.
        state.unit_metrics_by_sorter.pop(sorter_key, None)
        state.unit_diagnostics_by_sorter.pop(sorter_key, None)
        if replacing_active:
            state.unit_metrics = []
            state.unit_diagnostics = {}
            state.analysis = {}
            state.spike_train_analysis = {}
            state.statistics = {}
            state.decoding = {}
            state.regression = {}
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
    if activate or replacing_active:
        activate_sorting_result(state, sorter_key)
    return normalized


def activate_sorting_result(state: ProjectState, sorter_key: str) -> None:
    if sorter_key not in state.sorting_results:
        raise KeyError(f"No saved sorting result for {sorter_key}")
    state.active_sorter_key = sorter_key
    state.sorted_spikes = state.sorting_results[sorter_key]
    state.unit_metrics = list(
        state.unit_metrics_by_sorter.get(sorter_key, [])
    )
    state.unit_diagnostics = dict(
        state.unit_diagnostics_by_sorter.get(sorter_key, {})
    )
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
        active_key = str(state.active_sorter_key)
        if state.unit_metrics and active_key not in state.unit_metrics_by_sorter:
            state.unit_metrics_by_sorter[active_key] = state.unit_metrics
        if (
            state.unit_diagnostics
            and active_key not in state.unit_diagnostics_by_sorter
        ):
            state.unit_diagnostics_by_sorter[active_key] = state.unit_diagnostics
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


def _nearest_lag_seconds(
    reference: np.ndarray,
    tested: np.ndarray,
    *,
    search_window_seconds: float,
    bin_seconds: float = 0.00005,
    max_reference_spikes: int = 20_000,
) -> float:
    """Estimate a fixed sorter timestamp convention difference."""
    if reference.size == 0 or tested.size == 0:
        return 0.0
    if reference.size > max_reference_spikes:
        indices = np.linspace(
            0,
            reference.size - 1,
            max_reference_spikes,
            dtype=np.int64,
        )
        sampled = reference[indices]
    else:
        sampled = reference
    positions = np.searchsorted(tested, sampled)
    differences: list[np.ndarray] = []
    for offset in (-1, 0):
        candidates = np.clip(positions + offset, 0, tested.size - 1)
        delta = tested[candidates] - sampled
        differences.append(delta[np.abs(delta) <= search_window_seconds])
    valid = np.concatenate(differences) if differences else np.array([])
    if valid.size == 0:
        return 0.0
    edges = np.arange(
        -search_window_seconds,
        search_window_seconds + bin_seconds,
        bin_seconds,
    )
    counts, _ = np.histogram(valid, bins=edges)
    index = int(np.argmax(counts))
    return float((edges[index] + edges[index + 1]) / 2.0)


def _coincidence_count(
    reference: np.ndarray,
    tested: np.ndarray,
    *,
    lag_seconds: float,
    tolerance_seconds: float,
) -> int:
    """Count one-to-one coincidences with linear memory and runtime."""
    ref = reference + lag_seconds
    i = 0
    j = 0
    matches = 0
    while i < ref.size and j < tested.size:
        delta = tested[j] - ref[i]
        if abs(delta) <= tolerance_seconds:
            matches += 1
            i += 1
            j += 1
        elif delta < -tolerance_seconds:
            j += 1
        else:
            i += 1
    return matches


def _unit_label(state: ProjectState, sorter_key: str, unit_id: int) -> str:
    metadata = state.sorting_provenance.get(sorter_key, {}).get(
        "unit_metadata",
        {},
    )
    details = metadata.get(str(unit_id), metadata.get(unit_id, {}))
    return str(details.get("source_variable") or unit_id)


def _unit_channel(
    state: ProjectState,
    sorter_key: str,
    unit_id: int,
) -> int | None:
    metadata = state.sorting_provenance.get(sorter_key, {}).get(
        "unit_metadata",
        {},
    )
    details = metadata.get(str(unit_id), metadata.get(unit_id, {}))
    if details.get("channel_number") is not None:
        return int(details["channel_number"])
    metric = next(
        (
            row
            for row in state.unit_metrics_by_sorter.get(sorter_key, [])
            if int(row.get("unit_id", -1)) == int(unit_id)
        ),
        None,
    )
    if metric is None or metric.get("peak_channel") is None:
        return None
    peak_index = int(metric["peak_channel"])
    channel_ids = (
        state.metadata.get("recording_adapter", {}).get("channel_ids")
        or state.metadata.get("selected_channel_ids")
        or []
    )
    if 0 <= peak_index < len(channel_ids):
        try:
            return int(channel_ids[peak_index])
        except (TypeError, ValueError):
            return peak_index
    return peak_index


def _agreement_interpretation(
    precision: float,
    recall: float,
    f1: float,
    chance_corrected: float,
) -> str:
    if recall >= 0.75 and precision < 0.25:
        return "reference_unit_embedded_in_high_rate_or_contaminated_cluster"
    if f1 >= 0.70 and chance_corrected >= 0.60:
        return "strong_temporal_agreement"
    if f1 >= 0.40 and chance_corrected >= 0.25:
        return "partial_temporal_agreement"
    if f1 >= 0.15 and chance_corrected > 0.0:
        return "weak_or_merged_temporal_agreement"
    return "no_reliable_temporal_match"


def compare_sorting_pair_with_lag(
    state: ProjectState,
    reference_key: str,
    tested_key: str,
    *,
    tolerance_ms: float = 0.5,
    lag_search_ms: float = 2.0,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Compare two outputs while retaining offsets, labels, and uncertainty.

    The reference name describes the comparison direction only. Neither result
    is treated as biological ground truth.
    """
    from scipy.optimize import linear_sum_assignment

    if reference_key not in state.sorting_results:
        raise KeyError(f"Unknown reference sorting result: {reference_key}")
    if tested_key not in state.sorting_results:
        raise KeyError(f"Unknown tested sorting result: {tested_key}")
    reference = state.sorting_results[reference_key]
    tested = state.sorting_results[tested_key]
    reference_ids = sorted(reference)
    tested_ids = sorted(tested)
    tolerance_seconds = float(tolerance_ms) / 1000.0
    search_seconds = float(lag_search_ms) / 1000.0
    duration = max(float(state.duration_seconds), 1e-9)
    rows: list[dict[str, Any]] = []
    score_matrix = np.zeros((len(reference_ids), len(tested_ids)), dtype=float)
    for row_index, reference_id in enumerate(reference_ids):
        ref_times = np.asarray(reference[reference_id], dtype=float)
        for column_index, tested_id in enumerate(tested_ids):
            tested_times = np.asarray(tested[tested_id], dtype=float)
            lag = _nearest_lag_seconds(
                ref_times,
                tested_times,
                search_window_seconds=search_seconds,
            )
            matches = _coincidence_count(
                ref_times,
                tested_times,
                lag_seconds=lag,
                tolerance_seconds=tolerance_seconds,
            )
            precision = matches / max(tested_times.size, 1)
            recall = matches / max(ref_times.size, 1)
            f1 = (
                2.0 * precision * recall / (precision + recall)
                if precision + recall
                else 0.0
            )
            expected = min(
                float(min(ref_times.size, tested_times.size)),
                (
                    ref_times.size
                    * tested_times.size
                    * (2.0 * tolerance_seconds)
                    / duration
                ),
            )
            possible = max(min(ref_times.size, tested_times.size) - expected, 1.0)
            chance_corrected = float(
                np.clip((matches - expected) / possible, -1.0, 1.0)
            )
            score_matrix[row_index, column_index] = max(f1, 0.0)
            reference_channel = _unit_channel(
                state,
                reference_key,
                reference_id,
            )
            tested_channel = _unit_channel(state, tested_key, tested_id)
            rows.append(
                {
                    "reference_unit": int(reference_id),
                    "reference_label": _unit_label(
                        state,
                        reference_key,
                        reference_id,
                    ),
                    "reference_channel": reference_channel,
                    "reference_spike_count": int(ref_times.size),
                    "tested_unit": int(tested_id),
                    "tested_label": _unit_label(state, tested_key, tested_id),
                    "tested_channel": tested_channel,
                    "tested_spike_count": int(tested_times.size),
                    "channel_agreement": (
                        reference_channel == tested_channel
                        if reference_channel is not None
                        and tested_channel is not None
                        else None
                    ),
                    "estimated_lag_ms": float(lag * 1000.0),
                    "tolerance_ms": float(tolerance_ms),
                    "matched_spikes": int(matches),
                    "expected_chance_matches": float(expected),
                    "precision": float(precision),
                    "recall": float(recall),
                    "f1": float(f1),
                    "chance_corrected_agreement": chance_corrected,
                    "interpretation": _agreement_interpretation(
                        precision,
                        recall,
                        f1,
                        chance_corrected,
                    ),
                }
            )
    assigned: list[dict[str, Any]] = []
    if score_matrix.size:
        assigned_rows, assigned_columns = linear_sum_assignment(-score_matrix)
        lookup = {
            (row["reference_unit"], row["tested_unit"]): row
            for row in rows
        }
        for row_index, column_index in zip(
            assigned_rows,
            assigned_columns,
            strict=True,
        ):
            assigned.append(
                dict(
                    lookup[
                        (
                            reference_ids[int(row_index)],
                            tested_ids[int(column_index)],
                        )
                    ]
                )
            )
    summary: dict[str, Any] = {
        "schema": "neuroephys.external-sorting-comparison.v1",
        "reference_key": reference_key,
        "tested_key": tested_key,
        "reference_is_ground_truth": False,
        "tolerance_ms": float(tolerance_ms),
        "lag_search_ms": float(lag_search_ms),
        "duration_seconds": float(state.duration_seconds),
        "reference_unit_count": len(reference_ids),
        "tested_unit_count": len(tested_ids),
        "pairwise": rows,
        "one_to_one_assignment": assigned,
        "strong_match_count": sum(
            row["interpretation"] == "strong_temporal_agreement"
            for row in assigned
        ),
        "interpretation": (
            "Temporal agreement measures reproducibility between two sorting "
            "workflows. External manual/offline sorting remains a comparison "
            "reference, not ground truth. All assigned units require waveform, "
            "refractory-period, stability, and manual curation review."
        ),
    }
    destination = output_dir or (
        state.root
        / "results"
        / "sorting_comparison"
        / f"{reference_key}_vs_{tested_key}"
    )
    destination.mkdir(parents=True, exist_ok=True)
    pairwise_path = destination / "pairwise_agreement.csv"
    assignment_path = destination / "one_to_one_assignment.csv"
    summary_path = destination / "comparison_summary.json"
    if rows:
        with pairwise_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    if assigned:
        with assignment_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(assigned[0]))
            writer.writeheader()
            writer.writerows(assigned)
    summary["outputs"] = {
        "pairwise_csv": str(pairwise_path),
        "assignment_csv": str(assignment_path),
        "summary_json": str(summary_path),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary["outputs"].update(
        export_sorting_comparison_figures(summary, destination)
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    state.sorting_comparison.setdefault("external_references", {})[
        f"{reference_key}_vs_{tested_key}"
    ] = summary
    state.log(
        f"External sorter comparison completed: {reference_key} vs {tested_key}; "
        f"{summary['strong_match_count']} strong one-to-one match(es)"
    )
    return summary


def export_sorting_comparison_figures(
    summary: dict[str, Any],
    output_dir: Path,
) -> dict[str, str]:
    """Export readable comparison panels without claiming ground truth."""
    import matplotlib.pyplot as plt

    pairwise = summary.get("pairwise", [])
    assigned = summary.get("one_to_one_assignment", [])
    reference_units = sorted(
        {int(row["reference_unit"]) for row in pairwise}
    )
    tested_units = sorted(
        {int(row["tested_unit"]) for row in pairwise}
    )
    reference_labels = {
        int(row["reference_unit"]): str(row["reference_label"])
        for row in pairwise
    }
    tested_labels = {
        int(row["tested_unit"]): str(row["tested_label"])
        for row in pairwise
    }
    matrix = np.full((len(reference_units), len(tested_units)), np.nan)
    reference_index = {
        unit_id: index for index, unit_id in enumerate(reference_units)
    }
    tested_index = {
        unit_id: index for index, unit_id in enumerate(tested_units)
    }
    for row in pairwise:
        matrix[
            reference_index[int(row["reference_unit"])],
            tested_index[int(row["tested_unit"])],
        ] = float(row["f1"])

    output_dir.mkdir(parents=True, exist_ok=True)
    heatmap_png = output_dir / "sorting_agreement_heatmap.png"
    heatmap_svg = output_dir / "sorting_agreement_heatmap.svg"
    figure, axis = plt.subplots(
        figsize=(
            max(8.5, len(tested_units) * 0.58),
            max(5.0, len(reference_units) * 0.48),
        )
    )
    image = axis.imshow(
        matrix,
        vmin=0,
        vmax=1,
        cmap="viridis",
        aspect="auto",
    )
    axis.set_xticks(range(len(tested_units)))
    axis.set_xticklabels(
        [tested_labels[unit_id] for unit_id in tested_units],
        rotation=45,
        ha="right",
    )
    axis.set_yticks(range(len(reference_units)))
    axis.set_yticklabels(
        [reference_labels[unit_id] for unit_id in reference_units]
    )
    axis.set_xlabel(f"Tested result: {summary['tested_key']}")
    axis.set_ylabel(f"Comparison reference: {summary['reference_key']}")
    axis.set_title(
        f"Spike-time agreement (F1, ±{summary['tolerance_ms']:.2f} ms)"
    )
    colorbar = figure.colorbar(image, ax=axis, pad=0.02)
    colorbar.set_label("F1 agreement")
    figure.text(
        0.5,
        0.005,
        "Agreement measures reproducibility between outputs; neither result is ground truth.",
        ha="center",
        fontsize=8,
        color="#4b5563",
    )
    figure.tight_layout(rect=(0, 0.03, 1, 1))
    figure.savefig(heatmap_png, dpi=180, bbox_inches="tight")
    figure.savefig(heatmap_svg, bbox_inches="tight")
    plt.close(figure)

    assigned_png = output_dir / "assigned_unit_agreement.png"
    assigned_svg = output_dir / "assigned_unit_agreement.svg"
    figure, axis = plt.subplots(
        figsize=(9.5, max(4.8, len(assigned) * 0.52))
    )
    labels = [
        f"{row['reference_label']} → {row['tested_label']}"
        for row in assigned
    ]
    values = [float(row["f1"]) for row in assigned]
    colors = [
        (
            "#157a6e"
            if row["interpretation"] == "strong_temporal_agreement"
            else "#e9a23b"
            if row["interpretation"]
            in {
                "partial_temporal_agreement",
                "weak_or_merged_temporal_agreement",
            }
            else "#c24f5d"
        )
        for row in assigned
    ]
    positions = np.arange(len(assigned))
    axis.barh(positions, values, color=colors, height=0.7)
    axis.set_yticks(positions)
    axis.set_yticklabels(labels)
    axis.invert_yaxis()
    axis.set_xlim(0, 1)
    axis.set_xlabel("F1 agreement")
    axis.set_title("One-to-one assignment by spike-time agreement")
    axis.grid(axis="x", color="#d6dde0", linewidth=0.7)
    axis.set_axisbelow(True)
    for position, value in zip(positions, values, strict=True):
        axis.text(
            min(value + 0.015, 0.97),
            position,
            f"{value:.3f}",
            va="center",
            fontsize=8,
        )
    figure.text(
        0.5,
        0.005,
        "Manual waveform and refractory-period review remains required.",
        ha="center",
        fontsize=8,
        color="#4b5563",
    )
    figure.tight_layout(rect=(0, 0.03, 1, 1))
    figure.savefig(assigned_png, dpi=180, bbox_inches="tight")
    figure.savefig(assigned_svg, bbox_inches="tight")
    plt.close(figure)
    return {
        "agreement_heatmap_png": str(heatmap_png),
        "agreement_heatmap_svg": str(heatmap_svg),
        "assigned_units_png": str(assigned_png),
        "assigned_units_svg": str(assigned_svg),
    }
