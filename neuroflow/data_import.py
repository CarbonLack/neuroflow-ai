from __future__ import annotations

import csv
import inspect
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .models import ProjectState
from .project import save_project
from .simulation import generate_demo_recording
from .sorting_results import register_sorting_result


@dataclass(frozen=True)
class ImportFormat:
    key: str
    name: str
    description: str
    raw_signal: bool
    sorting_result: bool


SUPPORTED_FORMATS = (
    ImportFormat(
        "simulated", "模拟多通道记录", "Neuropixels、tetrode 或线性探针", True, True
    ),
    ImportFormat("binary", "通用二进制", "int16/float32 交错通道原始记录", True, False),
    ImportFormat(
        "device",
        "主流记录系统",
        "Intan、Open Ephys、SpikeGLX、Blackrock、Plexon、TDT、NWB",
        True,
        False,
    ),
    ImportFormat(
        "ibl_alf",
        "公开验证数据",
        "IBL ALF/BWM 或带 Units 与行为事件的 Buzsáki/DANDI NWB",
        False,
        True,
    ),
    ImportFormat(
        "kilosort",
        "Kilosort/Phy 结果",
        "spike_times、spike_clusters 与参数",
        False,
        True,
    ),
)


DEVICE_READERS = {
    "Intan": ("read_intan", False),
    "Open Ephys": ("read_openephys", True),
    "SpikeGLX / Neuropixels": ("read_spikeglx", True),
    "Blackrock": ("read_blackrock", False),
    "Plexon": ("read_plexon", False),
    "TDT": ("read_tdt", True),
    "NWB ElectricalSeries": ("read_nwb_recording", False),
}


def create_simulated_project(
    project_root: Path,
    electrode_type: str = "Neuropixels-like",
    duration_seconds: float = 30.0,
    sampling_rate: float = 30_000.0,
    channel_count: int | None = None,
    seed: int = 20260724,
) -> ProjectState:
    defaults = {
        "Neuropixels-like": 32,
        "Tetrode array (4 x 4)": 16,
        "Linear silicon probe": 32,
    }
    state = generate_demo_recording(
        project_root,
        seed=seed,
        duration_seconds=duration_seconds,
        channel_count=channel_count or defaults.get(electrode_type, 32),
        sampling_rate=sampling_rate,
    )
    state.name = f"模拟 {electrode_type} 全流程"
    state.source_type = "simulated"
    state.source_path = state.recording_path
    state.electrode_type = electrode_type
    state.metadata.update(
        {
            "provenance": "NeuroFlow deterministic simulator",
            "electrode_layout": electrode_type,
            "can_run_sorting": True,
        }
    )
    save_project(state)
    return state


def import_binary_recording(
    project_root: Path,
    source: Path,
    sampling_rate: float,
    channel_count: int,
    dtype: str = "int16",
    scale_uv_per_bit: float = 1.0,
    electrode_type: str = "generic",
    events_path: Path | None = None,
    copy_source: bool = False,
) -> ProjectState:
    if dtype not in {"int16", "float32", "int32"}:
        raise ValueError("当前通用导入支持 int16、int32 和 float32")
    if sampling_rate <= 0 or channel_count <= 0:
        raise ValueError("采样率和通道数必须大于 0")
    item_size = np.dtype(dtype).itemsize
    frame_bytes = item_size * channel_count
    if source.stat().st_size % frame_bytes:
        raise ValueError("文件大小不能被单帧字节数整除，请检查 dtype 和通道数")
    project_root.mkdir(parents=True, exist_ok=True)
    recording_path = source
    if copy_source:
        raw_dir = project_root / "raw"
        raw_dir.mkdir(exist_ok=True)
        recording_path = raw_dir / source.name
        shutil.copy2(source, recording_path)
    duration = source.stat().st_size / frame_bytes / sampling_rate
    events: list[dict[str, Any]] = []
    if events_path:
        with events_path.open("r", newline="", encoding="utf-8-sig") as handle:
            events = list(csv.DictReader(handle))
        for index, event in enumerate(events):
            if "time_seconds" not in event:
                raise ValueError("事件 CSV 必须包含 time_seconds 列")
            event["time_seconds"] = float(event["time_seconds"])
            event.setdefault("trial", index + 1)
            event.setdefault("condition", "all")
    state = ProjectState(
        root=project_root,
        name=source.stem,
        source_type="binary",
        source_path=source,
        recording_path=recording_path,
        sampling_rate=sampling_rate,
        channel_count=channel_count,
        duration_seconds=duration,
        dtype=dtype,
        scale_uv_per_bit=scale_uv_per_bit,
        electrode_type=electrode_type,
        events=events,
        metadata={
            "copy_source": copy_source,
            "can_run_sorting": dtype == "int16",
            "behavior_source": str(events_path) if events_path else None,
        },
    )
    state.log(f"Generic binary recording imported: {source.name}")
    save_project(state)
    return state


def import_device_recording(
    project_root: Path,
    source: Path,
    device_name: str,
    stream_id: str | None = None,
) -> ProjectState:
    """Read a supported device through SpikeInterface and cache a common binary."""
    if device_name not in DEVICE_READERS:
        raise ValueError(f"尚未注册的记录系统：{device_name}")
    import spikeinterface as si
    import spikeinterface.extractors as se

    reader_name, expects_directory = DEVICE_READERS[device_name]
    if expects_directory and not source.is_dir():
        raise ValueError(f"{device_name} 需要选择记录文件夹")
    if not expects_directory and not source.is_file():
        raise ValueError(f"{device_name} 需要选择记录文件")
    reader = getattr(se, reader_name)
    kwargs = {}
    if stream_id and "stream_id" in inspect.signature(reader).parameters:
        kwargs["stream_id"] = stream_id
    recording = reader(source, **kwargs)
    if recording.get_num_segments() != 1:
        raise ValueError("当前版本要求选择单一 recording segment")
    project_root.mkdir(parents=True, exist_ok=True)
    cache_dir = project_root / "cache"
    cache_dir.mkdir(exist_ok=True)
    binary_path = cache_dir / "normalized_recording.bin"
    source_dtype = str(recording.get_dtype())
    normalized = recording.astype("int16")
    si.write_binary_recording(
        normalized,
        file_paths=[binary_path],
        dtype="int16",
        add_file_extension=False,
        chunk_duration="1s",
        n_jobs=1,
    )
    state = ProjectState(
        root=project_root,
        name=f"{device_name} {source.stem}",
        source_type=reader_name,
        source_path=source,
        recording_path=binary_path,
        sampling_rate=float(recording.get_sampling_frequency()),
        channel_count=int(recording.get_num_channels()),
        duration_seconds=float(recording.get_total_duration()),
        dtype="int16",
        electrode_type=device_name,
        metadata={
            "device": device_name,
            "reader": f"SpikeInterface {reader_name}",
            "source_dtype": source_dtype,
            "normalized_dtype": "int16",
            "stream_id": stream_id,
            "conversion_notice": "缓存为交错 int16，原始文件保持只读且不修改。",
        },
    )
    state.log(
        f"{device_name} imported through SpikeInterface: "
        f"{state.channel_count} channels, {state.duration_seconds:.1f} seconds"
    )
    save_project(state)
    return state


def _find_one(root: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        direct = root / name
        if direct.exists():
            return direct
    for name in names:
        matches = list(root.rglob(name))
        if matches:
            return matches[0]
    return None


def import_kilosort_results(
    project_root: Path,
    source: Path,
    sampling_rate: float,
) -> ProjectState:
    times_path = _find_one(source, ("spike_times.npy", "spikes.times.npy"))
    clusters_path = _find_one(
        source, ("spike_clusters.npy", "spike_templates.npy", "spikes.clusters.npy")
    )
    if not times_path or not clusters_path:
        raise ValueError("未找到 spike_times 与 spike_clusters/spike_templates 文件")
    times = np.load(times_path).reshape(-1)
    clusters = np.load(clusters_path).reshape(-1).astype(int)
    if times.size != clusters.size:
        raise ValueError("spike times 与 cluster id 数量不一致")
    is_seconds = times_path.name.startswith("spikes.times")
    spike_seconds = (
        times.astype(float) if is_seconds else times.astype(float) / sampling_rate
    )
    sorted_spikes = {
        int(unit): spike_seconds[clusters == unit] for unit in np.unique(clusters)
    }
    state = ProjectState(
        root=project_root,
        name=f"{source.name} sorting",
        source_type="kilosort_output",
        source_path=source,
        sampling_rate=sampling_rate,
        duration_seconds=float(spike_seconds.max()) if spike_seconds.size else 0.0,
        sorted_spikes=sorted_spikes,
        metadata={"sorter": "Kilosort/Phy", "raw_signal_available": False},
    )
    register_sorting_result(
        state,
        "imported_kilosort",
        sorted_spikes,
        {
            "sorter": "Kilosort/Phy import",
            "backend": "External result import",
            "source_directory": str(source),
            "source_time_unit": "seconds" if is_seconds else "samples",
        },
    )
    state.log(f"Sorting results imported: {len(sorted_spikes)} units")
    save_project(state)
    return state


def _load_alf_object(root: Path, object_name: str) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    for path in root.rglob(f"{object_name}.*.npy"):
        attribute = path.name[len(object_name) + 1 : -4]
        result[attribute] = np.load(path, allow_pickle=True)
    table = _find_one(
        root, (f"{object_name}.table.pqt", f"_ibl_{object_name}.table.pqt")
    )
    if table:
        frame = pd.read_parquet(table)
        result.update({column: frame[column].to_numpy() for column in frame.columns})
    return result


def import_ibl_alf(project_root: Path, alf_root: Path) -> ProjectState:
    trials_obj = _load_alf_object(alf_root, "trials")
    if not trials_obj:
        trials_obj = _load_alf_object(alf_root, "_ibl_trials")
    spikes = _load_alf_object(alf_root, "spikes")
    if not spikes:
        spikes = _load_alf_object(alf_root, "_ibl_spikes")
    times = spikes.get("times")
    clusters = spikes.get("clusters")
    if times is None or clusters is None:
        raise ValueError("IBL ALF 文件夹缺少 spikes.times.npy 或 spikes.clusters.npy")
    clusters = np.asarray(clusters).reshape(-1).astype(int)
    times = np.asarray(times).reshape(-1).astype(float)
    sorted_spikes = {int(unit): times[clusters == unit] for unit in np.unique(clusters)}
    trial_count = max((len(value) for value in trials_obj.values()), default=0)
    trials: list[dict[str, Any]] = []
    for index in range(trial_count):
        row = {"trial": index + 1}
        for key, values in trials_obj.items():
            if index < len(values):
                value = values[index]
                row[key] = value.item() if isinstance(value, np.generic) else value
        trials.append(row)
    event_key = next(
        (
            key
            for key in ("stimOn_times", "goCue_times", "feedback_times")
            if key in trials_obj
        ),
        None,
    )
    events = []
    if event_key:
        contrast_left = np.asarray(
            trials_obj.get("contrastLeft", np.full(trial_count, np.nan))
        )
        contrast_right = np.asarray(
            trials_obj.get("contrastRight", np.full(trial_count, np.nan))
        )
        for index, event_time in enumerate(
            np.asarray(trials_obj[event_key], dtype=float)
        ):
            if not np.isfinite(event_time):
                continue
            if np.isfinite(contrast_left[index]):
                condition = "left"
            elif np.isfinite(contrast_right[index]):
                condition = "right"
            else:
                condition = "unknown"
            events.append(
                {
                    "trial": index + 1,
                    "time_seconds": float(event_time),
                    "condition": condition,
                    "event_name": event_key,
                }
            )
    state = ProjectState(
        root=project_root,
        name=f"IBL {alf_root.name}",
        source_type="ibl_alf",
        source_path=alf_root,
        sampling_rate=30_000.0,
        duration_seconds=float(times.max()) if times.size else 0.0,
        electrode_type="Neuropixels",
        events=events,
        trials=trials,
        sorted_spikes=sorted_spikes,
        metadata={
            "standard": "IBL ALF",
            "raw_signal_available": False,
            "trial_fields": sorted(trials_obj),
            "event_alignment": event_key,
            "source_notice": "Public IBL data; retain dataset citation and session identifiers.",
        },
    )
    register_sorting_result(
        state,
        "ibl_alf",
        sorted_spikes,
        {
            "sorter": "IBL ALF sorting import",
            "backend": "IBL ALF",
            "source_directory": str(alf_root),
            "source_time_unit": "seconds",
        },
    )
    state.log(
        f"IBL ALF imported: {len(trials)} trials, {len(sorted_spikes)} units, "
        f"alignment event {event_key or 'not found'}"
    )
    save_project(state)
    return state


def _decode_nwb_values(values: np.ndarray) -> list[Any]:
    decoded: list[Any] = []
    for value in np.asarray(values).reshape(-1):
        if isinstance(value, (bytes, np.bytes_)):
            decoded.append(value.decode("utf-8", errors="replace"))
        elif isinstance(value, np.generic):
            decoded.append(value.item())
        else:
            decoded.append(value)
    return decoded


def _read_nwb_ragged(
    handle: Any,
    value_path: str,
    index_path: str,
    ids: np.ndarray,
) -> dict[int, np.ndarray]:
    values = np.asarray(handle[value_path], dtype=float)
    stops = np.asarray(handle[index_path], dtype=np.int64).reshape(-1)
    if stops.size != ids.size:
        raise ValueError(
            "NWB Units 表中的 spike_times_index 与 unit id 数量不一致"
        )
    starts = np.concatenate(([0], stops[:-1]))
    return {
        int(unit_id): np.asarray(values[start:stop], dtype=float)
        for unit_id, start, stop in zip(ids, starts, stops)
    }


def import_nwb_units(
    project_root: Path,
    source: Path,
    *,
    event_series_path: str | None = None,
) -> ProjectState:
    """Import a processed NWB session with Units and optional behavior events.

    The importer deliberately starts downstream of raw QC and sorting unless the
    selected NWB also exposes a raw ElectricalSeries through the device adapter.
    Units are normalized to NeuroFlow's seconds-based sorting interface.
    """
    import h5py

    if not source.is_file():
        raise ValueError("请选择有效的 NWB 文件")
    with h5py.File(source, "r") as handle:
        required = ("units/id", "units/spike_times", "units/spike_times_index")
        missing = [path for path in required if path not in handle]
        if missing:
            raise ValueError(
                "该 NWB 不包含可导入的 Units 表：缺少 " + ", ".join(missing)
            )
        unit_ids = np.asarray(handle["units/id"], dtype=np.int64).reshape(-1)
        sorted_spikes = _read_nwb_ragged(
            handle,
            "units/spike_times",
            "units/spike_times_index",
            unit_ids,
        )

        reward_candidates = (
            event_series_path,
            "processing/behavior/RewardEventsEightMazeTrack",
            "processing/behavior/rewards",
            "acquisition/rewards",
        )
        selected_event_path = next(
            (
                candidate
                for candidate in reward_candidates
                if candidate and candidate in handle
            ),
            None,
        )
        events: list[dict[str, Any]] = []
        trials: list[dict[str, Any]] = []
        if selected_event_path:
            series = handle[selected_event_path]
            if "timestamps" in series:
                event_times = np.asarray(series["timestamps"], dtype=float).reshape(-1)
                event_values = (
                    _decode_nwb_values(np.asarray(series["data"]))
                    if "data" in series
                    else ["event"] * len(event_times)
                )
                for index, event_time in enumerate(event_times):
                    value = event_values[index] if index < len(event_values) else "event"
                    condition = f"reward-{value}"
                    row = {
                        "trial": index + 1,
                        "time_seconds": float(event_time),
                        "condition": condition,
                        "event_name": Path(selected_event_path).name,
                        "event_value": value,
                    }
                    events.append(row)
                    trials.append(dict(row))

        position_candidates = (
            "processing/behavior/LinearizedPosition/LinearizedSpatialSeries",
            "processing/behavior/SubjectPosition/SpatialSeries",
        )
        position_payload: dict[str, np.ndarray] = {}
        selected_positions: list[str] = []
        for candidate in position_candidates:
            if candidate not in handle:
                continue
            series = handle[candidate]
            if "data" not in series or "timestamps" not in series:
                continue
            key = "linearized_position" if "Linearized" in candidate else "subject_position"
            position_payload[f"{key}_data"] = np.asarray(series["data"])
            position_payload[f"{key}_timestamps"] = np.asarray(
                series["timestamps"], dtype=float
            )
            selected_positions.append(candidate)

        intervals: dict[str, list[dict[str, Any]]] = {}
        interval_candidates = {
            "sleep_states": "processing/behavior/SleepStates",
            "ripples": "processing/ecephys/Ripples",
        }
        for name, candidate in interval_candidates.items():
            if candidate not in handle:
                continue
            table = handle[candidate]
            if "start_time" not in table or "stop_time" not in table:
                continue
            starts = np.asarray(table["start_time"], dtype=float)
            stops = np.asarray(table["stop_time"], dtype=float)
            labels = (
                _decode_nwb_values(np.asarray(table["label"]))
                if "label" in table
                else [name] * len(starts)
            )
            intervals[name] = [
                {
                    "start_time": float(start),
                    "stop_time": float(stop),
                    "label": labels[index] if index < len(labels) else name,
                }
                for index, (start, stop) in enumerate(zip(starts, stops))
            ]

        electrode_path = "general/extracellular_ephys/electrodes/id"
        channel_count = (
            int(np.asarray(handle[electrode_path]).size)
            if electrode_path in handle
            else 0
        )
        session_id = (
            handle["general/session_id"][()].decode("utf-8", errors="replace")
            if "general/session_id" in handle
            and isinstance(handle["general/session_id"][()], bytes)
            else str(handle["general/session_id"][()])
            if "general/session_id" in handle
            else source.stem
        )

    project_root.mkdir(parents=True, exist_ok=True)
    derived_dir = project_root / "derived" / "public_data"
    derived_dir.mkdir(parents=True, exist_ok=True)
    position_path: Path | None = None
    if position_payload:
        position_path = derived_dir / "position_series.npz"
        np.savez_compressed(position_path, **position_payload)

    max_spike_time = max(
        (float(values.max()) for values in sorted_spikes.values() if values.size),
        default=0.0,
    )
    max_event_time = max(
        (float(event["time_seconds"]) for event in events), default=0.0
    )
    max_interval_time = max(
        (
            float(row["stop_time"])
            for rows in intervals.values()
            for row in rows
        ),
        default=0.0,
    )
    is_buzsaki = "buzsaki" in source.name.lower() or bool(
        intervals.get("ripples") or selected_positions
    )
    state = ProjectState(
        root=project_root,
        name=f"{'Buzsáki' if is_buzsaki else 'NWB'} {session_id}",
        source_type="nwb_units",
        source_path=source,
        sampling_rate=30_000.0,
        channel_count=channel_count,
        duration_seconds=max(max_spike_time, max_event_time, max_interval_time),
        electrode_type="silicon probe / processed NWB",
        events=events,
        trials=trials,
        sorted_spikes=sorted_spikes,
        metadata={
            "standard": "NWB Units + behavior",
            "session_id": session_id,
            "raw_signal_available": False,
            "event_series": selected_event_path,
            "position_series": selected_positions,
            "position_cache": str(position_path) if position_path else None,
            "intervals": intervals,
            "source_notice": (
                "Processed public NWB data. Preserve the DANDI DOI, dataset "
                "version, license, and article citation."
            ),
        },
    )
    register_sorting_result(
        state,
        "imported_nwb_units",
        sorted_spikes,
        {
            "sorter": "Imported NWB Units table",
            "backend": "NWB",
            "source_file": str(source),
            "source_time_unit": "seconds",
        },
    )
    state.log(
        f"NWB Units imported: {len(sorted_spikes)} units, {len(events)} events, "
        f"{sum(len(rows) for rows in intervals.values())} labeled intervals"
    )
    save_project(state)
    return state


def import_ibl_trials_aggregate(
    project_root: Path,
    parquet_path: Path,
    eid: str | None = None,
) -> ProjectState:
    frame = pd.read_parquet(parquet_path)
    required = {"eid", "stimOn_times", "contrastLeft", "contrastRight", "choice"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"IBL aggregate trials 缺少字段：{sorted(missing)}")
    if eid is None:
        eligible = frame
        if "bwm_include" in frame.columns and frame["bwm_include"].any():
            eligible = frame[frame["bwm_include"]]
        eid = str(eligible["eid"].value_counts().index[0])
    session = frame[frame["eid"].astype(str) == str(eid)].copy()
    if session.empty:
        raise ValueError(f"aggregate 中找不到 session {eid}")
    session = session.reset_index(drop=True)
    trials = session.where(pd.notna(session), None).to_dict(orient="records")
    events = []
    for index, row in session.iterrows():
        event_time = row.get("stimOn_times")
        if not np.isfinite(event_time):
            continue
        left = row.get("contrastLeft")
        right = row.get("contrastRight")
        condition = (
            "left" if np.isfinite(left) else "right" if np.isfinite(right) else "zero"
        )
        events.append(
            {
                "trial": index + 1,
                "time_seconds": float(event_time),
                "condition": condition,
                "event_name": "stimOn_times",
            }
        )
    state = ProjectState(
        root=project_root,
        name=f"IBL BWM behavior {eid}",
        source_type="ibl_bwm_trials",
        source_path=parquet_path,
        duration_seconds=float(session["stimOn_times"].max()),
        electrode_type="Neuropixels BWM session",
        events=events,
        trials=trials,
        metadata={
            "standard": "IBL Brain-Wide Map aggregate trials",
            "eid": str(eid),
            "raw_signal_available": False,
            "neural_data_available": False,
            "license": "CC-BY 4.0",
            "citation": "International Brain Laboratory et al., Nature (2025)",
        },
    )
    state.log(
        f"IBL BWM behavioral data imported: session {eid}, {len(trials)} trials"
    )
    save_project(state)
    return state
