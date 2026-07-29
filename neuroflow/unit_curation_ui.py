from __future__ import annotations

from typing import Callable

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .figures import unit_metrics_figure
from .models import ProjectState
from .unit_curation import (
    CURATION_CHECKS,
    curation_summary,
    save_unit_curation,
    unit_curation_record,
)

_LABELS = {
    "candidate_single_unit": ("候选单神经元", "Candidate single unit"),
    "multi_unit_activity": ("多单元活动", "Multi-unit activity"),
    "noise": ("噪声", "Noise"),
    "artifact": ("伪迹", "Artifact"),
    "uncertain": ("待定", "Uncertain"),
}

_CHECK_LABELS = {
    "waveform_shape": ("波形形态已检查", "Waveform shape reviewed"),
    "refractory_period": ("不应期与 ACG 已检查", "Refractory period and ACG reviewed"),
    "amplitude_stability": ("振幅稳定性已检查", "Amplitude stability reviewed"),
    "recording_stability": ("整段记录稳定性已检查", "Recording stability reviewed"),
    "spatial_or_channel_profile": (
        "通道或空间分布已检查",
        "Channel or spatial profile reviewed",
    ),
    "duplicate_template_risk": (
        "重复模板或拆分风险已检查",
        "Duplicate or split-cluster risk reviewed",
    ),
}


class UnitCurationDialog(QDialog):
    def __init__(
        self,
        state: ProjectState,
        language: str,
        *,
        saved_handler: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.state = state
        self.language = language
        self.english = language == "en_US"
        self.saved_handler = saved_handler
        self.sorter_key = state.active_sorter_key or "unassigned"
        self.checks: dict[str, QCheckBox] = {}
        self.setWindowTitle(
            "Manual Unit curation"
            if self.english
            else "人工 Unit 复核"
        )
        self.resize(1420, 860)
        self.setMinimumSize(1080, 680)
        self._build()
        self._load_units()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        heading = QLabel(
            (
                f"Sorter: {self.sorter_key} · candidate clusters require human review"
                if self.english
                else f"Sorter：{self.sorter_key} · 候选 cluster 需要人工复核"
            )
        )
        heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(heading)
        explanation = QLabel(
            (
                "Automatic metrics are screening evidence. Review the waveform, ACG, "
                "refractory-period violations, amplitude over time, stability and "
                "channel/spatial profile before assigning a label. A curated label "
                "remains an expert decision, not biological ground truth."
                if self.english
                else (
                    "自动指标只提供筛选证据。标记前请检查波形、ACG、不应期违例、"
                    "振幅随时间变化、记录稳定性和通道/空间分布。人工标签代表专家"
                    "复核结论，仍不能视为生物学真值。"
                )
            )
        )
        explanation.setWordWrap(True)
        root.addWidget(explanation)

        splitter = QSplitter(Qt.Horizontal)
        left = QFrame()
        left_layout = QVBoxLayout(left)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        left_layout.addWidget(self.summary_label)
        self.unit_list = QListWidget()
        self.unit_list.currentRowChanged.connect(self._unit_changed)
        left_layout.addWidget(self.unit_list, 1)
        splitter.addWidget(left)

        center = QFrame()
        center_layout = QVBoxLayout(center)
        self.canvas = FigureCanvasQTAgg(
            unit_metrics_figure(self.state, "overview")
        )
        self.toolbar = NavigationToolbar2QT(self.canvas, center)
        center_layout.addWidget(self.toolbar)
        center_layout.addWidget(self.canvas, 1)
        splitter.addWidget(center)

        right = QFrame()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.label_combo = QComboBox()
        for value, labels in _LABELS.items():
            self.label_combo.addItem(labels[1 if self.english else 0], value)
        form.addRow("Decision" if self.english else "人工分类", self.label_combo)
        self.confidence_combo = QComboBox()
        for value, zh, en in (
            ("low", "低", "Low"),
            ("medium", "中", "Medium"),
            ("high", "高", "High"),
        ):
            self.confidence_combo.addItem(en if self.english else zh, value)
        form.addRow("Confidence" if self.english else "置信度", self.confidence_combo)
        self.reviewer_edit = QLineEdit()
        form.addRow("Reviewer" if self.english else "复核人", self.reviewer_edit)
        right_layout.addLayout(form)
        check_title = QLabel(
            "Evidence checklist" if self.english else "证据检查清单"
        )
        check_title.setStyleSheet("font-weight: 700;")
        right_layout.addWidget(check_title)
        for key in CURATION_CHECKS:
            box = QCheckBox(_CHECK_LABELS[key][1 if self.english else 0])
            self.checks[key] = box
            right_layout.addWidget(box)
        notes_title = QLabel("Notes" if self.english else "复核备注")
        notes_title.setStyleSheet("font-weight: 700;")
        right_layout.addWidget(notes_title)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText(
            (
                "Record borderline evidence, suspected merges/splits, drift, or the "
                "reason for retaining a MUA cluster."
                if self.english
                else "记录边界证据、疑似合并/拆分、漂移，或保留 MUA 的原因。"
            )
        )
        right_layout.addWidget(self.notes_edit, 1)
        self.metric_label = QLabel()
        self.metric_label.setWordWrap(True)
        right_layout.addWidget(self.metric_label)
        splitter.addWidget(right)
        splitter.setSizes([220, 850, 340])
        root.addWidget(splitter, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Save).setText(
            "Save decision" if self.english else "保存本 Unit 结论"
        )
        buttons.button(QDialogButtonBox.Close).setText(
            "Close" if self.english else "关闭"
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.accept)
        root.addWidget(buttons)

    def _load_units(self) -> None:
        self.unit_list.clear()
        metrics = {
            int(item.get("unit_id", -1)): item for item in self.state.unit_metrics
        }
        for unit_id in sorted(self.state.sorted_spikes):
            record = unit_curation_record(self.state, unit_id, self.sorter_key)
            label = record.get("label")
            status = (
                _LABELS.get(str(label), ("", ""))[1 if self.english else 0]
                if label
                else ("Pending" if self.english else "待复核")
            )
            metric = metrics.get(unit_id, {})
            self.unit_list.addItem(
                f"Unit {unit_id} · {status} · "
                f"{float(metric.get('firing_rate_hz', 0.0)):.2f} Hz"
            )
        summary = curation_summary(self.state, self.sorter_key)
        self.summary_label.setText(
            (
                f"Reviewed {summary['reviewed_unit_count']} / "
                f"{summary['candidate_unit_count']} candidate clusters"
                if self.english
                else (
                    f"已复核 {summary['reviewed_unit_count']} / "
                    f"{summary['candidate_unit_count']} 个候选 cluster"
                )
            )
        )
        if self.unit_list.count():
            self.unit_list.setCurrentRow(0)

    def _selected_unit(self) -> int | None:
        row = self.unit_list.currentRow()
        units = sorted(self.state.sorted_spikes)
        return units[row] if 0 <= row < len(units) else None

    def _unit_changed(self, _row: int) -> None:
        unit_id = self._selected_unit()
        if unit_id is None:
            return
        self.canvas.figure = unit_metrics_figure(
            self.state,
            f"unit:{unit_id}",
        )
        self.canvas.draw_idle()
        record = unit_curation_record(self.state, unit_id, self.sorter_key)
        self.label_combo.setCurrentIndex(
            max(self.label_combo.findData(record.get("label", "uncertain")), 0)
        )
        self.confidence_combo.setCurrentIndex(
            max(self.confidence_combo.findData(record.get("confidence", "medium")), 0)
        )
        self.reviewer_edit.setText(str(record.get("reviewer", "")))
        self.notes_edit.setPlainText(str(record.get("notes", "")))
        saved_checks = record.get("checks", {})
        for key, box in self.checks.items():
            box.setChecked(bool(saved_checks.get(key, False)))
        metric = next(
            (
                item
                for item in self.state.unit_metrics
                if int(item.get("unit_id", -1)) == unit_id
            ),
            {},
        )
        self.metric_label.setText(
            (
                f"Spikes: {int(metric.get('spike_count', 0)):,}\n"
                f"Rate: {float(metric.get('firing_rate_hz', 0.0)):.3f} Hz\n"
                f"ISI violations: {float(metric.get('isi_violation_rate', 0.0)):.4f}\n"
                f"SNR: {float(metric.get('snr', float('nan'))):.2f}\n"
                f"Peak channel: {metric.get('peak_channel', '—')}\n"
                f"Maximum cross-unit timestamp overlap: "
                f"{float(metric.get('max_cross_unit_overlap_fraction', 0.0)):.1%}\n"
                f"Possible duplicate partner: "
                f"{metric.get('duplicate_partner_unit', '—')}"
            )
        )

    def _save(self) -> None:
        unit_id = self._selected_unit()
        if unit_id is None:
            return
        if not any(box.isChecked() for box in self.checks.values()):
            QMessageBox.warning(
                self,
                "Evidence not reviewed" if self.english else "尚未检查证据",
                (
                    "Review the diagnostic panels and select the completed checks "
                    "before saving a manual decision."
                    if self.english
                    else "请先查看诊断图，并勾选已经完成的证据检查。"
                ),
            )
            return
        save_unit_curation(
            self.state,
            unit_id,
            label=str(self.label_combo.currentData()),
            confidence=str(self.confidence_combo.currentData()),
            checks={key: box.isChecked() for key, box in self.checks.items()},
            notes=self.notes_edit.toPlainText(),
            reviewer=self.reviewer_edit.text(),
            sorter_key=self.sorter_key,
        )
        if self.saved_handler:
            self.saved_handler()
        current = self.unit_list.currentRow()
        self._load_units()
        self.unit_list.setCurrentRow(current)
