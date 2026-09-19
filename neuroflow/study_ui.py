"""Desktop workspace for multi-session and multi-animal studies."""

from __future__ import annotations

from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .multi_session import (
    MULTI_SESSION_MODELS,
    STUDY_MANIFEST_NAME,
    StudyState,
    add_project,
    infer_session_identity,
    inspect_sessions,
    load_study,
    run_multi_session_analysis,
    save_study,
    shared_conditions,
    study_figure,
)
from .project import MANIFEST_NAME

MODEL_LABELS_ZH = {
    "Logistic regression": "逻辑回归（线性基线）",
    "Linear SVM": "线性 SVM",
    "RBF SVM": "RBF SVM（非线性）",
    "Linear discriminant analysis": "线性判别分析（LDA）",
    "Random forest": "随机森林",
}


class StudyAnalysisWorker(QThread):
    """Keep grouped validation and permutation tests off the GUI thread."""

    succeeded = Signal(object, object)
    failed = Signal(str)

    def __init__(self, manifest: Path, parameters: dict, parent=None):
        super().__init__(parent)
        self.manifest = manifest
        self.parameters = parameters

    def run(self) -> None:
        try:
            study = load_study(self.manifest)
            result = run_multi_session_analysis(study, **self.parameters)
            self.succeeded.emit(study, result)
        except Exception as exc:  # noqa: BLE001 - delivered to the user in the GUI
            self.failed.emit(str(exc))


class MultiSessionStudyDialog(QDialog):
    def __init__(self, workspace: Path, language: str, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.language = language
        self.study: StudyState | None = None
        self.canvas: FigureCanvasQTAgg | None = None
        self.worker: StudyAnalysisWorker | None = None
        self.setWindowTitle(
            "Multi-session study" if language == "en_US" else "多 Session 研究"
        )
        self.resize(1280, 820)
        self.setMinimumSize(700, 520)
        self._build_ui()
        self._refresh()

    @property
    def english(self) -> bool:
        return self.language == "en_US"

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel(
            "Multi-session / multi-animal analysis"
            if self.english
            else "多 Session／多动物汇总分析"
        )
        title.setStyleSheet("font-size: 22px; font-weight: 750;")
        header.addWidget(title)
        header.addStretch()
        self.new_button = QPushButton("New study" if self.english else "新建研究")
        self.open_button = QPushButton("Open study" if self.english else "打开研究")
        self.save_button = QPushButton("Save" if self.english else "保存")
        header.addWidget(self.new_button)
        header.addWidget(self.open_button)
        header.addWidget(self.save_button)
        layout.addLayout(header)
        description = QLabel(
            (
                "Trials are nested in sessions and animals. Unit numbers are not "
                "treated as the same neuron across sessions unless cell tracking is supplied."
            )
            if self.english
            else (
                "trial 隶属于 session，session 隶属于动物。默认不把不同 session 的同号 Unit "
                "当成同一个神经元；跨 session 验证会整组留出，避免数据泄漏。"
            )
        )
        description.setObjectName("Muted")
        description.setWordWrap(True)
        layout.addWidget(description)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.study_label = QLabel("—")
        self.study_label.setStyleSheet("font-weight: 700;")
        left_layout.addWidget(self.study_label)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "Use" if self.english else "使用",
                "Animal" if self.english else "动物",
                "Session",
                "Project" if self.english else "项目",
                "Status" if self.english else "状态",
                "Conditions" if self.english else "条件",
            ]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.table, 1)
        session_actions = QHBoxLayout()
        self.add_button = QPushButton(
            "Add session projects…" if self.english else "添加 Session 项目…"
        )
        self.remove_button = QPushButton(
            "Remove selected" if self.english else "移除选中"
        )
        session_actions.addWidget(self.add_button)
        session_actions.addWidget(self.remove_button)
        session_actions.addStretch()
        left_layout.addLayout(session_actions)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        controls = QGridLayout()
        controls.addWidget(QLabel("Model" if self.english else "模型"), 0, 0)
        self.model_combo = QComboBox()
        for model in MULTI_SESSION_MODELS:
            self.model_combo.addItem(
                model if self.english else MODEL_LABELS_ZH[model], model
            )
        self.model_combo.setCurrentIndex(self.model_combo.findData("Linear SVM"))
        controls.addWidget(self.model_combo, 0, 1)
        controls.addWidget(QLabel("Hold out" if self.english else "整组留出"), 0, 2)
        self.group_combo = QComboBox()
        self.group_combo.addItem(
            "Auto: animal first" if self.english else "自动：优先动物", "auto"
        )
        self.group_combo.addItem("Animal" if self.english else "动物", "animal")
        self.group_combo.addItem("Session", "session")
        controls.addWidget(self.group_combo, 0, 3)
        controls.addWidget(QLabel("Condition A" if self.english else "条件 A"), 1, 0)
        self.condition_a_combo = QComboBox()
        controls.addWidget(self.condition_a_combo, 1, 1)
        controls.addWidget(QLabel("Condition B" if self.english else "条件 B"), 1, 2)
        self.condition_b_combo = QComboBox()
        controls.addWidget(self.condition_b_combo, 1, 3)
        controls.addWidget(QLabel("Permutations" if self.english else "置换次数"), 2, 0)
        self.permutation_spin = QSpinBox()
        self.permutation_spin.setRange(20, 5000)
        self.permutation_spin.setValue(200)
        controls.addWidget(self.permutation_spin, 2, 1)
        controls.setColumnStretch(1, 2)
        controls.setColumnStretch(3, 2)
        right_layout.addLayout(controls)
        method_note = QLabel(
            (
                "Paper-grade profile runs as one reproducible suite: session QC, paired "
                "condition effects, whole-group decoding, within-session permutations, "
                "time-resolved and cross-temporal decoding, cross-session transfer, "
                "representational stability, and descriptive latent dynamics. LDA is a "
                "classifier; the latent panel uses PCA plus a regularized transition model."
            )
            if self.english
            else (
                "期刊级综合方案会一次运行：Session QC、配对条件效应、整组留出解码、"
                "Session 内标签置换、随时间解码、时间泛化、跨 Session 转移、表征稳定性和"
                "描述性潜在动力学。LDA 是分类器；潜在面板使用 PCA 加正则化状态转移模型。"
            )
        )
        method_note.setObjectName("Muted")
        method_note.setWordWrap(True)
        right_layout.addWidget(method_note)
        self.run_button = QPushButton(
            "Run paper-grade multi-session suite"
            if self.english
            else "运行期刊级多 Session 综合分析"
        )
        self.run_button.setObjectName("Primary")
        self.run_button.setMinimumHeight(42)
        right_layout.addWidget(self.run_button)
        self.summary = QTextBrowser()
        self.summary.setMinimumHeight(145)
        right_layout.addWidget(self.summary)
        self.figure_host = QVBoxLayout()
        self.empty_state = QLabel(
            (
                "1  Add completed session projects\n\n"
                "2  Verify biological animal and session IDs\n\n"
                "3  Choose two shared conditions and hold out whole groups\n\n"
                "4  Run, inspect limits, and export"
            )
            if self.english
            else (
                "1  添加已完成事件分析的 Session 项目\n\n"
                "2  核对真实动物编号与唯一 Session 编号\n\n"
                "3  选择两个共有条件，并整组留出动物或 Session\n\n"
                "4  运行、检查解释边界并导出"
            )
        )
        self.empty_state.setAlignment(Qt.AlignCenter)
        self.empty_state.setWordWrap(True)
        self.empty_state.setObjectName("Muted")
        self.empty_state.setStyleSheet(
            "border: 1px solid #3d3447; border-radius: 10px; padding: 24px;"
        )
        self.figure_host.addWidget(self.empty_state)
        right_layout.addLayout(self.figure_host, 1)
        output_actions = QHBoxLayout()
        self.output_button = QPushButton(
            "Open result folder" if self.english else "打开结果文件夹"
        )
        self.close_button = QPushButton("Close" if self.english else "关闭")
        output_actions.addStretch()
        output_actions.addWidget(self.output_button)
        output_actions.addWidget(self.close_button)
        right_layout.addLayout(output_actions)
        splitter.addWidget(right)
        splitter.setSizes([560, 720])
        self.splitter = splitter
        layout.addWidget(splitter, 1)

        self.new_button.clicked.connect(self._new_study)
        self.open_button.clicked.connect(self._open_study)
        self.save_button.clicked.connect(self._save)
        self.add_button.clicked.connect(self._add_projects)
        self.remove_button.clicked.connect(self._remove_selected)
        self.run_button.clicked.connect(self._run)
        self.output_button.clicked.connect(self._open_output)
        self.close_button.clicked.connect(self.accept)

    def _new_study(self) -> None:
        name, accepted = QInputDialog.getText(
            self,
            "Study name" if self.english else "研究名称",
            "Name" if self.english else "名称",
        )
        if not accepted or not name.strip():
            return
        parent = QFileDialog.getExistingDirectory(
            self,
            "Choose study parent folder" if self.english else "选择研究保存位置",
            str(self.workspace / "Studies"),
        )
        if not parent:
            return
        safe_name = "_".join(name.strip().split())
        root = Path(parent) / safe_name
        if (root / STUDY_MANIFEST_NAME).exists():
            QMessageBox.warning(
                self, self.windowTitle(), "A study already exists there."
            )
            return
        self.study = StudyState(root, name.strip())
        save_study(self.study)
        self._notify_registration()
        self._refresh()

    def _open_study(self) -> None:
        selected = QFileDialog.getOpenFileName(
            self,
            "Open multi-session study" if self.english else "打开多 Session 研究",
            str(self.workspace),
            f"NeuroEphys study ({STUDY_MANIFEST_NAME})",
        )[0]
        if not selected:
            return
        try:
            self.study = load_study(Path(selected))
            self._notify_registration()
            self._refresh()
        except Exception as exc:  # noqa: BLE001 - user-facing manifest validation
            QMessageBox.warning(self, self.windowTitle(), str(exc))

    def _save_table(self) -> None:
        if self.study is None:
            return
        for row, item in enumerate(self.study.sessions):
            widget = self.table.cellWidget(row, 0)
            item.included = bool(widget and widget.isChecked())
            item.animal_id = self.table.item(row, 1).text().strip()
            item.session_id = self.table.item(row, 2).text().strip()
            if not item.animal_id or not item.session_id:
                raise ValueError("Animal and session identifiers cannot be empty")
        if len({item.session_id for item in self.study.sessions}) != len(
            self.study.sessions
        ):
            raise ValueError("Session identifiers must be unique")

    def _save(self) -> None:
        if self.study is None:
            return
        try:
            self._save_table()
            save_study(self.study)
            self._notify_registration()
            self._refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.windowTitle(), str(exc))

    def _add_projects(self) -> None:
        if self.study is None:
            self._new_study()
        if self.study is None:
            return
        selected = QFileDialog.getOpenFileNames(
            self,
            "Add completed session projects"
            if self.english
            else "添加已完成的 Session 项目",
            str(self.workspace),
            f"NeuroEphys project ({MANIFEST_NAME})",
        )[0]
        for path_text in selected:
            path = Path(path_text)
            try:
                animal, session = infer_session_identity(path)
                animal, ok = QInputDialog.getText(
                    self,
                    "Animal identity" if self.english else "动物编号",
                    (
                        "Biological subject ID (not a channel group):"
                        if self.english
                        else "生物学动物编号（不是通道组编号）："
                    ),
                    text=animal,
                )
                if not ok:
                    continue
                session, ok = QInputDialog.getText(
                    self,
                    "Session identity" if self.english else "Session 编号",
                    "Unique session ID:",
                    text=session,
                )
                if not ok:
                    continue
                add_project(self.study, path, animal, session)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(self, self.windowTitle(), f"{path.name}: {exc}")
        save_study(self.study)
        self._notify_registration()
        self._refresh()

    def _remove_selected(self) -> None:
        if self.study is None:
            return
        selected = sorted(
            {index.row() for index in self.table.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in selected:
            self.study.sessions.pop(row)
        save_study(self.study)
        self._notify_registration()
        self._refresh()

    def _notify_registration(self) -> None:
        if self.study is None:
            return
        callback = getattr(self.parent(), "_register_study", None)
        if callable(callback):
            callback(self.study)

    def _refresh(self) -> None:
        ready = self.study is not None
        for widget in (
            self.save_button,
            self.add_button,
            self.remove_button,
            self.run_button,
            self.output_button,
        ):
            widget.setEnabled(ready)
        if not ready:
            self.study_label.setText(
                "Create or open a study to begin."
                if self.english
                else "请先新建或打开研究。"
            )
            self.table.setRowCount(0)
            self.summary.setPlainText("")
            if self.canvas is not None:
                self.figure_host.removeWidget(self.canvas)
                self.canvas.deleteLater()
                self.canvas = None
            self.empty_state.show()
            return
        self.study_label.setText(f"{self.study.name}  ·  {self.study.manifest_path}")
        inventory = inspect_sessions(self.study)
        self.table.setRowCount(len(inventory))
        for row, (item, info) in enumerate(zip(self.study.sessions, inventory)):
            include = QCheckBox()
            include.setChecked(item.included)
            include.setStyleSheet("margin-left: 12px;")
            self.table.setCellWidget(row, 0, include)
            animal = QTableWidgetItem(item.animal_id)
            session = QTableWidgetItem(item.session_id)
            project = QTableWidgetItem(Path(item.project).parent.name)
            project.setToolTip(item.project)
            project.setFlags(project.flags() & ~Qt.ItemIsEditable)
            status = QTableWidgetItem(str(info["status"]))
            if not self.english:
                status_text = str(info["status"])
                status_map = {
                    "ready": "就绪",
                    "excluded": "已排除",
                    "event_analysis_required": "需先完成事件分析",
                }
                status.setText(
                    status_map.get(status_text, status_text.replace("error:", "错误："))
                )
            status.setFlags(status.flags() & ~Qt.ItemIsEditable)
            conditions = QTableWidgetItem(", ".join(info["conditions"]))
            conditions.setFlags(conditions.flags() & ~Qt.ItemIsEditable)
            for column, cell in enumerate(
                (animal, session, project, status, conditions), start=1
            ):
                self.table.setItem(row, column, cell)
        self.table.resizeColumnsToContents()
        conditions = shared_conditions(self.study)
        previous = list(self.study.settings.get("conditions", []))
        for combo in (self.condition_a_combo, self.condition_b_combo):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(conditions)
            combo.blockSignals(False)
        if conditions:
            preferred_a = previous[0] if len(previous) > 0 else conditions[0]
            preferred_b = (
                previous[1]
                if len(previous) > 1
                else (conditions[1] if len(conditions) > 1 else conditions[0])
            )
            self.condition_a_combo.setCurrentText(preferred_a)
            self.condition_b_combo.setCurrentText(preferred_b)
        if self.study.settings.get("model") in MULTI_SESSION_MODELS:
            model_index = self.model_combo.findData(str(self.study.settings["model"]))
            if model_index >= 0:
                self.model_combo.setCurrentIndex(model_index)
        group_by = str(self.study.settings.get("group_by", "auto"))
        group_index = self.group_combo.findData(group_by)
        if group_index >= 0:
            self.group_combo.setCurrentIndex(group_index)
        if self.study.settings.get("permutations"):
            self.permutation_spin.setValue(int(self.study.settings["permutations"]))
        if self.study.results:
            self._show_result()
        else:
            if self.canvas is not None:
                self.figure_host.removeWidget(self.canvas)
                self.canvas.deleteLater()
                self.canvas = None
            self.empty_state.show()
            self.summary.setHtml(
                "<b>Analysis has not run.</b>"
                if self.english
                else "<b>尚未运行跨 Session 分析。</b><br>每个纳入项目须先完成事件对齐分析。"
            )

    def _run(self) -> None:
        if self.study is None:
            return
        try:
            self._save_table()
            conditions = [
                self.condition_a_combo.currentText(),
                self.condition_b_combo.currentText(),
            ]
            if not all(conditions) or conditions[0] == conditions[1]:
                raise ValueError(
                    "Choose two different shared conditions."
                    if self.english
                    else "请选择两个不同、且所有 Session 共有的条件。"
                )
            parameters = {
                "model_name": str(self.model_combo.currentData()),
                "group_by": str(self.group_combo.currentData()),
                "n_splits": 5,
                "n_permutations": self.permutation_spin.value(),
                "selected_conditions": conditions,
            }
            self.study.settings.update(
                {
                    "model": parameters["model_name"],
                    "group_by": parameters["group_by"],
                    "cv_folds": parameters["n_splits"],
                    "permutations": parameters["n_permutations"],
                    "conditions": conditions,
                }
            )
            save_study(self.study)
            self.run_button.setEnabled(False)
            self.close_button.setEnabled(False)
            self.run_button.setText(
                "Running grouped validation…" if self.english else "正在进行整组验证…"
            )
            self.worker = StudyAnalysisWorker(
                self.study.manifest_path, parameters, self
            )
            self.worker.succeeded.connect(self._analysis_succeeded)
            self.worker.failed.connect(self._analysis_failed)
            self.worker.start()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, self.windowTitle(), str(exc))

    def _analysis_succeeded(self, study: StudyState, result: dict) -> None:
        self.study = study
        self.worker = None
        self.run_button.setEnabled(True)
        self.close_button.setEnabled(True)
        self.run_button.setText(
            "Run paper-grade multi-session suite"
            if self.english
            else "运行期刊级多 Session 综合分析"
        )
        callback = getattr(self.parent(), "_register_study_result", None)
        if callable(callback):
            callback(self.study, result)
        self._show_result()

    def _analysis_failed(self, message: str) -> None:
        self.worker = None
        self.run_button.setEnabled(True)
        self.close_button.setEnabled(True)
        self.run_button.setText(
            "Run paper-grade multi-session suite"
            if self.english
            else "运行期刊级多 Session 综合分析"
        )
        QMessageBox.warning(self, self.windowTitle(), message)

    def _show_result(self) -> None:
        if self.study is None or not self.study.results:
            return
        result = self.study.results
        effect = result["hierarchical_condition_effect"]
        warning = effect.get("warning") or ""
        temporal = result.get("time_resolved_decoding", {})
        peak_text = ""
        if temporal.get("balanced_accuracy"):
            scores = list(map(float, temporal["balanced_accuracy"]))
            peak_index = max(range(len(scores)), key=scores.__getitem__)
            peak_time = float(temporal["time_seconds"][peak_index])
            peak_text = f"{scores[peak_index]:.3f} at {peak_time:+.3f} s"
        if self.english:
            summary = (
                f"<h3>{result['model']} · {result['validation']}</h3>"
                f"<p><b>Animals:</b> {result['animal_count']} &nbsp; "
                f"<b>Sessions:</b> {result['session_count']} &nbsp; "
                f"<b>Trials:</b> {result['trial_count']}</p>"
                f"<p><b>Conditions:</b> {' vs '.join(result['classes'])}</p>"
                f"<p><b>Balanced accuracy:</b> {result['balanced_accuracy']:.3f} "
                f"(95% group-bootstrap CI {result['confidence_interval_95'][0]:.3f}–"
                f"{result['confidence_interval_95'][1]:.3f}); "
                f"<b>permutation p:</b> {result['permutation_p']:.4f}</p>"
                f"<p><b>Hierarchy:</b> {effect['method']}</p>"
                f"<p><b>Peak time-resolved decoding:</b> {peak_text}</p>"
                "<p>The result folder contains an English main figure, a controls "
                "supplement, CSV matrices, full JSON, and a plain-language interpretation.</p>"
            )
            limit_label = "Limit"
        else:
            summary = (
                f"<h3>{result['model']} · {result['validation']}</h3>"
                f"<p><b>动物：</b>{result['animal_count']} &nbsp; "
                f"<b>Session：</b>{result['session_count']} &nbsp; "
                f"<b>Trial：</b>{result['trial_count']}</p>"
                f"<p><b>比较条件：</b>{' vs '.join(result['classes'])}</p>"
                f"<p><b>平衡准确率：</b>{result['balanced_accuracy']:.3f} "
                f"（整组 bootstrap 95% 区间 {result['confidence_interval_95'][0]:.3f}–"
                f"{result['confidence_interval_95'][1]:.3f}）；"
                f"<b>置换 p：</b>{result['permutation_p']:.4f}</p>"
                f"<p><b>层级统计：</b>{effect['method']}</p>"
                f"<p><b>随时间解码峰值：</b>{peak_text}</p>"
                "<p>结果文件夹同时保存英文主图、控制/附图、CSV 矩阵、"
                "完整 JSON 和通俗解读。</p>"
            )
            limit_label = "解释边界"
        self.summary.setHtml(
            summary
            + (
                f"<p style='color:#b36b42'><b>{limit_label}:</b> {warning}</p>"
                if warning
                else ""
            )
        )
        if self.canvas is not None:
            self.figure_host.removeWidget(self.canvas)
            self.canvas.deleteLater()
        self.empty_state.hide()
        self.canvas = FigureCanvasQTAgg(study_figure(self.study))
        self.figure_host.addWidget(self.canvas)

    def _open_output(self) -> None:
        if self.study is None:
            return
        output = self.study.root / "results" / "multi_session"
        if not output.exists():
            QMessageBox.information(
                self,
                self.windowTitle(),
                "Run the analysis first." if self.english else "请先运行分析。",
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output)))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not hasattr(self, "splitter"):
            return
        orientation = Qt.Vertical if self.width() < 980 else Qt.Horizontal
        if self.splitter.orientation() != orientation:
            self.splitter.setOrientation(orientation)
            self.splitter.setSizes([1, 1])

    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            event.ignore()
            QMessageBox.information(
                self,
                self.windowTitle(),
                "Wait for grouped validation to finish."
                if self.english
                else "整组验证正在运行，请完成后再关闭。",
            )
            return
        super().closeEvent(event)
