from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from .models import ProjectState
from .product import PRODUCT_NAME, PRODUCT_VERSION

MANIFEST_NAME = "neuroflow_project.json"


def _migrate_event_trial_semantics(state: ProjectState) -> None:
    """Repair legacy MED-PC projects that stored every event as a trial."""
    is_medpc = bool(
        state.metadata.get("medpc")
        or str(state.metadata.get("behavior_format", "")).upper() == "MED-PC"
    )
    if not is_medpc:
        return
    for index, event in enumerate(state.events, start=1):
        if "event_index" in event:
            event.pop("trial", None)
            event.setdefault("event_order", index)
    mirrored_events = (
        len(state.trials) == len(state.events)
        and all("event_index" in row for row in state.trials)
    )
    if mirrored_events:
        state.trials = []
    counts = Counter(
        int(event["event_code"])
        for event in state.events
        if event.get("event_code") is not None
    )
    state.metadata["event_inventory"] = {
        "total_events": len(state.events),
        "task_events": sum(
            event.get("analysis_role") == "task_event"
            for event in state.events
        ),
        "synchronization_events": sum(
            event.get("analysis_role") == "synchronization"
            for event in state.events
        ),
        "by_code": {
            str(code): {
                "label": next(
                    (
                        event.get("label", f"event_{code}")
                        for event in state.events
                        if int(event.get("event_code", -1)) == code
                    ),
                    f"event_{code}",
                ),
                "count": count,
            }
            for code, count in sorted(counts.items())
        },
    }
    state.metadata["trial_definition"] = {
        "status": "not_defined",
        "trial_count": 0,
        "reason": (
            "The MED-PC C/D arrays provide an event stream. Define task-specific "
            "trial start/end rules before trial-level analysis."
        ),
    }


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
    from .sorting_results import ensure_sorting_registry
    from .project_records import update_human_project_records

    ensure_sorting_registry(state)
    state.root.mkdir(parents=True, exist_ok=True)
    update_human_project_records(state)
    derived = state.root / "derived"
    derived.mkdir(exist_ok=True)
    sortings_dir = derived / "sortings"
    sortings_dir.mkdir(exist_ok=True)
    ground_truth_archive: str | None = None
    if state.ground_truth:
        ground_truth_path = derived / "ground_truth.npz"
        np.savez(
            ground_truth_path,
            **{
                f"unit_{unit_id}": spikes
                for unit_id, spikes in state.ground_truth.items()
            },
        )
        ground_truth_archive = str(ground_truth_path.relative_to(state.root))
    sorting_archives: dict[str, str] = {}
    for sorter_key, spikes_by_unit in state.sorting_results.items():
        sorting_path = sortings_dir / f"{sorter_key}.npz"
        np.savez(
            sorting_path,
            **{
                f"unit_{unit_id}": spikes
                for unit_id, spikes in spikes_by_unit.items()
            },
        )
        sorting_archives[sorter_key] = str(sorting_path.relative_to(state.root))

    payload = {
        "schema_version": 5,
        "application": PRODUCT_NAME,
        "application_version": PRODUCT_VERSION,
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
        "ground_truth_archive": ground_truth_archive,
        "sorting_archives": sorting_archives,
        "sorting_provenance": _jsonable(state.sorting_provenance),
        "active_sorter_key": state.active_sorter_key,
        "sorting_comparison": _jsonable(state.sorting_comparison),
        "qc": _jsonable(state.qc),
        "preprocessing": _jsonable(state.preprocessing),
        "unit_metrics": _jsonable(state.unit_metrics),
        "unit_diagnostics": _jsonable(state.unit_diagnostics),
        "unit_metrics_by_sorter": _jsonable(state.unit_metrics_by_sorter),
        "unit_diagnostics_by_sorter": _jsonable(
            state.unit_diagnostics_by_sorter
        ),
        "analysis": _jsonable(state.analysis),
        "spike_train_analysis": _jsonable(state.spike_train_analysis),
        "lfp_analysis": _jsonable(state.lfp_analysis),
        "spike_field_analysis": _jsonable(state.spike_field_analysis),
        "case_studies": _jsonable(state.case_studies),
        "statistics": _jsonable(state.statistics),
        "decoding": _jsonable(state.decoding),
        "regression": _jsonable(state.regression),
        "metadata": _jsonable(state.metadata),
        "workflow_status": state.workflow_status,
        "run_log": state.run_log,
    }
    path = state.root / MANIFEST_NAME
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_project(path: Path) -> ProjectState:
    manifest_path = path / MANIFEST_NAME if path.is_dir() else path
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    sorting_results: dict[str, dict[int, np.ndarray]] = {}
    for sorter_key, archive_value in payload.get("sorting_archives", {}).items():
        archive_path = Path(archive_value)
        if not archive_path.is_absolute():
            archive_path = manifest_path.parent / archive_path
        if archive_path.exists():
            with np.load(archive_path) as archive:
                sorting_results[sorter_key] = {
                    int(key.rsplit("_", 1)[-1]): archive[key] for key in archive.files
                }
    sorted_spikes: dict[int, np.ndarray] = {}
    ground_truth: dict[int, np.ndarray] = {}
    ground_truth_value = payload.get("ground_truth_archive")
    if ground_truth_value:
        ground_truth_path = Path(ground_truth_value)
        if not ground_truth_path.is_absolute():
            ground_truth_path = manifest_path.parent / ground_truth_path
        if ground_truth_path.exists():
            with np.load(ground_truth_path) as archive:
                ground_truth = {
                    int(key.rsplit("_", 1)[-1]): archive[key]
                    for key in archive.files
                }
    active_sorter_key = payload.get("active_sorter_key")
    if active_sorter_key in sorting_results:
        sorted_spikes = sorting_results[active_sorter_key]
    archive_value = payload.get("sorting_archive")
    if not sorted_spikes and archive_value:
        archive_path = Path(archive_value)
        if archive_path.exists():
            with np.load(archive_path) as archive:
                sorted_spikes = {
                    int(key.rsplit("_", 1)[-1]): archive[key]
                    for key in archive.files
                }
    unit_metrics_by_sorter = payload.get("unit_metrics_by_sorter", {})
    unit_diagnostics_by_sorter = {
        str(sorter_key): {
            int(unit_id): diagnostics
            for unit_id, diagnostics in sorter_diagnostics.items()
        }
        for sorter_key, sorter_diagnostics in payload.get(
            "unit_diagnostics_by_sorter",
            {},
        ).items()
    }
    if (
        not unit_metrics_by_sorter
        and active_sorter_key
        and payload.get("unit_metrics")
    ):
        unit_metrics_by_sorter = {
            str(active_sorter_key): payload.get("unit_metrics", [])
        }
    if (
        not unit_diagnostics_by_sorter
        and active_sorter_key
        and payload.get("unit_diagnostics")
    ):
        unit_diagnostics_by_sorter = {
            str(active_sorter_key): {
                int(key): value
                for key, value in payload.get("unit_diagnostics", {}).items()
            }
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
        ground_truth=ground_truth,
        sorted_spikes=sorted_spikes,
        sorting_results=sorting_results,
        sorting_provenance=payload.get("sorting_provenance", {}),
        active_sorter_key=active_sorter_key,
        sorting_comparison=payload.get("sorting_comparison", {}),
        qc=payload.get("qc", {}),
        preprocessing=payload.get("preprocessing", {}),
        unit_metrics=payload.get("unit_metrics", []),
        unit_diagnostics={
            int(key): value
            for key, value in payload.get("unit_diagnostics", {}).items()
        },
        unit_metrics_by_sorter=unit_metrics_by_sorter,
        unit_diagnostics_by_sorter=unit_diagnostics_by_sorter,
        analysis=payload.get("analysis", {}),
        spike_train_analysis=payload.get("spike_train_analysis", {}),
        lfp_analysis=payload.get("lfp_analysis", {}),
        spike_field_analysis=payload.get("spike_field_analysis", {}),
        case_studies=payload.get("case_studies", {}),
        statistics=payload.get("statistics", {}),
        decoding=payload.get("decoding", {}),
        regression=payload.get("regression", {}),
        metadata=payload.get("metadata", {}),
        workflow_status=payload.get("workflow_status", {}),
        run_log=payload.get("run_log", []),
    )
    from .sorting_results import ensure_sorting_registry

    ensure_sorting_registry(state)
    _migrate_event_trial_semantics(state)
    state.log("NeuroEphys AI project restored")
    return state
