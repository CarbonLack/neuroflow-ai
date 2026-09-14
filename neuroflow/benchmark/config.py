from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 2,
    "seed": 20260914,
    "sampling_rate_hz": 30_000,
    "lfp_sampling_rate_hz": 1_000,
    "scale_uv_per_bit": 0.195,
    "chunk_seconds": 10,
    "reward_latency": {"mean_sec": 3.0, "sd_sec": 0.5, "min_sec": 2.0, "max_sec": 4.0},
    "lightweight": {"sessions": 2, "duration_seconds": [180, 240], "trial_range": [14, 20]},
    "full": {"sessions": 7, "duration_seconds": 1200, "trial_range": [50, 70]},
    "neuropixels": {
        "channels": 128,
        "lightweight_channels": 64,
        "regions": ["M1", "mPFC"],
        "units_per_region": {"M1": [50, 100], "mPFC": [40, 90]},
        "lightweight_units_per_region": {"M1": [18, 28], "mPFC": [16, 26]},
        "acquisition_profiles": ["SpikeGLX-like", "Open Ephys-like"],
    },
    "tetrode": {
        "channels": 32,
        "lightweight_channels": 32,
        "tetrodes": 8,
        "regions": ["M1", "mPFC"],
        "units_per_region": {"M1": [8, 20], "mPFC": [8, 20]},
        "lightweight_units_per_region": {"M1": [6, 10], "mPFC": [6, 10]},
        "acquisition_profiles": ["Open Ephys-like", "Neuralynx/Plexon-like binary"],
    },
    "neuron_class_proportions": {
        "M1": {"lever": 0.40, "reward_anticipation": 0.08, "reward_delivery": 0.08, "mixed": 0.19, "nonresponsive": 0.25},
        "mPFC": {"lever": 0.20, "reward_anticipation": 0.20, "reward_delivery": 0.15, "mixed": 0.27, "nonresponsive": 0.18},
    },
    "firing_rate_hz": {"min": 0.5, "max": 25.0, "fast_spiking_max": 38.0},
    "noise": {
        "normal_rms_uv": [12.0, 21.0], "line_noise_uv": [2.0, 5.0],
        "far_unit_rate_hz_per_4_channels": [45.0, 95.0],
        "far_unit_amplitude_uv": [5.0, 26.0],
        "local_correlation_fraction": [0.08, 0.22],
    },
    "qc": {
        "high_noise_channels": [0, 2], "line_noise_channels": [1, 2],
        "dead_channel_probability": 0.42, "transient_artifacts": [2, 5],
        "baseline_shift_probability": 0.55, "common_mode_probability": 0.5,
        "clipping_probability": 0.36, "drift_level": [0.03, 0.16],
    },
}


def load_config(path: Path | None = None) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    if path is None:
        return config
    supplied = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    def merge(target: dict, source: dict) -> None:
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                merge(target[key], value)
            else:
                target[key] = value

    merge(config, supplied)
    return config


def save_config(config: dict[str, Any], path: Path) -> None:
    path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
