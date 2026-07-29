from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
from scipy import signal, stats

from .models import ProjectState

try:
    from numba import njit
except ImportError:  # The desktop core remains usable without the sorting stack.
    njit = None


def _json_ready(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def load_recording(state: ProjectState, mode: str = "r"):
    if state.metadata.get("recording_adapter", {}).get("type") == "spikeinterface":
        if mode != "r":
            raise ValueError("Linked source recordings are read-only")
        cache_path = (
            state.root / "cache" / "sorting_input_selected_channels.bin"
        )
        sample_count = int(state.duration_seconds * state.sampling_rate)
        dtype = np.dtype(state.dtype)
        expected_bytes = (
            sample_count * state.channel_count * dtype.itemsize
        )
        if (
            cache_path.exists()
            and cache_path.stat().st_size == expected_bytes
        ):
            return np.memmap(
                cache_path,
                dtype=dtype,
                mode="r",
                shape=(sample_count, state.channel_count),
            )
        from .recording_io import load_linked_recording

        return load_linked_recording(state)
    if not state.ready:
        raise RuntimeError("尚未准备原始记录")
    sample_count = int(state.duration_seconds * state.sampling_rate)
    dtype = np.dtype(state.dtype)
    expected_bytes = sample_count * state.channel_count * dtype.itemsize
    actual_bytes = state.recording_path.stat().st_size
    if actual_bytes < expected_bytes:
        raise ValueError(
            "Recording file is shorter than its project metadata: "
            f"expected at least {expected_bytes:,} bytes, found {actual_bytes:,}. "
            "Re-import the file with the correct channel count, sampling rate, and dtype."
        )
    return np.memmap(
        state.recording_path,
        dtype=dtype,
        mode=mode,
        shape=(sample_count, state.channel_count),
    )


def _positive_lag_acg_kernel(
    spikes: np.ndarray,
    edges_seconds: np.ndarray,
) -> np.ndarray:
    """Count exact positive-lag pairs with a bounded two-pointer scan."""
    counts = np.zeros(len(edges_seconds) - 1, dtype=np.int64)
    if len(spikes) < 2 or len(counts) == 0:
        return counts
    max_lag = float(edges_seconds[-1])
    for left in range(len(spikes) - 1):
        right = left + 1
        while right < len(spikes):
            delta = spikes[right] - spikes[left]
            if delta >= max_lag:
                break
            bin_index = np.searchsorted(edges_seconds, delta, side="right") - 1
            if 0 <= bin_index < len(counts):
                counts[bin_index] += 1
            right += 1
    return counts


if njit is not None:
    _positive_lag_acg_kernel_compiled = njit(cache=False)(
        _positive_lag_acg_kernel
    )
    _ACG_BACKEND = "numba_exact_bounded_pair_count"
else:
    _positive_lag_acg_kernel_compiled = _positive_lag_acg_kernel
    _ACG_BACKEND = "python_exact_bounded_pair_count"


def _positive_lag_acg_counts(
    spike_times: np.ndarray,
    edges_ms: np.ndarray,
) -> np.ndarray:
    """Count exact forward spike pairs without allocating a pairwise matrix."""
    spikes = np.asarray(spike_times, dtype=np.float64)
    if spikes.size > 1 and np.any(np.diff(spikes) < 0):
        spikes = np.sort(spikes)
    edges_seconds = np.asarray(edges_ms, dtype=np.float64) / 1_000.0
    return _positive_lag_acg_kernel_compiled(spikes, edges_seconds)


def run_raw_qc(state: ProjectState, seconds: float = 8.0) -> dict:
    raw = load_recording(state)
    count = min(raw.shape[0], int(seconds * state.sampling_rate))
    preview = np.asarray(raw[:count], dtype=np.float32)
    rms = np.sqrt(np.mean(preview**2, axis=0))
    median_rms = float(np.median(rms))
    bad_channels = np.flatnonzero(rms > median_rms * 2.6).astype(int).tolist()

    frequencies, power = signal.welch(
        preview,
        fs=state.sampling_rate,
        nperseg=min(8192, count),
        axis=0,
    )
    mean_power = power.mean(axis=1)
    target_index = int(np.argmin(np.abs(frequencies - 50.0)))
    neighborhood = (frequencies >= 45.0) & (frequencies <= 55.0)
    baseline = np.median(mean_power[neighborhood])
    line_noise_ratio = float(mean_power[target_index] / max(baseline, 1e-12))
    channel_baseline = np.median(power[neighborhood], axis=0)
    channel_line_ratios = power[target_index] / np.maximum(channel_baseline, 1e-12)
    saturated_by_channel = np.count_nonzero(np.abs(preview) >= 32760, axis=0)
    saturated = int(saturated_by_channel.sum())

    timeline_window = max(int(state.sampling_rate), 1)
    timeline_starts = np.unique(
        np.linspace(
            0,
            max(raw.shape[0] - timeline_window, 0),
            num=min(12, max(int(state.duration_seconds), 2)),
            dtype=int,
        )
    )
    rms_timeline = []
    for start in timeline_starts:
        chunk = np.asarray(
            raw[start : min(start + timeline_window, raw.shape[0])],
            dtype=np.float32,
        )
        rms_timeline.append(np.sqrt(np.mean(chunk**2, axis=0)))
    rms_timeline_array = np.asarray(rms_timeline, dtype=float)
    preview_rms = rms.copy()
    stable_rms = np.median(rms_timeline_array, axis=0)
    median_rms = float(np.median(stable_rms))
    bad_channels = np.flatnonzero(
        stable_rms > median_rms * 2.6
    ).astype(int).tolist()
    temporal_peak_ratio = np.max(rms_timeline_array, axis=0) / np.maximum(
        stable_rms,
        1e-12,
    )
    transient_channels = np.flatnonzero(
        temporal_peak_ratio > 2.0
    ).astype(int).tolist()
    rms = stable_rms
    clipping_fraction = saturated_by_channel / max(count, 1)
    quality_score = 100.0
    quality_score -= min(40.0, len(bad_channels) / max(state.channel_count, 1) * 100)
    quality_score -= min(
        10.0,
        len(transient_channels) / max(state.channel_count, 1) * 25,
    )
    quality_score -= min(25.0, max(line_noise_ratio - 1.0, 0.0) * 6.0)
    quality_score -= min(25.0, saturated / max(preview.size, 1) * 100_000.0)
    quality_score = float(np.clip(quality_score, 0.0, 100.0))
    channel_labels = [
        (
            "high_noise"
            if channel in bad_channels
            else "clipped"
            if clipping_fraction[channel] > 0.001
            else "transient_artifact"
            if channel in transient_channels
            else "line_noise"
            if channel_line_ratios[channel] > 2.5
            else "candidate_good"
        )
        for channel in range(state.channel_count)
    ]
    psd_mask = frequencies <= min(300.0, state.sampling_rate * 0.45)

    result = {
        "channel_rms": rms.tolist(),
        "preview_channel_rms": preview_rms.tolist(),
        "median_rms": median_rms,
        "bad_channels": bad_channels,
        "transient_channels": transient_channels,
        "temporal_peak_ratio": temporal_peak_ratio.tolist(),
        "line_noise_ratio": line_noise_ratio,
        "channel_line_noise_ratio": channel_line_ratios.tolist(),
        "saturated_samples": saturated,
        "saturated_by_channel": saturated_by_channel.tolist(),
        "clipping_fraction": clipping_fraction.tolist(),
        "channel_labels": channel_labels,
        "quality_score": quality_score,
        "psd_frequencies_hz": frequencies[psd_mask].tolist(),
        "channel_psd": power[psd_mask].T.tolist(),
        "timeline_seconds": (timeline_starts / state.sampling_rate).tolist(),
        "rms_timeline": rms_timeline_array.tolist(),
        "preview_seconds": count / state.sampling_rate,
        "status": "warning" if bad_channels or line_noise_ratio > 2.5 else "pass",
    }
    state.qc = result
    state.log(
        f"Raw QC completed: quality score {quality_score:.1f}/100, "
        f"{len(bad_channels)} high-noise channels, 50 Hz ratio {line_noise_ratio:.2f}"
    )
    return result


def preprocessing_preview(
    state: ProjectState,
    start_seconds: float = 2.0,
    duration_seconds: float = 2.0,
    *,
    highpass_hz: float = 300.0,
    lowpass_hz: float | None = None,
    reference: str = "common_median",
) -> dict[str, np.ndarray]:
    raw = load_recording(state)
    start = int(start_seconds * state.sampling_rate)
    count = int(duration_seconds * state.sampling_rate)
    traces = np.asarray(raw[start : start + count, :8], dtype=np.float32)
    acquisition = state.metadata.get("acquisition_preprocessing", {})
    low_cutoff = float(highpass_hz)
    high_cutoff = min(
        float(lowpass_hz) if lowpass_hz is not None else 6000.0,
        state.sampling_rate * 0.45,
    )
    if low_cutoff <= 0 or high_cutoff <= low_cutoff:
        raise ValueError(
            "The AP preview requires 0 < high-pass < low-pass < Nyquist."
        )
    if reference not in {"none", "common_median", "common_average"}:
        raise ValueError(f"Unsupported AP reference preview: {reference}")
    if acquisition.get("ap_preprocessed"):
        referenced = traces.copy()
        ap_steps = [
            {
                "branch": "AP / sorting",
                "step": "online_preprocessing_detected",
                "parameters": {
                    "filters": acquisition.get("online_filters", []),
                    "reference": acquisition.get("online_reference"),
                },
                "status": "preserved",
            }
        ]
        state.log(
            "AP preprocessing skipped: online filtering/reference are already "
            "present in the acquisition settings"
        )
    else:
        if high_cutoff <= low_cutoff:
            raise ValueError("Sampling rate is too low for the requested AP preview")
        sos = signal.butter(
            3,
            [low_cutoff, high_cutoff],
            btype="bandpass",
            fs=state.sampling_rate,
            output="sos",
        )
        filtered = signal.sosfiltfilt(sos, traces, axis=0)
        if reference == "common_median":
            referenced = filtered - np.median(
                filtered,
                axis=1,
                keepdims=True,
            )
        elif reference == "common_average":
            referenced = filtered - np.mean(
                filtered,
                axis=1,
                keepdims=True,
            )
        else:
            referenced = filtered
        ap_steps = [
            {
                "branch": "AP / sorting",
                "step": "bandpass_filter",
                "parameters": {
                    "freq_min": low_cutoff,
                    "freq_max": high_cutoff,
                },
                "status": "previewed",
            },
            {
                "branch": "AP / sorting",
                "step": "reference",
                "parameters": {
                    "reference": "global" if reference != "none" else "none",
                    "operator": reference,
                },
                "status": "previewed",
            },
        ]

    lfp_available = bool(acquisition.get("lfp_available", True))
    if lfp_available:
        lfp_high = min(300.0, state.sampling_rate * 0.4)
        lfp_sos = signal.butter(
            3,
            [1.0, lfp_high],
            btype="bandpass",
            fs=state.sampling_rate,
            output="sos",
        )
        lfp = signal.sosfiltfilt(lfp_sos, traces, axis=0)
        lfp_target_rate = min(1_000.0, state.sampling_rate)
        divisor = max(round(state.sampling_rate / lfp_target_rate), 1)
        lfp = signal.resample_poly(lfp, up=1, down=divisor, axis=0)
        lfp_rate = state.sampling_rate / divisor
        lfp_step = {
            "branch": "LFP",
            "step": "bandpass_and_downsample",
            "parameters": {
                "freq_min": 1.0,
                "freq_max": lfp_high,
                "target_rate_hz": lfp_rate,
            },
            "status": "previewed",
        }
    else:
        lfp = np.empty((0, traces.shape[1]), dtype=np.float32)
        lfp_rate = 0.0
        lfp_step = {
            "branch": "LFP",
            "step": "unavailable",
            "parameters": {},
            "status": "blocked",
            "reason": acquisition.get(
                "lfp_unavailable_reason",
                "The imported source does not contain a valid LFP band.",
            ),
        }
    return {
        "time_ms": np.arange(count) / state.sampling_rate * 1000.0,
        "raw": traces,
        "processed": referenced,
        "lfp_time_s": (
            np.arange(len(lfp)) / lfp_rate if lfp_rate else np.empty(0)
        ),
        "lfp": lfp,
        "lfp_sampling_rate_hz": lfp_rate,
        "bandpass_hz": (low_cutoff, high_cutoff),
        "pipeline": [*ap_steps, lfp_step],
        "source_already_preprocessed": bool(acquisition.get("ap_preprocessed")),
        "lfp_available": lfp_available,
        "guardrails": [
            "Confirm bad-channel decisions before referencing.",
            "Do not whiten twice when the selected sorter already whitens internally.",
            "Apply Neuropixels phase-shift correction before common referencing when metadata support it.",
            "The preview never overwrites the source recording.",
        ],
    }


def compute_unit_metrics(state: ProjectState) -> list[dict]:
    raw = load_recording(state) if state.ready else None
    metrics: list[dict] = []
    diagnostics: dict[int, dict] = {}
    max_waveform_spikes = 300
    max_isi_plot_values = 20_000
    for unit_id, spikes in sorted(state.sorted_spikes.items()):
        firing_rate = len(spikes) / max(state.duration_seconds, 1e-9)
        intervals = np.diff(spikes)
        isi_violations = float(np.mean(intervals < 0.0015)) if intervals.size else 0.0
        sample_indices = (spikes * state.sampling_rate).astype(int)
        if raw is not None:
            sample_indices = sample_indices[
                (sample_indices >= 25) & (sample_indices < raw.shape[0] - 25)
            ]
        if raw is not None and sample_indices.size:
            selected_positions = np.linspace(
                0,
                sample_indices.size - 1,
                min(max_waveform_spikes, sample_indices.size),
                dtype=int,
            )
            selected = sample_indices[selected_positions]
            snippets = np.stack(
                [
                    np.asarray(raw[index - 20 : index + 21], dtype=np.float32)
                    for index in selected
                ]
            )
            mean_waveform = snippets.mean(axis=0)
            peak_channel = int(
                np.unravel_index(np.argmin(mean_waveform), mean_waveform.shape)[1]
            )
            peak_to_peak = float(np.ptp(mean_waveform[:, peak_channel]))
            noise = float(
                np.median(np.abs(raw[: min(raw.shape[0], 150_000), peak_channel]))
            )
            snr = peak_to_peak / max(noise * 1.4826, 1e-6)
            first_channel = max(peak_channel - 2, 0)
            last_channel = min(peak_channel + 3, state.channel_count)
            local_waveform = mean_waveform[:, first_channel:last_channel]
            selected_amplitudes = -np.min(snippets[:, :, peak_channel], axis=1)
            selected_times = selected / state.sampling_rate
        else:
            peak_channel = -1
            peak_to_peak = 0.0
            snr = float("nan") if raw is None else 0.0
            first_channel = 0
            last_channel = 0
            local_waveform = np.empty((0, 0))
            selected_amplitudes = np.empty(0)
            selected_times = np.empty(0)
        acg_edges = np.arange(0.0, 51.0, 1.0)
        acg_counts = _positive_lag_acg_counts(spikes, acg_edges)
        time_edges = np.arange(0.0, state.duration_seconds + 1.0, 1.0)
        if time_edges.size < 2:
            time_edges = np.array([0.0, max(state.duration_seconds, 1.0)])
        stability_counts, _ = np.histogram(spikes, bins=time_edges)
        if intervals.size > max_isi_plot_values:
            isi_plot_indices = np.linspace(
                0,
                intervals.size - 1,
                max_isi_plot_values,
                dtype=int,
            )
            isi_plot_values = intervals[isi_plot_indices]
            isi_plot_sampled = True
        else:
            isi_plot_values = intervals
            isi_plot_sampled = False
        diagnostics[int(unit_id)] = {
            "isi_ms": (isi_plot_values * 1_000.0).tolist(),
            "isi_total_count": int(intervals.size),
            "isi_plot_sampled": isi_plot_sampled,
            "isi_plot_max_values": max_isi_plot_values,
            "acg_lags_ms": ((acg_edges[:-1] + acg_edges[1:]) / 2).tolist(),
            "acg_counts": acg_counts.tolist(),
            "acg_backend": _ACG_BACKEND,
            "acg_spike_count": int(len(spikes)),
            "acg_sampling": "all_spikes",
            "stability_time_s": ((time_edges[:-1] + time_edges[1:]) / 2).tolist(),
            "stability_rate_hz": (
                stability_counts / np.maximum(np.diff(time_edges), 1e-9)
            ).tolist(),
            "waveform_time_ms": (
                (np.arange(local_waveform.shape[0]) - 20)
                / state.sampling_rate
                * 1_000.0
            ).tolist(),
            "waveform": local_waveform.tolist(),
            "waveform_channels": list(range(first_channel, last_channel)),
            "amplitude_time_s": selected_times.tolist(),
            "amplitude_adc": selected_amplitudes.tolist(),
            "waveform_spike_count_total": int(sample_indices.size),
            "waveform_spike_count_sampled": int(selected_times.size),
            "waveform_sampling": "evenly_spaced_across_recording",
        }
        label = (
            "候选单神经元"
            if isi_violations < 0.02 and (not np.isfinite(snr) or snr >= 4.0)
            else "需要复核"
        )
        metrics.append(
            {
                "unit_id": int(unit_id),
                "spike_count": len(spikes),
                "firing_rate_hz": float(firing_rate),
                "isi_violation_rate": isi_violations,
                "peak_channel": peak_channel,
                "peak_to_peak_adc": peak_to_peak,
                "snr": float(snr),
                "label": label,
            }
        )
    duplicate_screen = _screen_cross_unit_timestamp_overlap(
        state.sorted_spikes,
        metrics,
    )
    metric_by_unit = {
        int(metric["unit_id"]): metric for metric in metrics
    }
    for pair in duplicate_screen["flagged_pairs"]:
        for unit_key, partner_key in (
            ("unit_a", "unit_b"),
            ("unit_b", "unit_a"),
        ):
            unit_id = int(pair[unit_key])
            partner_id = int(pair[partner_key])
            metric = metric_by_unit[unit_id]
            if float(pair["overlap_fraction"]) > float(
                metric.get("max_cross_unit_overlap_fraction", 0.0)
            ):
                metric["max_cross_unit_overlap_fraction"] = float(
                    pair["overlap_fraction"]
                )
                metric["duplicate_partner_unit"] = partner_id
    state.metadata.setdefault("unit_qc_duplicate_screen", {})[
        state.active_sorter_key or "unassigned"
    ] = duplicate_screen
    state.unit_metrics = metrics
    state.unit_diagnostics = diagnostics
    if state.active_sorter_key:
        state.unit_metrics_by_sorter[state.active_sorter_key] = metrics
        state.unit_diagnostics_by_sorter[state.active_sorter_key] = diagnostics
    state.log(
        f"Unit QC completed: firing rate, ISI, waveform, stability, "
        f"and SNR computed for {len(metrics)} units"
    )
    return metrics


def _one_to_one_timestamp_overlap(
    first: np.ndarray,
    second: np.ndarray,
    tolerance_seconds: float,
) -> int:
    i = 0
    j = 0
    matches = 0
    while i < first.size and j < second.size:
        delta = second[j] - first[i]
        if abs(delta) <= tolerance_seconds:
            matches += 1
            i += 1
            j += 1
        elif delta < -tolerance_seconds:
            j += 1
        else:
            i += 1
    return matches


def _screen_cross_unit_timestamp_overlap(
    spikes_by_unit: dict[int, np.ndarray],
    metrics: list[dict],
    *,
    tolerance_seconds: float = 0.0001,
    warning_fraction: float = 0.20,
    exhaustive_unit_limit: int = 64,
) -> dict:
    """Flag possible duplicates without deleting or merging candidate units."""
    unit_ids = sorted(spikes_by_unit)
    peak_channels = {
        int(metric["unit_id"]): int(metric.get("peak_channel", -1))
        for metric in metrics
    }
    exhaustive = len(unit_ids) <= exhaustive_unit_limit
    rows: list[dict] = []
    flagged: list[dict] = []
    skipped_pairs = 0
    for first_index, first_id in enumerate(unit_ids):
        first = np.asarray(spikes_by_unit[first_id], dtype=float)
        for second_id in unit_ids[first_index + 1 :]:
            first_channel = peak_channels.get(first_id, -1)
            second_channel = peak_channels.get(second_id, -1)
            comparable_channels = (
                first_channel < 0
                or second_channel < 0
                or abs(first_channel - second_channel) <= 2
            )
            if not exhaustive and not comparable_channels:
                skipped_pairs += 1
                continue
            second = np.asarray(spikes_by_unit[second_id], dtype=float)
            matches = _one_to_one_timestamp_overlap(
                first,
                second,
                tolerance_seconds,
            )
            fraction = matches / max(min(first.size, second.size), 1)
            row = {
                "unit_a": int(first_id),
                "unit_b": int(second_id),
                "unit_a_peak_channel": first_channel,
                "unit_b_peak_channel": second_channel,
                "matched_spike_count": int(matches),
                "overlap_fraction": float(fraction),
                "tolerance_seconds": float(tolerance_seconds),
                "flagged_possible_duplicate": bool(
                    fraction >= warning_fraction
                ),
            }
            rows.append(row)
            if row["flagged_possible_duplicate"]:
                flagged.append(row)
    return {
        "schema": "neuroephys.unit-duplicate-screen.v1",
        "mode": (
            "all_unit_pairs"
            if exhaustive
            else "same_or_neighbor_peak_channel_pairs"
        ),
        "unit_count": len(unit_ids),
        "tolerance_seconds": float(tolerance_seconds),
        "warning_fraction": float(warning_fraction),
        "evaluated_pair_count": len(rows),
        "skipped_distant_channel_pair_count": skipped_pairs,
        "pairs": rows,
        "flagged_pairs": flagged,
        "interpretation": (
            "This is a screening flag. It does not delete or merge units. "
            "Review waveforms, cross-correlograms, channel profiles, amplitudes, "
            "and refractory-period evidence before a curation decision."
        ),
    }


def match_ground_truth(
    ground_truth: dict[int, np.ndarray],
    sorted_spikes: dict[int, np.ndarray],
    tolerance_seconds: float = 0.0008,
) -> list[dict]:
    matches: list[dict] = []
    for sorted_id, detected in sorted_spikes.items():
        best = {"truth_unit": -1, "precision": 0.0, "recall": 0.0, "f1": 0.0}
        for truth_id, truth in ground_truth.items():
            i = j = hits = 0
            while i < len(detected) and j < len(truth):
                delta = detected[i] - truth[j]
                if abs(delta) <= tolerance_seconds:
                    hits += 1
                    i += 1
                    j += 1
                elif delta < 0:
                    i += 1
                else:
                    j += 1
            precision = hits / max(len(detected), 1)
            recall = hits / max(len(truth), 1)
            f1 = 2 * precision * recall / max(precision + recall, 1e-12)
            if f1 > best["f1"]:
                best = {
                    "truth_unit": int(truth_id),
                    "precision": float(precision),
                    "recall": float(recall),
                    "f1": float(f1),
                }
        matches.append({"sorted_unit": int(sorted_id), **best})
    return matches


def _condition_timing_diagnostics(
    event_times: np.ndarray,
    condition_values: np.ndarray,
    *,
    tolerance_seconds: float = 0.001,
) -> dict:
    labels = np.unique(condition_values).tolist()
    counts = {
        str(label): int(np.count_nonzero(condition_values == label))
        for label in labels
    }
    pairwise = []
    warnings = []
    for first_index, first_label in enumerate(labels):
        first_times = np.sort(event_times[condition_values == first_label])
        for second_label in labels[first_index + 1 :]:
            second_times = np.sort(event_times[condition_values == second_label])
            if not len(first_times) or not len(second_times):
                fraction = 0.0
                matched = 0
            else:
                insertions = np.searchsorted(second_times, first_times)
                nearest = np.full(len(first_times), np.inf)
                right = insertions < len(second_times)
                nearest[right] = np.minimum(
                    nearest[right],
                    np.abs(first_times[right] - second_times[insertions[right]]),
                )
                left = insertions > 0
                nearest[left] = np.minimum(
                    nearest[left],
                    np.abs(
                        first_times[left]
                        - second_times[insertions[left] - 1]
                    ),
                )
                matched = int(np.count_nonzero(nearest <= tolerance_seconds))
                fraction = matched / max(min(len(first_times), len(second_times)), 1)
            pairwise.append(
                {
                    "condition_a": str(first_label),
                    "condition_b": str(second_label),
                    "matched_timestamp_count": matched,
                    "overlap_fraction": float(fraction),
                    "tolerance_seconds": float(tolerance_seconds),
                }
            )
            if fraction >= 0.8:
                warnings.append(
                    f"{first_label} and {second_label} share "
                    f"{fraction:.1%} of event timestamps; they are not "
                    "independent alignment conditions."
                )
    return {
        "condition_counts": counts,
        "pairwise_timestamp_overlap": pairwise,
        "warnings": warnings,
        "valid_for_condition_comparison": not warnings,
    }


def event_aligned_analysis(
    state: ProjectState,
    window: tuple[float, float] = (-0.5, 1.0),
    bin_size: float = 0.025,
    event_codes: list[int] | tuple[int, ...] | None = None,
    conditions: list[str] | tuple[str, ...] | None = None,
    include_synchronization: bool = False,
    baseline_window: tuple[float, float] = (-0.5, 0.0),
    response_window: tuple[float, float] = (0.0, 0.5),
) -> dict:
    if not state.sorted_spikes:
        raise RuntimeError("尚无sorting结果")
    if window[0] >= window[1]:
        raise ValueError("Event window start must be earlier than its end")
    if bin_size <= 0:
        raise ValueError("PSTH bin size must be positive")
    for label, interval in (
        ("baseline", baseline_window),
        ("response", response_window),
    ):
        if interval[0] >= interval[1]:
            raise ValueError(f"{label.title()} window start must precede its end")
        if interval[0] < window[0] or interval[1] > window[1]:
            raise ValueError(
                f"{label.title()} window must stay inside the event window"
            )

    requested_codes = (
        {int(value) for value in event_codes} if event_codes is not None else None
    )
    requested_conditions = (
        {str(value) for value in conditions} if conditions is not None else None
    )
    selected_events: list[dict] = []
    excluded = {
        "synchronization": 0,
        "outside_recording": 0,
        "event_code_filter": 0,
        "condition_filter": 0,
        "explicitly_excluded": 0,
    }
    for event in state.events:
        if event.get("exclude", False):
            excluded["explicitly_excluded"] += 1
            continue
        if (
            not include_synchronization
            and event.get("analysis_role") == "synchronization"
        ):
            excluded["synchronization"] += 1
            continue
        event_time = float(event["time_seconds"])
        if (
            event_time + window[0] < 0
            or event_time + window[1] > state.duration_seconds
        ):
            excluded["outside_recording"] += 1
            continue
        if (
            requested_codes is not None
            and int(event.get("event_code", -1)) not in requested_codes
        ):
            excluded["event_code_filter"] += 1
            continue
        condition = str(event.get("condition", "unknown"))
        if requested_conditions is not None and condition not in requested_conditions:
            excluded["condition_filter"] += 1
            continue
        selected_events.append(event)
    if not selected_events:
        raise ValueError(
            "No events remain after synchronization, recording-boundary, and "
            "user-selected event filters"
        )

    events = np.asarray(
        [float(event["time_seconds"]) for event in selected_events],
        dtype=float,
    )
    analysis_conditions = np.asarray(
        [str(event.get("condition", "unknown")) for event in selected_events],
        dtype=str,
    )
    condition_diagnostics = _condition_timing_diagnostics(
        events,
        analysis_conditions,
    )
    bins = np.arange(window[0], window[1] + bin_size, bin_size)
    centers = (bins[:-1] + bins[1:]) / 2
    condition_labels = np.unique(analysis_conditions).tolist()
    if len(condition_labels) < 2:
        condition_labels = [condition_labels[0] if condition_labels else "all", "other"]

    unit_results = {}
    response_matrix = []
    for unit_id, spike_times in sorted(state.sorted_spikes.items()):
        aligned: list[np.ndarray] = []
        counts = np.zeros((len(events), len(bins) - 1), dtype=float)
        for trial_index, event_time in enumerate(events):
            relative = spike_times - event_time
            relative = relative[(relative >= window[0]) & (relative <= window[1])]
            aligned.append(relative)
            counts[trial_index], _ = np.histogram(relative, bins=bins)
        rates = counts / bin_size
        baseline_mask = (centers >= baseline_window[0]) & (
            centers < baseline_window[1]
        )
        response_mask = (centers >= response_window[0]) & (
            centers < response_window[1]
        )
        if not np.any(baseline_mask) or not np.any(response_mask):
            raise ValueError(
                "Bin size and analysis windows produced an empty baseline or "
                "response interval"
            )
        baseline_rates = rates[:, baseline_mask].mean(axis=1)
        response_rates = rates[:, response_mask].mean(axis=1)
        if np.allclose(baseline_rates, response_rates):
            statistic, p_value = 0.0, 1.0
        else:
            statistic, p_value = stats.wilcoxon(response_rates, baseline_rates)
        mean_rate = rates.mean(axis=0)
        baseline_mean = float(mean_rate[baseline_mask].mean())
        baseline_std = float(mean_rate[baseline_mask].std())
        z_rate = (mean_rate - baseline_mean) / max(baseline_std, 0.25)
        response_matrix.append(z_rate)
        unit_results[int(unit_id)] = {
            "aligned_spikes": aligned,
            "rates": rates,
            "mean_rate": mean_rate,
            "condition_a": rates[
                analysis_conditions == condition_labels[0]
            ].mean(axis=0),
            "condition_b": (
                rates[analysis_conditions == condition_labels[1]].mean(axis=0)
                if np.any(analysis_conditions == condition_labels[1])
                else np.full(rates.shape[1], np.nan)
            ),
            "p_value": float(p_value),
            "statistic": float(statistic),
            "effect_hz": float(response_rates.mean() - baseline_rates.mean()),
        }

    p_values = np.asarray([value["p_value"] for value in unit_results.values()])
    order = np.argsort(p_values)
    adjusted = np.empty_like(p_values)
    running = 1.0
    for rank_from_end, index in enumerate(order[::-1], start=1):
        rank = len(p_values) - rank_from_end + 1
        running = min(running, p_values[index] * len(p_values) / max(rank, 1))
        adjusted[index] = running
    for adjusted_value, value in zip(adjusted, unit_results.values()):
        value["q_value"] = float(min(adjusted_value, 1.0))

    result = {
        "window": window,
        "baseline_window": baseline_window,
        "response_window": response_window,
        "bin_size": bin_size,
        "bin_centers": centers,
        "event_times": events,
        "conditions": analysis_conditions,
        "condition_labels": condition_labels[:2],
        "condition_diagnostics": condition_diagnostics,
        "selected_event_count": len(selected_events),
        "selected_event_codes": sorted(
            {
                int(event["event_code"])
                for event in selected_events
                if event.get("event_code") is not None
            }
        ),
        "selected_event_semantics": sorted(
            {
                str(event.get("event_semantics_status", "unspecified"))
                for event in selected_events
            }
        ),
        "event_filter": {
            "requested_codes": sorted(requested_codes) if requested_codes else None,
            "requested_conditions": (
                sorted(requested_conditions) if requested_conditions else None
            ),
            "include_synchronization": bool(include_synchronization),
            "excluded_counts": excluded,
        },
        "units": unit_results,
        "population_z": np.asarray(response_matrix),
        "responsive_units": int(np.sum(adjusted < 0.05)),
    }
    state.analysis = result
    state.log(
        f"Event analysis completed: {len(events)} selected events, "
        f"codes={result['selected_event_codes'] or 'not supplied'}, "
        f"{result['responsive_units']}/{len(unit_results)} units passed FDR correction"
    )
    return result


def export_reproducible_bundle(state: ProjectState, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    workflow = {
        "project": "NeuroEphys AI Demo",
        "source": str(state.recording_path),
        "sampling_rate_hz": state.sampling_rate,
        "channel_count": state.channel_count,
        "duration_seconds": state.duration_seconds,
        "steps": [
            "raw_qc",
            "preprocessing_preview",
            "spike_sorting",
            "unit_qc",
            "event_alignment",
            "behavior",
            "spike_train_statistics",
            "lfp_spectral_analysis",
            "spike_field_coupling",
            "method_validation_case",
            "statistics",
            "decoding",
            "regression",
            "figure_export",
        ],
        "parameters": {
            "bandpass_hz": [300, 6000],
            "reference": "common_median",
            "sorter": state.metadata.get("sorting", {}).get("sorter", "imported"),
            "event_window_seconds": list(state.analysis.get("window", (-0.5, 1.0))),
            "bin_size_seconds": state.analysis.get("bin_size", 0.025),
        },
    }
    (output_dir / "workflow.json").write_text(
        json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    provenance = {
        "data_type": state.source_type,
        "source_path": str(state.source_path) if state.source_path else None,
        "electrode_type": state.electrode_type,
        "ground_truth_available": bool(state.ground_truth),
        "raw_file": state.recording_path.name if state.recording_path else None,
        "qc": state.qc,
        "unit_metrics": state.unit_metrics,
        "spike_train_analysis": _json_ready(state.spike_train_analysis),
        "lfp_analysis": _json_ready(state.lfp_analysis),
        "spike_field_analysis": _json_ready(state.spike_field_analysis),
        "case_studies": _json_ready(state.case_studies),
        "statistics": _json_ready(state.statistics),
        "decoding": {
            key: _json_ready(value)
            for key, value in state.decoding.items()
            if key
            not in {
                "null_scores",
                "predictions",
                "labels",
                "probabilities",
                "pca",
                "population_trajectories",
            }
        },
        "regression": {
            key: _json_ready(value)
            for key, value in state.regression.items()
            if key not in {"observed", "predicted", "residuals"}
        },
        "workflow_status": state.workflow_status,
        "software_versions": {},
        "run_log": state.run_log,
    }
    for package in (
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "scikit-learn",
        "spikeinterface",
        "kilosort",
        "neo",
        "quantities",
        "elephant",
        "PySide6",
        "ONE-api",
        "statsmodels",
        "xgboost",
    ):
        try:
            provenance["software_versions"][package] = version(package)
        except PackageNotFoundError:
            provenance["software_versions"][package] = "not installed"
    (output_dir / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sorter_name = state.metadata.get("sorting", {}).get("sorter")
    sorting_sentence = (
        f"Spike sorting was performed with {sorter_name}. "
        if sorter_name
        else "Previously processed spike-sorting results were imported with source provenance. "
    )
    spike_train_sentence = (
        "Unit spike trains were represented as unit-aware Neo SpikeTrain objects. "
        "Elephant was used for firing-rate and inter-spike-interval statistics, "
        "trial Fano factors, cross-correlation histograms, STTC, and "
        "Victor-Purpura and van Rossum distances. "
        if state.spike_train_analysis
        else ""
    )
    lfp_sentence = (
        "The LFP branch was resampled to 1 kHz and analyzed using Welch power "
        "spectral density, magnitude-squared coherence, cross-spectral phase lag, "
        "spectrograms, and integrated canonical-band power. "
        if state.lfp_analysis
        else ""
    )
    coupling_sentence = (
        "Spike-field coupling was assessed from 1-5 Hz analytic phase using "
        "spike-triggered phase, mean vector length, a Rayleigh approximation, and "
        "circular-shift surrogate tests. Phase-amplitude coupling used 18 phase "
        "bins and Kullback-Leibler divergence from the uniform distribution. "
        if state.spike_field_analysis
        else ""
    )
    case_sentence = (
        "A respiration-state workflow was demonstrated on NeuroEphys AI's own "
        "simulated reference signal; it is a method validation case and does not "
        "reproduce or claim the numerical findings of the cited biological study. "
        if state.case_studies.get("respiration")
        else ""
    )
    methods = (
        "# Methods draft\n\n"
        f"A {state.channel_count}-channel extracellular recording was sampled at "
        f"{state.sampling_rate:.0f} Hz for {state.duration_seconds:.1f} s. "
        "Raw signals were inspected for channel noise, saturation, and line-frequency "
        f"contamination. {sorting_sentence}Candidate units "
        "were reviewed using firing rate, refractory-period violations, waveform "
        "amplitude, and signal-to-noise ratio. Spikes were aligned to experimental "
        "events in a -0.5 to 1.0 s window and summarized using 25 ms bins. Baseline "
        "and post-event firing rates were compared using paired tests, sign-flip "
        "permutation, bootstrap confidence intervals, and Benjamini-Hochberg "
        "correction across units. Trial labels were decoded with a preprocessing "
        "pipeline fit inside stratified cross-validation, and evaluated against a "
        "label-permutation null distribution. "
        f"{spike_train_sentence}{lfp_sentence}{coupling_sentence}{case_sentence}\n"
        "\n## Method sources\n\n"
        "- SpikeInterface: data interfaces, preprocessing and postprocessing architecture.\n"
        "- Neo: unit-aware electrophysiology data objects.\n"
        "- Elephant: validated spike-train, spectral and phase-analysis functions.\n"
        "- Folschweiller and Sauer (2023): respiration-state case-study structure only.\n"
    )
    (output_dir / "methods.md").write_text(methods, encoding="utf-8")

    import pandas as pd

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    if state.unit_metrics:
        pd.DataFrame(state.unit_metrics).to_csv(
            tables_dir / "unit_metrics.csv", index=False
        )
    if state.spike_train_analysis.get("rows"):
        pd.DataFrame(state.spike_train_analysis["rows"]).to_csv(
            tables_dir / "spike_train_statistics.csv", index=False
        )
    if state.lfp_analysis.get("band_power"):
        band_power = state.lfp_analysis["band_power"]
        pd.DataFrame(
            {
                "band": list(band_power),
                **{
                    f"channel_{channel_id}": [
                        band_power[band][index] for band in band_power
                    ]
                    for index, channel_id in enumerate(
                        state.lfp_analysis.get("channel_ids", [])
                    )
                },
            }
        ).to_csv(tables_dir / "lfp_band_power.csv", index=False)
    if state.spike_field_analysis.get("rows"):
        pd.DataFrame(state.spike_field_analysis["rows"]).to_csv(
            tables_dir / "spike_field_coupling.csv", index=False
        )
    respiration_case = state.case_studies.get("respiration", {})
    if respiration_case.get("rows"):
        pd.DataFrame(respiration_case["rows"]).to_csv(
            tables_dir / "respiration_case.csv", index=False
        )
    if state.statistics.get("rows"):
        pd.DataFrame(state.statistics["rows"]).to_csv(
            tables_dir / "statistics.csv", index=False
        )
    if state.events:
        pd.DataFrame(state.events).to_csv(
            tables_dir / "events.csv",
            index=False,
        )
    elif (tables_dir / "events.csv").exists():
        (tables_dir / "events.csv").unlink()
    if state.trials:
        pd.DataFrame(state.trials).to_csv(tables_dir / "trials.csv", index=False)
    elif (tables_dir / "trials.csv").exists():
        # A previous export may have treated event rows as trials. Never leave
        # that stale table beside a project whose trial definition is absent.
        (tables_dir / "trials.csv").unlink()
    if state.regression:
        pd.DataFrame(
            {
                "observed": state.regression["observed"],
                "predicted": state.regression["predicted"],
                "residual": state.regression["residuals"],
            }
        ).to_csv(tables_dir / "regression_predictions.csv", index=False)

    from .figures import (
        behavior_figure,
        decoding_figure,
        event_analysis_figure,
        neural_toolkit_figure,
        qc_figure,
        regression_figure,
        statistics_figure,
        unit_metrics_figure,
    )

    figure_builders = []
    if state.qc:
        figure_builders.append(("raw_qc", lambda: qc_figure(state)))
    if state.unit_metrics:
        figure_builders.append(("unit_qc", lambda: unit_metrics_figure(state)))
    if state.events or state.trials:
        figure_builders.append(("behavior", lambda: behavior_figure(state)))
    if state.analysis:
        figure_builders.append(
            ("raster_psth_population", lambda: event_analysis_figure(state))
        )
    if state.spike_train_analysis:
        figure_builders.extend(
            [
                (
                    "spike_train_statistics",
                    lambda: neural_toolkit_figure(state, "spike:statistics"),
                ),
                (
                    "spike_train_relationships",
                    lambda: neural_toolkit_figure(state, "spike:relationships"),
                ),
            ]
        )
    if state.lfp_analysis:
        figure_builders.extend(
            [
                ("lfp_psd", lambda: neural_toolkit_figure(state, "lfp:psd")),
                (
                    "lfp_coherence",
                    lambda: neural_toolkit_figure(state, "lfp:coherence"),
                ),
                (
                    "lfp_spectrogram",
                    lambda: neural_toolkit_figure(state, "lfp:spectrogram"),
                ),
            ]
        )
    if state.spike_field_analysis:
        figure_builders.append(
            (
                "spike_field_coupling",
                lambda: neural_toolkit_figure(state, "coupling:phase"),
            )
        )
    if respiration_case:
        figure_builders.extend(
            [
                (
                    "respiration_state_analysis",
                    lambda: neural_toolkit_figure(state, "case:respiration"),
                ),
                (
                    "respiration_phase_amplitude_coupling",
                    lambda: neural_toolkit_figure(state, "case:pac"),
                ),
            ]
        )
    if state.statistics:
        figure_builders.append(("statistics", lambda: statistics_figure(state)))
    if state.decoding:
        figure_builders.append(("decoding", lambda: decoding_figure(state)))
    if state.regression:
        figure_builders.append(("regression", lambda: regression_figure(state)))
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    for name, builder in figure_builders:
        figure = builder()
        figure.savefig(figures_dir / f"{name}.png", dpi=220, bbox_inches="tight")
        figure.savefig(figures_dir / f"{name}.svg", bbox_inches="tight")
        figure.clear()
    return output_dir
