from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .help_content import control_help

SORTER_ZH = {
    "kilosort4": ("建议 NVIDIA GPU", "高密度硅探针、Neuropixels"),
    "mountainsort5": ("CPU", "tetrode、低至中等通道数"),
    "spykingcircus2": ("CPU；可选 GPU", "通用多通道细胞外记录"),
    "tridesclous2": ("CPU", "低至中等通道数记录"),
    "simple": ("CPU", "快速教学、预览和流程检查"),
    "lupin": ("CPU", "SpikeInterface 原生方法比较"),
}


DIAGNOSTIC_VIEWS = (
    ("pipeline", "流程与运行日志", "Pipeline and run log"),
    ("validation", "模拟 ground truth 验证", "Simulation ground-truth validation"),
    ("drift", "Spike 深度-时间与漂移", "Spike depth-time and drift"),
    ("amplitudes", "振幅随时间稳定性", "Amplitude stability over time"),
    ("templates", "模板波形与空间分布", "Template waveforms and spatial footprint"),
    ("similarity", "模板相似度与污染率", "Template similarity and contamination"),
    ("files", "Kilosort 输出文件", "Kilosort output files"),
)


class SortingWorkbench(QFrame):
    selection_changed = Signal(str)
    diagnostic_changed = Signal(str)

    def __init__(self, language: str, parent=None):
        super().__init__(parent)
        self.language = language
        self.catalog: list[dict] = []
        self.setObjectName("SortingWorkbench")
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 11, 12, 11)
        root.setSpacing(9)

        heading_row = QHBoxLayout()
        self.heading = QLabel()
        self.heading.setObjectName("PanelTitle")
        heading_row.addWidget(self.heading)
        heading_row.addStretch()
        self.selected_badge = QLabel()
        self.selected_badge.setObjectName("StatusBadge")
        heading_row.addWidget(self.selected_badge)
        root.addLayout(heading_row)

        self.table = QTableWidget(0, 4)
        self.table.setObjectName("SorterTable")
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setMinimumHeight(183)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.setProperty("neuroflow_help_key", "sorting.selector")
        root.addWidget(self.table)

        self.selection_detail = QLabel()
        self.selection_detail.setWordWrap(True)
        self.selection_detail.setObjectName("Muted")
        root.addWidget(self.selection_detail)

        settings_row = QHBoxLayout()
        settings_row.setSpacing(12)
        parameter_frame = QFrame()
        parameter_frame.setObjectName("InsetPanel")
        parameter_form = QFormLayout(parameter_frame)
        parameter_form.setContentsMargins(12, 8, 12, 8)
        self.preset = QComboBox()
        self.preset.addItem("Demo / low-channel", "demo")
        self.preset.addItem("Neuropixels", "neuropixels")
        self.preset.addItem("Custom", "custom")
        self.preset.currentIndexChanged.connect(self._apply_preset)
        self.preset.setProperty("neuroflow_help_key", "sorting.preset")
        self.batch_size = QSpinBox()
        self.batch_size.setRange(15_000, 1_200_000)
        self.batch_size.setSingleStep(30_000)
        self.batch_size.setValue(120_000)
        self.batch_size.setProperty("neuroflow_help_key", "sorting.batch_size")
        self.nblocks = QSpinBox()
        self.nblocks.setRange(0, 20)
        self.nblocks.setValue(0)
        self.nblocks.setProperty("neuroflow_help_key", "sorting.nblocks")
        threshold_holder = QFrame()
        threshold_row = QHBoxLayout(threshold_holder)
        threshold_row.setContentsMargins(0, 0, 0, 0)
        self.th_universal = QSpinBox()
        self.th_universal.setRange(4, 20)
        self.th_universal.setValue(9)
        self.th_learned = QSpinBox()
        self.th_learned.setRange(4, 20)
        self.th_learned.setValue(8)
        self.th_universal.setProperty("neuroflow_help_key", "sorting.thresholds")
        self.th_learned.setProperty("neuroflow_help_key", "sorting.thresholds")
        threshold_row.addWidget(QLabel("Universal"))
        threshold_row.addWidget(self.th_universal)
        threshold_row.addWidget(QLabel("Learned"))
        threshold_row.addWidget(self.th_learned)
        self.save_extra = QCheckBox()
        self.save_extra.setChecked(True)
        parameter_form.addRow(self._label("预设", "Preset"), self.preset)
        parameter_form.addRow("batch_size", self.batch_size)
        parameter_form.addRow("nblocks", self.nblocks)
        parameter_form.addRow(
            self._label("检测阈值", "Detection thresholds"), threshold_holder
        )
        parameter_form.addRow(
            self._label("保存额外诊断变量", "Save extra diagnostic variables"),
            self.save_extra,
        )
        settings_row.addWidget(parameter_frame, 3)

        result_frame = QFrame()
        result_frame.setObjectName("InsetPanel")
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(12, 8, 12, 8)
        self.view_label = QLabel()
        self.view_label.setObjectName("FieldLabel")
        result_layout.addWidget(self.view_label)
        self.diagnostic_combo = QComboBox()
        self.diagnostic_combo.setProperty("neuroflow_help_key", "sorting.view")
        self.diagnostic_combo.currentIndexChanged.connect(
            lambda: self.diagnostic_changed.emit(
                str(self.diagnostic_combo.currentData() or "pipeline")
            )
        )
        result_layout.addWidget(self.diagnostic_combo)
        self.output_explanation = QLabel()
        self.output_explanation.setWordWrap(True)
        self.output_explanation.setObjectName("Muted")
        result_layout.addWidget(self.output_explanation)
        result_layout.addStretch()
        settings_row.addWidget(result_frame, 2)
        root.addLayout(settings_row)
        self.set_language(language)

    def _label(self, zh: str, en: str) -> str:
        return en if self.language == "en_US" else zh

    def set_language(self, language: str) -> None:
        self.language = language
        self.heading.setText(
            self._label("选择排序器并核对参数", "Select a sorter and verify parameters")
        )
        self.table.setHorizontalHeaderLabels(
            ["Sorter", "状态", "硬件", "适用记录"]
            if language == "zh_CN"
            else ["Sorter", "Status", "Hardware", "Best suited recordings"]
        )
        self.view_label.setText(
            self._label("运行后诊断视图", "Post-run diagnostic view")
        )
        self.output_explanation.setText(
            self._label(
                "运行前显示输入和参数；运行后这里可切换真实 Kilosort/SpikeInterface 输出。",
                "Before running, verify inputs and parameters. Afterward, switch among "
                "real Kilosort/SpikeInterface outputs here.",
            )
        )
        previous = self.diagnostic_combo.currentData()
        self.diagnostic_combo.blockSignals(True)
        self.diagnostic_combo.clear()
        for key, zh, en in DIAGNOSTIC_VIEWS:
            self.diagnostic_combo.addItem(en if language == "en_US" else zh, key)
        index = self.diagnostic_combo.findData(previous)
        self.diagnostic_combo.setCurrentIndex(max(index, 0))
        self.diagnostic_combo.blockSignals(False)
        for widget in (
            self.table,
            self.preset,
            self.batch_size,
            self.nblocks,
            self.th_universal,
            self.th_learned,
            self.diagnostic_combo,
        ):
            key = widget.property("neuroflow_help_key")
            if key:
                widget.setToolTip(control_help(str(key), language)[1])
        self._populate()

    def set_catalog(self, catalog: list[dict]) -> None:
        selected = self.selected_sorter()
        self.catalog = list(catalog)
        self._populate(selected)

    def _populate(self, selected: str | None = None) -> None:
        if not self.catalog:
            return
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.catalog))
        for row, item in enumerate(self.catalog):
            status = (
                self._label("可运行", "Available")
                if item["installed"]
                else self._label("不可用", "Unavailable")
            )
            hardware, best_for = (
                (item["hardware"], item["best_for"])
                if self.language == "en_US"
                else SORTER_ZH.get(item["key"], (item["hardware"], item["best_for"]))
            )
            for column, value in enumerate((item["name"], status, hardware, best_for)):
                table_item = QTableWidgetItem(str(value))
                table_item.setData(Qt.UserRole, item["key"])
                if not item["installed"]:
                    table_item.setForeground(Qt.darkGray)
                self.table.setItem(row, column, table_item)
            self.table.setRowHeight(row, 28)
        target = selected or "kilosort4"
        row = next(
            (index for index, item in enumerate(self.catalog) if item["key"] == target),
            0,
        )
        self.table.selectRow(row)
        self.table.blockSignals(False)
        self._selection_changed()

    def _selection_changed(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.catalog):
            return
        item = self.catalog[row]
        available = bool(item["installed"])
        self.selected_badge.setText(
            self._label("可运行", "Available")
            if available
            else self._label("当前不可用", "Unavailable")
        )
        self.selected_badge.setProperty("available", available)
        self.selected_badge.style().unpolish(self.selected_badge)
        self.selected_badge.style().polish(self.selected_badge)
        detail = f"{item['backend']} · {item['version']}" + (
            f"\n{item['error']}" if item.get("error") else ""
        )
        self.selection_detail.setText(detail)
        is_kilosort = item["key"] == "kilosort4"
        for widget in (
            self.preset,
            self.batch_size,
            self.nblocks,
            self.th_universal,
            self.th_learned,
            self.save_extra,
        ):
            widget.setEnabled(is_kilosort)
        self.selection_changed.emit(item["key"])

    def _apply_preset(self) -> None:
        preset = self.preset.currentData()
        if preset == "demo":
            self.batch_size.setValue(120_000)
            self.nblocks.setValue(0)
            self.th_universal.setValue(9)
            self.th_learned.setValue(8)
        elif preset == "neuropixels":
            self.batch_size.setValue(60_000)
            self.nblocks.setValue(1)
            self.th_universal.setValue(9)
            self.th_learned.setValue(8)

    def selected_sorter(self) -> str:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.catalog):
            return "kilosort4"
        return str(self.catalog[row]["key"])

    def selected_diagnostic(self) -> str:
        return str(self.diagnostic_combo.currentData() or "pipeline")

    def settings(self) -> dict:
        if self.selected_sorter() != "kilosort4":
            return {}
        return {
            "batch_size": int(self.batch_size.value()),
            "nblocks": int(self.nblocks.value()),
            "Th_universal": int(self.th_universal.value()),
            "Th_learned": int(self.th_learned.value()),
            "artifact_threshold": 12_000,
            "save_extra_vars": bool(self.save_extra.isChecked()),
        }

    def help_controls(self) -> list:
        return [
            self.table,
            self.preset,
            self.batch_size,
            self.nblocks,
            self.th_universal,
            self.th_learned,
            self.diagnostic_combo,
        ]
