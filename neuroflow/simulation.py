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
    import_config_path = raw_dir / "import_config.json"
    guide_path = project_root / "README_DATASET.md"

    rng = np.random.default_rng(seed)
    sample_count = int(duration_seconds * sampling_rate)
    scale_uv_per_bit = 0.195

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
        ground_truth[unit_id] = _enforce_refractory(
            times[(times > 0.05) & (times < duration_seconds - 0.05)]
        )

    raw = rng.normal(0.0, 16.0 / scale_uv_per_bit, size=(sample_count, channel_count))
    time_axis = np.arange(sample_count, dtype=np.float64) / sampling_rate
    common_noise = (
        5.0 * np.sin(2 * np.pi * 50.0 * time_axis)
        + 2.5 * np.sin(2 * np.pi * 2.0 * time_axis)
    ) / scale_uv_per_bit
    raw += common_noise[:, None]
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
    state.log("已生成可复现的模拟多通道原始记录")
    state.log(
        f"原始文件：{recording_path.name}，{channel_count}通道，{duration_seconds:.1f}秒"
    )
    return state


def load_or_generate_demo(project_root: Path) -> ProjectState:
    metadata_path = project_root / "raw" / "metadata.json"
    events_path = project_root / "raw" / "events.csv"
    truth_path = project_root / "raw" / "ground_truth.npz"
    recording_path = project_root / "raw" / "neuroflow_simulated_recording.bin"
    import_config_path = project_root / "raw" / "import_config.json"
    guide_path = project_root / "README_DATASET.md"
    if not all(
        path.exists()
        for path in (
            metadata_path,
            events_path,
            truth_path,
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
    state.log("已载入本地演示项目")
    return state
