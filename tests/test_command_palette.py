import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from neuroflow.command_palette import CommandPaletteDialog


def test_search_matches_bilingual_aliases_and_all_query_terms():
    app = QApplication.instance() or QApplication([])
    dialog = CommandPaletteDialog(
        [
            {
                "key": "save",
                "title": "保存项目",
                "keywords": ["save", "project"],
                "callback": lambda: None,
            },
            {
                "key": "sorting",
                "title": "Spike sorting",
                "description": "排序并比较",
                "callback": lambda: None,
            },
        ]
    )
    dialog.search_input.setText("ＳＡＶＥ project")
    assert dialog.command_list.count() == 1
    assert dialog._current_command()["key"] == "save"
    dialog.search_input.setText("排序")
    assert dialog._current_command()["key"] == "sorting"
    dialog.search_input.setText("missing-result")
    assert dialog.command_list.count() == 0
    assert not dialog.execute_button.isEnabled()
    assert not dialog.empty_label.isHidden()
    dialog.close()
    app.processEvents()


def test_keyboard_skips_unavailable_commands_and_dispatches_after_close():
    app = QApplication.instance() or QApplication([])
    calls = []
    dialog = CommandPaletteDialog(
        [
            {
                "key": "first",
                "title": "第一项",
                "callback": lambda: calls.append("first"),
            },
            {
                "key": "locked",
                "title": "排序",
                "enabled": False,
                "disabled_reason": "没有原始电压",
                "callback": lambda: calls.append("locked"),
            },
            {
                "key": "last",
                "title": "最后一项",
                "callback": lambda: calls.append("last"),
            },
        ]
    )
    assert "没有原始电压" in dialog.command_list.item(1).text()
    assert not dialog.command_list.item(1).flags() & Qt.ItemIsEnabled
    QTest.keyClick(dialog.search_input, Qt.Key_Down)
    assert dialog._current_command()["key"] == "last"
    QTest.keyClick(dialog.search_input, Qt.Key_Return)
    assert dialog.result() == QDialog.Accepted
    assert calls == []
    app.processEvents()
    assert calls == ["last"]
    dialog._execute_current()
    app.processEvents()
    assert calls == ["last"]


def test_enabled_state_is_rechecked_at_execution_and_escape_never_runs():
    app = QApplication.instance() or QApplication([])
    permitted = [True]
    calls = []
    dialog = CommandPaletteDialog(
        [
            {
                "key": "run",
                "title": "运行",
                "enabled": lambda: permitted[0],
                "callback": lambda: calls.append("run"),
            }
        ]
    )
    permitted[0] = False
    QTest.keyClick(dialog.search_input, Qt.Key_Return)
    app.processEvents()
    assert calls == []
    assert not dialog.execute_button.isEnabled()
    QTest.keyClick(dialog.search_input, Qt.Key_Escape)
    assert dialog.result() == QDialog.Rejected
    app.processEvents()
    assert calls == []
