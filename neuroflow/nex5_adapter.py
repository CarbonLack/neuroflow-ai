from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .audit import audited_stage
from .models import ProjectState
from .project import save_project
from .sorting_results import register_sorting_result

NEX5_IMPORT_SCHEMA = "neuroephys.nex5-import.v1"
_CHANNEL_PATTERN = re.compile(r"^CH(?P<channel>\d+)(?P<label>.*)$", re.IGNORECASE)


@dataclass(frozen=True)
class Nex5Unit:
    unit_id: int
    source_file: Path
    source_variable: str
    channel_number: int | None
    channel_label: str | None
    source_group: str | None
    timestamps_seconds: np.ndarray
    waveform_mean: np.ndarray | None
    waveform_std: np.ndarray | None
    waveform_sampling_rate_hz: float | None


def _reader():
    try:
        from nex5file.reader import Reader
    except ImportError as exc:  # pragma: no cover - exercised by packaged builds
        raise RuntimeError(
            "Reading NeuroExplorer files requires nex5file==0.1.3. "
            "Install the NeuroEphys AI optional NEX5 dependency."
        ) from exc
    return Reader()


def discover_nex5_files(
    source: Path,
    *,
    filename_filter: str | None = None,
) -> list[Path]:
    """Resolve one .nex5 file or a folder tree without changing the source."""
    source = Path(source)
    if source.is_file():
        paths = [source] if source.suffix.lower() == ".nex5" else []
    elif source.is_dir():
        paths = sorted(source.rglob("*.nex5"))
    else:
        paths = []
    token = (filename_filter or "").strip().casefold()
    if token:
        paths = [path for path in paths if token in path.name.casefold()]
    if not paths:
        detail = f" matching {filename_filter!r}" if filename_filter else ""
        raise ValueError(f"No .nex5 files found{detail}: {source}")
    return paths


def _source_group(path: Path) -> str | None:
    match = re.search(r"_(LO|MO)(?:\.nex5)$", path.name, re.IGNORECASE)
    return match.group(1).upper() if match else None


def _unit_identity(name: str) -> tuple[int | None, str | None]:
    match = _CHANNEL_PATTERN.match(name.strip())
    if not match:
        return None, None
    label = match.group("label").strip() or None
    return int(match.group("channel")), label


def inspect_nex5_source(
    source: Path,
    *,
    filename_filter: str | None = None,
) -> dict[str, Any]:
    files = discover_nex5_files(source, filename_filter=filename_filter)
    rows: list[dict[str, Any]] = []
    for path in files:
        data = _reader().ReadNex5HeadersOnly(str(path))
        neurons = [
            variable
            for variable in data.variables
            if int(variable.header.Type) == 0
        ]
        waveforms = [
            variable
            for variable in data.variables
            if int(variable.header.Type) == 3
        ]
        rows.append(
            {
                "path": str(path),
                "timestamp_frequency_hz": float(data.GetTimestampFrequency()),
                "start_seconds": float(data.GetDocStartTime()),
                "end_seconds": float(data.GetDocEndTime()),
                "duration_seconds": float(
                    data.GetDocEndTime() - data.GetDocStartTime()
                ),
                "neuron_count": len(neurons),
                "waveform_count": len(waveforms),
                "neuron_names": [variable.header.Name for variable in neurons],
                "source_group": _source_group(path),
            }
        )
    return {
        "schema": NEX5_IMPORT_SCHEMA,
        "source": str(source),
        "filename_filter": filename_filter,
        "file_count": len(files),
        "unit_count": sum(row["neuron_count"] for row in rows),
        "files": rows,
    }


def _alignment_offset(
    *,
    mode: str,
    document_start: float,
    document_end: float,
    project_duration: float,
    manual_offset_seconds: float,
    project_is_segment: bool,
) -> tuple[float, str, list[str]]:
    warnings: list[str] = []
    if mode == "manual":
        return (
            float(manual_offset_seconds),
            "manual offset supplied by user",
            warnings,
        )
    if mode == "preserve":
        return 0.0, "source timestamps preserved", warnings
    if mode != "auto_project_duration":
        raise ValueError(f"Unsupported NEX5 alignment mode: {mode}")
    if project_is_segment:
        raise ValueError(
            "Automatic NEX5 end alignment is unavailable for a recording "
            "segment. Choose 'preserve source timestamps' when both files "
            "already use the same clock, or enter a verified manual offset."
        )
    if project_duration <= 0:
        warnings.append(
            "Project duration is unavailable; source timestamps were preserved."
        )
        return 0.0, "auto alignment unavailable", warnings
    source_duration = float(document_end - document_start)
    offset = float(document_end - project_duration)
    if offset < -0.5:
        warnings.append(
            "NEX5 duration is shorter than the project recording; automatic "
            "offset was rejected and timestamps were preserved."
        )
        return 0.0, "auto alignment rejected", warnings
    if abs(offset) <= 0.5:
        return 0.0, "durations already agree", warnings
    if offset > max(source_duration * 0.25, 600.0):
        warnings.append(
            "The inferred NEX5 clock offset is unusually large; verify the "
            "session identity before interpreting sorter agreement."
        )
    return (
        offset,
        "document end aligned to project recording duration",
        warnings,
    )


def _waveform_lookup(data) -> dict[str, Any]:
    lookup: dict[str, Any] = {}
    for variable in data.variables:
        if int(variable.header.Type) != 3:
            continue
        name = str(variable.header.Name)
        key = name[:-3] if name.lower().endswith("_wf") else name
        lookup[key] = variable
    return lookup


def _read_units(
    paths: list[Path],
    *,
    project_duration: float,
    project_is_segment: bool,
    alignment_mode: str,
    manual_offset_seconds: float,
) -> tuple[list[Nex5Unit], dict[str, Any], dict[str, np.ndarray]]:
    units: list[Nex5Unit] = []
    files: list[dict[str, Any]] = []
    waveform_arrays: dict[str, np.ndarray] = {}
    next_unit_id = 0
    for path in paths:
        data = _reader().ReadNex5File(str(path))
        document_start = float(data.GetDocStartTime())
        document_end = float(data.GetDocEndTime())
        offset, method, file_warnings = _alignment_offset(
            mode=alignment_mode,
            document_start=document_start,
            document_end=document_end,
            project_duration=project_duration,
            manual_offset_seconds=manual_offset_seconds,
            project_is_segment=project_is_segment,
        )
        waveform_by_name = _waveform_lookup(data)
        file_rows: list[dict[str, Any]] = []
        for variable in data.variables:
            if int(variable.header.Type) != 0:
                continue
            name = str(variable.header.Name)
            timestamps = np.asarray(variable.Timestamps(), dtype=np.float64) - offset
            finite = np.isfinite(timestamps)
            timestamps = timestamps[finite]
            source_count = int(timestamps.size)
            if project_duration > 0:
                timestamps = timestamps[
                    (timestamps >= 0.0) & (timestamps <= project_duration)
                ]
            else:
                timestamps = timestamps[timestamps >= 0.0]
            timestamps = np.unique(np.sort(timestamps))
            channel_number, channel_label = _unit_identity(name)
            waveform = waveform_by_name.get(name)
            waveform_mean: np.ndarray | None = None
            waveform_std: np.ndarray | None = None
            waveform_rate: float | None = None
            if waveform is not None:
                values = np.asarray(waveform.WaveformValues(), dtype=np.float32)
                if values.ndim == 2 and values.shape[0]:
                    waveform_mean = np.mean(values, axis=0, dtype=np.float64)
                    waveform_std = np.std(values, axis=0, dtype=np.float64)
                    waveform_rate = float(waveform.SamplingRate())
                    waveform_arrays[f"unit_{next_unit_id}_mean"] = waveform_mean
                    waveform_arrays[f"unit_{next_unit_id}_std"] = waveform_std
            unit = Nex5Unit(
                unit_id=next_unit_id,
                source_file=path,
                source_variable=name,
                channel_number=channel_number,
                channel_label=channel_label,
                source_group=_source_group(path),
                timestamps_seconds=timestamps,
                waveform_mean=waveform_mean,
                waveform_std=waveform_std,
                waveform_sampling_rate_hz=waveform_rate,
            )
            units.append(unit)
            file_rows.append(
                {
                    "unit_id": next_unit_id,
                    "source_variable": name,
                    "channel_number": channel_number,
                    "channel_label": channel_label,
                    "source_group": unit.source_group,
                    "source_spike_count": source_count,
                    "retained_spike_count": int(timestamps.size),
                }
            )
            next_unit_id += 1
        files.append(
            {
                "path": str(path),
                "document_start_seconds": document_start,
                "document_end_seconds": document_end,
                "alignment_offset_seconds": offset,
                "alignment_method": method,
                "warnings": file_warnings,
                "units": file_rows,
            }
        )
    summary = {
        "schema": NEX5_IMPORT_SCHEMA,
        "alignment_mode": alignment_mode,
        "project_is_segment": bool(project_is_segment),
        "project_duration_seconds": float(project_duration),
        "file_count": len(paths),
        "unit_count": len(units),
        "spike_count": int(sum(unit.timestamps_seconds.size for unit in units)),
        "files": files,
    }
    return units, summary, waveform_arrays


def import_nex5_sorting_into_project(
    state: ProjectState,
    source: Path,
    *,
    sorter_key: str = "offline_sorter_nex5",
    filename_filter: str | None = None,
    alignment_mode: str = "auto_project_duration",
    manual_offset_seconds: float = 0.0,
    activate: bool = True,
) -> dict[str, Any]:
    """Attach NeuroExplorer/Offline Sorter output to a NeuroEphys AI project."""
    paths = discover_nex5_files(source, filename_filter=filename_filter)
    adapter = state.metadata.get("recording_adapter", {})
    frame_count = int(adapter.get("frame_count") or 0)
    start_frame = int(adapter.get("start_frame") or 0)
    configured_end = adapter.get("end_frame")
    end_frame = int(configured_end) if configured_end is not None else frame_count
    project_is_segment = bool(
        frame_count
        and (
            start_frame > 0
            or (configured_end is not None and end_frame < frame_count)
        )
    )
    output_dir = state.root / "derived" / "external_sortings" / sorter_key
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "nex5_import_summary.json"
    inventory_path = output_dir / "unit_inventory.csv"
    waveform_path = output_dir / "waveform_summaries.npz"
    with audited_stage(
        state,
        "external_sorting_import",
        input_files=paths,
        tool="NeuroExplorer nex5file",
        tool_version="0.1.3",
        parameters={
            "sorter_key": sorter_key,
            "filename_filter": filename_filter,
            "alignment_mode": alignment_mode,
            "manual_offset_seconds": float(manual_offset_seconds),
            "project_is_segment": project_is_segment,
        },
        expected_outputs=[summary_path, inventory_path, waveform_path],
        recovery="Source files stay read-only; correct the mapping or offset and re-import.",
    ) as audit:
        units, summary, waveforms = _read_units(
            paths,
            project_duration=float(state.duration_seconds),
            project_is_segment=project_is_segment,
            alignment_mode=alignment_mode,
            manual_offset_seconds=float(manual_offset_seconds),
        )
        spikes = {
            unit.unit_id: unit.timestamps_seconds
            for unit in units
        }
        unit_metadata = {
            str(unit.unit_id): {
                "source_file": str(unit.source_file),
                "source_variable": unit.source_variable,
                "channel_number": unit.channel_number,
                "channel_label": unit.channel_label,
                "source_group": unit.source_group,
                "waveform_sampling_rate_hz": unit.waveform_sampling_rate_hz,
                "waveform_summary_archive": str(waveform_path),
                "curation_status": "candidate_external_unit",
            }
            for unit in units
        }
        register_sorting_result(
            state,
            sorter_key,
            spikes,
            {
                "sorter": "Offline Sorter / NeuroExplorer import",
                "backend": "nex5file",
                "source_files": [str(path) for path in paths],
                "source_files_read_only": True,
                "filename_filter": filename_filter,
                "alignment_mode": alignment_mode,
                "unit_metadata": unit_metadata,
                "external_result_role": "comparison_reference_not_ground_truth",
            },
            activate=activate,
        )
        rows: list[dict[str, Any]] = []
        for unit in units:
            rows.append(
                {
                    "unit_id": unit.unit_id,
                    "source_variable": unit.source_variable,
                    "channel_number": unit.channel_number,
                    "channel_label": unit.channel_label,
                    "source_group": unit.source_group,
                    "spike_count": int(unit.timestamps_seconds.size),
                    "first_spike_seconds": (
                        float(unit.timestamps_seconds[0])
                        if unit.timestamps_seconds.size
                        else None
                    ),
                    "last_spike_seconds": (
                        float(unit.timestamps_seconds[-1])
                        if unit.timestamps_seconds.size
                        else None
                    ),
                    "waveform_sampling_rate_hz": unit.waveform_sampling_rate_hz,
                }
            )
        with inventory_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)
        np.savez(waveform_path, **waveforms)
        summary.update(
            {
                "sorter_key": sorter_key,
                "source": str(source),
                "filename_filter": filename_filter,
                "unit_inventory": str(inventory_path),
                "waveform_summaries": str(waveform_path),
                "interpretation": (
                    "Imported units are external candidate units. They are not ground "
                    "truth and require waveform, refractory-period, stability, and "
                    "manual curation review."
                ),
            }
        )
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        audit["outputs"] = [
            str(summary_path),
            str(inventory_path),
            str(waveform_path),
        ]
        audit["warnings"].extend(
            warning
            for file_summary in summary["files"]
            for warning in file_summary["warnings"]
        )
    state.metadata.setdefault("external_sorting_imports", {})[sorter_key] = summary
    state.workflow_status["sorting"] = "completed"
    state.log(
        f"NEX5 sorting imported as {sorter_key}: "
        f"{summary['unit_count']} candidate units, {summary['spike_count']} spikes"
    )
    save_project(state)
    return summary
