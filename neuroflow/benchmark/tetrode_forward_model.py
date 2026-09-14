from __future__ import annotations

import numpy as np


def channel_geometry(channel_count: int = 32) -> list[dict]:
    rows = []
    offsets = [(-10, -10), (10, -10), (-10, 10), (10, 10)]
    for channel in range(channel_count):
        tetrode = channel // 4
        x, y = offsets[channel % 4]
        rows.append({
            "channel_id": channel, "tetrode_id": f"T{tetrode + 1:02d}",
            "wire_id": channel % 4 + 1, "brain_region": "M1" if tetrode < 4 else "mPFC",
            "depth_um": float((tetrode % 4) * 250 + 500), "x_position_um": float(tetrode * 180 + x),
            "y_position_um": float(y), "gain": 1000.0,
            "voltage_scaling_factor_uv_per_bit": 0.195,
        })
    return rows


def spatial_weights(peak_channel: int, channel_count: int) -> tuple[np.ndarray, np.ndarray]:
    start = (peak_channel // 4) * 4
    channels = np.arange(start, min(start + 4, channel_count))
    base = np.array([1.0, 0.72, 0.48, 0.83])
    weights = np.roll(base, peak_channel % 4)[: len(channels)]
    return channels.astype(int), weights / weights.max()
