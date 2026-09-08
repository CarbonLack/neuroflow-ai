import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from neuroflow.tutorial_catalog import TUTORIAL_CATALOG
from neuroflow.tutorial_center import TutorialDialog, task_html
from neuroflow.ui import STEPS


def test_all_help_routes_and_bilingual_sections_are_renderable():
    keys = {step.key for step in STEPS}
    assert keys <= {item["id"] for item in TUTORIAL_CATALOG}
    assert len({item["id"] for item in TUTORIAL_CATALOG}) == len(TUTORIAL_CATALOG)
    for item in TUTORIAL_CATALOG:
        assert item["page_key"] is None or item["page_key"] in keys
        for language in ("zh_CN", "en_US"):
            for section in ("steps", "reference", "troubleshooting"):
                html = task_html(item, language, section)
                assert "<h3>" in html
                assert "<table" not in html
                assert "<script" not in html


def test_tutorial_search_navigation_zoom_and_empty_state(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("neuroflow.tutorial_center.QSettings", lambda *_: QSettings(str(tmp_path / "help.ini"), QSettings.IniFormat))
    dialog = TutorialDialog("sorting", language="zh_CN")
    dialog.show()
    app.processEvents()
    assert dialog.selected_id == "sorting"
    dialog.search.setText("Kilosort")
    assert dialog.list.count() > 0
    assert all("kilosort" in str(i).casefold() for i in dialog.filtered)
    dialog.search.setText("does-not-exist-1234")
    assert dialog.list.count() == 0
    assert not dialog.open_button.isEnabled()
    assert not dialog.next_button.isEnabled()
    dialog.search.clear()
    dialog._toggle_read()
    selected = dialog.selected_id
    assert selected in dialog.read_ids
    dialog._zoom(1)
    font_size = dialog.font_size
    dialog.resize(650, 700)
    app.processEvents()
    assert dialog.splitter.orientation() == Qt.Vertical
    assert dialog.browser.viewport().width() > 300
    dialog.close()
    reopened = TutorialDialog(selected, language="zh_CN")
    assert selected in reopened.read_ids
    assert reopened.font_size == font_size
    reopened.close()
