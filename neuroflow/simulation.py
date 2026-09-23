from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from .models import ProjectState

DEMO_PROFILES = {
    "neuropixels_decision": {
        "name": "Neuropixels-like two-choice task",
        "name_zh": "Neuropixels 类高密度探针 · 二选一任务",
        "folder": "Neuropixels_Decision",
        "electrode_family": "Neuropixels-like staggered linear probe",
        "channel_count": 32,
        "sampling_rate": 30_000.0,
        "behavior_paradigm": "two-choice decision task",
        "behavior_paradigm_zh": "二选一决策任务",
        "conditions": ("left", "right"),
        "epoch_names": ("Quiet", "Movement", "Reward"),
        "unit_count": 18,
        "recommended_sorters": ("Kilosort4", "SpyKING CIRCUS 2"),
        "scenario": (
            "High-density event responses, probe drift, a noisy channel, "
            "choice, outcome, reaction time, behavior-clock drift, and TTL jitter."
        ),
        "scenario_zh": "高密度事件响应、探针漂移、噪声通道、选择、结果、反应时、行为时钟漂移与 TTL 抖动。",
    },
    "tetrode_navigation": {
        "name": "Tetrode array navigation and reward",
        "name_zh": "Tetrode 阵列 · 空间探索与奖励",
        "folder": "Tetrode_Navigation",
        "electrode_family": "Tetrode array (4 tetrodes)",
        "channel_count": 16,
        "sampling_rate": 30_000.0,
        "behavior_paradigm": "open-field reward-zone navigation",
        "behavior_paradigm_zh": "开放场奖励区导航",
        "conditions": ("reward_zone", "control_zone"),
        "epoch_names": ("Forage", "Approach", "Reward"),
        "unit_count": 14,
        "recommended_sorters": ("MountainSort5", "Tridesclous2"),
        "scenario": (
            "Four spatially separated tetrodes with position, speed, reward-zone "
            "events, reaction latency, behavior-clock drift, and TTL jitter."
        ),
        "scenario_zh": "四组空间分离 tetrode，包含位置、速度、奖励区事件、反应延迟、行为时钟漂移与 TTL 抖动。",
    },
    "microwire_stimulus": {
        "name": "32-channel independent microwire/brush sensory task",
        "name_zh": "32 通道独立微丝/brush 电极 · 感觉刺激任务",
        "folder": "Microwire_Stimulus",
        "electrode_family": "Independent microwire array",
        "channel_count": 32,
        "sampling_rate": 25_000.0,
        "behavior_paradigm": "tone discrimination and licking",
        "behavior_paradigm_zh": "音调辨别与舔舐",
        "conditions": ("tone_low", "tone_high"),
        "epoch_names": ("Baseline", "Tone", "Consumption"),
        "unit_count": 20,
        "recommended_sorters": ("WaveClus", "MountainSort5", "SpikeInterface Simple"),
        "scenario": (
            "Thirty-two spatially independent brush/microwire contacts with tone "
            "identity, lick count, hit/miss outcome, behavior-clock drift, and TTL jitter."
        ),
        "scenario_zh": "32 根空间关系未知的独立 brush/微丝，包含音调、舔舐次数、正确/错误结果、行为时钟漂移与 TTL 抖动。",
    },
}


def demo_profile_catalog() -> list[dict]:
    return [
        {"key": key, **value}
        for key, value in DEMO_PROFILES.items()
    ]


def _contact_positions(profile_key: str, channel_count: int) -> np.ndarray:
    if profile_key == "tetrode_navigation":
        positions = []
        offsets = ((-10, -10), (10, -10), (-10, 10), (10, 10))
        for channel in range(channel_count):
            group = channel // 4
            offset_x, offset_y = offsets[channel % 4]
            positions.append((group * 180 + offset_x, offset_y))
        return np.asarray(positions, dtype=float)
    if profile_key == "microwire_stimulus":
        return np.asarray(
            [(channel * 200.0, (channel % 2) * 40.0) for channel in range(channel_count)],
            dtype=float,
        )
    rows = np.arange(channel_count)
    return np.column_stack(((rows % 2) * 32.0, (rows // 2) * 20.0))


def _poisson_spikes(
    rng: np.random.Generator,
    rate_hz: float,
    duration: float,
    refractory: float = 0.0015,
) -> np.ndarray:
    if rate_hz <= 0:
        return np.empty(0, dtype=np.float64)
    values: list[float] = []
    t = float(rng.exponential(1.0 / rate_hz))
    while t < duration:
        values.append(t)
        t += refractory + float(rng.exponential(1.0 / rate_hz))
    return np.asarray(values, dtype=np.float64)


def _enforce_refractory(times: np.ndarray, refractory: float = 0.0012) -> np.ndarray:
    if times.size == 0:
        return times
    times = np.unique(np.sort(times))
    keep = np.ones(times.size, dtype=bool)
    keep[1:] = np.diff(times) >= refractory
    return times[keep]


def simulate_sorter_output(
    ground_truth: dict[int, np.ndarray],
    duration_seconds: float,
    *,
    seed: int,
    native_id_offset: int = 100,
    recall_range: tuple[float, float] = (0.78, 0.94),
    false_positive_fraction: tuple[float, float] = (0.03, 0.11),
    jitter_seconds: float = 0.00012,
) -> dict[int, np.ndarray]:
    """Create a realistic *imperfect* sorter result for teaching and demos.

    This is deliberately not a disguised copy of ground truth.  Each Unit has
    missed detections, timing jitter and false positives, and a small fraction
    of detections leak between neighboring Units.  Native IDs contain gaps so
    the application's continuous display-ID/provenance behavior is exercised.
    """
    rng = np.random.default_rng(seed)
    source_units = sorted(int(unit_id) for unit_id in ground_truth)
    results: dict[int, np.ndarray] = {}
    for position, unit_id in enumerate(source_units):
        truth = np.asarray(ground_truth[unit_id], dtype=np.float64)
        recall = float(rng.uniform(*recall_range))
        kept = truth[rng.random(truth.size) < recall]
        detected = kept + rng.normal(0.0, jitter_seconds, kept.size)

        false_fraction = float(rng.uniform(*false_positive_fraction))
        false_count = max(1, int(round(max(1, truth.size) * false_fraction)))
        false_spikes = rng.uniform(0.05, max(0.051, duration_seconds - 0.05), false_count)

        # Occasional cross-unit leakage models unresolved overlaps without
        # making every cluster equally poor.
        if len(source_units) > 1 and position % 4 == 1:
            neighbor = np.asarray(
                ground_truth[source_units[position - 1]], dtype=np.float64
            )
            leak_count = min(len(neighbor), max(1, int(0.025 * max(1, truth.size))))
            if leak_count:
                leaked = rng.choice(neighbor, size=leak_count, replace=False)
                detected = np.concatenate(
                    [detected, leaked + rng.normal(0.0, jitter_seconds, leak_count)]
                )

        combined = np.concatenate([detected, false_spikes])
        combined = combined[(combined > 0.0) & (combined < duration_seconds)]
        native_id = native_id_offset + position * 3 + (position % 2)
        results[native_id] = _enforce_refractory(combined, refractory=0.0007)
    return results


def generate_demo_recording(
    project_root: Path,
    seed: int = 20260724,
    duration_seconds: float = 60.0,
    channel_count: int | None = None,
    sampling_rate: float | None = None,
    profile_key: str = "neuropixels_decision",
) -> ProjectState:
    if profile_key not in DEMO_PROFILES:
        raise ValueError(f"Unknown demo profile: {profile_key}")
    profile = DEMO_PROFILES[profile_key]
    channel_count = int(channel_count or profile["channel_count"])
    sampling_rate = float(sampling_rate or profile["sampling_rate"])
    project_root.mkdir(parents=True, exist_ok=True)
    raw_dir = project_root / "raw"
    raw_dir.mkdir(exist_ok=True)
    recording_path = raw_dir / "neuroflow_simulated_recording.bin"
    metadata_path = raw_dir / "metadata.json"
    events_path = raw_dir / "events.csv"
    behavior_events_path = raw_dir / "behavior_events.csv"
    ttl_events_path = raw_dir / "ttl_events.csv"
    truth_path = raw_dir / "ground_truth.npz"
    respiration_path = raw_dir / "respiration_reference.npy"
    states_path = raw_dir / "behavioral_states.csv"
    import_config_path = raw_dir / "import_config.json"
    guide_path = project_root / "README_DATASET.md"

    rng = np.random.default_rng(seed)
    sample_count = int(duration_seconds * sampling_rate)
    scale_uv_per_bit = 0.195
    respiration_sampling_rate = 1_000.0
    respiration_count = int(duration_seconds * respiration_sampling_rate)
    respiration_time = np.arange(respiration_count) / respiration_sampling_rate
    epoch_edges = np.linspace(0.0, duration_seconds, 4)
    behavioral_state_epochs = [
        {
            "state": name,
            "start_seconds": float(epoch_edges[index]),
            "stop_seconds": float(epoch_edges[index + 1]),
            "nominal_respiration_hz": frequency,
        }
        for index, (name, frequency) in enumerate(
            zip(profile["epoch_names"], (2.2, 1.6, 4.2), strict=True)
        )
    ]
    instantaneous_frequency = np.zeros(respiration_count, dtype=float)
    for epoch in behavioral_state_epochs:
        mask = (respiration_time >= epoch["start_seconds"]) & (
            respiration_time < epoch["stop_seconds"]
        )
        instantaneous_frequency[mask] = float(epoch["nominal_respiration_hz"])
    respiration_phase = np.cumsum(2 * np.pi * instantaneous_frequency) / (
        respiration_sampling_rate
    )
    respiration_reference = (
        np.sin(respiration_phase)
        + 0.18 * np.sin(2 * respiration_phase + 0.4)
        + rng.normal(0.0, 0.08, respiration_count)
    )

    events: list[dict[str, object]] = []
    event_margin = min(3.0, duration_seconds * 0.2)
    # Keep enough trials for cross-validation and a non-degenerate ROC while
    # avoiding a dense, perfectly periodic synthetic design.
    event_count = max(8, min(48, int(duration_seconds / 1.2)))
    nominal_times = np.linspace(
        event_margin, duration_seconds - event_margin, event_count
    )
    event_jitter = rng.normal(0.0, min(0.12, duration_seconds / 500.0), event_count)
    event_times = np.sort(
        np.clip(nominal_times + event_jitter, event_margin, duration_seconds - event_margin)
    )
    behavior_clock_offset = 0.037
    behavior_clock_scale = 1.00018
    first_condition, second_condition = profile["conditions"]
    for index, event_time in enumerate(event_times):
        behavior_time = (event_time - behavior_clock_offset) / behavior_clock_scale
        ttl_time = float(event_time + rng.normal(0.0, 0.00018))
        condition = first_condition if index % 2 == 0 else second_condition
        reaction_time = float(
            np.clip(
                rng.normal(0.42 if index % 2 == 0 else 0.58, 0.07),
                0.15,
                1.2,
            )
        )
        outcome = "correct" if rng.random() > 0.18 else "error"
        choice = (
            condition
            if profile_key == "neuropixels_decision"
            else ("approach" if index % 2 == 0 else "withhold")
        )
        events.append(
            {
                "trial": index + 1,
                "time_seconds": float(event_time),
                "behavior_time_seconds": float(behavior_time),
                "ttl_time_seconds": ttl_time,
                "event_type": "stimulus_onset",
                "condition": condition,
                "choice": choice,
                "outcome": outcome,
                "reaction_time": reaction_time,
                "position_x_cm": float(rng.uniform(-45, 45)),
                "position_y_cm": float(rng.uniform(-45, 45)),
                "speed_cm_s": float(np.clip(rng.normal(16, 6), 0, 45)),
                "lick_count": int(rng.poisson(5 if outcome == "correct" else 2)),
            }
        )

    ground_truth: dict[int, np.ndarray] = {}
    unit_count = int(profile.get("unit_count", 12))
    base_rates = np.clip(
        rng.lognormal(mean=np.log(10.0), sigma=0.38, size=unit_count),
        4.0,
        24.0,
    ).tolist()
    for unit_id, base_rate in enumerate(base_rates):
        times = _poisson_spikes(rng, base_rate, duration_seconds)
        preferred = (
            first_condition
            if unit_id < max(3, unit_count // 3)
            else second_condition
            if unit_id < max(6, (2 * unit_count) // 3)
            else None
        )
        locked: list[np.ndarray] = []
        for event in events:
            # Preferred and non-preferred trials deliberately overlap. Trial-to-trial
            # gain variation, omissions, and low-rate non-preferred responses prevent
            # the unrealistically perfect triangular ROC seen in the old examples.
            is_preferred = preferred is not None and event["condition"] == preferred
            response_probability = 0.80 if is_preferred else 0.30
            if rng.random() > response_probability:
                continue
            response_gain = float(rng.lognormal(0.0, 0.42))
            mean_count = (2.10 if is_preferred else 0.50) * response_gain
            if event["outcome"] == "error":
                mean_count *= 0.72
            count = int(rng.poisson(mean_count))
            if count:
                locked.append(
                    float(event["time_seconds"])
                    + rng.normal(0.14, 0.065, size=count)
                )
        if locked:
            times = np.concatenate([times, *locked])
        if unit_id in {0, 1, 2}:
            phase_locked = []
            phase_fraction = {0: 0.12, 1: 0.42, 2: 0.72}[unit_id]
            for epoch in behavioral_state_epochs:
                frequency = float(epoch["nominal_respiration_hz"])
                cycles = np.arange(
                    float(epoch["start_seconds"]) + phase_fraction / frequency,
                    float(epoch["stop_seconds"]),
                    1.0 / frequency,
                )
                phase_locked.append(cycles + rng.normal(0.0, 0.012, len(cycles)))
            times = np.concatenate([times, *phase_locked])
        ground_truth[unit_id] = _enforce_refractory(
            times[(times > 0.05) & (times < duration_seconds - 0.05)]
        )

    raw = rng.normal(0.0, 21.0 / scale_uv_per_bit, size=(sample_count, channel_count))
    time_axis = np.arange(sample_count, dtype=np.float64) / sampling_rate
    respiration_raw = np.interp(
        time_axis, respiration_time, respiration_reference
    )
    gamma_strength = np.select(
        [
            time_axis < epoch_edges[1],
            time_axis < epoch_edges[2],
        ],
        [7.0, 2.8],
        default=4.2,
    )
    respiration_phase_raw = np.interp(
        time_axis, respiration_time, respiration_phase
    )
    gamma_envelope = gamma_strength * (1.0 + 0.42 * np.cos(respiration_phase_raw))
    common_noise = (
        5.0 * np.sin(2 * np.pi * 50.0 * time_axis)
        + 7.5 * respiration_raw
    ) / scale_uv_per_bit
    raw += common_noise[:, None]
    raw[:, : min(8, channel_count)] += (
        gamma_envelope[:, None]
        * np.sin(2 * np.pi * 90.0 * time_axis)[:, None]
        / scale_uv_per_bit
    )
    noisy_channel = min(29, channel_count - 1)
    raw[:, noisy_channel] += rng.normal(0.0, 55.0 / scale_uv_per_bit, size=sample_count)

    waveform_samples = 61
    half = waveform_samples // 2
    x_ms = (np.arange(waveform_samples, dtype=np.float64) - half) / sampling_rate * 1000.0
    if profile_key == "microwire_stimulus":
        unit_channels = rng.choice(
            np.arange(channel_count), size=len(base_rates), replace=False
        ).astype(int).tolist()
    else:
        unit_channels = np.linspace(
            1, max(1, channel_count - 2), len(base_rates), dtype=int
        ).tolist()
    unit_amplitudes = np.clip(
        rng.lognormal(mean=np.log(145.0), sigma=0.28, size=len(base_rates)),
        78.0,
        235.0,
    ).tolist()
    templates = {}
    for unit_id, center_channel in enumerate(unit_channels):
        narrow = unit_id in {1, 4, 7}
        trough_width = rng.uniform(0.055, 0.092) if narrow else rng.uniform(0.070, 0.130)
        pre_gain = rng.uniform(0.07, 0.23)
        rebound_gain = rng.uniform(0.15, 0.32)
        pre_delay = rng.uniform(0.28, 0.40)
        rebound_delay = rng.uniform(0.46, 0.61)
        negative = -np.exp(-0.5 * (x_ms / trough_width) ** 2)
        pre_positive = pre_gain * np.exp(-0.5 * ((x_ms + pre_delay) / rng.uniform(0.07, 0.11)) ** 2)
        rebound = rebound_gain * np.exp(-0.5 * ((x_ms - rebound_delay) / rng.uniform(0.13, 0.23)) ** 2)
        slow_after = -rng.uniform(0.015, 0.045) * np.exp(-0.5 * ((x_ms - 1.05) / 0.40) ** 2)
        temporal = (negative + pre_positive + rebound + slow_after) * unit_amplitudes[unit_id] / scale_uv_per_bit
        template = np.zeros((waveform_samples, channel_count), dtype=np.float64)
        spatial_irregularity = rng.lognormal(0.0, 0.18, channel_count)
        for channel in range(channel_count):
            if profile_key == "microwire_stimulus":
                spatial = 1.0 if channel == center_channel else 0.0
            elif profile_key == "tetrode_navigation":
                same_tetrode = channel // 4 == center_channel // 4
                spatial = (
                    np.exp(-abs(channel - center_channel) / 1.15)
                    * spatial_irregularity[channel]
                    if same_tetrode
                    else 0.0
                )
            else:
                spatial = np.exp(-abs(channel - center_channel) / 1.6) * spatial_irregularity[channel]
            if channel == center_channel:
                spatial = 1.0
            template[:, channel] = temporal * spatial
        templates[unit_id] = template

    for unit_id, spike_times in ground_truth.items():
        template = templates[unit_id]
        previous_sample = -sample_count
        for spike_time in spike_times:
            center = round(spike_time * sampling_rate)
            start = center - half
            stop = start + waveform_samples
            if start >= 0 and stop <= sample_count:
                slow_drift = 0.86 + 0.22 * (spike_time / max(duration_seconds, 1e-6))
                amplitude_scale = float(
                    np.clip(rng.normal(slow_drift, 0.17), 0.48, 1.48)
                )
                isi_seconds = (center - previous_sample) / sampling_rate
                if isi_seconds < 0.015:
                    amplitude_scale *= 0.82 + 10.0 * isi_seconds
                raw[start:stop] += template * amplitude_scale
                previous_sample = center

    artifact_time = min(18.0, duration_seconds * 0.65)
    artifact_start = int(artifact_time * sampling_rate)
    artifact_stop = artifact_start + int(0.006 * sampling_rate)
    raw[artifact_start:artifact_stop, : min(4, channel_count)] += (
        700.0 / scale_uv_per_bit
    )

    np.clip(raw, -32760, 32760, out=raw)
    raw.astype(np.int16).tofile(recording_path)

    with events_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "trial",
                "time_seconds",
                "behavior_time_seconds",
                "ttl_time_seconds",
                "event_type",
                "condition",
                "choice",
                "outcome",
                "reaction_time",
                "position_x_cm",
                "position_y_cm",
                "speed_cm_s",
                "lick_count",
            ],
        )
        writer.writeheader()
        writer.writerows(events)
    with behavior_events_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "trial",
                "behavior_time_seconds",
                "event_type",
                "condition",
                "choice",
                "outcome",
                "reaction_time",
                "position_x_cm",
                "position_y_cm",
                "speed_cm_s",
                "lick_count",
            ],
        )
        writer.writeheader()
        writer.writerows(
            {
                key: event[key]
                for key in writer.fieldnames
            }
            for event in events
        )
    with ttl_events_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["trial", "ttl_time_seconds"],
        )
        writer.writeheader()
        writer.writerows(
            {
                "trial": event["trial"],
                "ttl_time_seconds": event["ttl_time_seconds"],
            }
            for event in events
        )

    np.savez(
        truth_path,
        **{f"unit_{unit_id}": spikes for unit_id, spikes in ground_truth.items()},
    )
    np.save(respiration_path, respiration_reference.astype(np.float32))
    with states_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "state",
                "start_seconds",
                "stop_seconds",
                "nominal_respiration_hz",
            ],
        )
        writer.writeheader()
        writer.writerows(behavioral_state_epochs)
    independent_contacts = profile_key == "microwire_stimulus"
    contact_positions = (
        None if independent_contacts else _contact_positions(profile_key, channel_count)
    )
    probe_metadata = {
        "geometry_mode": (
            "independent_contacts" if independent_contacts else "recorded_geometry"
        ),
        "contact_groups": (
            [[channel] for channel in range(channel_count)]
            if independent_contacts
            else [
                list(range(group, min(group + 4, channel_count)))
                for group in range(0, channel_count, 4)
            ]
            if profile_key == "tetrode_navigation"
            else []
        ),
    }
    metadata = {
        "dataset_name": profile["name"],
        "demo_profile": profile_key,
        "demo_schema_version": 3,
        "sampling_rate_hz": sampling_rate,
        "channel_count": channel_count,
        "duration_seconds": duration_seconds,
        "dtype": "int16",
        "scale_uv_per_bit": scale_uv_per_bit,
        "seed": seed,
        "electrode_family": profile["electrode_family"],
        "contact_positions_um": (
            contact_positions.tolist() if contact_positions is not None else None
        ),
        "probe": probe_metadata,
        "behavior_paradigm": profile["behavior_paradigm"],
        "behavior_columns": list(events[0]),
        "recommended_sorters": list(profile["recommended_sorters"]),
        "scenario": profile["scenario"],
        "ground_truth_unit_count": len(ground_truth),
        "known_issues": [
            f"Channel {noisy_channel} contains elevated broadband noise",
            (
                f"Channels 0-{min(3, channel_count - 1)} contain a brief artifact "
                f"near {artifact_time:.1f} seconds"
            ),
            "A weak 50 Hz common signal is present",
        ],
        "respiration_reference": str(respiration_path),
        "respiration_sampling_rate_hz": respiration_sampling_rate,
        "behavioral_state_epochs": behavioral_state_epochs,
        "behavior_source": str(behavior_events_path),
        "ttl_source": str(ttl_events_path),
        "case_study_notice": (
            "Synthetic method-validation case only; not the Folschweiller and "
            "Sauer paper dataset or a reproduction of its numerical findings."
        ),
        "dataset_folder": str(project_root),
        "import_config": str(import_config_path),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    import_config_path.write_text(
        json.dumps(
            {
                "recording": recording_path.name,
                "events": events_path.name,
                "behavior_events": behavior_events_path.name,
                "ttl_events": ttl_events_path.name,
                "sampling_rate_hz": sampling_rate,
                "channel_count": channel_count,
                "dtype": "int16",
                "scale_uv_per_bit": scale_uv_per_bit,
                "demo_profile": profile_key,
                "electrode_family": profile["electrode_family"],
                "contact_positions_um": (
                    contact_positions.tolist() if contact_positions is not None else None
                ),
                "probe": probe_metadata,
                "behavior_paradigm": profile["behavior_paradigm"],
                "layout": "time-major interleaved channels (samples x channels)",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    guide_path.write_text(
        (
            "# NeuroFlow demo dataset\n\n"
            "This is a complete deterministic extracellular recording example.\n\n"
            "## Files\n\n"
            "- `raw/neuroflow_simulated_recording.bin`: time-major interleaved int16 "
            "voltage (`samples x channels`).\n"
            "- `raw/events.csv`: trial, alignment time in seconds, condition, and "
            "behavior fields such as choice/outcome, position, speed, and licking.\n"
            "- `raw/behavior_events.csv`: events in the simulated behavior-device clock.\n"
            "- `raw/ttl_events.csv`: matching pulses in the electrophysiology clock.\n"
            "- `raw/metadata.json`: recording metadata and deliberately inserted issues.\n"
            "- `raw/import_config.json`: exact settings for the generic-binary importer.\n"
            "- `raw/ground_truth.npz`: simulated spike times for sorter validation only.\n\n"
            "- `raw/respiration_reference.npy`: 1 kHz synthetic respiration reference.\n"
            "- `raw/behavioral_states.csv`: three synthetic state epochs used by the "
            "respiration analysis case.\n\n"
            f"Profile: `{profile_key}` / {profile['electrode_family']}.\n\n"
            f"Behavior paradigm: {profile['behavior_paradigm']}.\n\n"
            f"Recommended sorter comparison: {', '.join(profile['recommended_sorters'])}.\n\n"
            "## 中文说明\n\n"
            "这是可重复生成的完整细胞外多通道示例。若要练习“导入自己的数据”，"
            "请选择通用二进制，并按 `import_config.json` 填写采样率、通道数、"
            "dtype 和缩放系数，同时选择 `events.csv`。原始二进制按时间优先交错"
            "存储，即数组形状为 `samples x channels`。\n"
        ),
        encoding="utf-8",
    )

    state = ProjectState(
        root=project_root,
        name=profile["name"],
        source_type="simulated",
        source_path=recording_path,
        recording_path=recording_path,
        sampling_rate=sampling_rate,
        channel_count=channel_count,
        duration_seconds=duration_seconds,
        dtype="int16",
        scale_uv_per_bit=scale_uv_per_bit,
        electrode_type=profile["electrode_family"],
        events=events,
        ground_truth=ground_truth,
        metadata=metadata,
    )
    state.log("Reproducible simulated multichannel raw recording generated")
    state.log(
        f"Raw file: {recording_path.name}, {channel_count} channels, "
        f"{duration_seconds:.1f} seconds"
    )
    state.metadata["behavior_source"] = str(behavior_events_path)
    state.metadata["ttl_source"] = str(ttl_events_path)
    return state


def load_or_generate_demo(
    project_root: Path,
    profile_key: str = "neuropixels_decision",
) -> ProjectState:
    metadata_path = project_root / "raw" / "metadata.json"
    events_path = project_root / "raw" / "events.csv"
    behavior_events_path = project_root / "raw" / "behavior_events.csv"
    ttl_events_path = project_root / "raw" / "ttl_events.csv"
    truth_path = project_root / "raw" / "ground_truth.npz"
    respiration_path = project_root / "raw" / "respiration_reference.npy"
    states_path = project_root / "raw" / "behavioral_states.csv"
    recording_path = project_root / "raw" / "neuroflow_simulated_recording.bin"
    import_config_path = project_root / "raw" / "import_config.json"
    guide_path = project_root / "README_DATASET.md"
    if not all(
        path.exists()
        for path in (
            metadata_path,
            events_path,
            behavior_events_path,
            ttl_events_path,
            truth_path,
            respiration_path,
            states_path,
            recording_path,
            import_config_path,
            guide_path,
        )
    ):
        return generate_demo_recording(project_root, profile_key=profile_key)

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (
        metadata.get("demo_profile", "neuropixels_decision") != profile_key
        or int(metadata.get("demo_schema_version", 0)) < 3
    ):
        return generate_demo_recording(project_root, profile_key=profile_key)
    with events_path.open("r", newline="", encoding="utf-8") as handle:
        events = list(csv.DictReader(handle))
    for event in events:
        event["trial"] = int(event["trial"])
        event["time_seconds"] = float(event["time_seconds"])
        if "reaction_time" in event:
            event["reaction_time"] = float(event["reaction_time"])
    truth_archive = np.load(truth_path)
    ground_truth = {
        int(key.split("_")[-1]): truth_archive[key] for key in truth_archive.files
    }
    state = ProjectState(
        root=project_root,
        name=metadata.get("dataset_name", project_root.name),
        source_type="simulated",
        source_path=recording_path,
        recording_path=recording_path,
        sampling_rate=float(metadata["sampling_rate_hz"]),
        channel_count=int(metadata["channel_count"]),
        duration_seconds=float(metadata["duration_seconds"]),
        dtype=metadata.get("dtype", "int16"),
        scale_uv_per_bit=float(metadata.get("scale_uv_per_bit", 1.0)),
        electrode_type=metadata.get("electrode_family", "generic"),
        events=events,
        ground_truth=ground_truth,
        metadata=metadata,
    )
    state.log("Local demo project loaded")
    state.metadata.setdefault("behavior_source", str(behavior_events_path))
    state.metadata.setdefault("ttl_source", str(ttl_events_path))
    return state
