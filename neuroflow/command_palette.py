"""Keyboard-first lookup for the application's existing, authorized actions."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

PALETTE_STYLE = """
QDialog { background: #100d17; color: #f2edf5; }
QLabel { color: #f2edf5; background: transparent; }
QLabel#PaletteHint { color: #b8adc6; }
QLineEdit {
    color: #f2edf5; background: #181421; border: 1px solid #66536e;
    border-radius: 7px; padding: 11px; font-size: 15px;
    selection-background-color: #674373;
}
QLineEdit:focus { border-color: #d885e9; }
QListWidget {
    color: #f2edf5; background: #181421; border: 1px solid #393043;
    border-radius: 7px; padding: 4px; outline: 0;
}
QListWidget::item { padding: 9px; border-radius: 5px; }
QListWidget::item:selected { color: #f2edf5; background: #44304e; }
QListWidget::item:hover { background: #211d2b; }
QListWidget::item:disabled { color: #b8adc6; }
QPushButton {
    color: #f2edf5; background: #211d2b; border: 1px solid #66536e;
    border-radius: 6px; padding: 8px 16px;
}
QPushButton:hover { border-color: #d885e9; }
QPushButton:disabled { color: #b8adc6; border-color: #393043; }
"""


def _search_text(value: object) -> str:
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(part) for part in value)
    return unicodedata.normalize("NFKC", str(value or "")).casefold()


class CommandPaletteDialog(QDialog):
    """Find and invoke an existing action without bypassing its own checks.

    Commands are mappings with ``key``, ``title``, ``description``, ``shortcut``,
    ``callback`` and ``enabled`` (bool or zero-argument callable). Optional
    ``keywords`` provides bilingual search aliases and ``disabled_reason``
    explains unavailable commands. Callbacks are dispatched after the dialog
    closes, so the original action may show its own dialog normally.
    """

    def __init__(
        self,
        commands: Iterable[Mapping],
        parent: QWidget | None = None,
        language: str = "zh_CN",
    ) -> None:
        super().__init__(parent)
        self.language = language
        self.commands = [dict(command) for command in commands]
        self._dispatched = False
        self.setWindowTitle(self._text("查找操作", "Find an action"))
        self.resize(650, 475)
        self.setMinimumSize(440, 350)
        self.setStyleSheet(PALETTE_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 16)
        root.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            self._text("查找操作、流程或教程…", "Find an action, stage, or tutorial…")
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setAccessibleName(self._text("查找操作", "Find an action"))
        self.search_input.installEventFilter(self)
        root.addWidget(self.search_input)
        self.command_list = QListWidget()
        self.command_list.setWordWrap(True)
        self.command_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.command_list.setSpacing(2)
        self.command_list.installEventFilter(self)
        root.addWidget(self.command_list, 1)
        self.empty_label = QLabel()
        self.empty_label.setObjectName("PaletteHint")
        self.empty_label.setWordWrap(True)
        root.addWidget(self.empty_label)
        self.detail_label = QLabel()
        self.detail_label.setObjectName("PaletteHint")
        self.detail_label.setWordWrap(True)
        self.detail_label.setTextFormat(Qt.PlainText)
        self.detail_label.setMinimumHeight(38)
        root.addWidget(self.detail_label)
        footer = QHBoxLayout()
        hint = QLabel(
            self._text(
                "↑ ↓ 选择    Enter 打开    Esc 关闭",
                "↑ ↓ Select    Enter Open    Esc Close",
            )
        )
        hint.setObjectName("PaletteHint")
        footer.addWidget(hint, 1)
        self.execute_button = QPushButton(self._text("打开", "Open"))
        self.execute_button.setDefault(True)
        self.execute_button.clicked.connect(self._execute_current)
        footer.addWidget(self.execute_button)
        root.addLayout(footer)
        self.search_input.textChanged.connect(self._filter)
        self.command_list.currentItemChanged.connect(self._update_selection)
        self.command_list.itemDoubleClicked.connect(self._execute_current)
        self._filter("")
        self.search_input.setFocus()

    def _text(self, chinese: str, english: str) -> str:
        return english if self.language == "en_US" else chinese

    @staticmethod
    def _enabled(command: Mapping) -> bool:
        enabled = command.get("enabled", True)
        return bool(enabled() if callable(enabled) else enabled) and callable(
            command.get("callback")
        )

    def _filter(self, query: str) -> None:
        tokens = _search_text(query).split()
        self.command_list.clear()
        first_enabled = None
        for index, command in enumerate(self.commands):
            haystack = " ".join(
                _search_text(command.get(field, ""))
                for field in ("key", "title", "description", "shortcut", "keywords")
            )
            if not all(token in haystack for token in tokens):
                continue
            enabled = self._enabled(command)
            title = str(command.get("title", command.get("key", "")))
            shortcut = str(command.get("shortcut") or "")
            if shortcut:
                title += f"    {shortcut}"
            description = str(command.get("description") or "")
            if not enabled:
                reason = str(command.get("disabled_reason") or description)
                description = self._text("暂不可用：", "Unavailable: ") + (
                    reason or self._text("请先打开项目。", "Open a project first.")
                )
            item = QListWidgetItem(f"{title}\n{description}")
            item.setData(Qt.UserRole, index)
            item.setToolTip(f"{title}\n{description}")
            if not enabled:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            elif first_enabled is None:
                first_enabled = self.command_list.count()
            self.command_list.addItem(item)
        has_matches = self.command_list.count() > 0
        self.empty_label.setVisible(not has_matches)
        self.empty_label.setText(
            self._text(
                "没有找到匹配的操作。试试“保存”“sorting”“教程”，或清空搜索。",
                "No matching actions. Try “save”, “sorting”, or “tutorial”, or clear the search.",
            )
        )
        if first_enabled is not None:
            self.command_list.setCurrentRow(first_enabled)
        self._resize_items()
        self._update_selection()

    def _resize_items(self) -> None:
        width = max(180, self.command_list.viewport().width() - 34)
        metrics = self.command_list.fontMetrics()
        for row in range(self.command_list.count()):
            item = self.command_list.item(row)
            text_rect = metrics.boundingRect(
                0, 0, width, 10_000, Qt.TextWordWrap, item.text()
            )
            item.setSizeHint(QSize(0, max(62, text_rect.height() + 24)))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_items()

    def _current_command(self) -> dict | None:
        item = self.command_list.currentItem()
        if item is None:
            return None
        return self.commands[int(item.data(Qt.UserRole))]

    def _update_selection(self, *_args) -> None:
        command = self._current_command()
        enabled = command is not None and self._enabled(command)
        self.execute_button.setEnabled(enabled)
        self.detail_label.setText(
            str(command.get("description") or "")
            if command and enabled
            else self._text(
                "不可用操作的原因显示在列表中。",
                "Unavailable actions show the reason in the list.",
            )
            if self.command_list.count()
            else ""
        )

    def _execute_current(self, *_args) -> None:
        command = self._current_command()
        if self._dispatched or command is None or not self._enabled(command):
            self._update_selection()
            return
        self._dispatched = True
        callback = command["callback"]
        self.accept()
        QTimer.singleShot(0, callback)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._execute_current()
                return True
            if key == Qt.Key_Escape:
                self.reject()
                return True
            if watched is self.search_input and key in (Qt.Key_Up, Qt.Key_Down):
                direction = 1 if key == Qt.Key_Down else -1
                row = self.command_list.currentRow() + direction
                while 0 <= row < self.command_list.count():
                    if self.command_list.item(row).flags() & Qt.ItemIsEnabled:
                        self.command_list.setCurrentRow(row)
                        break
                    row += direction
                return True
        return super().eventFilter(watched, event)
