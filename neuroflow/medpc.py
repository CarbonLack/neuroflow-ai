from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .models import ProjectState

CONFIRMED_EVENT_DICTIONARY = {
    1: {
        "label": "well_head",
        "zh_label": "进入取食/饮水口",
        "family": "well",
        "phase": "start",
        "analysis_role": "task_event",
        "description": "Well-head event",
    },
    2: {
        "label": "well_release",
        "zh_label": "离开取食/饮水口",
        "family": "well",
        "phase": "end",
        "analysis_role": "task_event",
        "description": "Well-release event",
    },
    3: {
        "label": "pump_on",
        "zh_label": "水泵开启",
        "family": "pump",
        "phase": "on",
        "analysis_role": "task_event",
        "description": "Pump on; the older pellet-on definition is not used",
    },
    4: {
        "label": "pump_off",
        "zh_label": "水泵关闭",
        "family": "pump",
        "phase": "off",
        "analysis_role": "task_event",
        "description": "Pump off; the older pellet-off definition is not used",
    },
    5: {
        "label": "left_light_on",
        "zh_label": "左灯开启",
        "family": "left_light",
        "phase": "on",
        "analysis_role": "task_event",
        "description": "Left cue light on",
    },
    6: {
        "label": "left_light_off",
        "zh_label": "左灯关闭",
        "family": "left_light",
        "phase": "off",
        "analysis_role": "task_event",
        "description": "Left cue light off",
    },
    7: {
        "label": "right_light_on",
        "zh_label": "右灯开启",
        "family": "right_light",
        "phase": "on",
        "analysis_role": "task_event",
        "description": "Right cue light on",
    },
    8: {
        "label": "right_light_off",
        "zh_label": "右灯关闭",
        "family": "right_light",
        "phase": "off",
        "analysis_role": "task_event",
        "description": "Right cue light off",
    },
    9: {
        "label": "noise_on",
        "zh_label": "声音开启",
        "family": "noise",
        "phase": "on",
        "analysis_role": "task_event",
        "description": "Noise stimulus on",
    },
    10: {
        "label": "noise_off",
        "zh_label": "声音关闭",
        "family": "noise",
        "phase": "off",
        "analysis_role": "task_event",
        "description": "Noise stimulus off",
    },
    11: {
        "label": "synchronization_on",
        "zh_label": "同步信号开启",
        "family": "synchronization",
        "phase": "on",
        "analysis_role": "synchronization",
        "description": "MED-PC synchronization signal rising/on edge",
    },
    12: {
        "label": "synchronization_off",
        "zh_label": "同步信号关闭",
        "family": "synchronization",
        "phase": "off",
        "analysis_role": "synchronization",
        "description": "MED-PC synchronization signal falling/off edge",
    },
    17: {
        "label": "left_lever_start",
        "zh_label": "左杆动作开始",
        "family": "left_lever_movement",
        "phase": "start",
        "analysis_role": "task_event",
        "description": "Left lever movement starts",
    },
    18: {
        "label": "left_lever_end",
        "zh_label": "左杆动作结束",
        "family": "left_lever_movement",
        "phase": "end",
        "analysis_role": "task_event",
        "description": "Left lever movement ends",
    },
    19: {
        "label": "right_lever_start",
        "zh_label": "右杆动作开始",
        "family": "right_lever_movement",
        "phase": "start",
        "analysis_role": "task_event",
        "description": "Right lever movement starts",
    },
    20: {
        "label": "right_lever_end",
        "zh_label": "右杆动作结束",
        "family": "right_lever_movement",
        "phase": "end",
        "analysis_role": "task_event",
        "description": "Right lever movement ends",
    },
    21: {
        "label": "left_lever_on",
        "zh_label": "左杆呈现",
        "family": "left_lever_availability",
        "phase": "on",
        "analysis_role": "task_event",
        "description": "Left lever on/extended",
    },
    22: {
        "label": "right_lever_on",
        "zh_label": "右杆呈现",
        "family": "right_lever_availability",
        "phase": "on",
        "analysis_role": "task_event",
        "description": "Right lever on/extended",
    },
    23: {
        "label": "left_lever_off",
        "zh_label": "左杆收回",
        "family": "left_lever_availability",
        "phase": "off",
        "analysis_role": "task_event",
        "description": "Left lever off/retracted",
    },
    24: {
        "label": "right_lever_off",
        "zh_label": "右杆收回",
        "family": "right_lever_availability",
        "phase": "off",
        "analysis_role": "task_event",
        "description": "Right lever off/retracted",
    },
}


@dataclass(frozen=True)
class MedPCRecord:
    path: Path
    metadata: dict[str, str]
    scalars: dict[str, float]
    arrays: dict[str, np.ndarray]


def parse_medpc_file(path: Path) -> MedPCRecord:
    """Parse one MED-PC text export while preserving unknown event codes."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    metadata: dict[str, str] = {}
    scalars: dict[str, float] = {}
    arrays: dict[str, list[float]] = {}
    current_array: str | None = None
    for line in text.splitlines():
        variable = re.match(r"^([A-Z]):\s*(.*)$", line)
        if variable:
            key, value = variable.groups()
            if value.strip():
                try:
                    scalars[key] = float(value)
                except ValueError:
                    pass
                current_array = None
            else:
                current_array = key
                arrays[current_array] = []
            continue
        indexed = re.match(r"^\s*\d+:\s*(.*)$", line)
        if current_array and indexed:
            for token in indexed.group(1).split():
                try:
                    arrays[current_array].append(float(token))
                except ValueError:
                    continue
            continue
        header = re.match(
            r"^\s*(File|Start Date|End Date|Subject|Experiment|Group|Box|"
            r"Start Time|End Time|MSN):\s*(.*?)\s*$",
            line,
        )
        if header:
            metadata[header.group(1)] = header.group(2)
    parsed_arrays = {
        key: np.asarray(values, dtype=float) for key, values in arrays.items()
    }
    return MedPCRecord(path, metadata, scalars, parsed_arrays)


def _match_periodic_anchors(
    behavior_times: np.ndarray,
    ephys_times: np.ndarray,
    tolerance_seconds: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    if not len(behavior_times) or not len(ephys_times):
        raise ValueError("Both MED-PC and electrophysiology TTL anchors are required")
    offset = float(ephys_times[0] - behavior_times[0])
    behavior_indices: list[int] = []
    ephys_indices: list[int] = []
    last_ephys_index = -1
    for behavior_index, behavior_time in enumerate(behavior_times):
        target = behavior_time + offset
        insertion = int(np.searchsorted(ephys_times, target))
        candidates = [
            index
            for index in (insertion - 1, insertion, insertion + 1)
            if last_ephys_index < index < len(ephys_times)
        ]
        if not candidates:
            continue
        best = min(candidates, key=lambda index: abs(ephys_times[index] - target))
        if abs(ephys_times[best] - target) <= tolerance_seconds:
            behavior_indices.append(behavior_index)
            ephys_indices.append(best)
            last_ephys_index = best
            recent = min(len(behavior_indices), 100)
            offset = float(
                np.median(
                    ephys_times[np.asarray(ephys_indices[-recent:])]
                    - behavior_times[np.asarray(behavior_indices[-recent:])]
                )
            )
    if len(behavior_indices) < 2:
        raise ValueError("Fewer than two behavior/TTL anchors could be matched")
    return np.asarray(behavior_indices, dtype=int), np.asarray(ephys_indices, dtype=int)


def _piecewise_map(
    values: np.ndarray,
    behavior_anchors: np.ndarray,
    ephys_anchors: np.ndarray,
) -> np.ndarray:
    mapped = np.interp(values, behavior_anchors, ephys_anchors)
    if len(behavior_anchors) < 2:
        return mapped
    first_slope = (ephys_anchors[1] - ephys_anchors[0]) / max(
        behavior_anchors[1] - behavior_anchors[0], np.finfo(float).eps
    )
    last_slope = (ephys_anchors[-1] - ephys_anchors[-2]) / max(
        behavior_anchors[-1] - behavior_anchors[-2], np.finfo(float).eps
    )
    before = values < behavior_anchors[0]
    after = values > behavior_anchors[-1]
    mapped[before] = ephys_anchors[0] + (
        values[before] - behavior_anchors[0]
    ) * first_slope
    mapped[after] = ephys_anchors[-1] + (
        values[after] - behavior_anchors[-1]
    ) * last_slope
    return mapped


def import_medpc_behavior(
    state: ProjectState,
    behavior_path: Path,
    ttl_channel: int,
    sync_event_code: int = 11,
    rising_edge: bool = True,
) -> dict[str, Any]:
    """Import MED-PC events and align them to one Open Ephys digital input."""
    record = parse_medpc_file(behavior_path)
    if "C" not in record.arrays or "D" not in record.arrays:
        raise ValueError("MED-PC import requires paired C event-code and D time arrays")
    codes = record.arrays["C"].astype(int)
    behavior_times = record.arrays["D"].astype(float)
    if len(codes) != len(behavior_times):
        raise ValueError("MED-PC C and D arrays have different lengths")
    if np.any(np.diff(behavior_times) < 0):
        raise ValueError("MED-PC D event times are not monotonic")

    edge_name = "rising" if rising_edge else "falling"
    digital_events = [
        event
        for event in state.metadata.get("digital_events", [])
        if int(event.get("channel", -1)) == int(ttl_channel)
        and event.get("edge") == edge_name
    ]
    ephys_ttl = np.asarray(
        [float(event["time_seconds"]) for event in digital_events],
        dtype=float,
    )
    behavior_ttl = behavior_times[codes == int(sync_event_code)]
    behavior_indices, ephys_indices = _match_periodic_anchors(
        behavior_ttl,
        ephys_ttl,
    )
    matched_behavior = behavior_ttl[behavior_indices]
    matched_ephys = ephys_ttl[ephys_indices]
    slope, intercept = np.polyfit(matched_behavior, matched_ephys, 1)
    global_residual_ms = (
        matched_ephys - (intercept + slope * matched_behavior)
    ) * 1000.0
    aligned_times = _piecewise_map(
        behavior_times,
        matched_behavior,
        matched_ephys,
    )

    events: list[dict[str, Any]] = []
    for index, (code, behavior_time, aligned_time) in enumerate(
        zip(codes, behavior_times, aligned_times),
        start=1,
    ):
        known = CONFIRMED_EVENT_DICTIONARY.get(int(code))
        events.append(
            {
                "event_order": index,
                "event_index": index - 1,
                "event_code": int(code),
                "label": known["label"] if known else f"MED-PC code {int(code)}",
                "zh_label": (
                    known["zh_label"] if known else f"MED-PC 事件码 {int(code)}"
                ),
                "description": (
                    known["description"]
                    if known
                    else "MED-PC event code without a confirmed semantic mapping"
                ),
                "condition": known["label"] if known else f"code_{int(code)}",
                "event_semantics_status": "confirmed" if known else "unmapped",
                "analysis_role": (
                    known["analysis_role"] if known else "unmapped_event"
                ),
                "event_family": known["family"] if known else "unmapped",
                "event_phase": known["phase"] if known else "unknown",
                "behavior_time_seconds": float(behavior_time),
                "time_seconds": float(aligned_time),
            }
        )

    result = {
        "status": "aligned",
        "method": "piecewise_linear_ttl_anchors",
        "behavior_file": str(record.path),
        "behavior_format": "MED-PC text",
        "subject": record.metadata.get("Subject"),
        "box": record.metadata.get("Box"),
        "msn": record.metadata.get("MSN"),
        "ttl_channel": int(ttl_channel),
        "ttl_edge": edge_name,
        "sync_event_code": int(sync_event_code),
        "behavior_event_count": len(behavior_times),
        "behavior_anchor_count": len(behavior_ttl),
        "ttl_event_count": len(ephys_ttl),
        "matched_count": len(matched_behavior),
        "missing_behavior_anchors": max(len(ephys_ttl) - len(matched_behavior), 0),
        "missing_ttl_anchors": max(len(behavior_ttl) - len(matched_behavior), 0),
        "slope": float(slope),
        "intercept_seconds": float(intercept),
        "drift_ppm": float((slope - 1.0) * 1_000_000.0),
        "global_fit_residual_ms": global_residual_ms.tolist(),
        "mean_abs_residual_ms": float(np.mean(np.abs(global_residual_ms))),
        "max_abs_residual_ms": float(np.max(np.abs(global_residual_ms))),
        "mapping_note": (
            "All behavior events use piecewise interpolation between matched TTL "
            "anchors. Global-fit residuals are retained as clock-quality evidence."
        ),
    }
    state.events = events
    state.trials = []
    state.metadata["behavior_source"] = str(record.path)
    state.metadata["behavior_format"] = "MED-PC"
    state.metadata["medpc"] = {
        "metadata": record.metadata,
        "scalars": record.scalars,
        "array_lengths": {
            key: len(value) for key, value in record.arrays.items()
        },
        "event_codes": sorted(int(value) for value in np.unique(codes)),
        "event_dictionary_status": (
            "complete_for_observed_codes"
            if all(int(code) in CONFIRMED_EVENT_DICTIONARY for code in np.unique(codes))
            else "partial"
        ),
        "confirmed_event_dictionary": CONFIRMED_EVENT_DICTIONARY,
        "event_dictionary_source": "User-provided MED-PC event ID table, 2026-07-28",
        "event_dictionary_warning": (
            "Observed codes are mapped from the supplied MED-PC event table. "
            "Codes 3/4 use the active pump on/off definition, not the commented "
            "legacy pellet definition. Lever availability pairs are 21/23 and 22/24."
        ),
    }
    observed_codes = sorted(int(value) for value in np.unique(codes))
    state.metadata["event_inventory"] = {
        "total_events": len(events),
        "task_events": sum(
            event.get("analysis_role") == "task_event" for event in events
        ),
        "synchronization_events": sum(
            event.get("analysis_role") == "synchronization"
            for event in events
        ),
        "by_code": {
            str(code): {
                "label": next(
                    (
                        event["label"]
                        for event in events
                        if event["event_code"] == code
                    ),
                    f"MED-PC code {code}",
                ),
                "count": int(np.sum(codes == code)),
            }
            for code in observed_codes
        },
    }
    state.metadata["trial_definition"] = {
        "status": "not_defined",
        "trial_count": 0,
        "reason": (
            "The MED-PC C/D arrays provide an event stream. A trial table requires "
            "an explicit task-specific start/end rule."
        ),
    }
    state.metadata["synchronization"] = result
    state.log(
        "MED-PC behavior imported and aligned: "
        f"{len(events)} events, {len(matched_behavior)} TTL anchors, "
        f"channel {ttl_channel}"
    )
    return result
