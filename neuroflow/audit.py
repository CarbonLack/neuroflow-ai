from __future__ import annotations

import json
import time
import traceback
import uuid
import warnings
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from .models import ProjectState
from .artifacts import project_file_snapshot, register_changed_artifacts

AUDIT_SCHEMA = "neuroflow.stage-audit.v1"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def audit_log_path(state: ProjectState) -> Path:
    return state.root / "logs" / "structured_runs.jsonl"


def _append_event(state: ProjectState, record: dict[str, Any]) -> None:
    path = audit_log_path(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(_jsonable(record), ensure_ascii=False, separators=(",", ":"))
            + "\n"
        )


@contextmanager
def audited_stage(
    state: ProjectState,
    stage: str,
    *,
    input_files: list[str | Path] | None = None,
    channel_selection: str | list[str] | None = None,
    segment: dict[str, float] | None = None,
    tool: str | None = None,
    tool_version: str | None = None,
    parameters: dict[str, Any] | None = None,
    expected_outputs: list[str | Path] | None = None,
    recovery: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Audit one stage and capture duration, warnings, errors, and outputs."""
    run_id = uuid.uuid4().hex
    started_at = _now()
    started_counter = time.perf_counter()
    record: dict[str, Any] = {
        "schema": AUDIT_SCHEMA,
        "run_id": run_id,
        "timestamp": started_at,
        "project": state.name,
        "project_root": str(state.root),
        "stage": stage,
        "input_files": [str(value) for value in input_files or []],
        "channel_selection": channel_selection,
        "segment": segment or {},
        "tool": tool,
        "tool_version": tool_version,
        "parameters": parameters or {},
        "started_at": started_at,
        "ended_at": None,
        "elapsed_seconds": None,
        "status": "running",
        "outputs": [str(value) for value in expected_outputs or []],
        "warnings": [],
        "error": None,
        "recovery": recovery,
        "artifacts": [],
    }
    before_files = project_file_snapshot(state)
    _append_event(state, record)
    state.log(f"{stage} started ({run_id[:8]})")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            yield record
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            raise
        else:
            record["status"] = "completed"
        finally:
            record["ended_at"] = _now()
            record["elapsed_seconds"] = float(time.perf_counter() - started_counter)
            captured = [
                {
                    "category": item.category.__name__,
                    "message": str(item.message),
                    "filename": item.filename,
                    "line": int(item.lineno),
                }
                for item in caught
            ]
            record["warnings"] = [
                *record.get("warnings", []),
                *captured,
            ]
            if record["status"] == "completed":
                record["artifacts"] = register_changed_artifacts(
                    state,
                    before=before_files,
                    stage=stage,
                    run_id=run_id,
                    tool=tool,
                    parameters=parameters or {},
                    input_files=[str(value) for value in input_files or []],
                )
            stored = _jsonable(record)
            state.metadata.setdefault("structured_run_log", []).append(stored)
            run_record_path = state.root / "logs" / "runs" / f"{run_id}.json"
            run_record_path.parent.mkdir(parents=True, exist_ok=True)
            run_record_path.write_text(
                json.dumps(stored, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            _append_event(state, stored)
            state.log(
                f"{stage} {record['status']} in "
                f"{record['elapsed_seconds']:.3f} s ({run_id[:8]})"
            )


def completed_stage_timings(state: ProjectState) -> list[dict[str, Any]]:
    return [
        record
        for record in state.metadata.get("structured_run_log", [])
        if record.get("status") in {"completed", "failed"}
    ]
