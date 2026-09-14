from __future__ import annotations

import numpy as np


def background_chunk(
    rng: np.random.Generator,
    sample_start: int,
    sample_count: int,
    channel_count: int,
    sampling_rate: float,
    normal_rms_uv: np.ndarray,
    line_amplitude_uv: np.ndarray,
) -> np.ndarray:
    raw = rng.standard_normal((sample_count, channel_count), dtype=np.float32)
    raw *= normal_rms_uv[None, :]
    time = (sample_start + np.arange(sample_count, dtype=np.float64)) / sampling_rate
    line = (
        np.sin(2 * np.pi * 50 * time)[:, None]
        + 0.28 * np.sin(2 * np.pi * 100 * time + 0.3)[:, None]
        + 0.12 * np.sin(2 * np.pi * 150 * time + 0.7)[:, None]
    )
    raw += (line * line_amplitude_uv[None, :]).astype(np.float32)
    return raw
