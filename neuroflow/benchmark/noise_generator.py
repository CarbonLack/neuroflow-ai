from __future__ import annotations

import numpy as np


def _add_far_unit_background(
    raw: np.ndarray,
    rng: np.random.Generator,
    sampling_rate: float,
    rate_range: tuple[float, float],
    amplitude_range: tuple[float, float],
) -> None:
    """Add unresolved multi-unit activity without creating sortable GT units."""
    x = np.arange(31, dtype=np.float32)
    kernel = (
        0.16 * np.exp(-0.5 * ((x - 6.0) / 1.25) ** 2)
        - np.exp(-0.5 * ((x - 10.0) / 1.75) ** 2)
        + 0.28 * np.exp(-0.5 * ((x - 16.0) / 3.0) ** 2)
    ).astype(np.float32)
    offsets = np.arange(len(kernel), dtype=np.int64) - 10
    for first in range(0, raw.shape[1], 4):
        width = min(4, raw.shape[1] - first)
        event_count = int(rng.poisson(rng.uniform(*rate_range) * len(raw) / sampling_rate))
        if not event_count:
            continue
        centers = rng.integers(10, max(11, len(raw) - 21), event_count)
        indices = centers[:, None] + offsets[None, :]
        amplitudes = rng.uniform(*amplitude_range, event_count).astype(np.float32)
        # Most far neurons are visible on multiple nearby contacts, but with an
        # irregular footprint and low enough SNR not to become benchmark units.
        weights = rng.lognormal(-0.25, 0.48, (event_count, width)).astype(np.float32)
        weights /= np.maximum(weights.max(axis=1, keepdims=True), 1e-6)
        signs = np.where(rng.random((event_count, 1)) < 0.04, -1.0, 1.0).astype(np.float32)
        for local in range(width):
            values = amplitudes[:, None] * weights[:, local, None] * signs * kernel[None, :]
            np.add.at(raw[:, first + local], indices.ravel(), values.ravel())


def background_chunk(
    rng: np.random.Generator,
    sample_start: int,
    sample_count: int,
    channel_count: int,
    sampling_rate: float,
    normal_rms_uv: np.ndarray,
    line_amplitude_uv: np.ndarray,
    noise_config: dict | None = None,
) -> np.ndarray:
    raw = rng.standard_normal((sample_count, channel_count), dtype=np.float32)
    raw *= normal_rms_uv[None, :]
    if noise_config:
        group_count = int(np.ceil(channel_count / 4))
        local = rng.standard_normal((sample_count, group_count), dtype=np.float32)
        fraction = rng.uniform(*noise_config.get("local_correlation_fraction", [0.08, 0.22]), group_count).astype(np.float32)
        raw += np.repeat(local * fraction[None, :] * np.median(normal_rms_uv), 4, axis=1)[:, :channel_count]
        _add_far_unit_background(
            raw, rng, sampling_rate,
            tuple(noise_config.get("far_unit_rate_hz_per_4_channels", [45.0, 95.0])),
            tuple(noise_config.get("far_unit_amplitude_uv", [5.0, 26.0])),
        )
    time = (sample_start + np.arange(sample_count, dtype=np.float64)) / sampling_rate
    line = (
        np.sin(2 * np.pi * 50 * time)[:, None]
        + 0.28 * np.sin(2 * np.pi * 100 * time + 0.3)[:, None]
        + 0.12 * np.sin(2 * np.pi * 150 * time + 0.7)[:, None]
    )
    raw += (line * line_amplitude_uv[None, :]).astype(np.float32)
    return raw
