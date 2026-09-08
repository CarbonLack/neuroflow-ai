"""Regression checks for navigation, persistence and safe project switching."""
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from neuroflow.models import ProjectState
from neuroflow.tutorial_catalog import TUTORIAL_CATALOG
from neuroflow.ui import NeuroFlowWindow


@pytest.fixture
def window(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("neuroflow.ui.QSettings", lambda *_: QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    widget = NeuroFlowWindow(tmp_path / "workspace")
    widget.auto_stage_guides = False
    yield widget
    widget.worker = None
    widget.ai_dialog = None
    widget.project_dirty = False
    widget.close()
    app.processEvents()


def test_recent_project_order_missing_paths_and_limit(window, tmp_path):
    paths = []
    for index in range(10):
        folder = tmp_path / f"project-{index}"
        folder.mkdir()
        path = folder / "neuroflow_project.json"
        path.write_text("{}", encoding="utf-8")
        paths.append(path)
        window._remember_project(path)
    assert len(window._recent_projects()) == 8
    window._remember_project(paths[4])
    assert window._recent_projects()[0] == str(paths[4].resolve())
    assert len(set(window._recent_projects())) == 8
    paths[4].unlink()
    window._refresh_recent_menu()
    assert not window.recent_menu.actions()[0].isEnabled()
    assert window.recent_menu.actions()[1].isEnabled()


def test_project_switch_respects_cancel_and_failed_save(window, monkeypatch, tmp_path):
    window.state = ProjectState(root=tmp_path / "project", sampling_rate=30000)
    window.project_dirty = True
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.Cancel)
    assert not window._can_switch_project()
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.Save)
    monkeypatch.setattr(window, "_save", lambda **_: False)
    assert not window._can_switch_project()
    monkeypatch.setattr(window, "_save", lambda **_: True)
    assert window._can_switch_project()
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.Discard)
    assert window._can_switch_project()


def test_project_switch_waits_for_analysis(window, monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *_: QMessageBox.Ok)
    window.worker = SimpleNamespace(isRunning=lambda: True)
    assert not window._can_switch_project()


def test_help_targets_specific_analysis_and_single_step_progress(window, tmp_path):
    window._load_state(ProjectState(root=tmp_path / "project", sampling_rate=30000))
    for key, target in (("population", "population:heatmap"), ("connectivity", "connectivity:examples")):
        item = next(item for item in TUTORIAL_CATALOG if item["id"] == key)
        window._navigate_from_tutorial(item)
        assert window.current_step == "analysis"
        assert window.option_combo.currentData() == target
    window.active_run_keys = ["import"]
    window.progress_bar.setRange(0, 1)
    window._on_step_done("import", {})
    assert window.progress_bar.value() == window.progress_bar.maximum() == 1
