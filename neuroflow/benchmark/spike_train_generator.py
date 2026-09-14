from __future__ import annotations

import numpy as np


def _renewal(rng: np.random.Generator, rate: float, duration: float, phenotype: str) -> np.ndarray:
    shape = 2.2 if phenotype == "regular-spiking-like" else 1.0
    expected = int(rate * duration * 1.35 + 200)
    intervals = rng.gamma(shape, 1.0 / (max(rate, 0.01) * shape), expected)
    times = np.cumsum(intervals)
    while times.size == 0 or times[-1] < duration:
        extra = rng.gamma(shape, 1.0 / (max(rate, 0.01) * shape), max(expected // 3, 200))
        times = np.concatenate((times, times[-1] + np.cumsum(extra)))
    return times[times < duration]


def _enforce_refractory(times: np.ndarray, refractory: float = 0.0012) -> np.ndarray:
    times = np.sort(times[(times > 0.04)])
    if not len(times):
        return times
    keep = np.r_[True, np.diff(times) >= refractory]
    return times[keep]


def generate_spike_trains(
    rng: np.random.Generator,
    units: list[dict],
    trials: list[dict],
    duration_seconds: float,
) -> dict[int, np.ndarray]:
    result: dict[int, np.ndarray] = {}
    for unit in units:
        rate = unit["baseline_firing_rate_hz"]
        times = _renewal(rng, rate, duration_seconds, unit["firing_phenotype"])
        drift = 1.0 + unit["baseline_drift_fraction"] * (times / duration_seconds - 0.5) * 2
        times = times[rng.random(len(times)) < np.clip(drift, 0.72, 1.0)]
        if unit["firing_phenotype"] == "bursting" and len(times):
            seeds = times[rng.random(len(times)) < 0.10]
            burst = np.concatenate([seeds + rng.uniform(0.0022, 0.006, len(seeds)), seeds + rng.uniform(0.007, 0.014, len(seeds))])
            times = np.concatenate((times, burst))
        locked: list[np.ndarray] = []
        suppress_windows: list[tuple[float, float]] = []
        for trial in trials:
            lever = trial["lever_press_time_sec"]
            reward = trial["reward_time_sec"]
            amplitude = unit["response_gain"] * float(rng.lognormal(0, 0.28))
            latency = unit["response_latency_sec"] + float(rng.normal(0, 0.035))
            response_duration = max(0.12, unit["response_duration_sec"] + float(rng.normal(0, 0.10)))
            if unit["lever_modulation_type"] == "excited":
                count = int(rng.poisson(max(amplitude * response_duration, 0.2)))
                locked.append(lever + latency + rng.beta(2, 5, count) * response_duration)
            elif unit["lever_modulation_type"] == "suppressed":
                suppress_windows.append((lever - 0.05, lever + response_duration))
            reward_type = unit["reward_modulation_type"]
            if reward_type == "anticipatory_excited":
                onset = reward + unit["reward_anticipation_onset_sec"] + float(rng.normal(0, 0.08))
                width = max(reward - onset + 0.18, 0.3)
                count = int(rng.poisson(max(amplitude * width, 0.2)))
                locked.append(onset + rng.beta(3.2, 1.7, count) * width)
            elif reward_type == "delivery_excited":
                count = int(rng.poisson(max(amplitude * response_duration, 0.2)))
                locked.append(reward + latency + rng.beta(2, 5, count) * response_duration)
            elif reward_type == "delivery_suppressed":
                suppress_windows.append((reward - 0.05, reward + response_duration))
        for start, stop in suppress_windows:
            in_window = (times >= start) & (times <= stop)
            remove = in_window & (rng.random(len(times)) < 0.78)
            times = times[~remove]
        if locked:
            valid = [row[(row > 0.04) & (row < duration_seconds - 0.04)] for row in locked if len(row)]
            if valid:
                times = np.concatenate((times, *valid))
        times = _enforce_refractory(times[times < duration_seconds - 0.04])
        result[int(unit["unit_id"])] = times.astype(np.float64)
        unit["true_spike_count"] = int(len(times))
        unit["mean_firing_rate_hz"] = float(len(times) / duration_seconds)
        isi = np.diff(times)
        unit["refractory_violation_rate"] = float(np.mean(isi < 0.002)) if len(isi) else 0.0
    return result
