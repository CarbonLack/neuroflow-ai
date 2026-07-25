import os
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog, QScrollArea

from neuroflow.models import ProjectState
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
        "sorter_a",
        {10: np.array([0.1001, 0.2001, 0.3001])},
        {"sorter": "Sorter A", "backend": "test"},
    )
    register_sorting_result(
        state,
        "sorter_b",
        {20: np.array([0.1002, 0.2002, 0.3002])},
        {"sorter": "Sorter B", "backend": "test"},
    )
    compare_sorting_results(state)
    window._load_state(state)
    window._select_step("sorting")
    index = window.sorting_workbench.diagnostic_combo.findData("comparison")
    window.sorting_workbench.diagnostic_combo.setCurrentIndex(index)
    window._refresh_figure()

    assert isinstance(window.main_scroll, QScrollArea)
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
