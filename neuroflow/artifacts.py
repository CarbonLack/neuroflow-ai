from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import ProjectState

_INDEXED_ROOTS = ("derived", "results", "exports", "figures", "tables", "logs")
_HASH_LIMIT_BYTES = 32 * 1024 * 1024


def project_file_snapshot(state: ProjectState) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    for root_name in _INDEXED_ROOTS:
        root = state.root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                stat = path.stat()
                relative = path.relative_to(state.root).as_posix()
                snapshot[relative] = (int(stat.st_size), int(stat.st_mtime_ns))
            except OSError:
                continue
    manifest = state.root / "neuroflow_project.json"
    if manifest.exists():
        stat = manifest.stat()
        snapshot[manifest.name] = (int(stat.st_size), int(stat.st_mtime_ns))
    return snapshot


def _sha256_for_small_file(path: Path) -> str | None:
    try:
        if path.stat().st_size > _HASH_LIMIT_BYTES:
            return None
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return None


def register_changed_artifacts(
    state: ProjectState,
    *,
    before: dict[str, tuple[int, int]],
    stage: str,
    run_id: str,
    tool: str | None,
    parameters: dict[str, Any],
    input_files: list[str],
) -> list[dict[str, Any]]:
    after = project_file_snapshot(state)
    records: list[dict[str, Any]] = []
    existing = {
        str(item.get("id")): item
        for item in state.metadata.setdefault("artifacts", [])
    }
    for relative, signature in sorted(after.items()):
        if before.get(relative) == signature:
            continue
        path = state.root / relative
        artifact_id = hashlib.sha256(
            f"{run_id}:{relative}".encode("utf-8")
        ).hexdigest()[:20]
        suffix = path.suffix.lower().lstrip(".") or "file"
        record = {
            "schema": "neuroephys.artifact.v1",
            "id": artifact_id,
            "created_at": datetime.now().astimezone().isoformat(
                timespec="milliseconds"
            ),
            "stage": stage,
            "run_id": run_id,
            "kind": suffix,
            "label": path.name,
            "relative_path": relative,
            "size_bytes": signature[0],
            "sha256": _sha256_for_small_file(path),
            "tool": tool,
            "parameters": parameters,
            "input_files": input_files,
            "status": "available",
            "open_with": (
                "NeuroEphys AI project"
                if suffix == "json" and path.name == "neuroflow_project.json"
                else suffix.upper()
            ),
        }
        existing[artifact_id] = record
        records.append(record)
    state.metadata["artifacts"] = list(existing.values())
    write_artifact_manifest(state)
    return records


def write_artifact_manifest(state: ProjectState) -> Path:
    path = state.root / "logs" / "artifact_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "neuroephys.artifact-manifest.v1",
        "project": state.name,
        "artifact_count": len(state.metadata.get("artifacts", [])),
        "artifacts": state.metadata.get("artifacts", []),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
