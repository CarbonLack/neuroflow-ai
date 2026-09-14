from __future__ import annotations

import numpy as np


def apply_artifacts(raw_uv: np.ndarray, sample_start: int, sampling_rate: float, plan: dict) -> None:
    sample_stop = sample_start + len(raw_uv)
    for item in [*plan["transients"], *plan["baseline_shifts"], *plan["common_mode"], *plan["clipping"]]:
        event_start = int(round(item["start_time"] * sampling_rate))
        event_stop = int(round(item["end_time"] * sampling_rate))
        left, right = max(sample_start, event_start), min(sample_stop, event_stop)
        if left >= right:
            continue
        local = np.arange(left, right) - event_start
        length = max(event_stop - event_start, 1)
        if item["artifact_type"] == "electrode_pop":
            shape = np.exp(-4.0 * local / length)
        elif item["artifact_type"] == "mild_clipping":
            shape = np.ones(len(local))
        else:
            shape = np.sin(np.pi * (local + 1) / (length + 1))
        rows = slice(left - sample_start, right - sample_start)
        raw_uv[rows, item["channels"]] += (item["amplitude_uv"] * shape[:, None]).astype(np.float32)
