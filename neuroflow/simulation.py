from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from .models import ProjectState


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
    channel_count: int = 32,
    sampling_rate: float = 30_000.0,
) -> ProjectState:
    project_root.mkdir(parents=True, exist_ok=True)
    raw_dir = project_root / "raw"
    raw_dir.mkdir(exist_ok=True)
    recording_path = raw_dir / "neuroflow_simulated_recording.bin"
    metadata_path = raw_dir / "metadata.json"
    events_path = raw_dir / "events.csv"
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
            (("Home cage", 2.2), ("Tail suspension", 1.6), ("Reward", 4.2))
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
    for index, event_time in enumerate(event_times):
        events.append(
            {
                "trial": index + 1,
                "time_seconds": float(event_time),
                "condition": "A" if index % 2 == 0 else "B",
                "reaction_time": float(
                    np.clip(
                        rng.normal(0.42 if index % 2 == 0 else 0.58, 0.07),
                        0.15,
                        1.2,
                    )
                ),
            }
        )

    ground_truth: dict[int, np.ndarray] = {}
    base_rates = [5.0, 7.0, 9.0, 6.0, 8.0, 11.0, 4.0, 6.5]
    for unit_id, base_rate in enumerate(base_rates):
        times = _poisson_spikes(rng, base_rate, duration_seconds)
        preferred = "A" if unit_id < 3 else "B" if unit_id < 6 else None
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
            fieldnames=["trial", "time_seconds", "condition", "reaction_time"],
        )
        writer.writeheader()
        writer.writerows(events)

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
    metadata = {
        "dataset_name": "NeuroFlow simulated extracellular recording",
        "sampling_rate_hz": sampling_rate,
        "channel_count": channel_count,
        "duration_seconds": duration_seconds,
        "dtype": "int16",
        "scale_uv_per_bit": scale_uv_per_bit,
        "seed": seed,
        "electrode_family": "Neuropixels-like linear probe",
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
                "sampling_rate_hz": sampling_rate,
                "channel_count": channel_count,
                "dtype": "int16",
                "scale_uv_per_bit": scale_uv_per_bit,
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
            "reaction time.\n"
            "- `raw/metadata.json`: recording metadata and deliberately inserted issues.\n"
            "- `raw/import_config.json`: exact settings for the generic-binary importer.\n"
            "- `raw/ground_truth.npz`: simulated spike times for sorter validation only.\n\n"
            "- `raw/respiration_reference.npy`: 1 kHz synthetic respiration reference.\n"
            "- `raw/behavioral_states.csv`: three synthetic state epochs used by the "
            "respiration analysis case.\n\n"
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
        name="NeuroFlow simulated extracellular recording",
        source_type="simulated",
        source_path=recording_path,
        recording_path=recording_path,
        sampling_rate=sampling_rate,
        channel_count=channel_count,
        duration_seconds=duration_seconds,
        dtype="int16",
        scale_uv_per_bit=scale_uv_per_bit,
        electrode_type="Neuropixels-like linear probe",
        events=events,
        ground_truth=ground_truth,
        metadata=metadata,
    )
    state.log("Reproducible simulated multichannel raw recording generated")
    state.log(
        f"Raw file: {recording_path.name}, {channel_count} channels, "
        f"{duration_seconds:.1f} seconds"
    )
    return state


def load_or_generate_demo(project_root: Path) -> ProjectState:
    metadata_path = project_root / "raw" / "metadata.json"
    events_path = project_root / "raw" / "events.csv"
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
            truth_path,
            respiration_path,
            states_path,
            recording_path,
            import_config_path,
            guide_path,
        )
    ):
        return generate_demo_recording(project_root)

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
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
    return state
