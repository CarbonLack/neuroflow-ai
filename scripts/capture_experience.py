"""Render the current desktop experience in an isolated demonstration workspace."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from neuroflow.analysis import compute_unit_metrics, run_raw_qc
from neuroflow.project import save_project
from neuroflow.simulation import generate_demo_recording
from neuroflow.ui import NeuroFlowWindow, StageGuideDialog, TutorialDialog
from neuroflow import ui, tutorial_center


def main():
    output = ROOT / "docs/site/assets"
    workspace = ROOT / "docs_capture_workspace/experience_1_2"
    QSettings.setDefaultFormat(QSettings.IniFormat)
    with tempfile.TemporaryDirectory(prefix="neuroephys-ui-") as settings_path:
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, settings_path)
        # Explicit organisation/application constructors otherwise use NativeFormat
        # on Windows even after setDefaultFormat(), leaking captures into recents.
        ui.QSettings = tutorial_center.QSettings = lambda *_: QSettings(str(Path(settings_path) / "capture.ini"), QSettings.IniFormat)
        app = QApplication.instance() or QApplication([])
        app.setFont(QFont("Microsoft YaHei", 10))
        window = NeuroFlowWindow(workspace)
        window.auto_stage_guides = False
        window.home_workspace_hint.setText("NeuroEphys AI  /  Local workspace")

        def capture(widget, name):
            widget.show()
            app.processEvents()
            QTest.qWait(150)
            assert widget.grab().save(str(output / name))

        window.resize(1280, 800)
        capture(window, "neuroephys-home-zh.png")
        tutorial = TutorialDialog("import", window, "zh_CN")
        capture(tutorial, "neuroephys-tutorial-zh.png")
        tutorial.resize(650, 760)
        capture(tutorial, "neuroephys-tutorial-small-zh.png")
        tutorial.close()
        guide = StageGuideDialog("sorting", window, "zh_CN")
        capture(guide, "neuroephys-guide-zh.png")
        guide.close()
        state = generate_demo_recording(workspace / "Teaching_example", duration_seconds=8, channel_count=8)
        state.name = "微丝教学示例"
        state.metadata["language"] = "zh_CN"
        run_raw_qc(state)
        state.sorted_spikes = state.ground_truth
        compute_unit_metrics(state)
        save_project(state)
        window._load_state(state)
        window._select_step("qc")
        window.resize(1500, 920)
        capture(window, "neuroephys-workspace-zh.png")
        window.resize(900, 650)
        capture(window, "neuroephys-workspace-small-zh.png")
        window._set_language("en_US")
        window.resize(1280, 800)
        window.pages.setCurrentWidget(window.home_page)
        window.home_workspace_hint.setText("NeuroEphys AI  /  Local workspace")
        capture(window, "neuroflow-home.png")
        tutorial = TutorialDialog("import", window, "en_US")
        capture(tutorial, "neuroflow-tutorial.png")
        tutorial.close()
        window.project_dirty = False
        window.close()
        app.processEvents()
    print(f"Experience screenshots: {output}")


if __name__ == "__main__":
    main()
