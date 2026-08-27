from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

import numpy as np

from .models import ProjectState

try:
    from neo.rawio.openephysrawio import (
        HEADER_SIZE,
        RECORD_SIZE,
        continuous_dtype,
        events_dtype,
        read_file_header,
    )
except ImportError:  # pragma: no cover - Neo is a required NeuroFlow dependency
    HEADER_SIZE = 1024
    RECORD_SIZE = 1024
    continuous_dtype = np.dtype(
        [
            ("timestamp", "<i8"),
            ("nb_sample", "<u2"),
            ("recording_number", ">u2"),
            ("samples", ">i2", 1024),
            ("markers", "u1", 10),
        ]
    )
    events_dtype = np.dtype(
        [
            ("timestamp", "i8"),
            ("sample_pos", "i2"),
            ("event_type", "u1"),
            ("processor_id", "u1"),
            ("event_id", "u1"),
            ("chan_id", "u1"),
            ("record_num", "u2"),
        ]
    )
    read_file_header = None


def find_open_ephys_legacy_folder(source: Path) -> Path | None:
    """Return the folder containing Legacy ``.continuous`` files."""
    source = Path(source)
    if source.is_dir() and any(source.glob("*.continuous")):
        return source
    if not source.is_dir():
        return None
    candidates = sorted(
        {
            path.parent
            for path in source.rglob("*.continuous")
            if path.is_file()
        }
    )
    return candidates[0] if len(candidates) == 1 else None


def _channel_number(path: Path) -> int:
    match = re.search(r"(?:^|_)CH(\d+)\.continuous$", path.name, re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot determine the channel number from {path.name}")
    return int(match.group(1))


def parse_channel_selection(
    selection: str | list[str] | tuple[str, ...] | None,
    available_ids: list[str],
) -> list[str]:
    """Resolve ``1-32,35`` style input against extractor channel IDs."""
    if selection is None or selection == "" or selection == []:
        return list(available_ids)
    if isinstance(selection, (list, tuple)):
        requested = [str(value).strip() for value in selection]
    else:
        requested: list[str] = []
        for token in str(selection).replace(" ", "").split(","):
            if not token:
                continue
            match = re.fullmatch(r"(-?\d+)-(-?\d+)", token)
            if match:
                start, stop = (int(value) for value in match.groups())
                step = 1 if stop >= start else -1
                requested.extend(str(value) for value in range(start, stop + step, step))
            else:
                requested.append(token)
    missing = [value for value in requested if value not in available_ids]
    if missing:
        raise ValueError(
            "Selected channels are not present in the recording: "
            + ", ".join(missing[:12])
        )
    if not requested:
        raise ValueError("At least one recording channel must be selected")
    return requested


def inspect_open_ephys_legacy(
    source: Path,
    channel_selection: str | list[str] | None = None,
) -> dict[str, Any]:
    """Inspect a Legacy recording without converting or scanning every sample."""
    folder = find_open_ephys_legacy_folder(source)
    if folder is None:
        raise ValueError(
            "No unique Open Ephys Legacy folder containing .continuous files was found"
        )
    files = sorted(folder.glob("*.continuous"), key=_channel_number)
    if not files:
        raise ValueError("The selected folder contains no .continuous files")
    available_ids = [str(_channel_number(path)) for path in files]
    selected_ids = parse_channel_selection(channel_selection, available_ids)
    file_by_id = {str(_channel_number(path)): path for path in files}
    selected_files = [file_by_id[channel_id] for channel_id in selected_ids]

    header = read_file_header(selected_files[0]) if read_file_header else {}
    sampling_rate = float(header.get("sampleRate", 30_000.0))
    frame_counts = [
        (
            (path.stat().st_size - HEADER_SIZE)
            // np.dtype(continuous_dtype).itemsize
        )
        * RECORD_SIZE
        for path in selected_files
    ]
    frame_count = int(min(frame_counts))
    gains = [float(header.get("bitVolts", 1.0)) for _ in selected_files]
    return {
        "folder": folder,
        "all_channel_ids": available_ids,
        "selected_channel_ids": selected_ids,
        "selected_files": selected_files,
        "sampling_rate": sampling_rate,
        "frame_count": frame_count,
        "duration_seconds": frame_count / sampling_rate,
        "dtype": "int16",
        "gains_uv_per_bit": gains,
        "format_version": str(header.get("version", "unknown")).strip("'"),
        "date_created": str(header.get("date_created", "")).strip("'"),
    }


def inspect_open_ephys_settings(folder: Path) -> dict[str, Any]:
    settings_path = Path(folder) / "settings.xml"
    if not settings_path.exists():
        return {}
    root = ElementTree.parse(settings_path).getroot()
    filters: list[dict[str, float]] = []
    reference_groups: list[list[int]] = []
    for processor in root.iter("PROCESSOR"):
        name = str(processor.attrib.get("name", "")).lower()
        parameters = processor.find(".//PARAMETERS")
        if parameters is None:
            continue
        if "bandpass" in name:
            try:
                filters.append(
                    {
                        "low_cut_hz": float(parameters.attrib["low_cut"]),
                        "high_cut_hz": float(parameters.attrib["high_cut"]),
                    }
                )
            except (KeyError, ValueError):
                pass
        if "common avg ref" in name or "common average" in name:
            reference = parameters.attrib.get("Reference", "")
            values = [
                int(value)
                for value in reference.split(",")
                if value.strip().isdigit()
            ]
            if values:
                reference_groups.append(values)
    low_cut = max((item["low_cut_hz"] for item in filters), default=0.0)
    return {
        "settings_file": str(settings_path),
        "online_filters": filters,
        "online_reference": (
            {
                "method": "common_average",
                "channel_groups": reference_groups,
            }
            if reference_groups
            else None
        ),
        "ap_preprocessed": bool(filters or reference_groups),
        "lfp_available": not (low_cut >= 30.0),
        "lfp_unavailable_reason": (
            f"The saved signal was high-pass filtered online at {low_cut:g} Hz; "
            "frequencies below that cutoff cannot be reconstructed."
            if low_cut >= 30.0
            else None
        ),
    }


def read_open_ephys_legacy_events(
    folder: Path,
    sampling_rate: float,
    reference_channel_file: Path | None = None,
) -> list[dict[str, Any]]:
    """Read digital edges from Legacy event files, including files Neo skips."""
    folder = Path(folder)
    event_files = sorted(
        path
        for path in folder.glob("*.events")
        if path.name.lower() != "messages.events" and path.stat().st_size > HEADER_SIZE
    )
    if not event_files:
        return []
    if reference_channel_file is None:
        candidates = sorted(folder.glob("*.continuous"), key=_channel_number)
        reference_channel_file = candidates[0] if candidates else None
    if reference_channel_file is None:
        return []
    reference = np.memmap(
        reference_channel_file,
        mode="r",
        offset=HEADER_SIZE,
        dtype=continuous_dtype,
    )
    first_timestamp = int(reference[0]["timestamp"])
    data = np.memmap(
        event_files[0],
        mode="r",
        offset=HEADER_SIZE,
        dtype=events_dtype,
    )
    result: list[dict[str, Any]] = []
    for row in data:
        event_id = int(row["event_id"])
        result.append(
            {
                "timestamp_samples": int(row["timestamp"]),
                "time_seconds": (
                    int(row["timestamp"]) - first_timestamp
                )
                / float(sampling_rate),
                "sample_position": int(row["sample_pos"]),
                "event_type": int(row["event_type"]),
                "processor_id": int(row["processor_id"]),
                "channel": int(row["chan_id"]),
                "edge": "rising" if event_id == 1 else "falling",
                "event_id": event_id,
            }
        )
    return result


def _selector_indices(selector: Any, size: int) -> tuple[np.ndarray, bool]:
    if isinstance(selector, (int, np.integer)):
        index = int(selector)
        if index < 0:
            index += size
        return np.asarray([index], dtype=int), True
    if isinstance(selector, slice):
        return np.arange(size, dtype=int)[selector], False
    values = np.asarray(selector)
    if values.dtype == bool:
        values = np.flatnonzero(values)
    return values.astype(int, copy=False), False


class OpenEphysLegacyArray:
    """Small, array-like random-access view over selected Legacy channel files."""

    def __init__(
        self,
        file_paths: tuple[str, ...],
        frame_count: int,
        start_frame: int = 0,
        end_frame: int | None = None,
    ):
        self.file_paths = tuple(Path(path) for path in file_paths)
        self.start_frame = max(int(start_frame), 0)
        self.end_frame = (
            min(int(end_frame), int(frame_count))
            if end_frame is not None
            else int(frame_count)
        )
        if self.end_frame < self.start_frame:
            raise ValueError("Open Ephys frame slice ends before it starts")
        self.shape = (
            self.end_frame - self.start_frame,
            len(self.file_paths),
        )
        self.dtype = np.dtype("int16")
        self._maps = [
            np.memmap(path, mode="r", offset=HEADER_SIZE, dtype=continuous_dtype)
            for path in self.file_paths
        ]

    def _channel_window(self, channel: int, start: int, stop: int) -> np.ndarray:
        start += self.start_frame
        stop += self.start_frame
        first_block = start // RECORD_SIZE
        last_block = math.ceil(stop / RECORD_SIZE)
        samples = np.asarray(
            self._maps[channel][first_block:last_block]["samples"]
        ).reshape(-1)
        local_start = start - first_block * RECORD_SIZE
        return samples[local_start : local_start + (stop - start)]

    def __getitem__(self, key: Any) -> np.ndarray:
        if isinstance(key, tuple):
            row_selector, channel_selector = key
        else:
            row_selector, channel_selector = key, slice(None)
        rows, row_scalar = _selector_indices(row_selector, self.shape[0])
        channels, channel_scalar = _selector_indices(
            channel_selector, self.shape[1]
        )
        if rows.size == 0 or channels.size == 0:
            result = np.empty((rows.size, channels.size), dtype=self.dtype)
        else:
            start = int(rows.min())
            stop = int(rows.max()) + 1
            result = np.column_stack(
                [
                    self._channel_window(int(channel), start, stop)
                    for channel in channels
                ]
            )
            result = result[rows - start]
        if row_scalar and channel_scalar:
            return result[0, 0]
        if row_scalar:
            return result[0]
        if channel_scalar:
            return result[:, 0]
        return result


@lru_cache(maxsize=8)
def _legacy_array(
    file_paths: tuple[str, ...],
    frame_count: int,
    start_frame: int = 0,
    end_frame: int | None = None,
) -> OpenEphysLegacyArray:
    return OpenEphysLegacyArray(
        file_paths,
        frame_count,
        start_frame=start_frame,
        end_frame=end_frame,
    )


@lru_cache(maxsize=4)
def _spikeinterface_recording(
    reader_name: str,
    source_path: str,
    stream_id: str | None,
    channel_ids: tuple[str, ...],
    start_frame: int,
    end_frame: int | None,
):
    import spikeinterface.extractors as se

    reader = getattr(se, reader_name)
    kwargs: dict[str, Any] = {}
    if stream_id:
        kwargs["stream_id"] = stream_id
    recording = reader(Path(source_path), **kwargs)
    if channel_ids:
        available = {str(value): value for value in recording.channel_ids}
        resolved = [available[value] for value in channel_ids]
        if hasattr(recording, "select_channels"):
            recording = recording.select_channels(resolved)
        elif hasattr(recording, "channel_slice"):
            recording = recording.channel_slice(channel_ids=resolved)
        else:
            raise RuntimeError(
                "The installed SpikeInterface recording does not expose a channel-selection API"
            )
    if start_frame or end_frame is not None:
        recording = recording.frame_slice(
            start_frame=start_frame,
            end_frame=end_frame,
        )
    return recording


def get_recording_extractor(state: ProjectState):
    adapter = state.metadata.get("recording_adapter", {})
    if adapter.get("type") != "spikeinterface":
        raise RuntimeError("This project does not use a linked SpikeInterface source")
    if adapter.get("format") == "open_ephys_legacy":
        from spikeinterface.core import BaseRecording, BaseRecordingSegment

        source_array = _legacy_array(
            tuple(str(value) for value in adapter["channel_files"]),
            int(adapter["frame_count"]),
            int(adapter.get("start_frame", 0)),
            (
                int(adapter["end_frame"])
                if adapter.get("end_frame") is not None
                else None
            ),
        )

        class LegacySegment(BaseRecordingSegment):
            def __init__(self):
                super().__init__(sampling_frequency=state.sampling_rate)

            def get_num_samples(self) -> int:
                return source_array.shape[0]

            def get_traces(
                self,
                start_frame: int | None,
                end_frame: int | None,
                channel_indices: Any,
            ) -> np.ndarray:
                start = 0 if start_frame is None else int(start_frame)
                stop = (
                    source_array.shape[0]
                    if end_frame is None
                    else int(end_frame)
                )
                channels = (
                    slice(None)
                    if channel_indices is None
                    else channel_indices
                )
                return np.asarray(source_array[start:stop, channels])

        class LegacyRecording(BaseRecording):
            def __init__(self):
                super().__init__(
                    sampling_frequency=state.sampling_rate,
                    channel_ids=np.asarray(adapter["channel_ids"]),
                    dtype=state.dtype,
                )
                self.add_recording_segment(LegacySegment())
                self.set_channel_gains(
                    np.full(state.channel_count, state.scale_uv_per_bit)
                )
                self.set_channel_offsets(np.zeros(state.channel_count))

        return LegacyRecording()
    return _spikeinterface_recording(
        str(adapter["reader_name"]),
        str(adapter["source_path"]),
        adapter.get("stream_id"),
        tuple(str(value) for value in adapter.get("channel_ids", [])),
        int(adapter.get("start_frame", 0)),
        (
            int(adapter["end_frame"])
            if adapter.get("end_frame") is not None
            else None
        ),
    )


def load_linked_recording(state: ProjectState):
    adapter = state.metadata.get("recording_adapter", {})
    if adapter.get("format") == "open_ephys_legacy":
        return _legacy_array(
            tuple(str(value) for value in adapter["channel_files"]),
            int(adapter["frame_count"]),
            int(adapter.get("start_frame", 0)),
            (
                int(adapter["end_frame"])
                if adapter.get("end_frame") is not None
                else None
            ),
        )
    recording = get_recording_extractor(state)

    class SpikeInterfaceArray:
        shape = (recording.get_num_samples(), recording.get_num_channels())
        dtype = np.dtype(recording.get_dtype())

        def __getitem__(self, key: Any) -> np.ndarray:
            if isinstance(key, tuple):
                row_selector, channel_selector = key
            else:
                row_selector, channel_selector = key, slice(None)
            rows, row_scalar = _selector_indices(row_selector, self.shape[0])
            channels, channel_scalar = _selector_indices(
                channel_selector, self.shape[1]
            )
            if rows.size == 0 or channels.size == 0:
                result = np.empty((rows.size, channels.size), dtype=self.dtype)
            else:
                start = int(rows.min())
                stop = int(rows.max()) + 1
                channel_ids = [recording.channel_ids[index] for index in channels]
                result = recording.get_traces(
                    start_frame=start,
                    end_frame=stop,
                    channel_ids=channel_ids,
                )
                result = result[rows - start]
            if row_scalar and channel_scalar:
                return result[0, 0]
            if row_scalar:
                return result[0]
            if channel_scalar:
                return result[:, 0]
            return result

    return SpikeInterfaceArray()


def prepare_interleaved_binary(
    state: ProjectState,
    output_path: Path,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Create the sorter-required interleaved cache, never a new source copy."""
    if state.metadata.get("recording_adapter", {}).get("type") != "spikeinterface":
        if state.recording_path is None:
            raise RuntimeError("No raw recording is available")
        return state.recording_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    expected_bytes = (
        int(state.duration_seconds * state.sampling_rate)
        * state.channel_count
        * np.dtype(state.dtype).itemsize
    )
    if output_path.exists() and output_path.stat().st_size == expected_bytes:
        if progress:
            progress("Reusing the verified interleaved sorting cache")
        return output_path
    if progress:
        progress(
            "Preparing an interleaved cache for the selected channels; "
            "the linked source remains read-only"
    )
    recording = get_recording_extractor(state)
    frame_count = int(recording.get_num_frames())
    target_chunk_bytes = int(
        state.metadata.get(
            "interleaved_cache_chunk_bytes",
            64 * 1024 * 1024,
        )
    )
    bytes_per_frame = state.channel_count * np.dtype(state.dtype).itemsize
    chunk_frames = max(
        1,
        min(
            frame_count,
            target_chunk_bytes // max(bytes_per_frame, 1),
        ),
    )
    chunk_count = max(1, math.ceil(frame_count / chunk_frames))
    progress_interval = max(1, chunk_count // 20)
    with output_path.open("wb") as handle:
        for chunk_index, start_frame in enumerate(
            range(0, frame_count, chunk_frames),
            start=1,
        ):
            end_frame = min(start_frame + chunk_frames, frame_count)
            traces = recording.get_traces(
                start_frame=start_frame,
                end_frame=end_frame,
            )
            contiguous = np.ascontiguousarray(traces, dtype=state.dtype)
            contiguous.tofile(handle)
            if progress and (
                chunk_index == chunk_count
                or chunk_index % progress_interval == 0
            ):
                written_seconds = min(end_frame, frame_count) / state.sampling_rate
                progress(
                    "Interleaved cache: "
                    f"{written_seconds:.1f}/{state.duration_seconds:.1f} seconds "
                    f"written ({chunk_index}/{chunk_count} chunks)"
                )
    if output_path.stat().st_size != expected_bytes:
        raise RuntimeError(
            "The sorting cache size does not match the linked recording metadata"
        )
    return output_path
