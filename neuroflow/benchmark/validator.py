from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy import signal


def validate_session(project_root: Path, truth_root: Path) -> dict:
    metadata = json.loads((project_root / "raw" / "metadata.json").read_text(encoding="utf-8"))
    truth = json.loads((truth_root / "session_ground_truth.json").read_text(encoding="utf-8"))
    raw_path = project_root / "raw" / "recording.bin"
    sampling_rate = float(metadata["sampling_rate_hz"])
    channel_count = int(metadata["channel_count"])
    sample_count = int(round(metadata["duration_seconds"] * sampling_rate))
    checks: list[dict] = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    expected_bytes = sample_count * channel_count * np.dtype("int16").itemsize
    record("raw_size", raw_path.stat().st_size == expected_bytes, f"{raw_path.stat().st_size} / {expected_bytes} bytes")
    with (project_root / "raw" / "behavior_trials.csv").open("r", newline="", encoding="utf-8") as handle:
        trials = list(csv.DictReader(handle))
    event_ok = True
    for trial in trials:
        lever, reward = float(trial["lever_press_time_sec"]), float(trial["reward_time_sec"])
        lever_sample, reward_sample = int(trial["lever_sample"]), int(trial["reward_sample"])
        event_ok &= 0 < lever < reward < metadata["duration_seconds"]
        event_ok &= lever_sample / sampling_rate == lever and reward_sample / sampling_rate == reward
    record("behavior_alignment", event_ok, f"{len(trials)} lever/reward pairs share the electrophysiology clock")
    with np.load(truth_root / "true_spike_times.npz") as archive:
        spikes = [archive[key] for key in archive.files]
    spike_bounds = all(np.all((row > 0) & (row < metadata["duration_seconds"])) for row in spikes)
    isi_ok = all(not len(row) or np.mean(np.diff(row) < 0.0012) < 0.002 for row in spikes)
    record("spike_bounds", spike_bounds, f"{sum(map(len, spikes))} ground-truth spikes")
    record("refractory_period", isi_ok, "normal truth units have negligible <1.2 ms ISIs")
    with np.load(truth_root / "waveform_templates.npz") as templates:
        footprint_sizes = [len(templates[key]) for key in templates.files if key.endswith("_channels")]
    minimum = 4 if metadata["electrode_type"] == "tetrode" else 5
    record("spatial_waveforms", bool(footprint_sizes) and min(footprint_sizes) >= minimum, f"minimum footprint {min(footprint_sizes)} channels")
    raw = np.memmap(raw_path, dtype=np.int16, mode="r", shape=(sample_count, channel_count))
    preview_count = min(int(8 * sampling_rate), sample_count)
    preview = np.asarray(raw[:preview_count], dtype=np.float32) * metadata["scale_uv_per_bit"]
    rms = np.sqrt(np.mean(preview**2, axis=0))
    plan = truth["qc_plan"]
    normal = [index for index in range(channel_count) if index not in plan["high_noise_channels"] + plan["dead_channels"]]
    median = float(np.median(rms[normal]))
    noisy_ok = all(rms[index] > median * 1.6 for index in plan["high_noise_channels"])
    dead_ok = all(rms[index] < median * 0.2 for index in plan["dead_channels"])
    record("high_noise_channels", noisy_ok, f"median normal RMS {median:.2f} uV")
    record("dead_channels", dead_ok, f"{plan['dead_channels']}")
    line_channels = plan["line_noise_channels"] or [0]
    frequencies, psd = signal.welch(preview[:, line_channels], fs=sampling_rate, nperseg=min(32768, preview_count), axis=0)
    index50 = int(np.argmin(np.abs(frequencies - 50)))
    neighborhood = (frequencies >= 45) & (frequencies <= 55)
    ratio = float(np.mean(psd[index50]) / max(float(np.median(psd[neighborhood])), 1e-12))
    record("line_noise", ratio > 4.0, f"50 Hz/local median PSD ratio {ratio:.2f}")
    with np.load(truth_root / "waveform_templates.npz") as templates, np.load(truth_root / "true_spike_times.npz") as spike_archive:
        visibility: list[float] = []
        for key in spike_archive.files[: min(12, len(spike_archive.files))]:
            unit_id = int(key.rsplit("_", 1)[-1])
            values = spike_archive[key]
            if not len(values):
                continue
            template = templates[f"unit_{unit_id}_waveform_uv"]
            local_channel = int(np.argmax(np.max(np.abs(template), axis=0)))
            channel = int(templates[f"unit_{unit_id}_channels"][local_channel])
            peak_offset = int(np.argmin(template[:, local_channel])) - 36
            chosen = values[np.linspace(0, len(values) - 1, min(20, len(values)), dtype=int)]
            indices = np.clip(np.rint(chosen * sampling_rate).astype(int) + peak_offset, 0, sample_count - 1)
            visibility.extend(np.abs(np.asarray(raw[indices, channel], dtype=float) * metadata["scale_uv_per_bit"]).tolist())
    visible_median = float(np.median(visibility)) if visibility else 0.0
    record("spike_visibility", visible_median > median * 1.25, f"median ground-truth peak magnitude {visible_median:.2f} uV")
    transient_ok = True
    for item in [*plan["transients"], *plan["common_mode"], *plan["baseline_shifts"]]:
        start, stop = int(item["start_time"] * sampling_rate), int(item["end_time"] * sampling_rate)
        segment = np.asarray(raw[start:stop, item["channels"]], dtype=np.float32) * metadata["scale_uv_per_bit"]
        transient_ok &= bool(segment.size and np.max(np.abs(segment)) > 70)
    record("artifacts_present", transient_ok, "all declared transient intervals contain a measurable deflection")
    clipping_ok = True
    for item in plan["clipping"]:
        start, stop = int(item["start_time"] * sampling_rate), int(item["end_time"] * sampling_rate)
        clipping_ok &= np.any(np.abs(np.asarray(raw[start:stop, item["channels"]], dtype=np.int32)) >= 32760)
    record("clipping_ground_truth", clipping_ok, f"{sum(truth['true_clipped_samples_by_channel'])} clipped samples recorded")
    record("lfp_reference", (project_root / "raw" / "lfp_ground_signal_1khz.npy").is_file(), "1 kHz M1/mPFC reference exists; broadband raw remains primary input")
    passed = all(row["passed"] for row in checks)
    return {"passed": passed, "project": str(project_root), "truth": str(truth_root), "checks": checks}


def write_validation_report(results: list[dict], output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    payload = {"passed": all(row["passed"] for row in results), "session_count": len(results), "sessions": results}
    (output / "validation_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# NeuroEphys AI benchmark validation", "", f"Overall: {'PASS' if payload['passed'] else 'FAIL'}", ""]
    for session in results:
        lines.extend([f"## {Path(session['project']).name}: {'PASS' if session['passed'] else 'FAIL'}", ""])
        lines.extend(f"- {'✓' if item['passed'] else '✗'} {item['check']}: {item['detail']}" for item in session["checks"])
        lines.append("")
    (output / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")
    return output / "validation_report.json"
