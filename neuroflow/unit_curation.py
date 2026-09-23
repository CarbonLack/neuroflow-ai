from __future__ import annotations

from datetime import datetime
from shutil import copy2
from pathlib import Path
from typing import Any

import numpy as np

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

SPIKE_CURATION_SCHEMA = "neuroephys.spike-level-curation.v1"


def _spike_curation_store(
    state: ProjectState,
    sorter_key: str | None = None,
) -> dict[str, Any]:
    """Return the non-destructive spike edit layer for one sorter."""
    key = sorter_key or state.active_sorter_key or "unassigned"
    stores = state.metadata.setdefault("spike_level_curation", {})
    store = stores.setdefault(
        key,
        {
            "schema": SPIKE_CURATION_SCHEMA,
            "sorter": key,
            "revision": 0,
            "sources": {},
            "audit": [],
        },
    )
    return store


def curated_unit_entries(
    state: ProjectState,
    sorter_key: str | None = None,
) -> dict[int, dict[str, Any]]:
    """Resolve raw sorter clusters plus manual exclude/split edits.

    Every returned spike retains its source sorter Unit and source-array index.
    The original ``state.sorting_results`` is never rewritten.
    """
    key = sorter_key or state.active_sorter_key or "unassigned"
    base = state.sorting_results.get(key, state.sorted_spikes)
    store = _spike_curation_store(state, key)
    entries: dict[int, dict[str, Any]] = {}
    for source_unit, values in sorted(base.items()):
        times = np.asarray(values, dtype=float)
        source_indices = np.arange(times.size, dtype=np.int64)
        edit = store.get("sources", {}).get(str(int(source_unit)), {})
        excluded = set(int(value) for value in edit.get("excluded_indices", []))
        split_rows = list(edit.get("splits", []))
        split_members: set[int] = set()
        for split in split_rows:
            indices = np.asarray(
                sorted({int(value) for value in split.get("source_indices", [])}),
                dtype=np.int64,
            )
            indices = indices[(indices >= 0) & (indices < times.size)]
            if excluded:
                indices = indices[~np.isin(indices, list(excluded))]
            split_members.update(indices.tolist())
            entries[int(split["unit_id"])] = {
                "times": times[indices],
                "source_unit": int(source_unit),
                "source_indices": indices,
                "kind": "manual_split",
            }
        removed = excluded | split_members
        parent_mask = ~np.isin(source_indices, list(removed)) if removed else np.ones(times.size, bool)
        entries[int(source_unit)] = {
            "times": times[parent_mask],
            "source_unit": int(source_unit),
            "source_indices": source_indices[parent_mask],
            "kind": "sorter_cluster",
        }
    return entries


def curated_spikes(
    state: ProjectState,
    sorter_key: str | None = None,
) -> dict[int, np.ndarray]:
    return {
        unit_id: np.asarray(row["times"], dtype=float)
        for unit_id, row in curated_unit_entries(state, sorter_key).items()
    }


def save_spike_selection_edit(
    state: ProjectState,
    *,
    source_unit: int,
    source_indices: list[int] | np.ndarray,
    action: str,
    current_unit: int | None = None,
    sorter_key: str | None = None,
) -> dict[str, Any]:
    """Exclude or split selected spikes while preserving the sorter result."""
    if action not in {"exclude", "split"}:
        raise ValueError(f"Unsupported spike curation action: {action}")
    key = sorter_key or state.active_sorter_key or "unassigned"
    base = state.sorting_results.get(key, state.sorted_spikes)
    if int(source_unit) not in base:
        raise KeyError(f"Unknown source Unit {source_unit}")
    valid = sorted({
        int(value) for value in np.asarray(source_indices, dtype=np.int64).tolist()
        if 0 <= int(value) < len(base[int(source_unit)])
    })
    if not valid:
        raise ValueError("No valid spikes were selected")
    store = _spike_curation_store(state, key)
    source = store.setdefault("sources", {}).setdefault(
        str(int(source_unit)), {"excluded_indices": [], "splits": []}
    )
    if action == "exclude":
        source["excluded_indices"] = sorted(
            set(int(value) for value in source.get("excluded_indices", [])) | set(valid)
        )
        result_unit = None
    else:
        # Moving spikes from an existing manual child into another split must
        # not duplicate assignments. Parent assignments are implicit.
        previous_split_unit: int | None = None
        for split in source.get("splits", []):
            if current_unit is not None and int(split.get("unit_id", -1)) == int(current_unit):
                previous_split_unit = int(current_unit)
                split["source_indices"] = [
                    value for value in split.get("source_indices", []) if int(value) not in set(valid)
                ]
        existing_ids = set(int(value) for value in base)
        for edits in store.get("sources", {}).values():
            existing_ids.update(int(row["unit_id"]) for row in edits.get("splits", []))
        result_unit = max(existing_ids, default=0) + 1
        source.setdefault("splits", []).append({
            "unit_id": int(result_unit),
            "source_indices": valid,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "parent_unit": int(current_unit if current_unit is not None else source_unit),
        })
        sorter_curation(state, key).setdefault(str(int(result_unit)), {
            "schema": "neuroephys.unit-curation.v1",
            "sorter": key,
            "unit_id": int(result_unit),
            "label": "uncertain",
            "confidence": "low",
            "checks": {name: False for name in CURATION_CHECKS},
            "notes": f"Manual split from Unit {current_unit if current_unit is not None else source_unit}; requires review.",
            "reviewer": "",
            "reviewed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "metric_snapshot": {},
            "decision_scope": "Manual split candidate; not biological ground truth.",
        })
    store["revision"] = int(store.get("revision", 0)) + 1
    record = {
        "revision": store["revision"],
        "action": action,
        "source_unit": int(source_unit),
        "current_unit": int(current_unit) if current_unit is not None else int(source_unit),
        "source_indices": valid,
        "result_unit": result_unit,
        "previous_split_unit": (
            previous_split_unit if action == "split" else None
        ),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    store.setdefault("audit", []).append(record)
    state.metadata["curation_downstream_stale"] = True
    selection = state.metadata.get("curated_unit_selection", {})
    if selection.get("enabled") and selection.get("sorter") == key:
        selection["needs_reapply"] = True
    state.log(
        f"Spike-level curation: sorter={key}, action={action}, "
        f"unit={current_unit if current_unit is not None else source_unit}, spikes={len(valid)}"
    )
    return record


def undo_spike_selection_edit(
    state: ProjectState,
    sorter_key: str | None = None,
) -> dict[str, Any] | None:
    """Undo the most recent spike-level edit for a sorter."""
    key = sorter_key or state.active_sorter_key or "unassigned"
    store = _spike_curation_store(state, key)
    audit = store.get("audit", [])
    if not audit:
        return None
    record = audit.pop()
    source = store.get("sources", {}).get(str(record["source_unit"]), {})
    indices = set(int(value) for value in record.get("source_indices", []))
    if record["action"] == "exclude":
        source["excluded_indices"] = [
            value for value in source.get("excluded_indices", []) if int(value) not in indices
        ]
    elif record["action"] == "split":
        result_unit = int(record["result_unit"])
        source["splits"] = [
            row for row in source.get("splits", []) if int(row.get("unit_id", -1)) != result_unit
        ]
        previous_split_unit = record.get("previous_split_unit")
        if previous_split_unit is not None:
            for row in source.get("splits", []):
                if int(row.get("unit_id", -1)) == int(previous_split_unit):
                    row["source_indices"] = sorted(
                        set(int(value) for value in row.get("source_indices", []))
                        | indices
                    )
                    break
        sorter_curation(state, key).pop(str(result_unit), None)
    store["revision"] = int(store.get("revision", 0)) + 1
    state.metadata["curation_downstream_stale"] = True
    selection = state.metadata.get("curated_unit_selection", {})
    if selection.get("enabled") and selection.get("sorter") == key:
        selection["needs_reapply"] = True
    state.log(f"Spike-level curation undo: sorter={key}, action={record['action']}")
    return record


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
    selection = state.metadata.get("curated_unit_selection", {})
    if selection.get("enabled") and selection.get("sorter") == key:
        selection["needs_reapply"] = True
        state.metadata["curation_downstream_stale"] = True
    state.metadata.setdefault("unit_curation_audit", []).append(record.copy())
    state.log(
        f"Unit curation saved: sorter={key}, unit={int(unit_id)}, "
        f"label={label}, confidence={confidence}"
    )
    return record


def apply_curated_single_units(state: ProjectState) -> dict[str, Any]:
    """Freeze reviewed single-unit IDs without altering the sorter output."""
    key = state.active_sorter_key or "unassigned"
    available = curated_spikes(state, key)
    records = sorter_curation(state, key)
    selected = sorted(
        int(unit_id) for unit_id in available
        if records.get(str(int(unit_id)), {}).get("label") == "candidate_single_unit"
    )
    if not selected:
        raise ValueError("No reviewed candidate single units are available for downstream analysis")
    manifest = Path(state.root) / "neuroflow_project.json"
    if manifest.is_file():
        history = Path(state.root) / "derived" / "curation_history"
        history.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
        copy2(manifest, history / f"before_selection_{stamp}.json")
    previous = state.metadata.get("curated_unit_selection", {})
    selection = {
        "schema": "neuroephys.curated-unit-selection.v1",
        "enabled": True,
        "sorter": key,
        "unit_ids": selected,
        "include_label": "candidate_single_unit",
        "unreviewed_policy": "exclude",
        "needs_reapply": False,
        "revision": int(previous.get("revision", 0)) + 1,
        "applied_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    state.metadata["curated_unit_selection"] = selection
    state.metadata["curation_downstream_stale"] = True
    state.analysis = {}
    state.spike_train_analysis = {}
    state.spike_field_analysis = {}
    state.statistics = {}
    state.decoding = {}
    state.regression = {}
    state.metadata["neural_activity_complete_package_stale"] = True
    for stage in ("analysis", "statistics", "decoding", "export"):
        state.workflow_status[stage] = "pending"
    state.log(
        f"Curated single-unit cohort applied: sorter={key}, "
        f"revision={selection['revision']}, units={selected}. "
        "Previous downstream outputs require rerun; original sorter spikes are unchanged."
    )
    return selection


def analysis_spikes(state: ProjectState) -> dict[int, Any]:
    """Return the explicit curated cohort, or all sorter candidates by default."""
    available = curated_spikes(state)
    selection = state.metadata.get("curated_unit_selection", {})
    if not selection.get("enabled") or selection.get("sorter") != state.active_sorter_key:
        result = available
    else:
        if selection.get("needs_reapply"):
            raise RuntimeError(
                "Manual Unit labels or spike assignments changed after the curated "
                "cohort was applied. Reapply the reviewed single-unit selection "
                "before downstream analysis."
            )
        result = {
            int(unit_id): available[int(unit_id)]
            for unit_id in selection.get("unit_ids", [])
            if int(unit_id) in available
        }
        if not result:
            raise RuntimeError("Curated Unit selection is empty for the active sorter")
    # Scientific provenance keeps the sorter/curation IDs, while figures and
    # matrices use a compact 1..N display namespace. This removes misleading
    # gaps without pretending that the sorter emitted different clusters.
    ordered = sorted(result)
    display_map = {index + 1: int(unit_id) for index, unit_id in enumerate(ordered)}
    state.metadata["analysis_unit_id_map"] = {
        "schema": "neuroephys.analysis-unit-id-map.v1",
        "sorter": state.active_sorter_key or "unassigned",
        "display_to_curated_unit": {
            str(display_id): source_id for display_id, source_id in display_map.items()
        },
        "policy": "Continuous 1-based IDs for downstream figures; source IDs retained here.",
    }
    return {
        display_id: np.asarray(result[source_id], dtype=float)
        for display_id, source_id in display_map.items()
    }


def curation_summary(
    state: ProjectState,
    sorter_key: str | None = None,
) -> dict[str, Any]:
    key = sorter_key or state.active_sorter_key or "unassigned"
    records = sorter_curation(state, key)
    available = curated_spikes(state, key)
    counts = {label: 0 for label in CURATION_LABELS}
    for record in records.values():
        label = str(record.get("label", "uncertain"))
        counts[label if label in counts else "uncertain"] += 1
    return {
        "sorter": key,
        "candidate_unit_count": len(available),
        "reviewed_unit_count": len(records),
        "label_counts": counts,
        "complete": len(records)
        == len(available)
        and bool(records),
    }
