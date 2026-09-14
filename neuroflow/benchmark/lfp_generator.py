from __future__ import annotations

import numpy as np
from scipy import signal


def generate_lfp(
    rng: np.random.Generator,
    duration_seconds: float,
    sampling_rate: float,
    trials: list[dict],
) -> np.ndarray:
    count = int(round(duration_seconds * sampling_rate))
    time = np.arange(count, dtype=np.float64) / sampling_rate
    regions = np.empty((2, count), dtype=np.float32)
    for region in range(2):
        white = rng.standard_normal(count, dtype=np.float32)
        slow = signal.lfilter([1.0], [1.0, -0.995], white).astype(np.float32)
        slow /= max(float(np.std(slow)), 1e-6)
        phase = rng.uniform(0, 2 * np.pi, 5)
        base = 24.0 * slow
        base += 12.0 * np.sin(2 * np.pi * 2.2 * time + phase[0])
        base += 8.0 * np.sin(2 * np.pi * 7.5 * time + phase[1])
        base += 4.0 * np.sin(2 * np.pi * 11.0 * time + phase[2])
        base += 3.0 * np.sin(2 * np.pi * 32.0 * time + phase[3])
        base += 2.0 * np.sin(2 * np.pi * 70.0 * time + phase[4])
        regions[region] = base.astype(np.float32)
    for trial in trials:
        lever = trial["lever_press_time_sec"]
        reward = trial["reward_time_sec"]
        for event_time, kind in ((lever, "lever"), (reward, "reward")):
            start = max(int((event_time - 1.5) * sampling_rate), 0)
            stop = min(int((event_time + 1.8) * sampling_rate), count)
            local = time[start:stop] - event_time
            if kind == "lever":
                envelope = np.exp(-0.5 * (local / 0.55) ** 2)
                regions[0, start:stop] += (5.0 * envelope * np.sin(2 * np.pi * 22 * local)).astype(np.float32)
            else:
                erp = -10.0 * np.exp(-0.5 * ((local - 0.08) / 0.12) ** 2)
                gamma = 4.5 * np.exp(-0.5 * (local / 0.45) ** 2) * np.sin(2 * np.pi * 62 * local)
                regions[1, start:stop] += (erp + gamma).astype(np.float32)
    return regions
