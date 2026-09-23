"""Explicit behavior-event selection for event-aligned Unit tuning."""

from __future__ import annotations

from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QLabel, QListWidget,
    QMessageBox, QVBoxLayout,
)

from .event_semantics import event_analysis_label
from .models import ProjectState


class EventTuningDialog(QDialog):
    def __init__(self, state: ProjectState, language: str, parent=None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(
            "选择行为事件 · Unit tuning" if language == "zh_CN"
            else "Select behavior events · Unit tuning"
        )
        self.resize(560, 520)
        layout = QVBoxLayout(self)
        instruction = QLabel(
            "选择 1 个行为：与自身事件前基线比较；选择 2 个行为：同时比较两条 PSTH。"
            "统计和解码中的条件对比只适用于两个可区分的条件。同步脉冲、显式排除及超出记录边界的事件不会纳入。"
            if language == "zh_CN" else
            "Select one behavior to compare with its pre-event baseline, or two "
            "to compare PSTHs. Condition statistics/decoding require two distinct "
            "conditions. Synchronization, excluded and out-of-recording events are omitted."
        )
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
        counts: Counter[str] = Counter()
        for event in state.events:
            if event.get("exclude") or event.get("analysis_role") == "synchronization":
                continue
            time = float(event.get("time_seconds", -1))
            if time - 0.5 < 0 or time + 1.0 > state.duration_seconds:
                continue
            label, _ = event_analysis_label(event)
            if label.casefold() not in {"unknown", "nan", "none"}:
                counts[label] += 1
        self.event_list = QListWidget()
        self.event_list.setSelectionMode(QAbstractItemView.MultiSelection)
        previous = state.analysis.get("event_filter", {}).get("requested_conditions")
        if not previous:
            previous = state.analysis.get("condition_labels", [])[:2]
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            self.event_list.addItem(f"{label} · n={count}")
            item = self.event_list.item(self.event_list.count() - 1)
            item.setData(Qt.UserRole, label)
            item.setSelected(label in previous)
        layout.addWidget(self.event_list, 1)
        self.count_label = QLabel()
        layout.addWidget(self.count_label)
        self.event_list.itemSelectionChanged.connect(self._update_count)
        self._update_count()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(
            "按所选事件重新分析" if language == "zh_CN" else "Analyze selected events"
        )
        buttons.accepted.connect(self._accept_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_conditions(self) -> list[str]:
        return [str(item.data(Qt.UserRole)) for item in self.event_list.selectedItems()]

    def _update_count(self) -> None:
        selected = self.selected_conditions()
        self.count_label.setText(
            f"已选 {len(selected)} / 2 个行为条件"
            if self.language == "zh_CN" else
            f"{len(selected)} / 2 behavior conditions selected"
        )

    def _accept_valid(self) -> None:
        count = len(self.selected_conditions())
        if not 1 <= count <= 2:
            QMessageBox.warning(
                self, self.windowTitle(),
                "请选择 1 或 2 个行为条件。" if self.language == "zh_CN"
                else "Select one or two behavior conditions.",
            )
            return
        self.accept()
