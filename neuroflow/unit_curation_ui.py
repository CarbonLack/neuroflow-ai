from __future__ import annotations

from typing import Callable

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)
from matplotlib.path import Path as MplPath
from matplotlib.widgets import LassoSelector
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .figures import unit_cluster_figure, unit_metrics_figure
from .models import ProjectState
from .unit_curation import (
    CURATION_CHECKS,
    apply_curated_single_units,
    curated_unit_entries,
    curation_summary,
    save_unit_curation,
    save_spike_selection_edit,
    unit_curation_record,
    undo_spike_selection_edit,
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
        self._cluster_data_cache: dict = {}
        self._lasso: LassoSelector | None = None
        self._selected_spike_refs: list[tuple[int, int, int]] = []
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
        self.diagnostic_view = QComboBox()
        self.diagnostic_view.addItem(
            "逐次波形 + 同接点 Cluster PCA（先看这里）"
            if not self.english else "Individual spikes + same-contact cluster PCA",
            "cluster",
        )
        self.diagnostic_view.addItem(
            "平均波形 / 不应期 / 稳定性"
            if not self.english else "Mean waveform / ACG / stability",
            "qc",
        )
        self.diagnostic_view.currentIndexChanged.connect(self._refresh_unit_figure)
        center_layout.addWidget(self.diagnostic_view)
        cluster_controls = QHBoxLayout()
        self.contact_combo = QComboBox()
        contacts = sorted({int(row["peak_channel"]) for row in self.state.unit_metrics
                           if row.get("peak_channel") is not None})
        for contact in contacts:
            count = sum(int(row.get("peak_channel", -1)) == contact
                        for row in self.state.unit_metrics)
            self.contact_combo.addItem(f"Contact {contact} · {count} clusters", contact)
        self.contact_combo.currentIndexChanged.connect(self._contact_changed)
        cluster_controls.addWidget(QLabel("接点" if not self.english else "Contact"))
        cluster_controls.addWidget(self.contact_combo, 1)
        self.pc_x_combo = QComboBox()
        self.pc_y_combo = QComboBox()
        for pc in (1, 2, 3):
            self.pc_x_combo.addItem(f"PC {pc}", pc)
            self.pc_y_combo.addItem(f"PC {pc}", pc)
        self.pc_y_combo.setCurrentIndex(1)
        for combo, label in ((self.pc_x_combo, "X"), (self.pc_y_combo, "Y")):
            cluster_controls.addWidget(QLabel(label))
            cluster_controls.addWidget(combo)
            combo.currentIndexChanged.connect(self._refresh_unit_figure)
        center_layout.addLayout(cluster_controls)
        edit_controls = QHBoxLayout()
        self.lasso_button = QPushButton(
            "套索选择 spike" if not self.english else "Lasso spikes"
        )
        self.lasso_button.setCheckable(True)
        self.lasso_button.toggled.connect(self._toggle_lasso)
        self.clear_selection_button = QPushButton(
            "清除选择" if not self.english else "Clear selection"
        )
        self.clear_selection_button.clicked.connect(self._clear_spike_selection)
        self.exclude_spikes_button = QPushButton(
            "排除选中离群 spike" if not self.english else "Exclude selected outliers"
        )
        self.exclude_spikes_button.clicked.connect(self._exclude_selected_spikes)
        self.split_spikes_button = QPushButton(
            "选中项拆分为新 Unit" if not self.english else "Split selection into new Unit"
        )
        self.split_spikes_button.clicked.connect(self._split_selected_spikes)
        self.undo_spike_edit_button = QPushButton(
            "撤销 spike 编辑" if not self.english else "Undo spike edit"
        )
        self.undo_spike_edit_button.clicked.connect(self._undo_spike_edit)
        for button in (
            self.lasso_button, self.clear_selection_button,
            self.exclude_spikes_button, self.split_spikes_button,
            self.undo_spike_edit_button,
        ):
            edit_controls.addWidget(button)
        center_layout.addLayout(edit_controls)
        self.selection_label = QLabel(
            "已选 0 个 spike" if not self.english else "0 spikes selected"
        )
        center_layout.addWidget(self.selection_label)
        waveform_note = QLabel(
            (
                "细线＝每次 spike 的原始波形；黑线＝所示波形的平均形态；阴影＝波形差异。"
                "所有 spike 都显示，每个 PCA 点均对应回原始 sorter spike。"
                "0 ms 是 sorter 时间戳，不一定恰好是波谷。"
                "可切换接点和 PC 轴，点击散点选择 Unit，或用套索选择后排除/拆分；"
                "编辑不改写原 sorter 结果。这里的 PCA 是从原始片段重算的复核视图，"
                "不是 sorter 原生特征。"
                if not self.english else
                "Thin lines are individual raw spikes; black is their mean and the band shows variation. "
                "Every valid spike is displayed and every PCA point maps back to its sorter spike. "
                "Choose a contact and PC axes; click a point to select a Unit. "
                "Use the lasso to exclude outliers or split a new Unit; edits never overwrite sorter output. "
                "PCA is recomputed from raw snippets for review, not a sorter-native feature. "
                "0 ms is the sorter timestamp, not necessarily the trough."
            )
        )
        waveform_note.setWordWrap(True)
        center_layout.addWidget(waveform_note)
        self.canvas = FigureCanvasQTAgg(
            unit_metrics_figure(self.state, "overview")
        )
        self.canvas.mpl_connect("pick_event", self._cluster_picked)
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
        self.apply_cohort_button = buttons.addButton(
            "应用已复核单神经元到下游分析"
            if not self.english else "Apply reviewed single units to analysis",
            QDialogButtonBox.ActionRole,
        )
        self.apply_cohort_button.clicked.connect(self._apply_curated_cohort)
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
        entries = curated_unit_entries(self.state, self.sorter_key)
        metrics = {
            int(item.get("unit_id", -1)): item for item in self.state.unit_metrics
        }
        for unit_id in sorted(entries):
            record = unit_curation_record(self.state, unit_id, self.sorter_key)
            label = record.get("label")
            status = (
                _LABELS.get(str(label), ("", ""))[1 if self.english else 0]
                if label
                else ("Pending" if self.english else "待复核")
            )
            source_unit = int(entries[unit_id].get("source_unit", unit_id))
            metric = metrics.get(unit_id, metrics.get(source_unit, {}))
            split_marker = " · split" if entries[unit_id].get("kind") == "manual_split" else ""
            self.unit_list.addItem(
                f"Unit {unit_id}{split_marker} · {status} · "
                f"{len(entries[unit_id]['times']):,} spikes"
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
        units = sorted(curated_unit_entries(self.state, self.sorter_key))
        return units[row] if 0 <= row < len(units) else None

    def _unit_changed(self, _row: int) -> None:
        unit_id = self._selected_unit()
        if unit_id is None:
            return
        entry = curated_unit_entries(self.state, self.sorter_key).get(unit_id, {})
        source_unit = int(entry.get("source_unit", unit_id))
        metric = next((row for row in self.state.unit_metrics
                       if int(row.get("unit_id", -1)) in {unit_id, source_unit}), {})
        contact_index = self.contact_combo.findData(metric.get("peak_channel"))
        if contact_index >= 0:
            self.contact_combo.blockSignals(True)
            self.contact_combo.setCurrentIndex(contact_index)
            self.contact_combo.blockSignals(False)
        self._refresh_unit_figure()
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
                if int(item.get("unit_id", -1)) in {unit_id, source_unit}
            ),
            {},
        )
        native_unit = (
            self.state.sorting_provenance.get(self.sorter_key, {})
            .get("source_unit_id_map", {})
            .get(str(source_unit), source_unit)
        )
        self.metric_label.setText(
            (
                f"Spikes after manual edits: {len(entry.get('times', [])):,}\n"
                f"NeuroEPhys AI Unit: {source_unit}\n"
                f"Native sorter cluster: {native_unit}\n"
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
        selected = self.state.metadata.get("curated_unit_selection", {})
        if selected.get("enabled") and selected.get("sorter") == self.sorter_key:
            suffix = (
                f"\nActive analysis cohort: {len(selected.get('unit_ids', []))} reviewed single units"
                if self.english else
                f"\n当前下游分析集：{len(selected.get('unit_ids', []))} 个已复核候选单神经元"
            )
            if selected.get("needs_reapply"):
                suffix += " · Reapply after label change" if self.english else " · 标签已变化，请重新应用"
            self.summary_label.setText(self.summary_label.text() + suffix)

    def _refresh_unit_figure(self) -> None:
        unit_id = self._selected_unit()
        if unit_id is None:
            return
        if self.diagnostic_view.currentData() == "cluster":
            self.canvas.figure = unit_cluster_figure(
                self.state, unit_id,
                contact=self.contact_combo.currentData(),
                pc_x=self.pc_x_combo.currentData() or 1,
                pc_y=self.pc_y_combo.currentData() or 2,
                feature_cache=self._cluster_data_cache,
            )
        else:
            self.canvas.figure = unit_metrics_figure(self.state, f"unit:{unit_id}")
        self.canvas.draw_idle()
        self._install_lasso()

    def _contact_changed(self, _index: int) -> None:
        contact = self.contact_combo.currentData()
        entries = curated_unit_entries(self.state, self.sorter_key)
        source_candidates = {int(row["unit_id"]) for row in self.state.unit_metrics
                             if row.get("peak_channel") == contact}
        candidates = [unit_id for unit_id, entry in entries.items()
                      if int(entry.get("source_unit", unit_id)) in source_candidates]
        selected = self._selected_unit()
        if candidates and selected not in candidates:
            units = sorted(entries)
            self.unit_list.setCurrentRow(units.index(candidates[0]))
        else:
            self._refresh_unit_figure()

    def _cluster_picked(self, event) -> None:
        unit_id = getattr(event.artist, "_neuro_unit_id", None)
        if unit_id is None:
            return
        units = sorted(curated_unit_entries(self.state, self.sorter_key))
        if unit_id in units:
            self.unit_list.setCurrentRow(units.index(unit_id))

    def _install_lasso(self) -> None:
        if self._lasso is not None:
            self._lasso.disconnect_events()
            self._lasso = None
        if self.diagnostic_view.currentData() != "cluster" or len(self.canvas.figure.axes) < 3:
            return
        self._lasso = LassoSelector(
            self.canvas.figure.axes[2], self._lasso_selected,
            button=1, useblit=True,
        )
        self._lasso.set_active(self.lasso_button.isChecked())

    def _toggle_lasso(self, active: bool) -> None:
        if self._lasso is None:
            self._install_lasso()
        if self._lasso is not None:
            self._lasso.set_active(active)

    def _lasso_selected(self, vertices) -> None:
        if len(self.canvas.figure.axes) < 3:
            return
        polygon = MplPath(vertices)
        selected: list[tuple[int, int, int]] = []
        axis = self.canvas.figure.axes[2]
        for artist in axis.collections:
            points = getattr(artist, "_neuro_projection", None)
            if points is None:
                continue
            inside = polygon.contains_points(points)
            candidate = int(getattr(artist, "_neuro_unit_id"))
            source_units = getattr(artist, "_neuro_source_units")
            source_indices = getattr(artist, "_neuro_source_indices")
            selected.extend(
                (candidate, int(source_unit), int(source_index))
                for source_unit, source_index in zip(
                    source_units[inside], source_indices[inside], strict=True
                )
            )
        self._selected_spike_refs = selected
        self.selection_label.setText(
            (f"已选 {len(selected):,} 个 spike" if not self.english
             else f"{len(selected):,} spikes selected")
        )
        if selected:
            chosen = np.asarray([
                point
                for artist in axis.collections
                if getattr(artist, "_neuro_projection", None) is not None
                for point, keep in zip(
                    artist._neuro_projection,
                    polygon.contains_points(artist._neuro_projection), strict=True,
                ) if keep
            ])
            if len(chosen):
                highlight = axis.scatter(
                    chosen[:, 0], chosen[:, 1], s=28, facecolors="none",
                    edgecolors="#ffcc33", linewidths=0.8, zorder=20,
                )
                highlight._neuro_selection_overlay = True
        self.canvas.draw_idle()

    def _clear_spike_selection(self) -> None:
        self._selected_spike_refs = []
        self.selection_label.setText(
            "已选 0 个 spike" if not self.english else "0 spikes selected"
        )
        if len(self.canvas.figure.axes) >= 3:
            axis = self.canvas.figure.axes[2]
            for artist in list(axis.collections):
                if getattr(artist, "_neuro_selection_overlay", False):
                    artist.remove()
        self.canvas.draw_idle()

    def _exclude_selected_spikes(self) -> None:
        if not self._selected_spike_refs:
            return
        by_source: dict[int, list[int]] = {}
        for _candidate, source, source_index in self._selected_spike_refs:
            by_source.setdefault(source, []).append(source_index)
        for source, indices in by_source.items():
            save_spike_selection_edit(
                self.state, source_unit=source, source_indices=indices,
                action="exclude", sorter_key=self.sorter_key,
            )
        self._after_spike_edit()

    def _split_selected_spikes(self) -> None:
        if not self._selected_spike_refs:
            return
        sources = {row[1] for row in self._selected_spike_refs}
        candidates = {row[0] for row in self._selected_spike_refs}
        if len(sources) != 1 or len(candidates) != 1:
            QMessageBox.warning(
                self,
                "Select one cluster" if self.english else "请只选一个 cluster",
                ("A split must contain spikes from one current cluster."
                 if self.english else "拆分时只能套索当前一个 cluster 中的 spike。"),
            )
            return
        candidate = next(iter(candidates))
        source = next(iter(sources))
        save_spike_selection_edit(
            self.state, source_unit=source,
            source_indices=[row[2] for row in self._selected_spike_refs],
            action="split", current_unit=candidate, sorter_key=self.sorter_key,
        )
        self._after_spike_edit()

    def _undo_spike_edit(self) -> None:
        if undo_spike_selection_edit(self.state, self.sorter_key) is not None:
            self._after_spike_edit()

    def _after_spike_edit(self) -> None:
        current = self._selected_unit()
        self._cluster_data_cache.clear()
        self._clear_spike_selection()
        if self.saved_handler:
            self.saved_handler()
        self._load_units()
        units = sorted(curated_unit_entries(self.state, self.sorter_key))
        if current in units:
            self.unit_list.setCurrentRow(units.index(current))

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

    def _apply_curated_cohort(self) -> None:
        available = curated_unit_entries(self.state, self.sorter_key)
        accepted = sum(
            unit_curation_record(self.state, unit_id, self.sorter_key).get("label")
            == "candidate_single_unit"
            for unit_id in available
        )
        if not accepted:
            QMessageBox.warning(
                self,
                "No accepted Units" if self.english else "没有可纳入的 Unit",
                "First review and label at least one candidate single unit."
                if self.english else "请先复核并将至少一个 Unit 标记为候选单神经元。",
            )
            return
        answer = QMessageBox.question(
            self,
            "Apply curated cohort" if self.english else "应用人工筛选集",
            (
                f"Use {accepted} reviewed candidate single units for subsequent "
                "spike-based analysis? MUA, noise, artifacts, uncertain and unreviewed "
                "clusters will be excluded. Original sorter output is preserved. "
                "Existing downstream results become outdated and must be rerun."
                if self.english else
                f"后续基于 spike 的分析仅使用 {accepted} 个已复核候选单神经元？"
                "MUA、噪声、伪迹、待定及未复核候选将排除。原 sorter 结果保留；"
                "已有下游结果标记为待重跑。"
            ),
        )
        if answer != QMessageBox.Yes:
            return
        apply_curated_single_units(self.state)
        if self.saved_handler:
            self.saved_handler()
        self._load_units()
