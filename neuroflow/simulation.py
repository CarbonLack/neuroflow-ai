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
        "recommended_sorters": ("MountainSort5", "Tridesclous2"),
        "scenario": (
            "Four spatially separated tetrodes with position, speed, reward-zone "
            "events, reaction latency, behavior-clock drift, and TTL jitter."
        ),
        "scenario_zh": "四组空间分离 tetrode，包含位置、速度、奖励区事件、反应延迟、行为时钟漂移与 TTL 抖动。",
    },
    "microwire_stimulus": {
        "name": "Independent microwires sensory task",
        "name_zh": "单根/多根微丝电极 · 感觉刺激任务",
        "folder": "Microwire_Stimulus",
        "electrode_family": "Independent microwire array",
        "channel_count": 8,
        "sampling_rate": 25_000.0,
        "behavior_paradigm": "tone discrimination and licking",
        "behavior_paradigm_zh": "音调辨别与舔舐",
        "conditions": ("tone_low", "tone_high"),
        "epoch_names": ("Baseline", "Tone", "Consumption"),
        "recommended_sorters": ("MountainSort5", "SpikeInterface Simple"),
        "scenario": (
            "Independent low-channel-count wires with tone identity, lick count, "
            "hit/miss outcome, behavior-clock drift, and TTL jitter."
        ),
        "scenario_zh": "独立低通道微丝，包含音调、舔舐次数、正确/错误结果、行为时钟漂移与 TTL 抖动。",
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


def generate_demo_recording(
    project_root: Path,
    seed: int = 20260724,
    duration_seconds: float = 30.0,
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
    event_times = np.linspace(event_margin, duration_seconds - event_margin, 20)
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
    base_rates = [5.0, 7.0, 9.0, 6.0, 8.0, 11.0, 4.0, 6.5]
    for unit_id, base_rate in enumerate(base_rates):
        times = _poisson_spikes(rng, base_rate, duration_seconds)
        preferred = (
            first_condition
            if unit_id < 3
            else second_condition
            if unit_id < 6
            else None
        )
        if preferred is not None:
            locked: list[np.ndarray] = []
            for event in events:
                if event["condition"] == preferred:
                    count = int(rng.poisson(5))
                    if count:
                        locked.append(
                            float(event["time_seconds"])
                            + rng.normal(0.12, 0.035, size=count)
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

    raw = rng.normal(0.0, 16.0 / scale_uv_per_bit, size=(sample_count, channel_count))
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
    x = np.arange(waveform_samples, dtype=np.float64)
    unit_channels = np.linspace(
        1, max(1, channel_count - 2), len(base_rates), dtype=int
    ).tolist()
    unit_amplitudes = [185, 225, 205, 245, 190, 230, 210, 200]
    templates = {}
    for unit_id, center_channel in enumerate(unit_channels):
        negative = -np.exp(-0.5 * ((x - 22.0) / 3.2) ** 2)
        rebound = 0.32 * np.exp(-0.5 * ((x - 31.0) / 5.0) ** 2)
        temporal = (negative + rebound) * unit_amplitudes[unit_id] / scale_uv_per_bit
        template = np.zeros((waveform_samples, channel_count), dtype=np.float64)
        for channel in range(channel_count):
            spatial = np.exp(-abs(channel - center_channel) / 1.6)
            template[:, channel] = temporal * spatial
        templates[unit_id] = template

    half = waveform_samples // 2
    for unit_id, spike_times in ground_truth.items():
        template = templates[unit_id]
        for spike_time in spike_times:
            center = round(spike_time * sampling_rate)
            start = center - half
            stop = start + waveform_samples
            if start >= 0 and stop <= sample_count:
                raw[start:stop] += template

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
    contact_positions = _contact_positions(profile_key, channel_count)
    metadata = {
        "dataset_name": profile["name"],
        "demo_profile": profile_key,
        "demo_schema_version": 2,
        "sampling_rate_hz": sampling_rate,
        "channel_count": channel_count,
        "duration_seconds": duration_seconds,
        "dtype": "int16",
        "scale_uv_per_bit": scale_uv_per_bit,
        "seed": seed,
        "electrode_family": profile["electrode_family"],
        "contact_positions_um": contact_positions.tolist(),
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
                "contact_positions_um": contact_positions.tolist(),
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
        or int(metadata.get("demo_schema_version", 0)) < 2
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
