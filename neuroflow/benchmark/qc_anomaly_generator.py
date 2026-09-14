from __future__ import annotations

import numpy as np


def generate_qc_plan(
    rng: np.random.Generator,
    session_id: str,
    electrode: str,
    channel_count: int,
    duration_seconds: float,
    config: dict,
    force_lightweight_coverage: bool = False,
) -> tuple[dict, list[dict]]:
    issue_rows: list[dict] = []
    high_count = int(rng.integers(config["high_noise_channels"][0], config["high_noise_channels"][1] + 1))
    if force_lightweight_coverage:
        high_count = max(high_count, 1)
    high_noise = sorted(rng.choice(channel_count, high_count, replace=False).astype(int).tolist()) if high_count else []
    remaining = [value for value in range(channel_count) if value not in high_noise]
    dead = []
    if rng.random() < config["dead_channel_probability"] or force_lightweight_coverage:
        dead = [int(rng.choice(remaining))]
        remaining.remove(dead[0])
    line_count = int(rng.integers(config["line_noise_channels"][0], config["line_noise_channels"][1] + 1))
    if force_lightweight_coverage:
        line_count = max(line_count, 1)
    line_channels = sorted(rng.choice(remaining, min(line_count, len(remaining)), replace=False).astype(int).tolist())
    transient_count = int(rng.integers(config["transient_artifacts"][0], config["transient_artifacts"][1] + 1))
    transient_count = max(transient_count, 1) if force_lightweight_coverage else transient_count
    transients = []
    for index in range(transient_count):
        start = float(rng.uniform(8, duration_seconds - 8))
        duration = float(rng.uniform(0.02, 0.30))
        width = int(rng.integers(1, min(10 if electrode == "neuropixels" else 4, channel_count) + 1))
        first = int(rng.integers(0, channel_count - width + 1))
        transients.append({"start_time": start, "end_time": start + duration, "channels": list(range(first, first + width)), "amplitude_uv": float(rng.uniform(350, 900)), "artifact_type": "movement_transient"})
    baseline_shifts = []
    if rng.random() < config["baseline_shift_probability"]:
        start = float(rng.uniform(20, duration_seconds - 20))
        baseline_shifts.append({"start_time": start, "end_time": start + float(rng.uniform(0.2, 1.8)), "channels": [int(rng.integers(0, channel_count))], "amplitude_uv": float(rng.uniform(80, 240)), "artifact_type": "electrode_pop"})
    common_mode = []
    if rng.random() < config["common_mode_probability"]:
        start = float(rng.uniform(20, duration_seconds - 20))
        common_mode.append({"start_time": start, "end_time": start + float(rng.uniform(0.05, 0.15)), "channels": list(range(channel_count)), "amplitude_uv": float(rng.uniform(180, 420)), "artifact_type": "common_mode"})
    clipping = []
    if rng.random() < config["clipping_probability"]:
        start = float(rng.uniform(30, duration_seconds - 30))
        clipping.append({"start_time": start, "end_time": start + float(rng.uniform(0.004, 0.025)), "channels": [int(rng.choice(remaining))], "amplitude_uv": 7000.0, "artifact_type": "mild_clipping"})
    drift = float(rng.uniform(*config["drift_level"]))
    for channel in high_noise:
        issue_rows.append({"session_id": session_id, "channel_id": channel, "qc_issue_type": "high_noise", "start_time": 0.0, "end_time": duration_seconds, "severity": "moderate", "expected_metric_change": "RMS 35-60 uV"})
    for channel in dead:
        issue_rows.append({"session_id": session_id, "channel_id": channel, "qc_issue_type": "near_dead", "start_time": 0.0, "end_time": duration_seconds, "severity": "moderate", "expected_metric_change": "variance below 10% of median"})
    for channel in line_channels:
        issue_rows.append({"session_id": session_id, "channel_id": channel, "qc_issue_type": "line_noise", "start_time": 0.0, "end_time": duration_seconds, "severity": "moderate", "expected_metric_change": "50 Hz PSD peak above neighbors"})
    for item in [*transients, *baseline_shifts, *common_mode, *clipping]:
        issue_rows.append({"session_id": session_id, "channel_id": ";".join(map(str, item["channels"])), "qc_issue_type": item["artifact_type"], "start_time": item["start_time"], "end_time": item["end_time"], "severity": "mild" if item["artifact_type"] == "mild_clipping" else "moderate", "expected_metric_change": f"transient amplitude about {item['amplitude_uv']:.1f} uV"})
    issue_rows.append({"session_id": session_id, "channel_id": "unit-dependent", "qc_issue_type": "slow_drift", "start_time": 0.0, "end_time": duration_seconds, "severity": "mild", "expected_metric_change": f"amplitude/spatial drift fraction {drift:.4f}"})
    plan = {"high_noise_channels": high_noise, "dead_channels": dead, "line_noise_channels": line_channels, "transients": transients, "baseline_shifts": baseline_shifts, "common_mode": common_mode, "clipping": clipping, "drift_fraction": drift}
    return plan, issue_rows
