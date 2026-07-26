import json
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QScrollArea

from neuroflow.models import ProjectState
from neuroflow.project import MANIFEST_NAME, load_project
from neuroflow.sorting_results import (
    compare_sorting_results,
    register_sorting_result,
)
from neuroflow.ui import NeuroFlowWindow


def test_scrollable_workspace_and_independent_panel_export(
    tmp_path: Path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    window = NeuroFlowWindow(tmp_path / "workspace")
    window._set_language("en_US")
    state = ProjectState(root=tmp_path / "project", sampling_rate=30_000)
    state.metadata["language"] = "en_US"
    state.ground_truth = {
        0: np.array([0.1, 0.2, 0.3]),
        1: np.array([0.15, 0.25, 0.35]),
    }
    register_sorting_result(
        state,
        "kilosort4",
        {10: np.array([0.1001, 0.2001, 0.3001])},
        {"sorter": "Kilosort4", "backend": "test"},
    )
    register_sorting_result(
        state,
        "mountainsort5",
        {20: np.array([0.1002, 0.2002, 0.3002])},
        {"sorter": "MountainSort5", "backend": "test"},
    )
    compare_sorting_results(state)
    window._load_state(state)
    window._select_step("sorting")
    index = window.sorting_workbench.diagnostic_combo.findData("comparison")
    window.sorting_workbench.diagnostic_combo.setCurrentIndex(index)
    window._refresh_figure()

    assert isinstance(window.main_scroll, QScrollArea)
    assert not window.main_scroll.widget().isAncestorOf(window.progress_bar)
    assert not window.main_scroll.widget().isAncestorOf(window.run_step_button)
    assert window.figure_host.minimumHeight() >= 600
    assert window.panel_combo.count() == 3
    assert "performance" in window.panel_combo.itemText(0).lower()

    visible_before = sum(axis.get_visible() for axis in window.canvas.figure.axes)
    window._toggle_panel_focus()
    visible_focused = sum(axis.get_visible() for axis in window.canvas.figure.axes)
    assert visible_focused < visible_before

    exported = tmp_path / "selected_panel.svg"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(exported), "SVG (*.svg)"),
    )
    window._save_selected_panel()
    assert exported.is_file()
    assert exported.stat().st_size > 500

    window._toggle_panel_focus()
    assert sum(axis.get_visible() for axis in window.canvas.figure.axes) == visible_before
    window.close()
    app.processEvents()


def test_saved_project_reopens_at_the_last_stage(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    window = NeuroFlowWindow(tmp_path / "workspace")
    state = ProjectState(
        root=tmp_path / "project",
        name="Saved project",
        source_type="binary",
        recording_path=tmp_path / "recording.bin",
        channel_count=8,
        sampling_rate=1_000.0,
        duration_seconds=0.1,
    )
    state.recording_path.write_bytes(b"\0" * (100 * 8 * 2))
    state.workflow_status = {
        "import": "completed",
        "qc": "completed",
        "preprocess": "completed",
    }
    state.metadata["last_open_step"] = "preprocess"

    window._load_state(state)
    assert window._save(notify=False)
    restored = load_project(state.root)
    window._load_state(restored)

    assert window.current_step == "preprocess"
    assert window.state.recording_path == state.recording_path
    assert window.state.workflow_status["qc"] == "completed"
    assert window.project_dirty is False
    window.close()
    app.processEvents()


def test_unsaved_close_save_choice_persists_project(
    tmp_path: Path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    window = NeuroFlowWindow(tmp_path / "workspace")
    state = ProjectState(
        root=tmp_path / "project",
        name="Unsaved project",
        source_type="binary",
        recording_path=tmp_path / "recording.bin",
        channel_count=4,
        sampling_rate=1_000.0,
        duration_seconds=0.1,
    )
    state.recording_path.write_bytes(b"\0" * (100 * 4 * 2))
    window._load_state(state)
    state.workflow_status["qc"] = "completed"
    window._mark_project_dirty()

    monkeypatch.setattr(QMessageBox, "exec", lambda _dialog: QMessageBox.Save)

    class CloseEvent:
        accepted = False
        ignored = False

        def accept(self):
            self.accepted = True

        def ignore(self):
            self.ignored = True

    event = CloseEvent()
    window.closeEvent(event)

    assert event.accepted is True
    assert event.ignored is False
    assert (state.root / MANIFEST_NAME).is_file()
    assert load_project(state.root).workflow_status["qc"] == "completed"
    assert window.project_dirty is False
    window.close()
    app.processEvents()


def test_selecting_an_unrun_sorter_refreshes_the_pending_view(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    window = NeuroFlowWindow(tmp_path / "workspace")
    state = ProjectState(
        root=tmp_path / "project",
        recording_path=tmp_path / "recording.bin",
        channel_count=8,
        sampling_rate=1_000.0,
        duration_seconds=0.1,
    )
    state.recording_path.write_bytes(b"\0" * (100 * 8 * 2))
    register_sorting_result(
        state,
        "kilosort4",
        {1: np.array([0.02, 0.05])},
        {"sorter": "Kilosort4", "backend": "test"},
    )
    register_sorting_result(
        state,
        "mountainsort5",
        {2: np.array([0.021, 0.051])},
        {"sorter": "MountainSort5", "backend": "test"},
    )
    compare_sorting_results(state)
    window._load_state(state)
    window._select_step("sorting")
    diagnostic_index = window.sorting_workbench.diagnostic_combo.findData("comparison")
    window.sorting_workbench.diagnostic_combo.setCurrentIndex(diagnostic_index)
    row = next(
        index
        for index, item in enumerate(window.sorting_workbench.catalog)
        if item["key"] == "spykingcircus2"
    )
    window.sorting_workbench.table.selectRow(row)
    app.processEvents()
    visible_text = " ".join(
        item.get_text()
        for axis in window.canvas.figure.axes
        for item in axis.texts
    )
    assert "spykingcircus2" in visible_text.lower()
    assert "kilosort4" not in visible_text.lower()
    window.close()
    app.processEvents()


def test_ai_assistant_is_discoverable_and_plan_never_auto_runs(
    tmp_path: Path,
    monkeypatch,
):
    app = QApplication.instance() or QApplication([])
    window = NeuroFlowWindow(tmp_path / "workspace")
    state = ProjectState(
        root=tmp_path / "project",
        name="AI review project",
        source_type="binary",
        recording_path=tmp_path / "recording.bin",
        channel_count=8,
        sampling_rate=30_000,
        duration_seconds=1.0,
    )
    state.recording_path.write_bytes(b"\0" * (30_000 * 8 * 2))
    state.workflow_status = {"import": "completed", "qc": "pending"}
    window._load_state(state)
    window.show()
    app.processEvents()

    assert window.ai_button.isVisible()
    assert window.open_ai_button.isVisible()
    window._open_ai_assistant()
    app.processEvents()
    assert window.ai_dialog is not None
    assert window.ai_dialog.isVisible()
    assert "recording.bin" not in json.dumps(window.ai_dialog._summary())

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args, **kwargs: QMessageBox.Ok,
    )
    plan = [
        {
            "stage": "qc",
            "reason": "Inspect noise first.",
            "prerequisites": ["Readable raw voltage"],
            "recommended_parameters": [],
        }
    ]
    window._apply_ai_plan(plan, "qc")

    assert state.metadata["ai_workflow_plan"]["status"] == "advisory_not_executed"
    assert state.workflow_status["qc"] == "pending"
    assert window.current_step == "qc"
    window.ai_dialog.hide()
    window._set_project_clean()
    window.close()
    app.processEvents()
