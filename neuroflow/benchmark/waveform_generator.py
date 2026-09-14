from __future__ import annotations

import numpy as np

from . import neuropixels_forward_model, tetrode_forward_model


def generate_templates(
    rng: np.random.Generator,
    units: list[dict],
    electrode: str,
    channel_count: int,
    sampling_rate: float,
) -> dict[int, dict]:
    sample_count = 91
    x = (np.arange(sample_count) - 36) / sampling_rate * 1000.0
    result: dict[int, dict] = {}
    model = neuropixels_forward_model if electrode == "neuropixels" else tetrode_forward_model
    for unit in units:
        narrow = unit["firing_phenotype"] == "fast-spiking-like"
        trough_width = float(rng.uniform(0.10, 0.20) if narrow else rng.uniform(0.18, 0.34))
        rebound_width = float(rng.uniform(0.24, 0.48))
        rebound_delay = float(rng.uniform(0.32, 0.58))
        amplitude = float(rng.uniform(45, 115) if unit["sorting_difficulty"] == "low_snr" else rng.uniform(85, 320))
        temporal = -np.exp(-0.5 * (x / trough_width) ** 2)
        temporal += float(rng.uniform(0.18, 0.45)) * np.exp(-0.5 * ((x - rebound_delay) / rebound_width) ** 2)
        channels, weights = model.spatial_weights(unit["peak_channel"], channel_count)
        template = temporal[:, None] * weights[None, :] * amplitude
        template *= rng.normal(1.0, 0.035, template.shape)
        result[int(unit["unit_id"])] = {"channels": channels, "waveform_uv": template.astype(np.float32)}
        unit["peak_amplitude_uv"] = amplitude
        unit["trough_to_peak_ms"] = rebound_delay
        unit["waveform_width_ms"] = trough_width * 2.355
        unit["spatial_footprint"] = channels.tolist()
        unit["spatial_weights"] = weights.tolist()
        unit["snr_target"] = float(amplitude / rng.uniform(12, 22))
    return result
