from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from .simulation import generate_demo_recording
from .sorting import kilosort_environment, run_sorter


def run_packaged_kilosort_self_test(workspace: Path) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    log_path = workspace / "packaged_kilosort_self_test.log"
    report_path = workspace / "packaged_kilosort_self_test.json"
    with log_path.open("w", encoding="utf-8", buffering=1) as stream:
        sys.stdout = stream
        sys.stderr = stream
        try:
            stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
            project_root = workspace / "self_test" / stamp
            state = generate_demo_recording(
                project_root,
                duration_seconds=8,
                channel_count=8,
                sampling_rate=30_000,
            )
            spikes = run_sorter(
                state,
                "kilosort4",
                project_root / "results" / "kilosort4",
                print,
                settings={
                    "batch_size": 120_000,
                    "nblocks": 0,
                    "Th_universal": 9,
                    "Th_learned": 8,
                    "save_extra_vars": True,
                },
            )
            report = {
                "ok": True,
                "environment": kilosort_environment(),
                "project": str(project_root),
                "units": len(spikes),
                "spikes": sum(len(value) for value in spikes.values()),
                "diagnostic_files": state.metadata["sorting"]["diagnostic_files"],
            }
        except Exception as exc:  # noqa: BLE001 - self-test must persist full failure
            report = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0 if report["ok"] else 1
