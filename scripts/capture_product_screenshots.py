from __future__ import annotations

# ruff: noqa: E402

from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from neuroflow.ai_tools import AIMode
from neuroflow.analysis import (
    compute_unit_metrics,
    match_ground_truth,
    preprocessing_preview,
    run_raw_qc,
)
from neuroflow.ephys_toolkit import run_neural_toolkit
from neuroflow.decoding import run_decoding_suite
from neuroflow.figure_studio import FigureStudioDialog
from neuroflow.project import load_project
from neuroflow.simulation import generate_demo_recording, simulate_sorter_output
from neuroflow.sorting_results import (
    activate_sorting_result,
    compare_sorting_results,
    register_sorting_result,
)
from neuroflow.statistics import run_statistical_suite
from neuroflow.synchronization import synchronize_existing_events
from neuroflow.ui import (
    DemoLibraryDialog,
    NeuroFlowWindow,
    NewProjectDialog,
    TutorialDialog,
)
from neuroflow.unit_curation_ui import UnitCurationDialog


def _capture(window, path: Path) -> None:
    QApplication.processEvents()
    QTest.qWait(350)
    # QWidget.grab() keeps text rendering intact in Remote Desktop/headless
    # sessions, where screen.grabWindow() can replace glyphs with tofu boxes.
    pixmap = window.grab()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not pixmap.save(str(path)):
        raise RuntimeError(f"Could not save screenshot: {path}")
    print(f"Captured {path.name}", flush=True)


def main() -> int:
    repository = REPOSITORY_ROOT
    output = repository / "docs" / "site" / "assets"
    workspace = repository / "docs_capture_workspace"
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Microsoft YaHei", 10))
    window = NeuroFlowWindow(workspace)
    window.auto_stage_guides = False
    window.resize(1900, 1080)
    window._set_language("en_US")
    window.home_workspace_hint.setText("NeuroEphys AI  /  Local workspace")
    window.show()
    _capture(window, output / "neuroflow-home.png")
    new_project = NewProjectDialog(workspace, window, "en_US")
    new_project.show()
    _capture(new_project, output / "neuroflow-new-project.png")
    new_project.close()
    library = DemoLibraryDialog(window, "en_US")
    library.show()
    _capture(library, output / "neuroflow-demo-library.png")
    library.close()

    state = generate_demo_recording(
        workspace / "capture_v05",
        duration_seconds=30.0,
        channel_count=32,
    )
    state.metadata["language"] = "en_US"
    synthetic_result_a = simulate_sorter_output(
        state.ground_truth,
        state.duration_seconds,
        seed=2026092301,
        native_id_offset=101,
        recall_range=(0.83, 0.95),
        false_positive_fraction=(0.025, 0.08),
        jitter_seconds=0.00010,
    )
    synthetic_result_b = simulate_sorter_output(
        state.ground_truth,
        state.duration_seconds,
        seed=2026092302,
        native_id_offset=207,
        recall_range=(0.76, 0.91),
        false_positive_fraction=(0.05, 0.13),
        jitter_seconds=0.00016,
    )
    register_sorting_result(
        state,
        "synthetic_detector_a",
        synthetic_result_a,
        {
            "sorter": "Synthetic imperfect benchmark A",
            "version": "teaching-1",
            "backend": "NeuroEphys AI teaching-data generator",
            "warning": "Synthetic benchmark output; not a Kilosort execution.",
        },
    )
    register_sorting_result(
        state,
        "synthetic_detector_b",
        synthetic_result_b,
        {
            "sorter": "Synthetic imperfect benchmark B",
            "version": "teaching-1",
            "backend": "NeuroEphys AI teaching-data generator",
            "warning": "Synthetic benchmark output; not a MountainSort execution.",
        },
    )
    activate_sorting_result(state, "synthetic_detector_a")
    compare_sorting_results(state)
    run_raw_qc(state)
    preview = preprocessing_preview(state)
    compute_unit_metrics(state)
    run_neural_toolkit(state)
    run_statistical_suite(state)
    run_decoding_suite(
        state,
        model_name="Logistic regression",
        n_splits=5,
        n_permutations=40,
    )
    synchronize_existing_events(state)
    window._load_state(state)
    window.preview = preview
    window.matches = match_ground_truth(state.ground_truth, state.sorted_spikes)
    window._select_step("sorting")
    diagnostic_index = window.sorting_workbench.diagnostic_combo.findData("comparison")
    window.sorting_workbench.diagnostic_combo.setCurrentIndex(diagnostic_index)
    window._refresh_figure()
    _capture(window, output / "neuroflow-sorting.png")
    pending_row = next(
        row
        for row, item in enumerate(window.sorting_workbench.catalog)
        if item["key"] == "spykingcircus2"
    )
    window.sorting_workbench.table.selectRow(pending_row)
    QApplication.processEvents()
    _capture(window, output / "neuroflow-sorting-pending.png")
    kilosort_row = next(
        row
        for row, item in enumerate(window.sorting_workbench.catalog)
        if item["key"] == "kilosort4"
    )
    window.sorting_workbench.table.selectRow(kilosort_row)
    diagnostic_index = window.sorting_workbench.diagnostic_combo.findData("comparison")
    window.sorting_workbench.diagnostic_combo.setCurrentIndex(diagnostic_index)
    window._refresh_figure()
    window._toggle_panel_focus()
    QApplication.processEvents()
    scroll_bar = window.main_scroll.verticalScrollBar()
    scroll_bar.setValue(scroll_bar.maximum())
    _capture(window, output / "neuroflow-panel-expanded.png")
    window._toggle_panel_focus()
    scroll_bar.setValue(0)

    window._select_step("sync")
    window._refresh_figure()
    _capture(window, output / "neuroflow-synchronization.png")
    tutorial = TutorialDialog("sync", window, "en_US")
    tutorial.show()
    _capture(tutorial, output / "neuroflow-tutorial.png")
    tutorial.close()

    window._select_step("unit_qc")
    curation = UnitCurationDialog(state, "en_US", parent=window)
    curation.show()
    _capture(curation, output / "neuroephys-ai-unit-curation.png")
    curation.close()

    window._open_ai_assistant()
    ai_dialog = window.ai_dialog
    if ai_dialog is not None:
        ai_dialog.settings.api_key = ""
        ai_dialog.settings.provider = "harness_sdk"
        ai_dialog.settings.base_url = "harness://local"
        ai_dialog.settings.harness_provider = "deepseek"
        ai_dialog.settings.managed_harness_name = "Institute DeepSeek Harness"
        ai_dialog.settings.model = "deepseek-v4.1-flash"
        ai_dialog.settings.mode = AIMode.COLLABORATIVE.value
        mode_index = ai_dialog.mode_combo.findData(AIMode.COLLABORATIVE.value)
        ai_dialog.mode_combo.setCurrentIndex(mode_index)
        ai_dialog.question_edit.setPlainText(
            "Review the active sorter result and propose the next evidence-producing step."
        )
        ai_dialog._append_message(
            "assistant",
            "Raw QC and sorting evidence are available. Review Unit QC before "
            "event-aligned interpretation; verify refractory violations, waveform "
            "stability, and the active sorter result.",
        )
        ai_dialog.current_plan = [
            {
                "stage": "unit_qc",
                "reason": "Confirm candidate-unit quality before event analysis.",
                "prerequisites": ["Completed sorting result"],
                "recommended_parameters": [
                    {
                        "name": "ISI review window",
                        "value": "0-10 ms",
                        "rationale": "Inspect the refractory region explicitly.",
                    }
                ],
            },
            {
                "stage": "sync",
                "reason": "Verify TTL and behavior clocks before alignment.",
                "prerequisites": ["Behavior events and electrophysiology TTL"],
                "recommended_parameters": [],
            },
        ]
        ai_dialog.current_next_stage = "unit_qc"
        ai_dialog.current_tool_calls = [
            {
                "name": "compute_unit_qc",
                "arguments": {},
                "reason": "Refresh common metrics before manual curation.",
            }
        ]
        ai_dialog._refresh_status()
        ai_dialog._render_plan()
        _capture(ai_dialog, output / "neuroflow-ai-assistant.png")
        ai_dialog.hide()
        window.assistant_panel.setVisible(True)
        window._refresh_ai_sidebar()
        _capture(
            window,
            output / "neuroephys-ai-assistant-interface-preview-en.png",
        )

    window.assistant_panel.setVisible(False)
    window._select_step("analysis")
    event_index = window.option_combo.findData(
        f"event:{sorted(state.sorted_spikes)[0]}"
    )
    window.option_combo.setCurrentIndex(event_index)
    window._refresh_figure()
    window._refresh_table()
    _capture(window, output / "neuroephys-event-analysis-en.png")
    window.main_scroll.verticalScrollBar().setValue(
        window.main_scroll.verticalScrollBar().maximum()
    )
    _capture(window, output / "neuroephys-event-analysis-detail-en.png")
    window.main_scroll.verticalScrollBar().setValue(0)
    window._set_language("zh_CN")
    window._select_step("analysis")
    event_index = window.option_combo.findData(
        f"event:{sorted(state.sorted_spikes)[0]}"
    )
    window.option_combo.setCurrentIndex(event_index)
    window._refresh_figure()
    _capture(window, output / "neuroephys-event-analysis-zh.png")
    window.main_scroll.verticalScrollBar().setValue(
        window.main_scroll.verticalScrollBar().maximum()
    )
    _capture(window, output / "neuroephys-event-analysis-detail-zh.png")
    window.main_scroll.verticalScrollBar().setValue(0)

    window._set_language("en_US")
    window._select_step("decoding")
    decoding_index = window.option_combo.findData(
        "classification:Logistic regression"
    )
    window.option_combo.setCurrentIndex(decoding_index)
    window._refresh_figure()
    _capture(window, output / "neuroephys-decoding-en.png")
    window.main_scroll.verticalScrollBar().setValue(
        window.main_scroll.verticalScrollBar().maximum()
    )
    _capture(window, output / "neuroephys-decoding-detail-en.png")
    window.main_scroll.verticalScrollBar().setValue(0)
    window._set_language("zh_CN")
    window._select_step("decoding")
    decoding_index = window.option_combo.findData(
        "classification:Logistic regression"
    )
    window.option_combo.setCurrentIndex(decoding_index)
    window._refresh_figure()
    _capture(window, output / "neuroephys-decoding-zh.png")
    window.main_scroll.verticalScrollBar().setValue(
        window.main_scroll.verticalScrollBar().maximum()
    )
    _capture(window, output / "neuroephys-decoding-detail-zh.png")
    window.main_scroll.verticalScrollBar().setValue(0)

    window._set_language("en_US")
    window.assistant_panel.setVisible(True)
    window._select_step("analysis")
    analysis_index = window.option_combo.findData("case:respiration")
    window.option_combo.setCurrentIndex(analysis_index)
    window._refresh_figure()
    window._refresh_table()
    _capture(window, output / "neuroflow-analysis.png")
    studio = FigureStudioDialog(window.canvas.figure, "en_US", window)
    if studio.tree.topLevelItemCount() > 1:
        studio.tree.setCurrentItem(studio.tree.topLevelItem(1))
    studio.show()
    _capture(studio, output / "neuroflow-figure-studio.png")
    studio.mode_tabs.setCurrentIndex(1)
    _capture(studio, output / "neuroflow-figure-studio-axes.png")
    studio.close()

    publication_project = (
        repository.parents[1]
        / "03_Example_Projects"
        / "Current_Local_Teaching_Suite"
        / "Neuropixels_Decision"
    )
    if (publication_project.exists()):
        publication_state = load_project(publication_project)
        publication_state.metadata["language"] = "en_US"
        window._load_state(publication_state)
        window._set_language("en_US")
        window.assistant_panel.setVisible(False)
        window._select_step("export")
        window._refresh_publication_panel()
        QApplication.processEvents()
        _capture(window, output / "neuroflow-publication-gallery.png")
    # The application correctly prompts before closing a dirty project. This
    # automation has already persisted its screenshots and must not block on
    # an unattended confirmation dialog.
    window.project_dirty = False
    window.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
