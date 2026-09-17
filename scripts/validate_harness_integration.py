"""Explicit opt-in live GUI acceptance, using an existing project read-only.

Run with --project <manifest> --output <new verification directory>.
The input project is not saved or modified. Outputs contain the new chat evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont
from neuroflow.ai import AISettings
from neuroflow.ai_harness import discover_deepseek_harness_profiles
from neuroflow.project import load_project, restore_ai_conversation
from neuroflow.ui import NeuroFlowWindow


def run(project: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    profile = discover_deepseek_harness_profiles()[0]
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Microsoft YaHei", 10))
    state = load_project(project)
    state.root = output / "project"
    state.root.mkdir(parents=True, exist_ok=True)
    state.metadata["ai_history"] = []
    window = NeuroFlowWindow(output / "workspace")
    window._load_state(state)
    window.resize(1100, 760)
    window.show()
    window._select_step("unit_qc")
    window._refresh_ai_sidebar()
    dialog = window._ensure_ai_dialog()
    dialog.settings = AISettings(provider="harness_sdk", harness_provider=profile.provider_id,
        model=profile.default_model, mode="collaborative", timeout_seconds=180)
    dialog.context_authorized = True  # Explicit CLI invocation authorizes this test.
    failures = []
    QMessageBox.critical = lambda *args: failures.append(str(args[-1])) or QMessageBox.Ok
    questions = [
        "请调用项目查询工具，读取 unit_metrics 的最后一行（offset=25,limit=1）。"
        "报告 unit_id、spike_count、firing_rate_hz 和 snr 的实际值。不要运行分析。",
        "接着上一轮：我刚才关注的是哪个 Unit？请查询项目历史对话确认，并说明该 Unit "
        "能否仅凭 SNR 就认定是有效单神经元。不要运行分析。",
    ]
    for i, question in enumerate(questions, 1):
        dialog.question_edit.setPlainText(question)
        dialog._submit("ask")
        deadline = time.monotonic() + 210
        while dialog.worker and dialog.worker.isRunning() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.05)
        app.processEvents()
        if failures:
            raise RuntimeError(failures[-1])
        if len(state.metadata["ai_history"]) != i:
            raise RuntimeError("GUI did not persist this answer.")
        print(f"GUI_TURN_{i}_COMPLETE", flush=True)
    first, second = state.metadata["ai_history"]
    assert any(q["tool"] == "query_project_data" and q["arguments"].get("section") == "unit_metrics"
               for q in first["query_evidence"])
    assert any(q["tool"] == "search_project_conversation" and q["result"] for q in second["query_evidence"])
    expected = state.unit_metrics[-1]
    for key in ("unit_id", "spike_count", "snr"):
        assert any(str(expected[key]) in json.dumps(q["result"]) for q in first["query_evidence"])
    from neuroflow.models import ProjectState
    reopened = ProjectState(root=state.root)
    restore_ai_conversation(reopened)
    assert len(reopened.metadata["ai_history"]) == 2
    dialog.resize(640, 620)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(output / "ai_dialog_small.png"))
    window.grab().save(str(output / "app_three_columns.png"))
    report = {"ok": True, "channel_count": state.channel_count,
        "duration_seconds": state.duration_seconds, "sorter": state.active_sorter_key,
        "expected_unit": expected, "turns": state.metadata["ai_history"],
        "reopen_history_passed": True, "input_project_modified": False,
        "model": profile.default_model}
    (output / "live_gui_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("LIVE_GUI_ACCEPTANCE_PASSED", flush=True)
    dialog.close()
    window._set_project_clean()
    window.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.project, args.output)
