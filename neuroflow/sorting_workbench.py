from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QStackedWidget,
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
    ("comparison", "Sorter 统一结果与比较", "Normalized sorter comparison"),
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
        self.completed_keys: set[str] = set()
        self.active_key: str | None = None
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

        self.table = QTableWidget(0, 5)
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
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setMinimumHeight(148)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.setProperty("neuroflow_help_key", "sorting.selector")
        root.addWidget(self.table)

        self.selection_detail = QLabel()
        self.selection_detail.setWordWrap(True)
        self.selection_detail.setObjectName("Muted")
        root.addWidget(self.selection_detail)

        settings_row = QHBoxLayout()
        settings_row.setSpacing(12)
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
        self.threshold_holder = QFrame()
        threshold_row = QHBoxLayout(self.threshold_holder)
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
        self.ms5_scheme = QComboBox()
        self.ms5_scheme.addItem("Scheme 1 · quick/debug", "1")
        self.ms5_scheme.addItem("Scheme 2 · standard", "2")
        self.ms5_scheme.addItem("Scheme 3 · long/drift", "3")
        self.ms5_scheme.setCurrentIndex(1)
        self.ms5_scheme.setProperty("neuroflow_help_key", "sorting.ms5_scheme")
        self.ms5_threshold = QDoubleSpinBox()
        self.ms5_threshold.setRange(3.0, 12.0)
        self.ms5_threshold.setSingleStep(0.5)
        self.ms5_threshold.setValue(5.5)
        self.ms5_threshold.setProperty(
            "neuroflow_help_key", "sorting.ms5_threshold"
        )
        self.ms5_training = QSpinBox()
        self.ms5_training.setRange(30, 3_600)
        self.ms5_training.setSingleStep(30)
        self.ms5_training.setValue(300)
        self.ms5_training.setSuffix(" s")
        self.ms5_training.setProperty("neuroflow_help_key", "sorting.ms5_training")
        self.preset_label = QLabel()
        self.threshold_label = QLabel()
        self.ms5_scheme_label = QLabel()
        self.ms5_threshold_label = QLabel()
        self.ms5_training_label = QLabel()

        self.parameter_stack = QStackedWidget()
        self.kilosort_panel = QFrame()
        self.kilosort_panel.setObjectName("InsetPanel")
        kilosort_grid = QGridLayout(self.kilosort_panel)
        kilosort_grid.setContentsMargins(12, 8, 12, 8)
        kilosort_grid.setHorizontalSpacing(10)
        kilosort_grid.setVerticalSpacing(6)
        kilosort_grid.addWidget(self.preset_label, 0, 0)
        kilosort_grid.addWidget(self.preset, 0, 1, 1, 3)
        kilosort_grid.addWidget(QLabel("batch_size"), 1, 0)
        kilosort_grid.addWidget(self.batch_size, 1, 1)
        kilosort_grid.addWidget(QLabel("nblocks"), 1, 2)
        kilosort_grid.addWidget(self.nblocks, 1, 3)
        kilosort_grid.addWidget(self.threshold_label, 2, 0)
        kilosort_grid.addWidget(self.threshold_holder, 2, 1, 1, 2)
        kilosort_grid.addWidget(self.save_extra, 2, 3)
        kilosort_grid.setColumnStretch(1, 2)
        kilosort_grid.setColumnStretch(3, 2)

        self.mountainsort_panel = QFrame()
        self.mountainsort_panel.setObjectName("InsetPanel")
        mountainsort_grid = QGridLayout(self.mountainsort_panel)
        mountainsort_grid.setContentsMargins(12, 8, 12, 8)
        mountainsort_grid.setHorizontalSpacing(10)
        mountainsort_grid.setVerticalSpacing(6)
        mountainsort_grid.addWidget(self.ms5_scheme_label, 0, 0)
        mountainsort_grid.addWidget(self.ms5_scheme, 0, 1, 1, 3)
        mountainsort_grid.addWidget(self.ms5_threshold_label, 1, 0)
        mountainsort_grid.addWidget(self.ms5_threshold, 1, 1)
        mountainsort_grid.addWidget(self.ms5_training_label, 1, 2)
        mountainsort_grid.addWidget(self.ms5_training, 1, 3)
        mountainsort_grid.setColumnStretch(1, 2)
        mountainsort_grid.setColumnStretch(3, 2)

        self.default_panel = QFrame()
        self.default_panel.setObjectName("InsetPanel")
        default_layout = QVBoxLayout(self.default_panel)
        default_layout.setContentsMargins(12, 8, 12, 8)
        self.default_parameter_text = QLabel()
        self.default_parameter_text.setWordWrap(True)
        self.default_parameter_text.setObjectName("Muted")
        default_layout.addWidget(self.default_parameter_text)

        self.parameter_stack.addWidget(self.kilosort_panel)
        self.parameter_stack.addWidget(self.mountainsort_panel)
        self.parameter_stack.addWidget(self.default_panel)
        settings_row.addWidget(self.parameter_stack, 3)

        result_frame = QFrame()
        result_frame.setObjectName("InsetPanel")
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(12, 8, 12, 8)
        self.view_label = QLabel()
        self.view_label.setObjectName("FieldLabel")
        result_layout.addWidget(self.view_label)
        self.diagnostic_combo = QComboBox()
        self.diagnostic_combo.setProperty("neuroflow_help_key", "sorting.view")
        self.diagnostic_combo.currentIndexChanged.connect(self._diagnostic_selected)
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
            ["Sorter", "环境", "结果", "硬件", "适用记录"]
            if language == "zh_CN"
            else ["Sorter", "Environment", "Result", "Hardware", "Best suited recordings"]
        )
        self.view_label.setText(
            self._label("运行后诊断视图", "Post-run diagnostic view")
        )
        self.preset_label.setText(self._label("预设", "Preset"))
        self.threshold_label.setText(self._label("检测阈值", "Detection thresholds"))
        self.ms5_scheme_label.setText(
            self._label("MountainSort5 方案", "MountainSort5 scheme")
        )
        self.ms5_threshold_label.setText(
            self._label("MS5 检测阈值", "MS5 detection threshold")
        )
        self.ms5_training_label.setText(
            self._label("MS5 训练时长", "MS5 training duration")
        )
        self.default_parameter_text.setText(
            self._label(
                "该 SpikeInterface 内部 sorter 使用当前版本的受控默认参数。"
                "运行前可在教程中查看参数来源，结果会保留版本与完整配置。",
                "This SpikeInterface internal sorter uses versioned, controlled defaults. "
                "The tutorial explains their source and the complete configuration is saved.",
            )
        )
        self.save_extra.setText(
            self._label("保存额外诊断变量", "Save extra diagnostic variables")
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
            self.ms5_scheme,
            self.ms5_threshold,
            self.ms5_training,
        ):
            key = widget.property("neuroflow_help_key")
            if key:
                widget.setToolTip(control_help(str(key), language)[1])
        self._populate()

    def _diagnostic_selected(self) -> None:
        view = str(self.diagnostic_combo.currentData() or "pipeline")
        self.parameter_stack.setVisible(view != "comparison")
        self.diagnostic_changed.emit(view)

    def set_catalog(self, catalog: list[dict]) -> None:
        selected = self.selected_sorter()
        self.catalog = list(catalog)
        self._populate(selected)

    def set_results(self, sorter_keys: set[str], active_key: str | None) -> None:
        self.completed_keys = set(sorter_keys)
        self.active_key = active_key
        self._populate(active_key or self.selected_sorter())

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
            if item["key"] == self.active_key:
                result_status = self._label("当前结果", "Active result")
            elif item["key"] in self.completed_keys:
                result_status = self._label("已保存", "Saved")
            else:
                result_status = self._label("未运行", "Not run")
            hardware, best_for = (
                (item["hardware"], item["best_for"])
                if self.language == "en_US"
                else SORTER_ZH.get(item["key"], (item["hardware"], item["best_for"]))
            )
            for column, value in enumerate(
                (item["name"], status, result_status, hardware, best_for)
            ):
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
        if item["key"] in self.completed_keys:
            detail += self._label(
                "\n已保存统一格式结果；选择此行可重新查看，重新运行会形成可追溯更新。",
                "\nA normalized result is saved. Select this row to inspect it; reruns are audited.",
            )
        self.selection_detail.setText(detail)
        is_kilosort = item["key"] == "kilosort4"
        is_mountainsort = item["key"] == "mountainsort5"
        for widget in (
            self.preset,
            self.batch_size,
            self.nblocks,
            self.th_universal,
            self.th_learned,
            self.save_extra,
        ):
            widget.setEnabled(is_kilosort)
        for widget in (
            self.ms5_scheme,
            self.ms5_threshold,
            self.ms5_training,
        ):
            widget.setEnabled(is_mountainsort)
        self.parameter_stack.setCurrentWidget(
            self.kilosort_panel
            if is_kilosort
            else self.mountainsort_panel
            if is_mountainsort
            else self.default_panel
        )
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
        sorter = self.selected_sorter()
        if sorter == "kilosort4":
            return {
                "batch_size": int(self.batch_size.value()),
                "nblocks": int(self.nblocks.value()),
                "Th_universal": int(self.th_universal.value()),
                "Th_learned": int(self.th_learned.value()),
                "artifact_threshold": 12_000,
                "save_extra_vars": bool(self.save_extra.isChecked()),
            }
        if sorter == "mountainsort5":
            return {
                "scheme": str(self.ms5_scheme.currentData()),
                "detect_threshold": float(self.ms5_threshold.value()),
                "scheme2_training_duration_sec": int(self.ms5_training.value()),
            }
        return {}

    def help_controls(self) -> list:
        return [
            self.table,
            self.preset,
            self.batch_size,
            self.nblocks,
            self.th_universal,
            self.th_learned,
            self.diagnostic_combo,
            self.ms5_scheme,
            self.ms5_threshold,
            self.ms5_training,
        ]
