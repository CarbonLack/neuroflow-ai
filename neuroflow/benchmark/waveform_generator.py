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
        # Calibrated against 87 negative-dominant real units exported from two
        # independent Kilosort sessions.  These ranges target a 0.13--0.33 ms
        # negative half-width and a 0.46--0.60 ms trough-to-positive-peak delay.
        trough_width = float(rng.uniform(0.045, 0.082) if narrow else rng.uniform(0.058, 0.122))
        rebound_width = float(rng.uniform(0.12, 0.24))
        rebound_delay = float(rng.uniform(0.44, 0.64))
        amplitude = float(rng.uniform(38, 105) if unit["sorting_difficulty"] == "low_snr" else rng.uniform(75, 285))
        family = str(rng.choice(
            ["somatic_biphasic", "triphasic", "broad_somatic", "axonal_like"],
            p=[0.50, 0.24, 0.20, 0.06],
        ))
        pre_gain = float(rng.uniform(0.07, 0.22))
        post_gain = float(rng.uniform(0.14, 0.34))
        if family == "triphasic":
            pre_gain = float(rng.uniform(0.20, 0.38))
        elif family == "broad_somatic":
            trough_width *= float(rng.uniform(1.18, 1.48))
            rebound_width *= float(rng.uniform(1.05, 1.30))
        elif family == "axonal_like":
            trough_width *= 0.72
            pre_gain = float(rng.uniform(0.32, 0.58))
            post_gain = float(rng.uniform(0.08, 0.22))

        pre_delay = float(rng.uniform(0.27, 0.42))
        pre_width = float(rng.uniform(0.065, 0.115))
        slow_gain = float(rng.uniform(0.012, 0.055))

        def temporal_shape(time: np.ndarray, stretch: float = 1.0) -> np.ndarray:
            pre = pre_gain * np.exp(-0.5 * ((time + pre_delay * stretch) / (pre_width * stretch)) ** 2)
            trough = -np.exp(-0.5 * (time / (trough_width * stretch)) ** 2)
            rebound = post_gain * np.exp(-0.5 * ((time - rebound_delay * stretch) / (rebound_width * stretch)) ** 2)
            slow = -slow_gain * np.exp(-0.5 * ((time - 1.05 * stretch) / (0.42 * stretch)) ** 2)
            return pre + trough + rebound + slow

        channels, weights = model.spatial_weights(unit["peak_channel"], channel_count)
        if electrode == "tetrode":
            weights = rng.lognormal(-0.38, 0.55, len(channels))
            weights[int(np.flatnonzero(channels == unit["peak_channel"])[0])] = 1.0
            weights = np.clip(weights / weights.max(), 0.12, 1.0)
        else:
            weights = weights * rng.lognormal(0.0, 0.12, len(weights))
            weights /= weights.max()
        channel_delays = rng.normal(0.0, 0.018 if electrode == "tetrode" else 0.028, len(channels))
        channel_delays += (channels - unit["peak_channel"]) * (0.006 if electrode == "neuropixels" else 0.0)

        variants = []
        for stretch in (0.90, 1.0, 1.12):
            for phase_samples in (-0.34, 0.0, 0.34):
                phase_ms = phase_samples / sampling_rate * 1000.0
                template = np.column_stack([
                    temporal_shape(x - channel_delays[local] - phase_ms, stretch) * weights[local] * amplitude
                    for local in range(len(channels))
                ])
                # Contact-specific roughness represents tiny filtering and
                # impedance differences; acquisition noise is added later.
                template += rng.normal(0.0, amplitude * 0.004, template.shape)
                variants.append(template.astype(np.float32))
        variants_array = np.stack(variants)
        template = variants_array[4]
        result[int(unit["unit_id"])] = {
            "channels": channels, "waveform_uv": template,
            "variants_uv": variants_array,
        }
        unit["waveform_family"] = family
        unit["waveform_amplitude_cv"] = float(rng.uniform(0.06, 0.15))
        unit["peak_amplitude_uv"] = amplitude
        unit["trough_to_peak_ms"] = rebound_delay
        unit["waveform_width_ms"] = trough_width * 2.355
        unit["spatial_footprint"] = channels.tolist()
        unit["spatial_weights"] = weights.tolist()
        unit["snr_target"] = float(amplitude / rng.uniform(12, 22))
    return result
