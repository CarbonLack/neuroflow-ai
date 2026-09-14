from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal


PURPLE = "#A98AC2"
GREEN = "#A7D3A0"
INK = "#303036"
GRAY = "#A7A9AC"


def _style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
        "xtick.major.width": 0.8, "ytick.major.width": 0.8,
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 180,
    })


def _save(fig, root: Path, name: str) -> None:
    fig.tight_layout()
    fig.savefig(root / f"{name}.png", bbox_inches="tight")
    fig.savefig(root / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def generate_session_figures(project_root: Path, truth_root: Path, output: Path) -> list[str]:
    _style()
    output.mkdir(parents=True, exist_ok=True)
    meta = json.loads((project_root / "raw" / "metadata.json").read_text(encoding="utf-8"))
    gt = json.loads((truth_root / "session_ground_truth.json").read_text(encoding="utf-8"))
    fs, channels = float(meta["sampling_rate_hz"]), int(meta["channel_count"])
    samples = int(meta["duration_seconds"] * fs)
    raw = np.memmap(project_root / "raw" / "recording.bin", dtype=np.int16, mode="r", shape=(samples, channels))
    scale = float(meta["scale_uv_per_bit"])
    made: list[str] = []

    start = int(min(20, meta["duration_seconds"] / 4) * fs)
    n = int(min(2.0, meta["duration_seconds"] / 8) * fs)
    step = max(int(fs / 1000), 1)
    segment = np.asarray(raw[start:start + n:step, :min(channels, 12)], dtype=float) * scale
    time = np.arange(len(segment)) * step / fs
    spacing = max(float(np.percentile(np.abs(segment), 99)) * 1.8, 80)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for channel in range(segment.shape[1]):
        ax.plot(time, segment[:, channel] + channel * spacing, lw=0.55, color=PURPLE if channel % 2 == 0 else GREEN)
    ax.set(xlabel="Time (s)", ylabel="Channel offset", title="Broadband raw signal")
    _save(fig, output, "01_raw_multichannel_segment"); made.append("01_raw_multichannel_segment")

    preview = np.asarray(raw[:min(int(8 * fs), samples)], dtype=float) * scale
    normal = next(index for index in range(channels) if index not in gt["qc_plan"]["high_noise_channels"] + gt["qc_plan"]["dead_channels"])
    selected = [normal, *gt["qc_plan"]["high_noise_channels"][:1], *gt["qc_plan"]["dead_channels"][:1]]
    fig, axes = plt.subplots(len(selected), 1, figsize=(7.2, 1.8 * len(selected)), sharex=True)
    axes = np.atleast_1d(axes)
    shown = min(int(0.35 * fs), len(preview))
    x = np.arange(shown) / fs * 1000
    for ax, channel in zip(axes, selected, strict=True):
        ax.plot(x, preview[:shown, channel], color=INK, lw=0.55)
        ax.set_ylabel(f"Ch {channel}\nµV")
    axes[-1].set_xlabel("Time (ms)")
    _save(fig, output, "02_normal_noisy_dead_channels"); made.append("02_normal_noisy_dead_channels")

    line = gt["qc_plan"]["line_noise_channels"][0]
    f, p = signal.welch(preview[:, line], fs=fs, nperseg=min(32768, len(preview)))
    fig, ax = plt.subplots(figsize=(6.2, 3.8)); mask = f <= 180
    ax.semilogy(f[mask], p[mask], color=PURPLE, lw=1.1); ax.axvline(50, color=GREEN, lw=1)
    ax.set(xlabel="Frequency (Hz)", ylabel="PSD (µV²/Hz)", title=f"Line-noise QC · channel {line}")
    _save(fig, output, "03_line_noise_psd"); made.append("03_line_noise_psd")

    with np.load(truth_root / "waveform_templates.npz") as archive:
        unit_keys = sorted({int(key.split("_")[1]) for key in archive.files})
        chosen = unit_keys[:min(8, len(unit_keys))]
        fig, ax = plt.subplots(figsize=(6.4, 4.0))
        for index, unit in enumerate(chosen):
            wave = archive[f"unit_{unit}_waveform_uv"]
            channel = int(np.argmax(np.max(np.abs(wave), axis=0)))
            ax.plot((np.arange(len(wave)) - 36) / fs * 1000, wave[:, channel] + index * 220, color=PURPLE if index % 2 == 0 else GREEN, lw=1)
        ax.set(xlabel="Time from trough (ms)", ylabel="Unit offset", title="Ground-truth waveform diversity")
        _save(fig, output, "04_waveform_diversity"); made.append("04_waveform_diversity")

    with np.load(truth_root / "true_spike_times.npz") as archive:
        spikes = {int(key.rsplit("_", 1)[-1]): archive[key] for key in archive.files}
    unit = sorted(spikes)[0]
    isi = np.diff(spikes[unit]) * 1000
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    axes[0].hist(isi[isi < 200], bins=50, color=PURPLE); axes[0].axvline(2, color=GREEN); axes[0].set(xlabel="ISI (ms)", ylabel="Count", title="ISI distribution")
    train = np.zeros(int(meta["duration_seconds"] * 1000), dtype=float); idx = np.minimum((spikes[unit] * 1000).astype(int), len(train) - 1); train[idx] = 1
    acg = signal.correlate(train, train, mode="full", method="fft"); mid = len(acg) // 2; lag = np.arange(-100, 101)
    axes[1].plot(lag, acg[mid - 100:mid + 101], color=GREEN); axes[1].set(xlabel="Lag (ms)", ylabel="Coincidences", title="Autocorrelogram")
    _save(fig, output, "05_unit_isi_acg"); made.append("05_unit_isi_acg")

    with (truth_root / "units.csv").open(encoding="utf-8") as handle:
        units = list(csv.DictReader(handle))
    classes = ["lever", "reward_anticipation", "reward_delivery", "mixed", "nonresponsive"]
    fig, ax = plt.subplots(figsize=(6.8, 3.8)); x = np.arange(len(classes)); width = 0.36
    for offset, region, color in [(-width / 2, "M1", PURPLE), (width / 2, "mPFC", GREEN)]:
        counts = [sum(row["brain_region"] == region and row["true_neuron_class"] == name for row in units) for name in classes]
        ax.bar(x + offset, counts, width, color=color, label=region)
    ax.set_xticks(x, [name.replace("_", "\n") for name in classes]); ax.set(ylabel="True unit count", title="Functional-class composition"); ax.legend(frameon=False)
    _save(fig, output, "06_unit_class_composition"); made.append("06_unit_class_composition")

    lfp = np.load(project_root / "raw" / "lfp_ground_signal_1khz.npy", mmap_mode="r")
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for region, color, label in [(0, PURPLE, "M1"), (1, GREEN, "mPFC")]:
        f, p = signal.welch(np.asarray(lfp[region]), fs=meta["lfp_sampling_rate_hz"], nperseg=4096)
        mask = (f >= 1) & (f <= 120); ax.semilogy(f[mask], p[mask], color=color, label=label)
    ax.set(xlabel="Frequency (Hz)", ylabel="PSD (µV²/Hz)", title="Structured LFP spectrum"); ax.legend(frameon=False)
    _save(fig, output, "07_lfp_psd"); made.append("07_lfp_psd")

    artifact_sets = [*gt["qc_plan"]["transients"], *gt["qc_plan"]["baseline_shifts"], *gt["qc_plan"]["common_mode"]]
    if artifact_sets:
        item = artifact_sets[0]; center = int(item["start_time"] * fs); left = max(center - int(.15 * fs), 0); right = min(center + int(.45 * fs), samples)
        channel = item["channels"][0]; y = np.asarray(raw[left:right:step, channel], dtype=float) * scale
        fig, ax = plt.subplots(figsize=(6.4, 3.2)); ax.plot(np.arange(len(y)) * step / fs, y, color=PURPLE, lw=.65)
        ax.set(xlabel="Time (s)", ylabel="Voltage (µV)", title=f"Declared QC artifact · {item['artifact_type']}")
        _save(fig, output, "08_transient_artifact"); made.append("08_transient_artifact")

    representative = sorted(spikes)[0]
    with np.load(truth_root / "waveform_templates.npz") as archive:
        wave = archive[f"unit_{representative}_waveform_uv"]
        footprint_channels = archive[f"unit_{representative}_channels"]
    trough = np.min(wave, axis=0)
    fig, ax = plt.subplots(figsize=(5.8, 3.5))
    if meta["electrode_type"] == "tetrode":
        ax.bar(np.arange(1, len(trough) + 1), -trough, color=[PURPLE, GREEN, PURPLE, GREEN][:len(trough)])
        ax.set(xlabel="Wire within tetrode", ylabel="Trough amplitude (µV)", title="Four-wire spatial signature")
    else:
        ax.plot(-trough, footprint_channels, "o-", color=PURPLE, markerfacecolor=GREEN)
        ax.set(xlabel="Trough amplitude (µV)", ylabel="Channel", title="Neuropixels spatial footprint")
        ax.invert_yaxis()
    _save(fig, output, "09_spatial_waveform_footprint"); made.append("09_spatial_waveform_footprint")

    with (project_root / "raw" / "behavior_trials.csv").open(encoding="utf-8-sig") as handle:
        trials = list(csv.DictReader(handle))
    unit_by_class: dict[str, int] = {}
    for class_name in classes:
        candidates = [row for row in units if row["true_neuron_class"] == class_name]
        chosen_row = max(candidates, key=lambda row: float(row["response_gain"]))
        unit_by_class[class_name] = int(chosen_row["unit_id"])
    fig, axes = plt.subplots(len(classes), 2, figsize=(8.4, 10.0), sharex=True)
    bins = np.linspace(-1.5, 1.5, 61)
    for row_index, class_name in enumerate(classes):
        unit_id = unit_by_class[class_name]
        event_key = "reward_time_sec" if class_name in {"reward_anticipation", "reward_delivery"} else "lever_press_time_sec"
        aligned = []
        for trial_index, trial in enumerate(trials):
            event = float(trial[event_key])
            local = spikes[unit_id] - event
            local = local[(local >= bins[0]) & (local <= bins[-1])]
            aligned.append(local)
            axes[row_index, 0].scatter(local, np.full(len(local), trial_index + 1), s=2, color=INK, rasterized=True)
        histogram = np.histogram(np.concatenate(aligned) if aligned else [], bins=bins)[0]
        rate = histogram / max(len(trials) * np.diff(bins)[0], 1e-9)
        axes[row_index, 1].plot((bins[:-1] + bins[1:]) / 2, rate, color=PURPLE if row_index % 2 == 0 else GREEN)
        axes[row_index, 0].axvline(0, color=GRAY, lw=.8); axes[row_index, 1].axvline(0, color=GRAY, lw=.8)
        axes[row_index, 0].set_ylabel(class_name.replace("_", "\n"))
    axes[0, 0].set_title("Trial raster"); axes[0, 1].set_title("PETH")
    axes[-1, 0].set_xlabel("Time from event (s)"); axes[-1, 1].set_xlabel("Time from event (s)")
    _save(fig, output, "10_five_class_raster_peth"); made.append("10_five_class_raster_peth")

    spectrogram_signal = np.asarray(lfp[1, :min(lfp.shape[1], 120_000)], dtype=float)
    f, t, power = signal.spectrogram(spectrogram_signal, fs=meta["lfp_sampling_rate_hz"], nperseg=512, noverlap=448)
    mask = (f >= 1) & (f <= 120)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    image = ax.pcolormesh(t, f[mask], 10 * np.log10(power[mask] + 1e-12), shading="auto", cmap="Purples")
    ax.set(xlabel="Time (s)", ylabel="Frequency (Hz)", title="mPFC LFP spectrogram (first 120 s)")
    fig.colorbar(image, ax=ax, label="Power (dB)")
    _save(fig, output, "11_lfp_spectrogram"); made.append("11_lfp_spectrogram")

    lever = np.asarray([float(row["lever_press_time_sec"]) for row in trials])
    latency = np.asarray([float(row["reward_latency_sec"]) for row in trials])
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3))
    axes[0].eventplot(lever, colors=PURPLE, lineoffsets=1, linelengths=.7); axes[0].set(xlabel="Session time (s)", yticks=[], title="Lever-press timeline")
    axes[1].hist(latency, bins=np.linspace(2, 4, 13), color=GREEN, edgecolor="white"); axes[1].axvline(np.mean(latency), color=PURPLE, lw=1)
    axes[1].set(xlabel="Reward latency (s)", ylabel="Trials", title=f"Latency · mean {np.mean(latency):.2f} s")
    _save(fig, output, "12_behavior_timing"); made.append("12_behavior_timing")
    return made
