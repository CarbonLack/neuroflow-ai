from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .models import ProjectState

MANIFEST_NAME = "neuroflow_project.json"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def save_project(state: ProjectState) -> Path:
    state.root.mkdir(parents=True, exist_ok=True)
    derived = state.root / "derived"
    derived.mkdir(exist_ok=True)
    sorting_path = derived / "sorted_spikes.npz"
    if state.sorted_spikes:
        np.savez(
            sorting_path,
            **{
                f"unit_{unit_id}": spikes
                for unit_id, spikes in state.sorted_spikes.items()
            },
        )

    payload = {
        "schema_version": 2,
        "name": state.name,
        "source_type": state.source_type,
        "source_path": str(state.source_path) if state.source_path else None,
        "recording_path": str(state.recording_path) if state.recording_path else None,
        "sampling_rate": state.sampling_rate,
        "channel_count": state.channel_count,
        "duration_seconds": state.duration_seconds,
        "dtype": state.dtype,
        "scale_uv_per_bit": state.scale_uv_per_bit,
        "electrode_type": state.electrode_type,
        "events": _jsonable(state.events),
        "trials": _jsonable(state.trials),
        "qc": _jsonable(state.qc),
        "unit_metrics": _jsonable(state.unit_metrics),
        "statistics": _jsonable(state.statistics),
        "decoding": _jsonable(state.decoding),
        "regression": _jsonable(state.regression),
        "metadata": _jsonable(state.metadata),
        "workflow_status": state.workflow_status,
        "run_log": state.run_log,
        "sorting_archive": str(sorting_path) if state.sorted_spikes else None,
    }
    path = state.root / MANIFEST_NAME
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_project(path: Path) -> ProjectState:
    manifest_path = path / MANIFEST_NAME if path.is_dir() else path
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    sorted_spikes: dict[int, np.ndarray] = {}
    archive_path = payload.get("sorting_archive")
    if archive_path and Path(archive_path).exists():
        archive = np.load(archive_path)
        sorted_spikes = {
            int(key.rsplit("_", 1)[-1]): archive[key] for key in archive.files
        }
    state = ProjectState(
        root=manifest_path.parent,
        name=payload.get("name", manifest_path.parent.name),
        source_type=payload.get("source_type", "unknown"),
        source_path=Path(payload["source_path"])
        if payload.get("source_path")
        else None,
        recording_path=(
            Path(payload["recording_path"]) if payload.get("recording_path") else None
        ),
        sampling_rate=float(payload.get("sampling_rate", 30_000)),
        channel_count=int(payload.get("channel_count", 0)),
        duration_seconds=float(payload.get("duration_seconds", 0)),
        dtype=payload.get("dtype", "int16"),
        scale_uv_per_bit=float(payload.get("scale_uv_per_bit", 1.0)),
        electrode_type=payload.get("electrode_type", "generic"),
        events=payload.get("events", []),
        trials=payload.get("trials", []),
        sorted_spikes=sorted_spikes,
        qc=payload.get("qc", {}),
        unit_metrics=payload.get("unit_metrics", []),
        statistics=payload.get("statistics", {}),
        decoding=payload.get("decoding", {}),
        regression=payload.get("regression", {}),
        metadata=payload.get("metadata", {}),
        workflow_status=payload.get("workflow_status", {}),
        run_log=payload.get("run_log", []),
    )
    if (
        state.sorted_spikes
        and state.events
        and (
            state.statistics
            or state.decoding
            or state.workflow_status.get("analysis") == "completed"
        )
    ):
        from .analysis import event_aligned_analysis

        event_aligned_analysis(state)
    state.log("已恢复 NeuroFlow 项目")
    return state
