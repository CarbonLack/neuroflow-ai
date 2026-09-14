from __future__ import annotations

import numpy as np


def channel_geometry(channel_count: int) -> list[dict]:
    half = channel_count // 2
    rows = []
    for channel in range(channel_count):
        local = channel if channel < half else channel - half
        rows.append({
            "channel_id": channel, "probe_id": "Probe_A" if channel < half else "Probe_B",
            "brain_region": "M1" if channel < half else "mPFC",
            "depth_um": float((local // 2) * 20), "x_position_um": float((local % 2) * 32),
            "y_position_um": float((local // 2) * 20), "gain": 500.0,
            "voltage_scaling_factor_uv_per_bit": 0.195,
        })
    return rows


def spatial_weights(peak_channel: int, channel_count: int, width: float = 1.8) -> tuple[np.ndarray, np.ndarray]:
    region_start = 0 if peak_channel < channel_count // 2 else channel_count // 2
    region_stop = channel_count // 2 if peak_channel < channel_count // 2 else channel_count
    channels = np.arange(max(region_start, peak_channel - 4), min(region_stop, peak_channel + 5))
    weights = np.exp(-np.abs(channels - peak_channel) / width)
    return channels.astype(int), weights / weights.max()
