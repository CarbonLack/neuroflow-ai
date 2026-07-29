from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import ProjectState

CURATION_LABELS = (
    "candidate_single_unit",
    "multi_unit_activity",
    "noise",
    "artifact",
    "uncertain",
)

CURATION_CHECKS = (
    "waveform_shape",
    "refractory_period",
    "amplitude_stability",
    "recording_stability",
    "spatial_or_channel_profile",
    "duplicate_template_risk",
)


def sorter_curation(
    state: ProjectState,
    sorter_key: str | None = None,
) -> dict[str, dict[str, Any]]:
    key = sorter_key or state.active_sorter_key or "unassigned"
    all_records = state.metadata.setdefault("unit_curation", {})
    return all_records.setdefault(key, {})


def unit_curation_record(
    state: ProjectState,
    unit_id: int,
    sorter_key: str | None = None,
) -> dict[str, Any]:
    return sorter_curation(state, sorter_key).get(str(int(unit_id)), {})


def save_unit_curation(
    state: ProjectState,
    unit_id: int,
    *,
    label: str,
    confidence: str,
    checks: dict[str, bool],
    notes: str,
    reviewer: str = "",
    sorter_key: str | None = None,
) -> dict[str, Any]:
    if label not in CURATION_LABELS:
        raise ValueError(f"Unsupported Unit curation label: {label}")
    key = sorter_key or state.active_sorter_key or "unassigned"
    metric = next(
        (
            item
            for item in state.unit_metrics_by_sorter.get(
                key,
                state.unit_metrics,
            )
            if int(item.get("unit_id", -1)) == int(unit_id)
        ),
        {},
    )
    normalized_checks = {
        name: bool(checks.get(name, False)) for name in CURATION_CHECKS
    }
    record = {
        "schema": "neuroephys.unit-curation.v1",
        "sorter": key,
        "unit_id": int(unit_id),
        "label": label,
        "confidence": confidence,
        "checks": normalized_checks,
        "notes": str(notes).strip(),
        "reviewer": str(reviewer).strip(),
        "reviewed_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "metric_snapshot": {
            field: metric.get(field)
            for field in (
                "spike_count",
                "firing_rate_hz",
                "isi_violation_rate",
                "peak_channel",
                "peak_to_peak_adc",
                "snr",
            )
        },
        "decision_scope": (
            "Human review of a candidate cluster. This label does not establish "
            "biological ground truth."
        ),
    }
    sorter_curation(state, key)[str(int(unit_id))] = record
    state.metadata.setdefault("unit_curation_audit", []).append(record.copy())
    state.log(
        f"Unit curation saved: sorter={key}, unit={int(unit_id)}, "
        f"label={label}, confidence={confidence}"
    )
    return record


def curation_summary(
    state: ProjectState,
    sorter_key: str | None = None,
) -> dict[str, Any]:
    key = sorter_key or state.active_sorter_key or "unassigned"
    records = sorter_curation(state, key)
    counts = {label: 0 for label in CURATION_LABELS}
    for record in records.values():
        label = str(record.get("label", "uncertain"))
        counts[label if label in counts else "uncertain"] += 1
    return {
        "sorter": key,
        "candidate_unit_count": len(
            state.sorting_results.get(key, state.sorted_spikes)
        ),
        "reviewed_unit_count": len(records),
        "label_counts": counts,
        "complete": len(records)
        == len(state.sorting_results.get(key, state.sorted_spikes))
        and bool(records),
    }
