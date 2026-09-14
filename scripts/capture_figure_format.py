"""Capture real Qt formatting controls without touching user preferences or records."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from neuroflow import ui, tutorial_center
from neuroflow.figure_studio import FigureStudioDialog
from neuroflow.figures import raw_overview_figure
from neuroflow.simulation import generate_demo_recording


def main():
    output = ROOT / "docs/site/assets"
    workspace = ROOT / "docs_capture_workspace/figure_format_1_2_1"
    with tempfile.TemporaryDirectory(prefix="neuroephys-format-") as temp:
        ui.QSettings = tutorial_center.QSettings = lambda *_: QSettings(str(Path(temp) / "capture.ini"), QSettings.IniFormat)
        app = QApplication.instance() or QApplication([])
        app.setFont(QFont("Microsoft YaHei", 10))
        window = ui.NeuroFlowWindow(workspace)
        state = generate_demo_recording(workspace / "example", duration_seconds=8, channel_count=8)
        window.state = state
        figure = raw_overview_figure(state, show_ground_truth=True)
        dialog = FigureStudioDialog(figure, parent=window, initial_axis=figure.axes[1])
        dialog.resize(1280, 820)
        dialog.show()
        app.processEvents()
        QTest.qWait(150)
        dialog._update_preview()
        app.processEvents()
        print("Preview geometry:", dialog.preview_label.size(), "Figure:", figure.get_size_inches(), flush=True)
        dialog.grab().save(str(output / "neuroephys-format-panel.png"))
        dialog.mode_tabs.setCurrentIndex(1)
        app.processEvents()
        dialog.grab().save(str(output / "neuroephys-format-shared.png"))
        dialog.resize(920, 700)
        app.processEvents()
        dialog._update_preview()
        app.processEvents()
        dialog.grab().save(str(output / "neuroephys-format-small.png"))
        dialog.close()
        window.project_dirty = False
        window.close()
        app.processEvents()
    print("Figure-format screenshots captured")


if __name__ == "__main__":
    main()
