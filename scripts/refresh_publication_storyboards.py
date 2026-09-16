"""Rebuild publication storyboards from saved projects and existing figures."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neuroflow.project import load_project
from neuroflow.publication_report import write_publication_report


def closest_manifest(output: Path, delivery: Path) -> Path | None:
    for folder in (output, *output.parents):
        candidate = folder / "neuroflow_project.json"
        if candidate.exists():
            return candidate
        if folder == delivery:
            break
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delivery", type=Path, required=True)
    args = parser.parse_args()
    delivery = args.delivery.resolve()
    records = []
    for figures in sorted(delivery.glob("**/figures")):
        if not figures.is_dir():
            continue
        names = sorted(path.stem for path in figures.glob("*.svg"))
        if not names:
            continue
        output = figures.parent
        manifest = closest_manifest(output, delivery)
        if manifest is None:
            records.append({"output": str(output), "status": "no_project_manifest"})
            continue
        state = load_project(manifest)
        report = write_publication_report(state, output, names)
        records.append({
            "output": str(output),
            "project": str(manifest),
            "figure_count": len(names),
            "report": str(report),
            "status": "refreshed",
        })
    summary = {
        "schema": "neuroephys.publication-refresh.v1",
        "delivery": str(delivery),
        "refreshed": sum(item["status"] == "refreshed" for item in records),
        "records": records,
    }
    target = delivery / "publication_storyboard_refresh.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
