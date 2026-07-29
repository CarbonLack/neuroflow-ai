from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from .models import ProjectState

TIME_COLUMNS = (
    "behavior_time_seconds",
    "time_seconds",
    "timestamp",
    "time",
    "frame",
    "sample",
)
TTL_COLUMNS = (
    "ttl_time_seconds",
    "ephys_time_seconds",
    "time_seconds",
    "timestamp",
    "time",
    "sample",
)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV contains no data rows: {path.name}")
    return rows


def _find_column(rows: list[dict[str, Any]], candidates: tuple[str, ...]) -> str:
    columns = {str(column).strip() for column in rows[0]}
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise ValueError(
        "No recognized time column was found. Expected one of: "
        + ", ".join(candidates)
    )


def _to_seconds(value: Any, unit: str, sampling_rate: float) -> float:
    numeric = float(value)
    if unit == "milliseconds":
        return numeric / 1000.0
    if unit == "samples":
        return numeric / sampling_rate
    return numeric


def import_behavior_events(
    state: ProjectState,
    behavior_path: Path,
    ttl_path: Path | None = None,
    time_unit: str = "seconds",
) -> dict[str, Any]:
    behavior_rows = _read_csv(behavior_path)
    behavior_column = _find_column(behavior_rows, TIME_COLUMNS)
    behavior_times = np.asarray(
        [
            _to_seconds(row[behavior_column], time_unit, state.sampling_rate)
            for row in behavior_rows
        ],
        dtype=float,
    )

    ttl_rows: list[dict[str, Any]] = []
    ttl_column: str | None = None
    if ttl_path:
        ttl_rows = _read_csv(ttl_path)
        ttl_column = _find_column(ttl_rows, TTL_COLUMNS)
        ephys_times = np.asarray(
            [
                _to_seconds(row[ttl_column], time_unit, state.sampling_rate)
                for row in ttl_rows
            ],
            dtype=float,
        )
    elif "ephys_time_seconds" in behavior_rows[0]:
        ttl_column = "ephys_time_seconds"
        ephys_times = np.asarray(
            [float(row[ttl_column]) for row in behavior_rows],
            dtype=float,
        )
    else:
        ephys_times = behavior_times.copy()

    matched_count = min(len(behavior_times), len(ephys_times))
    if matched_count < 1:
        raise ValueError("At least one behavior/TTL event is required")
    behavior_matched = behavior_times[:matched_count]
    ephys_matched = ephys_times[:matched_count]
    if matched_count >= 2 and not np.allclose(
        behavior_matched, behavior_matched[0]
    ):
        slope, intercept = np.polyfit(behavior_matched, ephys_matched, 1)
    else:
        slope = 1.0
        intercept = float(ephys_matched[0] - behavior_matched[0])
    predicted = intercept + slope * behavior_matched
    residual_ms = (ephys_matched - predicted) * 1000.0

    events: list[dict[str, Any]] = []
    for index, row in enumerate(behavior_rows):
        behavior_time = behavior_times[index]
        event = dict(row)
        event["trial"] = int(float(row.get("trial", index + 1)))
        event["behavior_time_seconds"] = float(behavior_time)
        event["time_seconds"] = float(intercept + slope * behavior_time)
        event["condition"] = str(row.get("condition", "all"))
        if row.get("reaction_time") not in {None, ""}:
            event["reaction_time"] = float(row["reaction_time"])
        if index < len(ephys_times):
            event["ttl_time_seconds"] = float(ephys_times[index])
            event["alignment_residual_ms"] = float(
                (ephys_times[index] - event["time_seconds"]) * 1000.0
            )
        events.append(event)

    result = {
        "status": "aligned" if ttl_path or ttl_column == "ephys_time_seconds" else "shared_clock",
        "behavior_file": str(behavior_path),
        "ttl_file": str(ttl_path) if ttl_path else None,
        "behavior_time_column": behavior_column,
        "ttl_time_column": ttl_column,
        "input_time_unit": time_unit,
        "behavior_event_count": len(behavior_times),
        "ttl_event_count": len(ephys_times),
        "matched_count": matched_count,
        "missing_behavior_events": max(len(ephys_times) - len(behavior_times), 0),
        "missing_ttl_events": max(len(behavior_times) - len(ephys_times), 0),
        "slope": float(slope),
        "intercept_seconds": float(intercept),
        "drift_ppm": float((slope - 1.0) * 1_000_000.0),
        "residual_ms": residual_ms.tolist(),
        "mean_abs_residual_ms": float(np.mean(np.abs(residual_ms))),
        "max_abs_residual_ms": float(np.max(np.abs(residual_ms))),
    }
    state.events = events
    state.trials = [dict(event) for event in events]
    state.metadata["synchronization"] = result
    state.metadata["behavior_source"] = str(behavior_path)
    state.metadata["ttl_source"] = str(ttl_path) if ttl_path else None
    state.log(
        "Behavior/ephys synchronization completed: "
        f"{matched_count} paired events, slope={slope:.9f}, "
        f"max residual={result['max_abs_residual_ms']:.3f} ms"
    )
    return result


def synchronize_existing_events(state: ProjectState) -> dict[str, Any]:
    if not state.events:
        raise RuntimeError("No behavior events are available")
    existing = state.metadata.get("synchronization", {})
    if (
        existing.get("status") == "aligned"
        and existing.get("method") == "piecewise_linear_ttl_anchors"
    ):
        state.trials = []
        state.log(
            "Existing piecewise MED-PC/TTL synchronization retained; "
            "trial boundaries remain undefined."
        )
        return existing
    behavior_times = np.asarray(
        [
            float(event.get("behavior_time_seconds", event["time_seconds"]))
            for event in state.events
        ],
        dtype=float,
    )
    ephys_times = np.asarray(
        [
            float(event.get("ttl_time_seconds", event["time_seconds"]))
            for event in state.events
        ],
        dtype=float,
    )
    if len(behavior_times) >= 2 and not np.allclose(
        behavior_times, behavior_times[0]
    ):
        slope, intercept = np.polyfit(behavior_times, ephys_times, 1)
    else:
        slope = 1.0
        intercept = float(ephys_times[0] - behavior_times[0])
    predicted = intercept + slope * behavior_times
    residual_ms = (ephys_times - predicted) * 1000.0
    for event, aligned, residual in zip(state.events, predicted, residual_ms):
        event["behavior_time_seconds"] = float(
            event.get("behavior_time_seconds", event["time_seconds"])
        )
        event["ttl_time_seconds"] = float(
            event.get("ttl_time_seconds", event["time_seconds"])
        )
        event["time_seconds"] = float(aligned)
        event["alignment_residual_ms"] = float(residual)
    if state.metadata.get("trial_definition", {}).get("status") == "not_defined":
        state.trials = []
    else:
        state.trials = [dict(event) for event in state.events]
    result = {
        "status": (
            "aligned"
            if any("ttl_time_seconds" in event for event in state.events)
            else "shared_clock"
        ),
        "behavior_file": state.metadata.get("behavior_source"),
        "ttl_file": state.metadata.get("ttl_source"),
        "behavior_time_column": "behavior_time_seconds",
        "ttl_time_column": "ttl_time_seconds",
        "input_time_unit": "seconds",
        "behavior_event_count": len(behavior_times),
        "ttl_event_count": len(ephys_times),
        "matched_count": len(behavior_times),
        "missing_behavior_events": 0,
        "missing_ttl_events": 0,
        "slope": float(slope),
        "intercept_seconds": float(intercept),
        "drift_ppm": float((slope - 1.0) * 1_000_000.0),
        "residual_ms": residual_ms.tolist(),
        "mean_abs_residual_ms": float(np.mean(np.abs(residual_ms))),
        "max_abs_residual_ms": float(np.max(np.abs(residual_ms))),
    }
    state.metadata["synchronization"] = result
    state.log(
        f"Existing events synchronized: {len(behavior_times)} events, "
        f"drift={result['drift_ppm']:.2f} ppm"
    )
    return result
