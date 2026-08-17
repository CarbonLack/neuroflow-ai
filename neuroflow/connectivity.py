from __future__ import annotations

from itertools import combinations
from math import erfc, sqrt
from typing import Any

import numpy as np

from .models import ProjectState


CONNECTIVITY_METHODS = (
    {
        "key": "raw_ccg",
        "name": "Raw cross-correlogram",
        "best_for": "Exploratory timing relationships",
    },
    {
        "key": "trial_rate_ccg",
        "name": "Trial/rate/edge-normalized CCG",
        "best_for": "Comparable CCG magnitude across trials, lags, and firing rates",
    },
    {
        "key": "jitter_corrected",
        "name": "Interval-jitter corrected CCG",
        "best_for": "Fine timing after removing slow or stimulus-locked structure",
    },
)

SIGNIFICANCE_METHODS = (
    {
        "key": "flank_sd",
        "name": "CCG flank standard deviation",
        "best_for": "Published workflows with an explicit peak SD threshold",
    },
    {
        "key": "jitter_percentile",
        "name": "Empirical jitter percentile",
        "best_for": "Permutation-style inference with an explicit p-value",
    },
)


def _clean_spikes(values: np.ndarray | list[float]) -> np.ndarray:
    spikes = np.asarray(values, dtype=float).reshape(-1)
    return np.unique(np.sort(spikes[np.isfinite(spikes) & (spikes >= 0)]))


def _clean_intervals(
    intervals: list[tuple[float, float]] | np.ndarray | None,
    duration_seconds: float,
) -> list[tuple[float, float]]:
    if intervals is None:
        return [(0.0, float(duration_seconds))]
    cleaned = []
    for start, stop in np.asarray(intervals, dtype=float):
        start = max(float(start), 0.0)
        stop = min(float(stop), float(duration_seconds))
        if stop > start:
            cleaned.append((start, stop))
    if not cleaned:
        raise ValueError("At least one non-empty trial interval is required")
    return cleaned


def _lag_axis(bin_size_seconds: float, max_lag_seconds: float) -> np.ndarray:
    if bin_size_seconds <= 0:
        raise ValueError("bin_size_seconds must be positive")
    if max_lag_seconds < bin_size_seconds:
        raise ValueError("max_lag_seconds must be at least one bin")
    half_bins = int(np.floor(max_lag_seconds / bin_size_seconds))
    return np.arange(-half_bins, half_bins + 1, dtype=float) * bin_size_seconds


def cross_correlogram(
    reference_spikes: np.ndarray | list[float],
    target_spikes: np.ndarray | list[float],
    *,
    duration_seconds: float,
    bin_size_seconds: float = 0.001,
    max_lag_seconds: float = 0.05,
    trial_intervals: list[tuple[float, float]] | np.ndarray | None = None,
    normalization: str = "counts",
) -> dict[str, Any]:
    """Compute a memory-bounded cross-correlogram in explicit time units.

    Only spikes that belong to the same supplied trial interval are paired. This
    prevents pairs from being formed across trial boundaries while allowing a
    whole-session analysis when ``trial_intervals`` is omitted.
    """

    reference = _clean_spikes(reference_spikes)
    target = _clean_spikes(target_spikes)
    lags = _lag_axis(bin_size_seconds, max_lag_seconds)
    edges = np.concatenate(
        (
            [lags[0] - bin_size_seconds / 2],
            lags + bin_size_seconds / 2,
        )
    )
    counts = np.zeros(len(lags), dtype=float)
    intervals = _clean_intervals(trial_intervals, duration_seconds)
    paired_reference_count = 0
    paired_target_count = 0
    interval_bin_counts: list[int] = []
    for start, stop in intervals:
        first_ref = np.searchsorted(reference, start, side="left")
        last_ref = np.searchsorted(reference, stop, side="left")
        first_target = np.searchsorted(target, start, side="left")
        last_target = np.searchsorted(target, stop, side="left")
        local_reference = reference[first_ref:last_ref]
        local_target = target[first_target:last_target]
        paired_reference_count += len(local_reference)
        paired_target_count += len(local_target)
        interval_bin_counts.append(
            max(int(np.floor((stop - start) / bin_size_seconds)), 1)
        )
        for spike in local_reference:
            left = np.searchsorted(
                local_target,
                spike - max_lag_seconds - bin_size_seconds / 2,
                side="left",
            )
            right = np.searchsorted(
                local_target,
                spike + max_lag_seconds + bin_size_seconds / 2,
                side="right",
            )
            if right > left:
                counts += np.histogram(local_target[left:right] - spike, edges)[0]

    if normalization == "reference_rate":
        denominator = max(paired_reference_count * bin_size_seconds, 1e-12)
        values = counts / denominator
        value_unit = "target_spikes_per_reference_second"
    elif normalization == "trial_rate":
        lag_bins = np.rint(lags / bin_size_seconds).astype(int)
        overlap_bins = np.asarray(
            [
                sum(max(bin_count - abs(lag_bin), 0) for bin_count in interval_bin_counts)
                for lag_bin in lag_bins
            ],
            dtype=float,
        )
        total_bins = max(sum(interval_bin_counts), 1)
        reference_mean_count = paired_reference_count / total_bins
        target_mean_count = paired_target_count / total_bins
        rate_scale = sqrt(reference_mean_count * target_mean_count)
        denominator = overlap_bins * rate_scale
        values = np.divide(
            counts,
            denominator,
            out=np.zeros_like(counts),
            where=denominator > 0,
        )
        value_unit = "dimensionless_trial_rate_normalized_ccg"
    elif normalization == "counts":
        values = counts
        value_unit = "spike_pairs"
    else:
        raise ValueError(
            "normalization must be 'counts', 'reference_rate', or 'trial_rate'"
        )
    return {
        "lags_seconds": lags,
        "values": values,
        "counts": counts,
        "normalization": normalization,
        "value_unit": value_unit,
        "reference_spike_count": int(paired_reference_count),
        "target_spike_count": int(paired_target_count),
        "interval_count": len(intervals),
    }


def _jitter_spikes(
    spikes: np.ndarray,
    *,
    intervals: list[tuple[float, float]],
    window_seconds: float,
    strategy: str,
    rng: np.random.Generator,
) -> np.ndarray:
    jittered: list[np.ndarray] = []
    for start, stop in intervals:
        first = np.searchsorted(spikes, start, side="left")
        last = np.searchsorted(spikes, stop, side="left")
        local = spikes[first:last]
        if not len(local):
            continue
        if strategy == "interval":
            window_index = np.floor((local - start) / window_seconds)
            window_start = start + window_index * window_seconds
            window_stop = np.minimum(window_start + window_seconds, stop)
            values = window_start + rng.random(len(local)) * (
                window_stop - window_start
            )
        elif strategy == "centered":
            values = local + rng.uniform(
                -window_seconds / 2,
                window_seconds / 2,
                size=len(local),
            )
            values = np.clip(values, start, np.nextafter(stop, start))
        else:
            raise ValueError("jitter_strategy must be 'interval' or 'centered'")
        jittered.append(values)
    if not jittered:
        return np.array([], dtype=float)
    return np.sort(np.concatenate(jittered))


def jitter_corrected_correlogram(
    reference_spikes: np.ndarray | list[float],
    target_spikes: np.ndarray | list[float],
    *,
    duration_seconds: float,
    bin_size_seconds: float = 0.001,
    max_lag_seconds: float = 0.05,
    jitter_window_seconds: float = 0.025,
    jitter_iterations: int = 100,
    jitter_strategy: str = "interval",
    trial_intervals: list[tuple[float, float]] | np.ndarray | None = None,
    normalization: str = "counts",
    seed: int = 20260817,
) -> dict[str, Any]:
    if jitter_window_seconds <= bin_size_seconds:
        raise ValueError("jitter_window_seconds must be larger than one CCG bin")
    if jitter_iterations < 2:
        raise ValueError("jitter_iterations must be at least 2")
    reference = _clean_spikes(reference_spikes)
    target = _clean_spikes(target_spikes)
    intervals = _clean_intervals(trial_intervals, duration_seconds)
    raw = cross_correlogram(
        reference,
        target,
        duration_seconds=duration_seconds,
        bin_size_seconds=bin_size_seconds,
        max_lag_seconds=max_lag_seconds,
        trial_intervals=intervals,
        normalization=normalization,
    )
    rng = np.random.default_rng(seed)
    jitter_values = []
    for _ in range(jitter_iterations):
        surrogate = _jitter_spikes(
            target,
            intervals=intervals,
            window_seconds=jitter_window_seconds,
            strategy=jitter_strategy,
            rng=rng,
        )
        jitter_values.append(
            cross_correlogram(
                reference,
                surrogate,
                duration_seconds=duration_seconds,
                bin_size_seconds=bin_size_seconds,
                max_lag_seconds=max_lag_seconds,
                trial_intervals=intervals,
                normalization=normalization,
            )["values"]
        )
    jitter_stack = np.asarray(jitter_values, dtype=float)
    jitter_mean = np.mean(jitter_stack, axis=0)
    return {
        **raw,
        "raw_values": np.asarray(raw["values"], dtype=float),
        "jitter_mean": jitter_mean,
        "jitter_std": np.std(jitter_stack, axis=0, ddof=1),
        "corrected_values": np.asarray(raw["values"], dtype=float) - jitter_mean,
        "jitter_iterations_values": jitter_stack,
        "jitter_window_seconds": float(jitter_window_seconds),
        "jitter_iterations": int(jitter_iterations),
        "jitter_strategy": jitter_strategy,
        "seed": int(seed),
    }


def _pair_significance(
    result: dict[str, Any],
    *,
    central_window_seconds: float,
    threshold_sd: float,
    method: str,
    alpha: float,
) -> dict[str, Any]:
    lags = np.asarray(result["lags_seconds"], dtype=float)
    corrected = np.asarray(result["corrected_values"], dtype=float)
    central = np.abs(lags) <= central_window_seconds + 1e-12
    flank = ~central
    if not np.any(central) or not np.any(flank):
        raise ValueError("Lag range must contain both central and flank bins")
    central_indices = np.flatnonzero(central)
    peak_index = int(central_indices[np.argmax(corrected[central])])
    peak_value = float(corrected[peak_index])
    flank_mean = float(np.mean(corrected[flank]))
    flank_std = float(np.std(corrected[flank], ddof=1))
    peak_z = (
        float((peak_value - flank_mean) / flank_std)
        if flank_std > 0
        else (float("inf") if peak_value > flank_mean else 0.0)
    )
    raw_values = np.asarray(result["raw_values"], dtype=float)
    observed_peak = float(np.max(raw_values[central]))
    jitter_stack = np.asarray(result["jitter_iterations_values"], dtype=float)
    surrogate_peaks = np.max(jitter_stack[:, central], axis=1)
    empirical_p = float(
        (1 + np.count_nonzero(surrogate_peaks >= observed_peak))
        / (len(surrogate_peaks) + 1)
    )
    if method == "flank_sd":
        significant = bool(peak_z >= threshold_sd and peak_value > 0)
        p_value = float(0.5 * erfc(max(peak_z, 0.0) / sqrt(2)))
    elif method == "jitter_percentile":
        significant = bool(empirical_p <= alpha and peak_value > 0)
        p_value = empirical_p
    else:
        raise ValueError(
            "significance_method must be 'flank_sd' or 'jitter_percentile'"
        )
    bin_size = float(np.median(np.diff(lags))) if len(lags) > 1 else 0.0
    peak_lag = float(lags[peak_index])
    relationship = (
        "synchronous" if abs(peak_lag) <= bin_size + 1e-12 else "asynchronous"
    )
    return {
        "significant_uncorrected": significant,
        "significance_method": method,
        "p_value": p_value,
        "empirical_jitter_p": empirical_p,
        "peak_lag_seconds": peak_lag,
        "peak_value": peak_value,
        "peak_z_flank": peak_z,
        "flank_mean": flank_mean,
        "flank_std": flank_std,
        "relationship": relationship,
    }


def _adjust_pvalues(values: list[float], method: str) -> np.ndarray:
    p_values = np.asarray(values, dtype=float)
    if method == "none":
        return p_values.copy()
    if method == "bonferroni":
        return np.minimum(p_values * len(p_values), 1.0)
    if method != "fdr_bh":
        raise ValueError("multiple_comparison must be 'none', 'fdr_bh', or 'bonferroni'")
    order = np.argsort(p_values)
    ranked = p_values[order] * len(p_values) / np.arange(1, len(p_values) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adjusted = np.empty_like(ranked)
    adjusted[order] = np.minimum(ranked, 1.0)
    return adjusted


def _unit_positions(state: ProjectState) -> dict[int, tuple[float, float]]:
    explicit = state.metadata.get("unit_positions_um", {})
    positions = {
        int(unit_id): (float(value[0]), float(value[1]))
        for unit_id, value in explicit.items()
        if len(value) >= 2
    }
    contacts = np.asarray(state.metadata.get("contact_positions_um", []), dtype=float)
    if contacts.ndim == 2 and contacts.shape[1] >= 2:
        for metric in state.unit_metrics:
            unit_id = int(metric.get("unit_id", -1))
            peak_channel = int(metric.get("peak_channel", -1))
            if unit_id not in positions and 0 <= peak_channel < len(contacts):
                positions[unit_id] = (
                    float(contacts[peak_channel, 0]),
                    float(contacts[peak_channel, 1]),
                )
    return positions


def project_interval_sets(
    state: ProjectState,
) -> dict[str, list[tuple[float, float]]]:
    """Return only explicit, non-empty project interval definitions.

    Event timestamps are never silently converted into trials. A set is exposed
    only when both start and stop fields are present, preserving the project's
    synchronization and trial-definition decisions.
    """

    result: dict[str, list[tuple[float, float]]] = {}
    for label, rows in state.metadata.get("intervals", {}).items():
        intervals = []
        for row in rows:
            try:
                intervals.append((float(row["start_time"]), float(row["stop_time"])))
            except (KeyError, TypeError, ValueError):
                continue
        if intervals:
            result[str(label)] = intervals

    trial_intervals = []
    start_keys = ("start_time", "start_seconds", "trial_start", "trial_start_time")
    stop_keys = (
        "stop_time",
        "end_time",
        "stop_seconds",
        "trial_end",
        "trial_end_time",
    )
    for row in state.trials:
        start = next((row[key] for key in start_keys if row.get(key) is not None), None)
        stop = next((row[key] for key in stop_keys if row.get(key) is not None), None)
        if start is None or stop is None:
            continue
        try:
            trial_intervals.append((float(start), float(stop)))
        except (TypeError, ValueError):
            continue
    if trial_intervals:
        result["defined_trials"] = trial_intervals
    return result


def analyze_spike_connectivity(
    spike_trains: dict[int, np.ndarray],
    *,
    duration_seconds: float,
    unit_positions_um: dict[int, tuple[float, float]] | None = None,
    unit_regions: dict[int, str] | None = None,
    pair_mode: str = "all",
    pair_selection: str = "random",
    max_distance_um: float | None = None,
    max_pairs: int | None = 5000,
    min_rate_hz: float = 1.0,
    bin_size_seconds: float = 0.001,
    max_lag_seconds: float = 0.05,
    jitter_window_seconds: float = 0.025,
    jitter_iterations: int = 100,
    jitter_strategy: str = "interval",
    trial_intervals: list[tuple[float, float]] | np.ndarray | None = None,
    interval_label: str | None = None,
    normalization: str = "counts",
    significance_method: str = "flank_sd",
    central_window_seconds: float = 0.010,
    threshold_sd: float = 7.0,
    alpha: float = 0.05,
    multiple_comparison: str = "fdr_bh",
    seed: int = 20260817,
    include_correlograms: bool = True,
) -> dict[str, Any]:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    positions = unit_positions_um or {}
    regions = unit_regions or {}
    cleaned = {int(key): _clean_spikes(value) for key, value in spike_trains.items()}
    eligible = [
        unit_id
        for unit_id, spikes in sorted(cleaned.items())
        if len(spikes) / duration_seconds >= min_rate_hz
    ]
    candidates = []
    for first_id, second_id in combinations(eligible, 2):
        first_region = regions.get(first_id)
        second_region = regions.get(second_id)
        if pair_mode == "within_region" and (
            first_region is None or first_region != second_region
        ):
            continue
        if pair_mode == "between_regions" and (
            first_region is None or second_region is None or first_region == second_region
        ):
            continue
        if pair_mode not in {"all", "within_region", "between_regions"}:
            raise ValueError(
                "pair_mode must be 'all', 'within_region', or 'between_regions'"
            )
        distance = None
        if first_id in positions and second_id in positions:
            distance = float(
                np.linalg.norm(
                    np.asarray(positions[first_id]) - np.asarray(positions[second_id])
                )
            )
        if max_distance_um is not None and (
            distance is None or distance > max_distance_um
        ):
            continue
        candidates.append((first_id, second_id, distance))
    if pair_selection == "distance":
        candidates.sort(
            key=lambda item: (
                float("inf") if item[2] is None else item[2],
                item[0],
                item[1],
            )
        )
    elif pair_selection == "unit_id":
        candidates.sort(key=lambda item: (item[0], item[1]))
    elif pair_selection == "random":
        selection_rng = np.random.default_rng(seed)
        if candidates:
            candidates = [
                candidates[index]
                for index in selection_rng.permutation(len(candidates))
            ]
    else:
        raise ValueError(
            "pair_selection must be 'random', 'distance', or 'unit_id'"
        )
    candidate_pair_count = len(candidates)
    if max_pairs is not None:
        if int(max_pairs) < 1:
            raise ValueError("max_pairs must be positive or None")
        candidates = candidates[: int(max_pairs)]
    pair_selection_truncated = len(candidates) < candidate_pair_count

    pair_results = []
    for pair_index, (first_id, second_id, distance) in enumerate(candidates):
        ccg = jitter_corrected_correlogram(
            cleaned[first_id],
            cleaned[second_id],
            duration_seconds=duration_seconds,
            bin_size_seconds=bin_size_seconds,
            max_lag_seconds=max_lag_seconds,
            jitter_window_seconds=jitter_window_seconds,
            jitter_iterations=jitter_iterations,
            jitter_strategy=jitter_strategy,
            trial_intervals=trial_intervals,
            normalization=normalization,
            seed=seed + pair_index,
        )
        significance = _pair_significance(
            ccg,
            central_window_seconds=central_window_seconds,
            threshold_sd=threshold_sd,
            method=significance_method,
            alpha=alpha,
        )
        row: dict[str, Any] = {
            "unit_a": int(first_id),
            "unit_b": int(second_id),
            "rate_a_hz": float(len(cleaned[first_id]) / duration_seconds),
            "rate_b_hz": float(len(cleaned[second_id]) / duration_seconds),
            "region_a": regions.get(first_id),
            "region_b": regions.get(second_id),
            "position_a_um": positions.get(first_id),
            "position_b_um": positions.get(second_id),
            "distance_um": distance,
            **significance,
        }
        if include_correlograms:
            row.update(
                {
                    "lags_seconds": np.asarray(ccg["lags_seconds"]).tolist(),
                    "raw_values": np.asarray(ccg["raw_values"]).tolist(),
                    "jitter_mean": np.asarray(ccg["jitter_mean"]).tolist(),
                    "corrected_values": np.asarray(
                        ccg["corrected_values"]
                    ).tolist(),
                }
            )
        pair_results.append(row)

    adjusted = _adjust_pvalues(
        [float(row["p_value"]) for row in pair_results],
        multiple_comparison,
    )
    for row, adjusted_p in zip(pair_results, adjusted):
        row["adjusted_p_value"] = float(adjusted_p)
        row["significant"] = bool(
            row["significant_uncorrected"] and adjusted_p <= alpha
        )
    significant_pairs = [row for row in pair_results if row["significant"]]
    return {
        "schema": "neuroflow.connectivity.v1",
        "configuration": {
            "pair_mode": pair_mode,
            "pair_selection": pair_selection,
            "max_distance_um": max_distance_um,
            "max_pairs": max_pairs,
            "min_rate_hz": float(min_rate_hz),
            "bin_size_seconds": float(bin_size_seconds),
            "max_lag_seconds": float(max_lag_seconds),
            "jitter_window_seconds": float(jitter_window_seconds),
            "jitter_iterations": int(jitter_iterations),
            "jitter_strategy": jitter_strategy,
            "normalization": normalization,
            "significance_method": significance_method,
            "central_window_seconds": float(central_window_seconds),
            "threshold_sd": float(threshold_sd),
            "alpha": float(alpha),
            "multiple_comparison": multiple_comparison,
            "seed": int(seed),
            "include_correlograms": bool(include_correlograms),
            "trial_interval_count": (
                0 if trial_intervals is None else len(trial_intervals)
            ),
            "interval_label": interval_label or "whole_session",
        },
        "eligible_unit_ids": eligible,
        "eligible_unit_count": len(eligible),
        "candidate_pair_count": candidate_pair_count,
        "tested_pair_count": len(pair_results),
        "pair_selection_truncated": pair_selection_truncated,
        "estimated_surrogate_ccg_count": len(pair_results) * jitter_iterations,
        "significant_pair_count": len(significant_pairs),
        "pairs": pair_results,
        "limitations": [
            "A significant timing relationship is functional evidence, not proof of a monosynaptic anatomical connection.",
            "Results depend on spike sorting, trial segmentation, jitter window, pair filtering, and multiple-comparison choices.",
            (
                f"Pair selection was truncated from {candidate_pair_count} eligible "
                f"pairs to {len(pair_results)} tested pairs."
                if pair_selection_truncated
                else "All eligible pairs were tested."
            ),
        ],
    }


def run_connectivity_suite(
    state: ProjectState,
    **settings: Any,
) -> dict[str, Any]:
    if not state.sorted_spikes:
        raise RuntimeError("Connectivity analysis requires sorted spike times")
    positions = _unit_positions(state)
    unit_regions = {
        int(unit_id): str(region)
        for unit_id, region in state.metadata.get("unit_regions", {}).items()
    }
    result = analyze_spike_connectivity(
        state.sorted_spikes,
        duration_seconds=state.duration_seconds,
        unit_positions_um=positions,
        unit_regions=unit_regions,
        **settings,
    )
    state.spike_train_analysis["connectivity"] = result
    state.log(
        "Connectivity analysis completed: "
        f"{result['tested_pair_count']} pairs tested, "
        f"{result['significant_pair_count']} significant"
    )
    return result
