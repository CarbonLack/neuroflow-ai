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
from neuroflow.sorting_workbench import SortingWorkbench
from neuroflow.ui import (
    ConnectivitySettingsDialog,
    ImportDialog,
    NeuroFlowWindow,
    PipelineWorker,
    PopulationSettingsDialog,
)
from neuroflow.unit_curation_ui import UnitCurationDialog


def test_sorting_workbench_lists_imported_read_only_results():
    QApplication.instance() or QApplication([])
    workbench = SortingWorkbench("en_US")
    workbench.set_catalog(
        [
            {
                "key": "kilosort4",
                "name": "Kilosort4",
                "installed": True,
                "hardware": "GPU",
                "best_for": "Dense recordings",
                "backend": "Kilosort",
                "version": "4.1.7",
                "error": None,
            }
        ]
    )

    workbench.set_results(
        {"kilosort4", "offline_sorter_nex5"},
        "offline_sorter_nex5",
    )

    assert workbench.select_sorter("offline_sorter_nex5")
    assert workbench.selected_sorter() == "offline_sorter_nex5"
    assert "read-only" in workbench.selected_description().lower()


def test_gui_worker_writes_reloadable_structured_audit(tmp_path: Path):
    QApplication.instance() or QApplication([])
    state = ProjectState(
        root=tmp_path / "audited_project",
        name="Audited GUI project",
        source_type="binary",
        recording_path=tmp_path / "recording.bin",
        channel_count=4,
        sampling_rate=1_000.0,
        duration_seconds=1.0,
    )
    state.recording_path.write_bytes(b"\0" * (1_000 * 4 * 2))
    worker = PipelineWorker(
        state,
        ["import"],
        "kilosort4",
        {},
        "classification:Logistic regression",
    )

    worker.run()

    audit_path = state.root / "logs" / "structured_runs.jsonl"
    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["status"] for record in records] == ["running", "completed"]
    assert records[-1]["input_files"] == [str(state.recording_path)]
    assert records[-1]["elapsed_seconds"] >= 0
    restored = load_project(state.root)
    assert restored.metadata["structured_run_log"][-1]["stage"] == "import"
    assert restored.metadata["structured_run_log"][-1]["status"] == "completed"


def test_connectivity_dialog_exposes_choices_and_estimates_work(tmp_path: Path):
    QApplication.instance() or QApplication([])
    state = ProjectState(
        root=tmp_path / "connectivity_project",
        duration_seconds=10.0,
        sorted_spikes={
            1: np.linspace(0.1, 9.9, 30),
            2: np.linspace(0.2, 9.8, 30),
            3: np.linspace(0.3, 9.7, 30),
        },
        metadata={"unit_regions": {"1": "M1", "2": "M1", "3": "PMd"}},
    )
    dialog = ConnectivitySettingsDialog(state, "en_US")
    dialog.max_pairs.setValue(2)
    dialog.iterations.setValue(10)
    dialog._update_estimate()

    settings = dialog.settings()
    assert settings["pair_mode"] == "all"
    assert settings["max_pairs"] == 2
    assert settings["jitter_iterations"] == 10
    assert "3" in dialog.estimate.text()
    assert "20" in dialog.estimate.text()
    dialog.close()


def test_population_dialog_filters_events_and_regions(tmp_path: Path):
    QApplication.instance() or QApplication([])
    state = ProjectState(
        root=tmp_path / "population_project",
        duration_seconds=10.0,
        events=[
            {"time_seconds": 1.0, "condition": "left"},
            {"time_seconds": 2.0, "condition": "right"},
            {"time_seconds": 3.0, "condition": "left"},
        ],
        sorted_spikes={
            1: np.array([0.9, 1.1]),
            2: np.array([1.0, 2.0]),
            3: np.array([2.1, 3.1]),
        },
        metadata={"unit_regions": {"1": "LIP", "2": "LIP", "3": "SC"}},
    )
    dialog = PopulationSettingsDialog(state, "en_US")
    dialog.event_scope.setCurrentIndex(dialog.event_scope.findData("left"))
    dialog.unit_scope.setCurrentIndex(dialog.unit_scope.findData("LIP"))
    dialog.bin_ms.setValue(10.0)
    settings = dialog.settings()

    assert settings["event_times_seconds"] == [1.0, 3.0]
    assert settings["event_labels"] == ["left", "left"]
    assert settings["unit_ids"] == [1, 2]
    assert settings["bin_size_seconds"] == 0.01
    assert "2 trials" in dialog.estimate.text()
    dialog.close()


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


def test_import_dialog_saves_generic_probe_and_behavior_configuration(
    tmp_path: Path,
):
    app = QApplication.instance() or QApplication([])
    dialog = ImportDialog(tmp_path / "workspace", language="en_US")
    state = ProjectState(
        root=tmp_path / "project",
        name="Own recording",
        source_type="read_openephys",
        recording_path=tmp_path / "source",
        channel_count=32,
        sampling_rate=30_000,
        duration_seconds=1_800,
    )
    dialog.state = state
    dialog.electrode_type_edit.setCurrentText("independent microwires")
    dialog.brain_region_edit.setText("OFC")
    geometry_index = dialog.geometry_mode_combo.findData("independent_contacts")
    dialog.geometry_mode_combo.setCurrentIndex(geometry_index)
    dialog.reference_edit.setText("External reference; not stored")
    dialog.known_bad_channels_edit.setText("")
    dialog.device_channels.setText("1-32")

    dialog._apply_import_metadata_and_behavior("device")

    assert state.electrode_type == "independent microwires"
    assert state.metadata["probe"] == {
        "type": "independent microwires",
        "contact_count": 32,
        "geometry_mode": "independent_contacts",
        "brain_region": "OFC",
        "reference_configuration": "External reference; not stored",
        "known_hardware_bad_channels": [],
    }
    assert state.metadata["import_configuration"]["channel_selection"] == "1-32"
    assert state.metadata["behavior_import_configuration"]["status"] == (
        "not_configured"
    )
    dialog.close()
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
    window.ai_dialog.current_plan = plan
    window.ai_dialog._render_plan()
    assert window.ai_dialog.plan_table.rowCount() == 1
    assert window.ai_dialog.plan_table.item(0, 0).checkState().value == 2
    window._apply_ai_plan(plan, "qc")

    assert state.metadata["ai_workflow_plan"]["status"] == "advisory_not_executed"
    assert state.workflow_status["qc"] == "pending"
    assert window.current_step == "qc"
    window.ai_dialog.hide()
    window._set_project_clean()
    window.close()
    app.processEvents()


def test_manual_unit_curation_dialog_saves_review_evidence(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    state = ProjectState(
        root=tmp_path / "project",
        duration_seconds=10.0,
    )
    state.active_sorter_key = "kilosort4"
    state.sorted_spikes = {3: np.array([0.1, 0.2, 0.5])}
    state.sorting_results = {"kilosort4": state.sorted_spikes}
    state.unit_metrics = [
        {
            "unit_id": 3,
            "spike_count": 3,
            "firing_rate_hz": 0.3,
            "isi_violation_rate": 0.0,
            "snr": 4.2,
            "peak_channel": 1,
            "label": "候选单神经元",
        }
    ]
    state.unit_metrics_by_sorter = {"kilosort4": state.unit_metrics}
    state.unit_diagnostics = {
        3: {
            "waveform": np.zeros((41, 1)).tolist(),
            "waveform_time_ms": np.linspace(-0.67, 0.67, 41).tolist(),
            "waveform_channels": [1],
            "isi_ms": [100.0, 300.0],
            "acg_lags_ms": np.arange(0.5, 50.0, 1.0).tolist(),
            "acg_counts": np.zeros(50).tolist(),
            "stability_time_s": np.arange(10).tolist(),
            "stability_rate_hz": np.zeros(10).tolist(),
            "amplitude_time_s": [],
            "amplitude_adc": [],
        }
    }
    state.unit_diagnostics_by_sorter = {
        "kilosort4": state.unit_diagnostics
    }

    dialog = UnitCurationDialog(state, "en_US")
    dialog.label_combo.setCurrentIndex(
        dialog.label_combo.findData("candidate_single_unit")
    )
    dialog.checks["waveform_shape"].setChecked(True)
    dialog.checks["refractory_period"].setChecked(True)
    dialog.notes_edit.setPlainText("Waveform and refractory evidence reviewed.")
    dialog._save()

    record = state.metadata["unit_curation"]["kilosort4"]["3"]
    assert record["label"] == "candidate_single_unit"
    assert record["checks"]["waveform_shape"] is True
    assert "ground truth" in record["decision_scope"]
    dialog.close()
    app.processEvents()
