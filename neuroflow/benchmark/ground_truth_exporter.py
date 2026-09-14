from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


def _csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value for key, value in row.items()})


def export_ground_truth(
    root: Path,
    session_summary: dict,
    units: list[dict],
    spikes: dict[int, np.ndarray],
    templates: dict[int, dict],
    qc_rows: list[dict],
    qc_plan: dict,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    np.savez(root / "true_spike_times.npz", **{f"unit_{unit_id}": values for unit_id, values in spikes.items()})
    np.savez(
        root / "waveform_templates.npz",
        **{
            key: value
            for unit_id, payload in templates.items()
            for key, value in ((f"unit_{unit_id}_channels", payload["channels"]), (f"unit_{unit_id}_waveform_uv", payload["waveform_uv"]))
        },
    )
    _csv(root / "units.csv", units)
    _csv(root / "qc_issues.csv", qc_rows)
    (root / "session_ground_truth.json").write_text(
        json.dumps({**session_summary, "qc_plan": qc_plan}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / "GROUND_TRUTH_LOCKED.txt").write_text(
        "本目录是 benchmark 答案，仅供独立验证脚本读取。正常 NeuroEphys AI 项目清单不引用本目录。\n",
        encoding="utf-8",
    )
