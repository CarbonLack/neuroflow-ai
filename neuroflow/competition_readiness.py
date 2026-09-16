"""Evidence-based competition demo checklist and short-form narrative."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ProjectState


DEMO_STORY = (
    ("Problem", "Fragmented electrophysiology tools make import, sorting, behavior alignment, interpretation and reproducible export difficult to audit."),
    ("Solution", "A local-first guided workbench keeps raw-data links, parameters, intermediate results, figures and decisions in one project."),
    ("AI role", "The assistant reads a redacted structured project context, explains evidence, proposes next steps and can request only registered tools."),
    ("Evidence", "Show one simulation with ground truth, one real session, three-sorter comparison, event alignment and English publication export."),
    ("Impact", "Repeatable projects, fewer manual hand-offs, visible assumptions and publication-ready evidence with an offline fallback."),
)


def readiness_snapshot(
    state: ProjectState | None,
    *,
    workspace: Path,
    ai_configured: bool,
    installed_sorters: list[str] | None = None,
) -> dict[str, Any]:
    """Return claims as checks; unavailable evidence remains explicitly open."""
    installed_sorters = installed_sorters or []
    figures = []
    publications = []
    if state is not None:
        figures = sorted(
            path.relative_to(state.root).as_posix()
            for path in state.root.glob("exports/**/figures/*")
            if path.is_file()
        )
        publications = sorted(
            path.relative_to(state.root).as_posix()
            for path in state.root.glob("exports/**/publication/index.html")
        )
    checks = [
        {
            "id": "project",
            "label": "A project is open and can be restored",
            "ready": state is not None,
        },
        {
            "id": "raw_or_result",
            "label": "Raw voltage or an imported sorting result is available",
            "ready": bool(state and (state.ready or state.sorted_spikes)),
        },
        {
            "id": "three_sorters",
            "label": "Three sorter backends are installed for the live fallback",
            "ready": len(set(installed_sorters)) >= 3,
            "detail": sorted(set(installed_sorters)),
        },
        {
            "id": "analysis",
            "label": "The project contains derived analysis evidence",
            "ready": bool(
                state
                and (
                    state.qc
                    or state.unit_metrics
                    or state.analysis
                    or state.statistics
                    or state.decoding
                )
            ),
        },
        {
            "id": "figures",
            "label": "Exported figures exist",
            "ready": bool(figures),
            "detail": figures[:20],
        },
        {
            "id": "publication",
            "label": "English publication storyboard exists",
            "ready": bool(publications),
            "detail": publications,
        },
        {
            "id": "ai",
            "label": "AI endpoint is configured; manual mode remains available offline",
            "ready": bool(ai_configured),
        },
        {
            "id": "offline_docs",
            "label": "Offline documentation is available",
            "ready": (workspace / "docs" / "_build" / "html" / "index.html").exists(),
        },
    ]
    return {
        "schema": "neuroephys.competition-readiness.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Demonstration readiness, not scientific validity certification.",
        "project": state.name if state else None,
        "checks": checks,
        "ready_count": sum(item["ready"] for item in checks),
        "check_count": len(checks),
        "demo_story": [
            {"section": section, "message": message}
            for section, message in DEMO_STORY
        ],
        "run_of_show": [
            "0:00–1:00 — practical problem and target users",
            "1:00–2:00 — create/import a project and show provenance",
            "2:00–4:30 — QC, three-sorter comparison and behavior synchronization",
            "4:30–6:30 — event-aligned analysis, statistics and beginner explanations",
            "6:30–8:00 — English main/supplementary publication export",
            "8:00–9:00 — constrained AI context, registered tools and audit trail",
            "9:00–10:00 — measured benefits, limitations and offline fallback",
        ],
        "fallbacks": [
            "Keep one fully exported simulation and one real-data project locally.",
            "Use saved PNG/SVG/HTML results if a long sorter cannot finish live.",
            "Use manual mode if the network or managed AI endpoint is unavailable.",
            "Keep installer, portable edition, offline manual and a short screen recording together.",
        ],
    }


def write_readiness_bundle(snapshot: dict[str, Any], output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    (output / "competition_readiness.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# NeuroEphys AI — Competition readiness",
        "",
        snapshot["scope"],
        "",
        f"Ready checks: {snapshot['ready_count']}/{snapshot['check_count']}",
        "",
        "## Evidence checklist",
        "",
    ]
    for item in snapshot["checks"]:
        lines.append(f"- [{'x' if item['ready'] else ' '}] {item['label']}")
    lines += ["", "## 5–10 minute run of show", ""]
    lines += [f"- {item}" for item in snapshot["run_of_show"]]
    lines += ["", "## Narrative", ""]
    lines += [f"### {item['section']}\n\n{item['message']}\n" for item in snapshot["demo_story"]]
    lines += ["", "## Offline fallback", ""]
    lines += [f"- {item}" for item in snapshot["fallbacks"]]
    target = output / "competition_readiness.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
