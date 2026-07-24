from __future__ import annotations

import re
import traceback
from datetime import datetime, timezone
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .analysis import (
    compute_unit_metrics,
    event_aligned_analysis,
    export_reproducible_bundle,
    match_ground_truth,
    preprocessing_preview,
    run_raw_qc,
)
from .data_import import (
    DEVICE_READERS,
    SUPPORTED_FORMATS,
    create_simulated_project,
    import_binary_recording,
    import_device_recording,
    import_ibl_alf,
    import_ibl_trials_aggregate,
    import_kilosort_results,
)
from .decoding import MODELS, run_decoding_suite
from .figures import (
    behavior_figure,
    decoding_figure,
    event_analysis_figure,
    preprocessing_figure,
    qc_figure,
    raw_overview_figure,
    sorting_figure,
    statistics_figure,
    unit_metrics_figure,
)
from .ibl import download_bwm_trials_aggregate
from .models import ProjectState, WorkflowStep
from .project import MANIFEST_NAME, load_project, save_project
from .sorting import kilosort_environment, run_sorter, sorter_catalog
from .statistics import run_statistical_suite
from .tutorials import TUTORIALS

STEPS = [
    WorkflowStep("import", "01  数据与项目", "格式、探针、事件和来源"),
    WorkflowStep("qc", "02  原始质控", "噪声、坏通道、饱和与工频"),
    WorkflowStep("preprocess", "03  预处理", "滤波与参考的处理前后预览"),
    WorkflowStep("sorting", "04  Spike sorting", "Kilosort4 与可替换 sorter"),
    WorkflowStep("unit_qc", "05  Unit 质控", "放电率、ISI、波形与 SNR"),
    WorkflowStep("sync", "06  事件同步", "统一时间轴、trial 与条件"),
    WorkflowStep("behavior", "07  行为分析", "条件、反应时与心理测量曲线"),
    WorkflowStep("analysis", "08  神经活动", "Raster、PSTH、热图与群体响应"),
    WorkflowStep("statistics", "09  统计检验", "效应量、置信区间、置换与 FDR"),
    WorkflowStep("decoding", "10  机器学习", "解码、交叉验证、置换与 PCA"),
    WorkflowStep("export", "11  论文与复现", "图、表、Methods、环境与项目"),
]


STEP_TUTORIAL = {
    "import": "start",
    "qc": "qc",
    "preprocess": "preprocess",
    "sorting": "sorting",
    "unit_qc": "sorting",
    "sync": "events",
    "behavior": "events",
    "analysis": "events",
    "statistics": "statistics",
    "decoding": "decoding",
    "export": "figures",
}


APP_STYLE = """
QMainWindow, QWidget {
    background: #f4f6f5;
    color: #17221f;
    font-family: "Microsoft YaHei", "Segoe UI";
    font-size: 13px;
}
#Header, #HomeHeader { background: #ffffff; border-bottom: 1px solid #dce3e0; }
#Brand { font-size: 21px; font-weight: 700; color: #17221f; }
#Hero { font-size: 31px; font-weight: 750; color: #14211d; }
#Sidebar, #Assistant { background: #ffffff; }
#Sidebar { border-right: 1px solid #dce3e0; }
#Assistant { border-left: 1px solid #dce3e0; }
QPushButton {
    min-height: 35px;
    border: 1px solid #cbd6d1;
    background: #ffffff;
    padding: 0 12px;
    border-radius: 5px;
}
QPushButton:hover { border-color: #1f7a63; background: #eff6f3; }
QPushButton:checked, QPushButton#Primary {
    color: #ffffff; background: #1f7a63; border-color: #1f7a63; font-weight: 600;
}
QPushButton#StepButton {
    text-align: left; min-height: 50px; border: none; border-left: 3px solid transparent;
    border-radius: 0; padding-left: 14px;
}
QPushButton#StepButton:checked {
    color: #17221f; background: #e7f0ec; border-left: 3px solid #1f7a63; font-weight: 650;
}
QPushButton#StepButton[status="completed"] { color: #1f7a63; }
QPushButton#StepButton[status="failed"] { color: #b34f36; }
QFrame#Card, QFrame#Metric {
    background: #ffffff; border: 1px solid #dce3e0; border-radius: 6px;
}
QLabel#MetricValue { font-size: 20px; font-weight: 700; }
QLabel#Muted, QLabel#MetricLabel { color: #69756f; }
QLineEdit, QPlainTextEdit, QTextBrowser, QTableWidget, QComboBox, QSpinBox, QDoubleSpinBox, QListWidget {
    background: #ffffff; border: 1px solid #d5ded9; border-radius: 4px; min-height: 30px;
}
QHeaderView::section {
    background: #edf1ef; border: none; border-bottom: 1px solid #d2dcd7; padding: 6px; font-weight: 600;
}
QProgressBar {
    border: 1px solid #cfd8d4; border-radius: 4px; background: #ffffff;
    text-align: center; min-height: 18px;
}
QProgressBar::chunk { background: #1f7a63; border-radius: 3px; }
"""


class ImportDialog(QDialog):
    def __init__(self, workspace: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.workspace = workspace
        self.state: ProjectState | None = None
        self.setWindowTitle("导入或生成电生理数据")
        self.resize(670, 570)
        layout = QVBoxLayout(self)
        title = QLabel("建立 NeuroFlow 项目")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)
        subtitle = QLabel("原始文件保持只读；项目只保存参数、中间结果与来源索引。")
        subtitle.setObjectName("Muted")
        layout.addWidget(subtitle)

        source_form = QFormLayout()
        self.source_combo = QComboBox()
        for item in SUPPORTED_FORMATS:
            self.source_combo.addItem(item.name, item.key)
        source_form.addRow("数据来源", self.source_combo)
        self.project_name = QLineEdit("NeuroFlow project")
        source_form.addRow("项目名称", self.project_name)
        layout.addLayout(source_form)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._simulation_page())
        self.pages.addWidget(self._binary_page())
        self.pages.addWidget(self._device_page())
        self.pages.addWidget(self._alf_page())
        self.pages.addWidget(self._kilosort_page())
        layout.addWidget(self.pages, 1)
        self.source_combo.currentIndexChanged.connect(self.pages.setCurrentIndex)

        note = QLabel(
            "完整全流程演示请选择“模拟多通道记录”：它会生成真实二进制电压，"
            "随后由 Kilosort4 实际 sorting。IBL ALF 与 Kilosort 结果从 sorting 后阶段接入。"
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("创建并打开")
        buttons.accepted.connect(self._create)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _simulation_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.electrode_combo = QComboBox()
        self.electrode_combo.addItems(
            ["Neuropixels-like", "Tetrode array (4 x 4)", "Linear silicon probe"]
        )
        self.sim_duration = QDoubleSpinBox()
        self.sim_duration.setRange(6, 300)
        self.sim_duration.setValue(30)
        self.sim_duration.setSuffix(" s")
        self.sim_rate = QSpinBox()
        self.sim_rate.setRange(10_000, 40_000)
        self.sim_rate.setValue(30_000)
        self.sim_rate.setSuffix(" Hz")
        self.sim_channels = QSpinBox()
        self.sim_channels.setRange(4, 128)
        self.sim_channels.setValue(32)
        form.addRow("电极结构", self.electrode_combo)
        form.addRow("模拟时长", self.sim_duration)
        form.addRow("采样率", self.sim_rate)
        form.addRow("通道数", self.sim_channels)
        explanation = QLabel(
            "生成包含事件锁定神经元、宽带噪声、50 Hz 共同噪声、坏通道和瞬时伪迹的 "
            "int16 原始记录，并保存 ground truth 用于定量验证 sorting。"
        )
        explanation.setWordWrap(True)
        form.addRow(explanation)
        return page

    def _path_row(self, directory: bool = False) -> tuple[QWidget, QLineEdit]:
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        line = QLineEdit()
        button = QPushButton("浏览…")
        if directory:
            button.clicked.connect(
                lambda: line.setText(QFileDialog.getExistingDirectory(self, "选择文件夹"))
            )
        else:
            button.clicked.connect(
                lambda: line.setText(QFileDialog.getOpenFileName(self, "选择文件")[0])
            )
        row.addWidget(line, 1)
        row.addWidget(button)
        return holder, line

    def _binary_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        holder, self.binary_path = self._path_row()
        event_holder, self.events_path = self._path_row()
        self.binary_rate = QSpinBox()
        self.binary_rate.setRange(1000, 100_000)
        self.binary_rate.setValue(30_000)
        self.binary_channels = QSpinBox()
        self.binary_channels.setRange(1, 2048)
        self.binary_channels.setValue(32)
        self.binary_dtype = QComboBox()
        self.binary_dtype.addItems(["int16", "int32", "float32"])
        self.binary_scale = QDoubleSpinBox()
        self.binary_scale.setRange(0.000001, 1000)
        self.binary_scale.setDecimals(6)
        self.binary_scale.setValue(0.195)
        self.copy_source = QCheckBox("复制原始文件到项目（默认只建立只读索引）")
        form.addRow("原始二进制", holder)
        form.addRow("事件 CSV（可选）", event_holder)
        form.addRow("采样率", self.binary_rate)
        form.addRow("通道数", self.binary_channels)
        form.addRow("数据类型", self.binary_dtype)
        form.addRow("μV / bit", self.binary_scale)
        form.addRow(self.copy_source)
        return page

    def _alf_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        self.alf_path = QLineEdit()
        folder_button = QPushButton("ALF 文件夹…")
        file_button = QPushButton("Aggregate .pqt…")
        folder_button.clicked.connect(
            lambda: self.alf_path.setText(
                QFileDialog.getExistingDirectory(self, "选择 IBL ALF 文件夹")
            )
        )
        file_button.clicked.connect(
            lambda: self.alf_path.setText(
                QFileDialog.getOpenFileName(
                    self,
                    "选择 IBL trials aggregate",
                    filter="Parquet (*.pqt *.parquet)",
                )[0]
            )
        )
        row.addWidget(self.alf_path, 1)
        row.addWidget(folder_button)
        row.addWidget(file_button)
        download_button = QPushButton("下载官方示例")
        download_button.clicked.connect(self._download_ibl_aggregate)
        self.ibl_eid = QLineEdit()
        self.ibl_eid.setPlaceholderText("留空时自动选择一个 BWM session")
        form.addRow("IBL 数据", holder)
        form.addRow("Session eID（aggregate 可选）", self.ibl_eid)
        form.addRow(download_button)
        text = QLabel(
            "读取 trials.table.pqt 或 trials.*.npy，以及 probe 下的 spikes.times、"
            "spikes.clusters。导入后可直接运行 Unit 质控、行为图、PSTH、统计和解码。"
        )
        text.setWordWrap(True)
        form.addRow(text)
        return page

    def _download_ibl_aggregate(self) -> None:
        try:
            path = download_bwm_trials_aggregate(
                self.workspace / "ibl_cache",
                progress=lambda text: self.project_name.setText("正在下载 IBL 数据…"),
            )
            self.alf_path.setText(str(path))
            self.project_name.setText("IBL Brain-Wide Map behavior")
            QMessageBox.information(
                self,
                "IBL 数据已就绪",
                f"已缓存官方 BWM trials aggregate：\n{path}",
            )
        except Exception as exc:  # noqa: BLE001 - network errors are user-facing
            QMessageBox.warning(self, "IBL 下载失败", str(exc))

    def _device_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.device_combo = QComboBox()
        self.device_combo.addItems(DEVICE_READERS)
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        self.device_path = QLineEdit()
        file_button = QPushButton("文件…")
        folder_button = QPushButton("文件夹…")
        file_button.clicked.connect(
            lambda: self.device_path.setText(
                QFileDialog.getOpenFileName(self, "选择记录文件")[0]
            )
        )
        folder_button.clicked.connect(
            lambda: self.device_path.setText(
                QFileDialog.getExistingDirectory(self, "选择记录文件夹")
            )
        )
        row.addWidget(self.device_path, 1)
        row.addWidget(file_button)
        row.addWidget(folder_button)
        self.stream_id = QLineEdit()
        self.stream_id.setPlaceholderText("多流记录时填写，例如 imec0.ap")
        form.addRow("记录系统", self.device_combo)
        form.addRow("文件或文件夹", holder)
        form.addRow("Stream ID（可选）", self.stream_id)
        text = QLabel(
            "NeuroFlow 使用 SpikeInterface 的官方 extractor 读取源格式，并在项目缓存中"
            "生成统一的 int16 交错二进制；源文件不会被修改。"
        )
        text.setWordWrap(True)
        form.addRow(text)
        return page

    def _kilosort_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        holder, self.ks_path = self._path_row(directory=True)
        self.ks_rate = QSpinBox()
        self.ks_rate.setRange(1000, 100_000)
        self.ks_rate.setValue(30_000)
        form.addRow("Kilosort/Phy 文件夹", holder)
        form.addRow("原记录采样率", self.ks_rate)
        text = QLabel("要求至少包含 spike_times.npy 和 spike_clusters.npy 或 spike_templates.npy。")
        text.setWordWrap(True)
        form.addRow(text)
        return page

    def _project_root(self) -> Path:
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", self.project_name.text()).strip("_")
        slug = slug or "project"
        stamp = datetime.now(timezone.utc).astimezone()
        return self.workspace / "projects" / f"{slug}_{stamp:%Y%m%d_%H%M%S}"

    def _create(self) -> None:
        try:
            key = self.source_combo.currentData()
            root = self._project_root()
            if key == "simulated":
                self.state = create_simulated_project(
                    root,
                    electrode_type=self.electrode_combo.currentText(),
                    duration_seconds=self.sim_duration.value(),
                    sampling_rate=float(self.sim_rate.value()),
                    channel_count=self.sim_channels.value(),
                )
            elif key == "binary":
                source = Path(self.binary_path.text())
                if not source.is_file():
                    raise ValueError("请选择有效的原始二进制文件")
                events = Path(self.events_path.text()) if self.events_path.text() else None
                self.state = import_binary_recording(
                    root,
                    source,
                    sampling_rate=float(self.binary_rate.value()),
                    channel_count=self.binary_channels.value(),
                    dtype=self.binary_dtype.currentText(),
                    scale_uv_per_bit=self.binary_scale.value(),
                    events_path=events,
                    copy_source=self.copy_source.isChecked(),
                )
            elif key == "device":
                source = Path(self.device_path.text())
                if not source.exists():
                    raise ValueError("请选择有效的记录文件或文件夹")
                self.state = import_device_recording(
                    root,
                    source,
                    self.device_combo.currentText(),
                    self.stream_id.text().strip() or None,
                )
            elif key == "ibl_alf":
                source = Path(self.alf_path.text())
                if source.is_dir():
                    self.state = import_ibl_alf(root, source)
                elif source.is_file() and source.suffix.lower() in {".pqt", ".parquet"}:
                    self.state = import_ibl_trials_aggregate(
                        root, source, self.ibl_eid.text().strip() or None
                    )
                else:
                    raise ValueError("请选择 IBL ALF 文件夹或 aggregate trials.pqt")
            else:
                source = Path(self.ks_path.text())
                if not source.is_dir():
                    raise ValueError("请选择有效的 Kilosort/Phy 文件夹")
                self.state = import_kilosort_results(
                    root, source, float(self.ks_rate.value())
                )
            self.state.name = self.project_name.text().strip() or self.state.name
            save_project(self.state)
            self.accept()
        except Exception as exc:  # noqa: BLE001 - UI boundary reports adapter errors
            QMessageBox.warning(self, "无法创建项目", str(exc))


class TutorialDialog(QDialog):
    def __init__(self, initial_key: str = "start", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("NeuroFlow 教程中心")
        self.resize(940, 650)
        layout = QHBoxLayout(self)
        self.list = QListWidget()
        self.list.setFixedWidth(250)
        self.browser = QTextBrowser()
        layout.addWidget(self.list)
        layout.addWidget(self.browser, 1)
        for chapter in TUTORIALS:
            self.list.addItem(chapter["title"])
        self.list.currentRowChanged.connect(self._show)
        index = next(
            (index for index, item in enumerate(TUTORIALS) if item["key"] == initial_key),
            0,
        )
        self.list.setCurrentRow(index)

    def _show(self, index: int) -> None:
        if index < 0:
            return
        item = TUTORIALS[index]
        self.browser.setHtml(
            f"<h1>{item['title']}</h1>"
            f"<h3>为什么做</h3><p>{item['why']}</p>"
            f"<h3>输入</h3><p>{item['input']}</p>"
            f"<h3>输出</h3><p>{item['output']}</p>"
            f"<h3>必须检查</h3><p>{item['checks']}</p>"
            f"<h3>方法来源</h3><p>{item['reference']}</p>"
            "<p><b>原则：</b>教程解释的是决策依据，最终参数仍由用户确认并记录。</p>"
        )


class PipelineWorker(QThread):
    step_done = Signal(str, object)
    progress = Signal(str)
    failed = Signal(str, str)
    succeeded = Signal()

    def __init__(
        self,
        state: ProjectState,
        keys: list[str],
        sorter_name: str,
        model_name: str,
    ):
        super().__init__()
        self.state = state
        self.keys = keys
        self.sorter_name = sorter_name
        self.model_name = model_name

    def _emit(self, key: str, value: object, message: str) -> None:
        self.progress.emit(message)
        self.step_done.emit(key, value)

    def _skip(self, key: str, reason: str) -> None:
        self._emit(key, {"skipped": True, "reason": reason}, f"{key} 已跳过：{reason}")

    def run(self) -> None:
        key = self.keys[0] if self.keys else "import"
        try:
            for key in self.keys:
                if key == "import":
                    self._emit(key, self.state, "项目来源、格式与事件清单已确认")
                elif key == "qc":
                    if self.state.ready:
                        self._emit(key, run_raw_qc(self.state), "原始质控完成")
                    else:
                        self._skip(key, "当前项目只有处理后数据，没有原始电压")
                elif key == "preprocess":
                    if self.state.ready:
                        self._emit(key, preprocessing_preview(self.state), "预处理预览完成")
                    else:
                        self._skip(key, "当前项目没有原始电压")
                elif key == "sorting":
                    if self.state.ready:
                        value = run_sorter(
                            self.state,
                            self.sorter_name,
                            self.state.root / "results" / self.sorter_name,
                            self.progress.emit,
                        )
                        self._emit(key, value, f"{self.sorter_name} sorting 完成")
                    elif self.state.sorted_spikes:
                        self._skip(key, "已导入外部 sorting 结果")
                    else:
                        raise RuntimeError("没有可用于 sorting 的原始记录")
                elif key == "unit_qc":
                    self._emit(key, compute_unit_metrics(self.state), "Unit 质控完成")
                elif key == "sync":
                    if not self.state.events:
                        raise RuntimeError("事件相关分析需要事件时间；请导入 events.csv 或 ALF trials")
                    self.state.log(f"事件时间轴确认：{len(self.state.events)} trials")
                    self._emit(key, self.state.events, "事件时间轴与条件已确认")
                elif key == "behavior":
                    self._emit(key, self.state.trials or self.state.events, "行为摘要已生成")
                elif key == "analysis":
                    self._emit(key, event_aligned_analysis(self.state), "Raster、PSTH 与热图已生成")
                elif key == "statistics":
                    self._emit(key, run_statistical_suite(self.state), "统计套件完成")
                elif key == "decoding":
                    self._emit(
                        key,
                        run_decoding_suite(self.state, self.model_name),
                        f"{self.model_name} 解码完成",
                    )
                elif key == "export":
                    output = export_reproducible_bundle(
                        self.state, self.state.root / "exports"
                    )
                    save_project(self.state)
                    self._emit(key, output, "可复现分析包与项目已保存")
            self.succeeded.emit()
        except Exception as exc:  # noqa: BLE001 - worker forwards full tool failure
            self.failed.emit(key, f"{exc}\n\n{traceback.format_exc()}")


class MetricBox(QFrame):
    def __init__(self, label: str, value: str):
        super().__init__()
        self.setObjectName("Metric")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 9, 13, 9)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")
        label_widget = QLabel(label)
        label_widget.setObjectName("MetricLabel")
        layout.addWidget(self.value_label)
        layout.addWidget(label_widget)


class NeuroFlowWindow(QMainWindow):
    def __init__(self, workspace: Path):
        super().__init__()
        self.workspace = workspace
        self.state: ProjectState | None = None
        self.preview: dict | None = None
        self.matches: list[dict] = []
        self.worker: PipelineWorker | None = None
        self.current_step = "import"
        self.step_buttons: dict[str, QPushButton] = {}
        self.setWindowTitle("NeuroFlow - 在体电生理全流程工作台")
        self.resize(1500, 920)
        self.setMinimumSize(1180, 720)
        self.pages = QStackedWidget()
        self.home_page = self._home_page()
        self.workspace_page = self._workspace_page()
        self.pages.addWidget(self.home_page)
        self.pages.addWidget(self.workspace_page)
        self.setCentralWidget(self.pages)
        self.setStyleSheet(APP_STYLE)

    def _home_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        header = QWidget()
        header.setObjectName("HomeHeader")
        header.setFixedHeight(68)
        row = QHBoxLayout(header)
        row.setContentsMargins(24, 10, 24, 10)
        brand = QLabel("NeuroFlow")
        brand.setObjectName("Brand")
        row.addWidget(brand)
        row.addStretch()
        tutorial = QPushButton("教程中心")
        tutorial.clicked.connect(lambda: TutorialDialog(parent=self).exec())
        row.addWidget(tutorial)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(70, 45, 70, 50)
        layout.setSpacing(18)
        hero = QLabel("从自己的原始数据开始，\n逐步走到可复现的论文图。")
        hero.setObjectName("Hero")
        layout.addWidget(hero)
        sub = QLabel(
            "本地优先 · 模块可替换 · 每一步可解释 · Kilosort4 真实运行 · AI 非必需"
        )
        sub.setObjectName("Muted")
        sub.setStyleSheet("font-size: 15px;")
        layout.addWidget(sub)

        actions = QHBoxLayout()
        import_button = QPushButton("导入我的数据")
        import_button.setObjectName("Primary")
        import_button.clicked.connect(self._show_import)
        sample_button = QPushButton("打开完整模拟 Demo")
        sample_button.clicked.connect(self._open_sample)
        project_button = QPushButton("恢复 NeuroFlow 项目")
        project_button.clicked.connect(self._open_project)
        actions.addWidget(import_button)
        actions.addWidget(sample_button)
        actions.addWidget(project_button)
        actions.addStretch()
        layout.addLayout(actions)

        capability = QFrame()
        capability.setObjectName("Card")
        cap_layout = QVBoxLayout(capability)
        cap_title = QLabel("当前可验证的数据入口")
        cap_title.setStyleSheet("font-size: 17px; font-weight: 700;")
        cap_layout.addWidget(cap_title)
        table = QTableWidget(len(SUPPORTED_FORMATS), 4)
        table.setHorizontalHeaderLabels(["来源", "可读内容", "原始电压", "可从 sorting 后接入"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        for row_index, item in enumerate(SUPPORTED_FORMATS):
            values = [
                item.name,
                item.description,
                "是" if item.raw_signal else "否",
                "是" if item.sorting_result else "否",
            ]
            for column, value in enumerate(values):
                table.setItem(row_index, column, QTableWidgetItem(value))
        table.horizontalHeader().setStretchLastSection(True)
        table.setFixedHeight(180)
        cap_layout.addWidget(table)
        layout.addWidget(capability)

        flow = QFrame()
        flow.setObjectName("Card")
        flow_layout = QVBoxLayout(flow)
        flow_title = QLabel("完整纵向链路")
        flow_title.setStyleSheet("font-size: 17px; font-weight: 700;")
        flow_layout.addWidget(flow_title)
        flow_text = QLabel(
            "数据与项目  →  原始质控  →  预处理  →  Spike sorting  →  Unit 质控  →  "
            "事件同步  →  行为分析  →  Raster/PSTH  →  统计检验  →  神经解码  →  论文与复现"
        )
        flow_text.setWordWrap(True)
        flow_text.setStyleSheet("font-size: 15px; color: #1f7a63;")
        flow_layout.addWidget(flow_text)
        layout.addWidget(flow)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        return page

    def _workspace_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._header())
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addWidget(self._sidebar())
        content.addWidget(self._main_area(), 1)
        content.addWidget(self._assistant())
        body = QWidget()
        body.setLayout(content)
        root.addWidget(body, 1)
        return page

    def _header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(72)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 9, 18, 9)
        home = QPushButton("首页")
        home.clicked.connect(lambda: self.pages.setCurrentWidget(self.home_page))
        layout.addWidget(home)
        title_box = QVBoxLayout()
        brand = QLabel("NeuroFlow")
        brand.setObjectName("Brand")
        self.project_label = QLabel("尚未打开项目")
        self.project_label.setObjectName("Muted")
        title_box.addWidget(brand)
        title_box.addWidget(self.project_label)
        layout.addLayout(title_box)
        layout.addStretch()
        save = QPushButton("保存项目")
        save.clicked.connect(self._save)
        tutorial = QPushButton("教程")
        tutorial.clicked.connect(self._open_context_tutorial)
        self.run_button = QPushButton("运行完整流程")
        self.run_button.setObjectName("Primary")
        self.run_button.clicked.connect(self._run_full_pipeline)
        layout.addWidget(save)
        layout.addWidget(tutorial)
        layout.addWidget(self.run_button)
        return header

    def _sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(245)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 10, 0, 10)
        label = QLabel("  分析流程")
        label.setObjectName("Muted")
        layout.addWidget(label)
        step_holder = QWidget()
        step_layout = QVBoxLayout(step_holder)
        step_layout.setContentsMargins(0, 0, 0, 0)
        step_layout.setSpacing(0)
        step_scroll = QScrollArea()
        step_scroll.setWidgetResizable(True)
        step_scroll.setFrameShape(QFrame.NoFrame)
        step_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for step in STEPS:
            button = QPushButton(f"{step.title}\n    {step.subtitle}")
            button.setObjectName("StepButton")
            button.setCheckable(True)
            button.setProperty("status", "pending")
            button.clicked.connect(lambda checked=False, key=step.key: self._select_step(key))
            group.addButton(button)
            step_layout.addWidget(button)
            self.step_buttons[step.key] = button
        step_layout.addStretch()
        step_scroll.setWidget(step_holder)
        layout.addWidget(step_scroll, 1)
        self.environment_label = QLabel()
        self.environment_label.setWordWrap(True)
        self.environment_label.setContentsMargins(14, 8, 14, 8)
        self.environment_label.setObjectName("Muted")
        layout.addWidget(self.environment_label)
        self._refresh_environment()
        return sidebar

    def _main_area(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(17, 14, 17, 12)
        layout.setSpacing(10)
        title_row = QHBoxLayout()
        title_box = QVBoxLayout()
        self.page_title = QLabel("数据与项目")
        self.page_title.setStyleSheet("font-size: 21px; font-weight: 700;")
        self.page_subtitle = QLabel("先从首页导入数据")
        self.page_subtitle.setObjectName("Muted")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_subtitle)
        title_row.addLayout(title_box)
        title_row.addStretch()
        self.option_combo = QComboBox()
        self.option_combo.setMinimumWidth(190)
        self.option_combo.currentIndexChanged.connect(self._refresh_figure)
        title_row.addWidget(self.option_combo)
        self.run_step_button = QPushButton("运行此节点")
        self.run_step_button.clicked.connect(self._run_current_step)
        title_row.addWidget(self.run_step_button)
        layout.addLayout(title_row)

        metrics = QHBoxLayout()
        self.metric_source = MetricBox("数据源", "—")
        self.metric_channels = MetricBox("通道", "—")
        self.metric_duration = MetricBox("时长", "—")
        self.metric_units = MetricBox("Unit", "—")
        for metric in (
            self.metric_source,
            self.metric_channels,
            self.metric_duration,
            self.metric_units,
        ):
            metrics.addWidget(metric)
        layout.addLayout(metrics)
        placeholder = ProjectState(root=self.workspace)
        self.canvas = FigureCanvasQTAgg(raw_overview_figure_empty(placeholder))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, 1)
        self.detail_table = QTableWidget()
        self.detail_table.setVisible(False)
        self.detail_table.setMaximumHeight(190)
        layout.addWidget(self.detail_table)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(STEPS))
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("请从首页打开或创建项目")
        self.status_label.setObjectName("Muted")
        layout.addWidget(self.status_label)
        return widget

    def _assistant(self) -> QWidget:
        assistant = QWidget()
        assistant.setObjectName("Assistant")
        assistant.setFixedWidth(310)
        layout = QVBoxLayout(assistant)
        layout.setContentsMargins(16, 15, 16, 13)
        title = QLabel("引导与证据")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)
        mode = QLabel("离线规则与教程 · 不依赖大模型")
        mode.setObjectName("Muted")
        layout.addWidget(mode)
        self.help_title = QLabel("先选择数据来源")
        self.help_title.setStyleSheet("font-weight: 700; color: #1f7a63;")
        layout.addWidget(self.help_title)
        self.help_text = QLabel("NeuroFlow 不会替你隐藏数据结构和关键参数。")
        self.help_text.setWordWrap(True)
        self.help_text.setAlignment(Qt.AlignTop)
        layout.addWidget(self.help_text)
        open_tutorial = QPushButton("打开本章完整教程")
        open_tutorial.clicked.connect(self._open_context_tutorial)
        layout.addWidget(open_tutorial)
        warning = QLabel("当前检查")
        warning.setStyleSheet("font-weight: 700;")
        layout.addWidget(warning)
        self.warning_text = QLabel("尚未打开项目。")
        self.warning_text.setWordWrap(True)
        self.warning_text.setObjectName("Muted")
        layout.addWidget(self.warning_text)
        log_title = QLabel("运行与审计记录")
        log_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(log_title)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(300)
        layout.addWidget(self.log_view, 1)
        return assistant

    def _show_import(self) -> None:
        dialog = ImportDialog(self.workspace, self)
        if dialog.exec() == QDialog.Accepted and dialog.state:
            self._load_state(dialog.state)

    def _open_sample(self) -> None:
        dialog = ImportDialog(self.workspace, self)
        dialog.project_name.setText("NeuroFlow full pipeline demo")
        if dialog.exec() == QDialog.Accepted and dialog.state:
            self._load_state(dialog.state)

    def _open_project(self) -> None:
        path = QFileDialog.getOpenFileName(
            self, "选择 NeuroFlow 项目", str(self.workspace), f"NeuroFlow ({MANIFEST_NAME})"
        )[0]
        if not path:
            return
        try:
            self._load_state(load_project(Path(path)))
        except Exception as exc:  # noqa: BLE001 - project parse errors are user-facing
            QMessageBox.warning(self, "无法打开项目", str(exc))

    def _load_state(self, state: ProjectState) -> None:
        self.state = state
        self.preview = None
        self.matches = []
        self.project_label.setText(f"{state.name}  ·  {state.root}")
        self.metric_source.value_label.setText(state.source_type.upper())
        self.metric_channels.value_label.setText(str(state.channel_count or "—"))
        self.metric_duration.value_label.setText(f"{state.duration_seconds:.1f}s")
        self.metric_units.value_label.setText(str(len(state.sorted_spikes) or "—"))
        for key, status in state.workflow_status.items():
            if key in self.step_buttons:
                self._set_step_status(key, status)
        if state.sorted_spikes:
            self._set_step_status("sorting", "completed")
        self.pages.setCurrentWidget(self.workspace_page)
        self._select_step("import")
        self.status_label.setText("项目已打开；可逐节点运行，也可执行完整流程")
        self._refresh_warnings()

    def _save(self) -> None:
        if self.state:
            path = save_project(self.state)
            self.status_label.setText(f"项目已保存：{path.name}")

    def _refresh_environment(self) -> None:
        env = kilosort_environment()
        sorters = sorter_catalog()
        installed = [item["name"] for item in sorters if item["installed"]]
        gpu = env["device_name"] if env["cuda_available"] else "未检测到 CUDA GPU"
        self.environment_label.setText(
            f"计算环境\n{gpu}\n可运行 sorter：{', '.join(installed) or '无'}"
        )

    def _select_step(self, key: str) -> None:
        self.current_step = key
        step = next(item for item in STEPS if item.key == key)
        self.step_buttons[key].setChecked(True)
        self.page_title.setText(step.title)
        self.page_subtitle.setText(step.subtitle)
        tutorial_key = STEP_TUTORIAL[key]
        chapter = next(item for item in TUTORIALS if item["key"] == tutorial_key)
        self.help_title.setText(chapter["title"])
        self.help_text.setText(chapter["why"] + "\n\n检查：" + chapter["checks"])
        self.option_combo.blockSignals(True)
        self.option_combo.clear()
        if key == "sorting":
            for item in sorter_catalog():
                suffix = "可运行" if item["installed"] else "未安装"
                self.option_combo.addItem(f"{item['name']} · {suffix}", item["key"])
        elif key == "decoding":
            for model in MODELS:
                self.option_combo.addItem(model, model)
        elif key in {"analysis", "statistics"} and self.state:
            for unit_id in sorted(self.state.sorted_spikes):
                self.option_combo.addItem(f"Unit {unit_id}", unit_id)
        self.option_combo.setVisible(self.option_combo.count() > 0)
        self.option_combo.blockSignals(False)
        self._refresh_figure()
        self._refresh_table()
        self._refresh_warnings()

    def _replace_figure(self, figure) -> None:
        parent_layout = self.canvas.parentWidget().layout()
        index = parent_layout.indexOf(self.canvas)
        parent_layout.removeWidget(self.canvas)
        self.canvas.setParent(None)
        self.canvas.deleteLater()
        self.canvas = FigureCanvasQTAgg(figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        parent_layout.insertWidget(index, self.canvas, 1)
        self.canvas.draw_idle()

    def _refresh_figure(self) -> None:
        if not self.state:
            return
        key = self.current_step
        if key == "qc" and self.state.qc:
            figure = qc_figure(self.state)
        elif key == "preprocess" and self.preview:
            figure = preprocessing_figure(self.preview)
        elif key == "sorting" and self.matches:
            figure = sorting_figure(self.matches, self.state)
        elif key == "unit_qc" and self.state.unit_metrics:
            figure = unit_metrics_figure(self.state)
        elif key == "behavior":
            figure = behavior_figure(self.state)
        elif key == "analysis" and self.state.analysis:
            figure = event_analysis_figure(self.state, self.option_combo.currentData())
        elif key == "statistics" and self.state.statistics:
            figure = statistics_figure(self.state)
        elif key == "decoding" and self.state.decoding:
            figure = decoding_figure(self.state)
        else:
            figure = raw_overview_figure(self.state)
        self._replace_figure(figure)

    def _refresh_table(self) -> None:
        if not self.state:
            return
        rows: list[dict] = []
        if self.current_step == "unit_qc":
            rows = self.state.unit_metrics
        elif self.current_step == "statistics":
            rows = self.state.statistics.get("rows", [])
        self.detail_table.setVisible(bool(rows))
        if not rows:
            return
        columns = list(rows[0])
        self.detail_table.setRowCount(len(rows))
        self.detail_table.setColumnCount(len(columns))
        self.detail_table.setHorizontalHeaderLabels(columns)
        for row_index, row in enumerate(rows):
            for column, key in enumerate(columns):
                value = row[key]
                if isinstance(value, float):
                    text = f"{value:.4g}"
                else:
                    text = str(value)
                self.detail_table.setItem(row_index, column, QTableWidgetItem(text))
        self.detail_table.resizeColumnsToContents()

    def _refresh_warnings(self) -> None:
        if not self.state:
            return
        messages = [
            f"来源：{self.state.source_type}",
            f"原始电压：{'可用' if self.state.ready else '不可用'}",
            f"事件：{len(self.state.events)}",
        ]
        if self.state.qc:
            messages.append(f"坏通道：{self.state.qc.get('bad_channels', []) or '未检出'}")
            messages.append(f"50 Hz 比值：{self.state.qc.get('line_noise_ratio', 0):.2f}")
        if self.state.sorted_spikes:
            messages.append(f"Unit：{len(self.state.sorted_spikes)}")
        if self.state.statistics:
            messages.append(f"FDR 显著：{self.state.statistics['significant_count']}")
        if self.state.decoding:
            messages.append(
                f"解码：{self.state.decoding['balanced_accuracy']:.3f}，"
                f"置换 p={self.state.decoding['permutation_p']:.4f}"
            )
        self.warning_text.setText("\n".join(messages))
        self.log_view.setPlainText("\n".join(self.state.run_log))
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def _set_step_status(self, key: str, status: str) -> None:
        button = self.step_buttons[key]
        button.setProperty("status", status)
        button.style().unpolish(button)
        button.style().polish(button)
        if self.state:
            self.state.workflow_status[key] = status

    def _run_full_pipeline(self) -> None:
        self._start_worker([step.key for step in STEPS])

    def _run_current_step(self) -> None:
        self._start_worker([self.current_step])

    def _start_worker(self, keys: list[str]) -> None:
        if not self.state:
            QMessageBox.information(self, "没有项目", "请先从首页导入或生成数据。")
            return
        if self.worker and self.worker.isRunning():
            return
        sorter_name = "kilosort4"
        model_name = "Logistic regression"
        if self.current_step == "sorting" and self.option_combo.currentData():
            sorter_name = self.option_combo.currentData()
        if self.current_step == "decoding" and self.option_combo.currentData():
            model_name = self.option_combo.currentData()
        self.run_button.setEnabled(False)
        self.run_step_button.setEnabled(False)
        self.progress_bar.setFormat("正在运行… %v/%m")
        self.worker = PipelineWorker(self.state, keys, sorter_name, model_name)
        self.worker.progress.connect(self._on_progress)
        self.worker.step_done.connect(self._on_step_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.succeeded.connect(self._on_succeeded)
        self.worker.start()

    def _on_progress(self, message: str) -> None:
        self.status_label.setText(message)
        if self.state:
            self.state.log(message)
        self._refresh_warnings()

    def _on_step_done(self, key: str, value: object) -> None:
        skipped = isinstance(value, dict) and value.get("skipped")
        self._set_step_status(key, "skipped" if skipped else "completed")
        self.progress_bar.setValue([step.key for step in STEPS].index(key) + 1)
        if key == "preprocess" and not skipped:
            self.preview = value
        elif key == "sorting":
            if self.state and self.state.ground_truth and not skipped:
                self.matches = match_ground_truth(
                    self.state.ground_truth, self.state.sorted_spikes
                )
            if self.state:
                self.metric_units.value_label.setText(str(len(self.state.sorted_spikes)))
        if self.state:
            save_project(self.state)
        self._select_step(key)

    def _on_failed(self, key: str, details: str) -> None:
        self._set_step_status(key, "failed")
        self.run_button.setEnabled(True)
        self.run_step_button.setEnabled(True)
        self.progress_bar.setFormat("运行失败")
        self.status_label.setText(details.splitlines()[0])
        if self.state:
            self.state.log(f"{key} 失败：{details.splitlines()[0]}")
        self._refresh_warnings()
        QMessageBox.critical(
            self,
            "节点运行失败",
            f"{details.splitlines()[0]}\n\n详细信息已写入运行记录，已完成结果不会被删除。",
        )

    def _on_succeeded(self) -> None:
        self.run_button.setEnabled(True)
        self.run_step_button.setEnabled(True)
        self.progress_bar.setFormat("运行完成")
        self.status_label.setText("所选节点已完成，结果、参数与日志已经保存")
        self._refresh_figure()
        self._refresh_table()
        self._refresh_warnings()

    def _open_context_tutorial(self) -> None:
        TutorialDialog(STEP_TUTORIAL.get(self.current_step, "start"), self).exec()


def raw_overview_figure_empty(state: ProjectState):
    from matplotlib.figure import Figure

    figure = Figure(figsize=(9, 5), facecolor="#ffffff")
    axis = figure.subplots()
    axis.axis("off")
    axis.text(
        0.5,
        0.55,
        "从首页导入自己的数据，或生成可运行 Kilosort4 的模拟记录",
        ha="center",
        va="center",
        fontsize=15,
        color="#44534d",
    )
    axis.text(
        0.5,
        0.43,
        "数据结构、参数、分析结果和教程会在同一个项目中保持可追溯",
        ha="center",
        va="center",
        fontsize=10,
        color="#718079",
    )
    return figure


def run_app(workspace: Path) -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("NeuroFlow")
    app.setFont(QFont("Microsoft YaHei", 10))
    window = NeuroFlowWindow(workspace)
    window.show()
    return app.exec()
