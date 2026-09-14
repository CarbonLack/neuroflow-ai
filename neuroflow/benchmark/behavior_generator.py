from __future__ import annotations

import numpy as np


def generate_behavior(
    rng: np.random.Generator,
    session_id: str,
    duration_seconds: float,
    trial_range: tuple[int, int],
    sampling_rate: float,
    latency: dict,
) -> tuple[list[dict], list[dict]]:
    trial_count = int(rng.integers(trial_range[0], trial_range[1] + 1))
    margin = 12.0
    nominal = np.linspace(margin, duration_seconds - margin - latency["max_sec"], trial_count)
    jitter_sd = min(2.8, max((duration_seconds - 2 * margin) / trial_count * 0.13, 0.5))
    lever = np.sort(nominal + rng.normal(0, jitter_sd, trial_count))
    lever = np.clip(lever, margin, duration_seconds - margin - latency["max_sec"])
    reward_latency = np.clip(
        rng.normal(latency["mean_sec"], latency["sd_sec"], trial_count),
        latency["min_sec"], latency["max_sec"],
    )
    reward = lever + reward_latency
    trials: list[dict] = []
    events: list[dict] = []
    for index, (lever_time, reward_time, delay) in enumerate(zip(lever, reward, reward_latency, strict=True), 1):
        lever_sample = int(round(float(lever_time) * sampling_rate))
        reward_sample = int(round(float(reward_time) * sampling_rate))
        lever_time = lever_sample / sampling_rate
        reward_time = reward_sample / sampling_rate
        trial = {
            "session_id": session_id, "trial_id": index,
            "lever_press_time_sec": lever_time, "reward_time_sec": reward_time,
            "reward_latency_sec": reward_time - lever_time,
            "lever_sample": lever_sample, "reward_sample": reward_sample,
        }
        trials.append(trial)
        events.extend([
            {"session_id": session_id, "trial": index, "event_type": "lever_press", "time_seconds": lever_time, "sample_index": lever_sample},
            {"session_id": session_id, "trial": index, "event_type": "reward_delivery", "time_seconds": reward_time, "sample_index": reward_sample},
        ])
    events.sort(key=lambda row: row["sample_index"])
    return trials, events
