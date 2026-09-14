from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np

from .artifact_generator import apply_artifacts
from .noise_generator import background_chunk


def _add_spikes(
    raw_uv: np.ndarray,
    sample_start: int,
    sampling_rate: float,
    duration_seconds: float,
    units: list[dict],
    spikes: dict[int, np.ndarray],
    templates: dict[int, dict],
    channel_count: int,
    electrode: str,
) -> None:
    sample_stop = sample_start + len(raw_uv)
    for unit in units:
        unit_id = int(unit["unit_id"])
        template = templates[unit_id]["waveform_uv"]
        channels = templates[unit_id]["channels"].copy()
        peak_index = int(np.argmin(template[:, int(np.argmax(np.max(np.abs(template), axis=0)))]))
        centers = np.rint(spikes[unit_id] * sampling_rate).astype(np.int64)
        left = np.searchsorted(centers, sample_start - (len(template) - peak_index), side="left")
        right = np.searchsorted(centers, sample_stop + peak_index, side="right")
        centers = centers[left:right]
        if not len(centers):
            continue
        progress = np.clip((centers / sampling_rate) / duration_seconds, 0, 1)
        amplitude_scale = 1.0 + unit["amplitude_drift_fraction"] * (progress - 0.5) * 2
        if electrode == "neuropixels" and unit["spatial_drift_sites"]:
            shift = int(round(unit["spatial_drift_sites"] * float(np.mean(progress))))
            candidate = channels + shift
            half = channel_count // 2
            low, high = (0, half) if unit["brain_region"] == "M1" else (half, channel_count)
            if np.all((candidate >= low) & (candidate < high)):
                channels = candidate
        offsets = np.arange(len(template), dtype=np.int64) - peak_index
        indices = centers[:, None] + offsets[None, :] - sample_start
        valid = (indices >= 0) & (indices < len(raw_uv))
        for local_channel, channel in enumerate(channels):
            values = amplitude_scale[:, None] * template[None, :, local_channel]
            if electrode == "tetrode":
                wire_gradient = local_channel - (len(channels) - 1) / 2
                values *= 1.0 + unit["relative_wire_drift_fraction"] * wire_gradient * (progress[:, None] - 0.5)
            np.add.at(raw_uv[:, int(channel)], indices[valid], values[valid].astype(np.float32))


def export_raw_recording(
    path: Path,
    rng: np.random.Generator,
    duration_seconds: float,
    sampling_rate: float,
    lfp_sampling_rate: float,
    channel_count: int,
    scale_uv_per_bit: float,
    lfp: np.ndarray,
    geometry: list[dict],
    units: list[dict],
    spikes: dict[int, np.ndarray],
    templates: dict[int, dict],
    qc_plan: dict,
    noise_config: dict,
    chunk_seconds: float,
    progress: Callable[[str], None] | None = None,
) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_samples = int(round(duration_seconds * sampling_rate))
    chunk_samples = max(int(round(chunk_seconds * sampling_rate)), 1)
    ratio = sampling_rate / lfp_sampling_rate
    if not float(ratio).is_integer():
        raise ValueError("Benchmark generator requires an integer raw/LFP sampling-rate ratio")
    ratio = int(ratio)
    normal_rms = rng.uniform(*noise_config["normal_rms_uv"], channel_count).astype(np.float32)
    normal_rms[qc_plan["high_noise_channels"]] = rng.uniform(55, 75, len(qc_plan["high_noise_channels"]))
    line_amplitude = rng.uniform(*noise_config["line_noise_uv"], channel_count).astype(np.float32)
    line_amplitude[qc_plan["line_noise_channels"]] = rng.uniform(14, 26, len(qc_plan["line_noise_channels"]))
    region_index = np.asarray([0 if row["brain_region"] == "M1" else 1 for row in geometry], dtype=int)
    lfp_gain = rng.uniform(0.78, 1.18, channel_count).astype(np.float32)
    clipped_by_channel = np.zeros(channel_count, dtype=np.int64)
    with path.open("wb", buffering=1024 * 1024 * 16) as handle:
        for sample_start in range(0, total_samples, chunk_samples):
            count = min(chunk_samples, total_samples - sample_start)
            raw_uv = background_chunk(rng, sample_start, count, channel_count, sampling_rate, normal_rms, line_amplitude)
            lfp_indices = np.minimum((sample_start + np.arange(count, dtype=np.int64)) // ratio, lfp.shape[1] - 1)
            for region in (0, 1):
                channels = np.flatnonzero(region_index == region)
                raw_uv[:, channels] += lfp[region, lfp_indices, None] * lfp_gain[channels][None, :]
            _add_spikes(raw_uv, sample_start, sampling_rate, duration_seconds, units, spikes, templates, channel_count, units[0]["electrode_type"])
            apply_artifacts(raw_uv, sample_start, sampling_rate, qc_plan)
            for channel in qc_plan["dead_channels"]:
                raw_uv[:, channel] = rng.normal(0, 0.8, count).astype(np.float32)
            converted = np.clip(np.rint(raw_uv / scale_uv_per_bit), -32760, 32760).astype(np.int16)
            clipped_by_channel += np.count_nonzero(np.abs(converted.astype(np.int32)) >= 32760, axis=0)
            converted.tofile(handle)
            if progress and (sample_start == 0 or sample_start + count == total_samples or (sample_start // chunk_samples) % 12 == 0):
                progress(f"raw {100 * (sample_start + count) / total_samples:5.1f}%")
    return {
        "sample_count": total_samples,
        "bytes": path.stat().st_size,
        "normal_rms_uv": normal_rms.tolist(),
        "line_noise_amplitude_uv": line_amplitude.tolist(),
        "true_clipped_samples_by_channel": clipped_by_channel.tolist(),
    }
