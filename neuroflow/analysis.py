from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
from scipy import signal, stats

from .models import ProjectState


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


def load_recording(state: ProjectState, mode: str = "r") -> np.memmap:
    if not state.ready:
        raise RuntimeError("尚未准备原始记录")
    sample_count = int(state.duration_seconds * state.sampling_rate)
    return np.memmap(
        state.recording_path,
        dtype=np.dtype(state.dtype),
        mode=mode,
        shape=(sample_count, state.channel_count),
    )


def run_raw_qc(state: ProjectState, seconds: float = 8.0) -> dict:
    raw = load_recording(state)
    count = min(raw.shape[0], int(seconds * state.sampling_rate))
    preview = np.asarray(raw[:count], dtype=np.float32)
    rms = np.sqrt(np.mean(preview**2, axis=0))
    median_rms = float(np.median(rms))
    bad_channels = np.flatnonzero(rms > median_rms * 2.6).astype(int).tolist()

    frequencies, power = signal.welch(
        preview[:, : min(8, state.channel_count)],
        fs=state.sampling_rate,
        nperseg=min(8192, count),
        axis=0,
    )
    mean_power = power.mean(axis=1)
    target_index = int(np.argmin(np.abs(frequencies - 50.0)))
    neighborhood = (frequencies >= 45.0) & (frequencies <= 55.0)
    baseline = np.median(mean_power[neighborhood])
    line_noise_ratio = float(mean_power[target_index] / max(baseline, 1e-12))
    saturated = int(np.count_nonzero(np.abs(preview) >= 32760))

    result = {
        "channel_rms": rms.tolist(),
        "median_rms": median_rms,
        "bad_channels": bad_channels,
        "line_noise_ratio": line_noise_ratio,
        "saturated_samples": saturated,
        "preview_seconds": count / state.sampling_rate,
        "status": "warning" if bad_channels or line_noise_ratio > 2.5 else "pass",
    }
    state.qc = result
    state.log(
        f"原始质控完成：识别{len(bad_channels)}个高噪声通道，"
        f"50 Hz比值{line_noise_ratio:.2f}"
    )
    return result


def preprocessing_preview(
    state: ProjectState,
    start_seconds: float = 2.0,
    duration_seconds: float = 0.08,
) -> dict[str, np.ndarray]:
    raw = load_recording(state)
    start = int(start_seconds * state.sampling_rate)
    count = int(duration_seconds * state.sampling_rate)
    traces = np.asarray(raw[start : start + count, :8], dtype=np.float32)
    high_cutoff = min(6000.0, state.sampling_rate * 0.45)
    if high_cutoff <= 300.0:
        raise ValueError(
            "Sampling rate is too low for the 300 Hz spike-band preview"
        )
    sos = signal.butter(
        3,
        [300.0, high_cutoff],
        btype="bandpass",
        fs=state.sampling_rate,
        output="sos",
    )
    filtered = signal.sosfiltfilt(sos, traces, axis=0)
    referenced = filtered - np.median(filtered, axis=1, keepdims=True)
    state.log("已生成300-6000 Hz带通与common median reference预览")
    return {
        "time_ms": np.arange(count) / state.sampling_rate * 1000.0,
        "raw": traces,
        "processed": referenced,
        "bandpass_hz": (300.0, high_cutoff),
    }


def compute_unit_metrics(state: ProjectState) -> list[dict]:
    raw = load_recording(state) if state.ready else None
    metrics: list[dict] = []
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
            selected = sample_indices[: min(300, sample_indices.size)]
            snippets = np.stack(
                [np.asarray(raw[index - 20 : index + 21], dtype=np.float32) for index in selected]
            )
            mean_waveform = snippets.mean(axis=0)
            peak_channel = int(np.unravel_index(np.argmin(mean_waveform), mean_waveform.shape)[1])
            peak_to_peak = float(np.ptp(mean_waveform[:, peak_channel]))
            noise = float(np.median(np.abs(raw[: min(raw.shape[0], 150_000), peak_channel])))
            snr = peak_to_peak / max(noise * 1.4826, 1e-6)
        else:
            peak_channel = -1
            peak_to_peak = 0.0
            snr = float("nan") if raw is None else 0.0
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
    state.unit_metrics = metrics
    state.log(f"Unit质控完成：计算{len(metrics)}个Unit的放电率、ISI和SNR")
    return metrics


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


def event_aligned_analysis(
    state: ProjectState,
    window: tuple[float, float] = (-0.5, 1.0),
    bin_size: float = 0.025,
) -> dict:
    if not state.sorted_spikes:
        raise RuntimeError("尚无sorting结果")
    events = np.asarray([float(event["time_seconds"]) for event in state.events])
    conditions = np.asarray([str(event["condition"]) for event in state.events])
    bins = np.arange(window[0], window[1] + bin_size, bin_size)
    centers = (bins[:-1] + bins[1:]) / 2
    condition_labels = np.unique(conditions).tolist()
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
        baseline_mask = (centers >= -0.5) & (centers < 0.0)
        response_mask = (centers >= 0.0) & (centers < 0.5)
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
            "condition_a": rates[conditions == condition_labels[0]].mean(axis=0),
            "condition_b": rates[conditions == condition_labels[1]].mean(axis=0),
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
        "bin_size": bin_size,
        "bin_centers": centers,
        "conditions": conditions,
        "condition_labels": condition_labels[:2],
        "units": unit_results,
        "population_z": np.asarray(response_matrix),
        "responsive_units": int(np.sum(adjusted < 0.05)),
    }
    state.analysis = result
    state.log(
        f"事件分析完成：{len(events)}个trial，"
        f"{result['responsive_units']}/{len(unit_results)}个Unit通过FDR校正"
    )
    return result


def export_reproducible_bundle(state: ProjectState, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    workflow = {
        "project": "NeuroFlow AI Demo",
        "source": str(state.recording_path),
        "sampling_rate_hz": state.sampling_rate,
        "channel_count": state.channel_count,
        "duration_seconds": state.duration_seconds,
        "steps": [
            "raw_qc",
            "preprocessing_preview",
            "kilosort4",
            "unit_qc",
            "event_alignment",
            "behavior",
            "statistics",
            "decoding",
            "figure_export",
        ],
        "parameters": {
            "bandpass_hz": [300, 6000],
            "reference": "common_median",
            "sorter": state.metadata.get("sorter", "Kilosort4"),
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
        "PySide6",
        "ONE-api",
    ):
        try:
            provenance["software_versions"][package] = version(package)
        except PackageNotFoundError:
            provenance["software_versions"][package] = "not installed"
    (output_dir / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sorting_sentence = (
        "Spike sorting was performed with Kilosort4. "
        if state.source_type in {"simulated", "binary", "read_intan", "read_openephys", "read_spikeglx"}
        else "Previously processed spike-sorting results were imported with source provenance. "
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
        "label-permutation null distribution.\n"
    )
    (output_dir / "methods.md").write_text(methods, encoding="utf-8")

    import pandas as pd

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    if state.unit_metrics:
        pd.DataFrame(state.unit_metrics).to_csv(
            tables_dir / "unit_metrics.csv", index=False
        )
    if state.statistics.get("rows"):
        pd.DataFrame(state.statistics["rows"]).to_csv(
            tables_dir / "statistics.csv", index=False
        )
    if state.trials:
        pd.DataFrame(state.trials).to_csv(tables_dir / "trials.csv", index=False)

    from .figures import (
        behavior_figure,
        decoding_figure,
        event_analysis_figure,
        qc_figure,
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
    if state.statistics:
        figure_builders.append(("statistics", lambda: statistics_figure(state)))
    if state.decoding:
        figure_builders.append(("decoding", lambda: decoding_figure(state)))
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    for name, builder in figure_builders:
        figure = builder()
        figure.savefig(figures_dir / f"{name}.png", dpi=220, bbox_inches="tight")
        figure.savefig(figures_dir / f"{name}.svg", bbox_inches="tight")
        figure.clear()
    return output_dir
