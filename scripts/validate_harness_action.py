"""Explicit live acceptance of a confirmed raw-QC action on new synthetic data."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QMessageBox
from neuroflow.ai import AISettings
from neuroflow.ai_harness import discover_deepseek_harness_profiles
from neuroflow.simulation import generate_demo_recording
from neuroflow.ui import NeuroFlowWindow


def run(output):
    app = QApplication.instance() or QApplication([])
    state = generate_demo_recording(output / "project", duration_seconds=2, channel_count=4, sampling_rate=30000)
    window = NeuroFlowWindow(output / "workspace")
    window._load_state(state)
    dialog = window._ensure_ai_dialog()
    profile = discover_deepseek_harness_profiles()[0]
    dialog.settings = AISettings(provider="harness_sdk", harness_provider=profile.provider_id,
        model=profile.default_model, mode="collaborative", timeout_seconds=180)
    dialog.context_authorized = True
    failures = []
    QMessageBox.critical = lambda *args: failures.append(str(args[-1])) or QMessageBox.Ok
    QMessageBox.information = lambda *args: QMessageBox.Ok
    QMessageBox.warning = lambda *args: failures.append(str(args[-1])) or QMessageBox.Ok
    def wait_for(check):
        deadline = time.monotonic() + 210
        while not check() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.05)
        if failures:
            raise RuntimeError(failures[-1])
        assert check(), "Acceptance timed out"
    dialog.question_edit.setPlainText("请使用 propose_analysis_action 提议 run_raw_qc，参数为空。只提议一次原始质控，等待我确认，不要提议其他操作。")
    dialog._submit("ask")
    wait_for(lambda: bool(dialog.current_tool_calls))
    assert not state.qc, "Action executed before confirmation"
    assert dialog.current_tool_calls[0]["name"] == "run_raw_qc"
    QMessageBox.question = lambda *args: QMessageBox.No
    dialog._review_first_tool()
    assert not state.qc, "Rejected action executed"
    QMessageBox.question = lambda *args: QMessageBox.Yes
    dialog._review_first_tool()
    wait_for(lambda: len(state.metadata.get("ai_history", [])) >= 2)
    assert state.qc
    audit = state.metadata["ai_tool_audit"][-1]
    assert audit["status"] == "completed", audit
    followup = state.metadata["ai_history"][-1]
    assert followup["task"] == "action_result"
    assert not followup["tool_calls"]
    assert any(item["tool"] == "query_project_data" for item in followup["query_evidence"])
    (output / "live_action_acceptance.json").write_text(json.dumps({
        "ok": True, "proposal_did_not_execute": True, "rejection_did_not_execute": True,
        "confirmed_action_completed": True, "audit": audit, "qc": state.qc,
        "turns": state.metadata["ai_history"]}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("LIVE_ACTION_ACCEPTANCE_PASSED", flush=True)
    dialog.close()
    window._set_project_clean()
    window.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    run(args.output)
