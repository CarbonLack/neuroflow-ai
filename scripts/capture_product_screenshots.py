from __future__ import annotations

from pathlib import Path

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
from neuroflow.figure_studio import FigureStudioDialog
from neuroflow.simulation import generate_demo_recording
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
    PublicExampleDialog,
    TutorialDialog,
)
from neuroflow.unit_curation_ui import UnitCurationDialog


def _capture(window, path: Path) -> None:
    QApplication.processEvents()
    QTest.qWait(350)
    screen = window.screen()
    pixmap = screen.grabWindow(int(window.winId()))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not pixmap.save(str(path)):
        raise RuntimeError(f"Could not save screenshot: {path}")


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    output = repository / "docs" / "site" / "assets"
    workspace = repository / "docs_capture_workspace"
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Microsoft YaHei", 10))
    window = NeuroFlowWindow(workspace)
    window.resize(1900, 1080)
    window._set_language("en_US")
    window.show()
    _capture(window, output / "neuroflow-home.png")
    new_project = NewProjectDialog(workspace, window, "en_US")
    new_project.show()
    _capture(new_project, output / "neuroflow-new-project.png")
    new_project.close()
    documents = Path.home() / "Documents"
    preferred_workspace = documents / "NeuroEphysAI"
    legacy_workspace = documents / "NeuroFlow"
    public_examples = PublicExampleDialog(
        (
            preferred_workspace
            if preferred_workspace.exists() or not legacy_workspace.exists()
            else legacy_workspace
        ),
        window,
        "en_US",
    )
    public_examples.show()
    _capture(public_examples, output / "neuroflow-public-projects.png")
    public_examples.close()
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
    kilosort_result = {
        100 + unit_id: spikes + 0.0001
        for unit_id, spikes in state.ground_truth.items()
    }
    mountainsort_result = {
        200 + unit_id: spikes + 0.0002
        for unit_id, spikes in state.ground_truth.items()
    }
    register_sorting_result(
        state,
        "kilosort4",
        kilosort_result,
        {
            "sorter": "Kilosort4",
            "version": "4.1.7",
            "backend": "Native NeuroEphys AI adapter",
        },
    )
    register_sorting_result(
        state,
        "mountainsort5",
        mountainsort_result,
        {
            "sorter": "MountainSort5",
            "version": "0.5.9",
            "backend": "SpikeInterface",
        },
    )
    activate_sorting_result(state, "kilosort4")
    compare_sorting_results(state)
    run_raw_qc(state)
    preview = preprocessing_preview(state)
    compute_unit_metrics(state)
    run_neural_toolkit(state)
    run_statistical_suite(state)
    synchronize_existing_events(state)
    window._load_state(state)
    window.project_label.setText(
        "NeuroEphys AI demonstration project  ·  local path hidden"
    )
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
        ai_dialog.settings.api_key = "preview-credential-not-saved"
        ai_dialog.settings.provider = "deepseek"
        ai_dialog.settings.base_url = "https://api.deepseek.com"
        ai_dialog.settings.model = "deepseek-v4-flash"
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
    studio.editor_scroll.verticalScrollBar().setValue(
        int(studio.editor_scroll.verticalScrollBar().maximum() * 0.78)
    )
    _capture(studio, output / "neuroflow-figure-studio-axes.png")
    studio.close()
    window.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
