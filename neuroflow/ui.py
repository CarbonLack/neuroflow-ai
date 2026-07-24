from __future__ import annotations

import json
import traceback
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
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
from .figures import (
    event_analysis_figure,
    preprocessing_figure,
    qc_figure,
    raw_overview_figure,
    sorting_figure,
    unit_metrics_figure,
)
from .models import ProjectState, WorkflowStep
from .simulation import load_or_generate_demo
from .sorting import kilosort_environment, run_kilosort4


STEPS = [
    WorkflowStep("import", "01  数据导入", "原始电压、事件与探针"),
    WorkflowStep("qc", "02  原始质控", "噪声、坏通道与伪迹"),
    WorkflowStep("preprocess", "03  预处理", "滤波与参考预览"),
    WorkflowStep("sorting", "04  Kilosort 4", "GPU spike sorting"),
    WorkflowStep("unit_qc", "05  Unit质控", "ISI、SNR与稳定性"),
    WorkflowStep("sync", "06  事件同步", "统一时间轴与trial"),
    WorkflowStep("analysis", "07  神经分析", "Raster、PSTH与群体响应"),
    WorkflowStep("statistics", "08  统计与出图", "检验、FDR与论文图"),
    WorkflowStep("export", "09  复现导出", "参数、Methods与来源"),
]


STEP_HELP = {
    "import": (
        "为什么需要",
        "所有后续计算都依赖采样率、通道数、数据类型、探针几何和事件时间。"
        "这里先建立数据清单，并保持原始文件只读。",
    ),
    "qc": (
        "重点检查",
        "高噪声通道、饱和、工频干扰和短暂伪迹可能制造假spike。"
        "质控结果必须作为sorting输入决策，而不是分析结束后的装饰。",
    ),
    "preprocess": (
        "当前策略",
        "显示300–6000 Hz带通和common median reference预览。"
        "Kilosort4会根据确认后的设置执行内部预处理，避免重复滤波。",
    ),
    "sorting": (
        "真实计算节点",
        "本节点调用Kilosort4，不使用预置动画。模拟数据包含ground truth，"
        "因此可以直接比较检出spike与真实spike，而不只看Unit数量。",
    ),
    "unit_qc": (
        "不要自动宣布Good Unit",
        "结合放电率、不应期违例、波形幅度和SNR给出候选标签。"
        "最终是否保留仍由研究者确认。",
    ),
    "sync": (
        "统一时间轴",
        "事件时间已经与原始电压使用同一秒单位。正式数据还需检查起始偏移、"
        "漏TTL和时钟漂移。",
    ),
    "analysis": (
        "事件相关分析",
        "默认以事件为0点截取-0.5至1.0秒，使用25 ms分箱，分别显示条件A和B。",
    ),
    "statistics": (
        "统计单位",
        "以trial为重复观测，比较同一Unit的基线与刺激后放电率；"
        "跨Unit使用Benjamini-Hochberg校正。",
    ),
    "export": (
        "可复现要求",
        "图形、绘图数据、参数、软件环境和Methods草稿一起导出，"
        "确保每张图都能追溯到输入与处理步骤。",
    ),
}


APP_STYLE = """
QMainWindow, QWidget {
    background: #f4f6f5;
    color: #17221f;
    font-family: "Microsoft YaHei", "Segoe UI";
    font-size: 13px;
}
#Header {
    background: #ffffff;
    border-bottom: 1px solid #dce3e0;
}
#Brand {
    font-size: 20px;
    font-weight: 700;
    color: #17221f;
}
#SubBrand {
    color: #6b7772;
    font-size: 12px;
}
#Sidebar, #Assistant {
    background: #ffffff;
}
#Sidebar {
    border-right: 1px solid #dce3e0;
}
#Assistant {
    border-left: 1px solid #dce3e0;
}
QPushButton {
    min-height: 34px;
    border: 1px solid #cfd8d4;
    background: #ffffff;
    padding: 0 12px;
    border-radius: 5px;
}
QPushButton:hover {
    border-color: #1f7a63;
    background: #f0f7f4;
}
QPushButton:checked, QPushButton#Primary {
    color: #ffffff;
    background: #1f7a63;
    border-color: #1f7a63;
    font-weight: 600;
}
QPushButton#StepButton {
    text-align: left;
    min-height: 52px;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding-left: 14px;
}
QPushButton#StepButton:checked {
    color: #17221f;
    background: #e9f2ee;
    border-left: 3px solid #1f7a63;
    font-weight: 650;
}
QPushButton#StepButton[status="completed"] {
    color: #1f7a63;
}
QPushButton#StepButton[status="failed"] {
    color: #b34f36;
}
QFrame#Metric {
    background: #ffffff;
    border: 1px solid #dce3e0;
    border-radius: 6px;
}
QLabel#MetricValue {
    font-size: 22px;
    font-weight: 700;
}
QLabel#MetricLabel, QLabel#Muted {
    color: #6b7772;
}
QProgressBar {
    border: 1px solid #cfd8d4;
    border-radius: 4px;
    background: #ffffff;
    text-align: center;
    min-height: 18px;
}
QProgressBar::chunk {
    background: #1f7a63;
    border-radius: 3px;
}
QPlainTextEdit, QTableWidget, QComboBox {
    background: #ffffff;
    border: 1px solid #dce3e0;
    border-radius: 5px;
}
QHeaderView::section {
    background: #edf1ef;
    border: none;
    border-bottom: 1px solid #d2dcd7;
    padding: 6px;
    font-weight: 600;
}
"""


class PipelineWorker(QThread):
    step_done = Signal(str, object)
    progress = Signal(str)
    failed = Signal(str, str)
    succeeded = Signal()

    def __init__(self, state: ProjectState, start_key: str | None = None):
        super().__init__()
        self.state = state
        self.start_key = start_key

    def _emit(self, key: str, value: object, message: str) -> None:
        self.progress.emit(message)
        self.step_done.emit(key, value)

    def run(self) -> None:
        try:
            keys = [step.key for step in STEPS]
            start_index = keys.index(self.start_key) if self.start_key in keys else 0
            for key in keys[start_index:]:
                if key == "import":
                    self._emit(key, self.state, "原始数据与事件文件已载入")
                elif key == "qc":
                    self._emit(key, run_raw_qc(self.state), "原始质控完成")
                elif key == "preprocess":
                    self._emit(key, preprocessing_preview(self.state), "预处理预览完成")
                elif key == "sorting":
                    result = run_kilosort4(
                        self.state,
                        self.state.root / "results" / "kilosort4",
                        self.progress.emit,
                    )
                    self._emit(key, result, "Kilosort4 sorting完成")
                elif key == "unit_qc":
                    self._emit(key, compute_unit_metrics(self.state), "Unit质控完成")
                elif key == "sync":
                    self.state.log(f"事件同步完成：{len(self.state.events)}个trial")
                    self._emit(key, self.state.events, "事件时间轴已确认")
                elif key == "analysis":
                    self._emit(key, event_aligned_analysis(self.state), "Raster与PSTH已生成")
                elif key == "statistics":
                    self._emit(key, self.state.analysis, "统计与FDR校正完成")
                elif key == "export":
                    output = export_reproducible_bundle(
                        self.state, self.state.root / "exports"
                    )
                    self._emit(key, output, "可复现分析包已导出")
            self.succeeded.emit()
        except Exception as exc:
            key = key if "key" in locals() else "import"
            self.failed.emit(key, f"{exc}\n\n{traceback.format_exc()}")


class MetricBox(QFrame):
    def __init__(self, label: str, value: str):
        super().__init__()
        self.setObjectName("Metric")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 10, 13, 10)
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
        self.state = load_or_generate_demo(workspace / "demo_project")
        self.preview: dict | None = None
        self.matches: list[dict] = []
        self.worker: PipelineWorker | None = None
        self.step_buttons: dict[str, QPushButton] = {}
        self.current_step = "import"
        self.setWindowTitle("NeuroFlow AI - Full Pipeline Demo")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 720)
        self._build_ui()
        self._select_step("import")

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._header())
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addWidget(self._sidebar())
        content.addWidget(self._main_area(), 1)
        content.addWidget(self._assistant())
        body = QWidget()
        body.setLayout(content)
        root_layout.addWidget(body, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(APP_STYLE)

    def _header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(72)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        brand_box = QVBoxLayout()
        brand = QLabel("NeuroFlow AI")
        brand.setObjectName("Brand")
        sub = QLabel("在体细胞外电生理 · 可解释全流程工作台")
        sub.setObjectName("SubBrand")
        brand_box.addWidget(brand)
        brand_box.addWidget(sub)
        layout.addLayout(brand_box)
        layout.addStretch()

        self.manual_button = QPushButton("手动")
        self.guided_button = QPushButton("引导")
        self.guided_button.setChecked(True)
        for button in (self.manual_button, self.guided_button):
            button.setCheckable(True)
            button.setFixedWidth(76)
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        mode_group.addButton(self.manual_button)
        mode_group.addButton(self.guided_button)
        layout.addWidget(self.manual_button)
        layout.addWidget(self.guided_button)

        self.run_button = QPushButton("运行完整流程")
        self.run_button.setObjectName("Primary")
        self.run_button.setFixedWidth(138)
        self.run_button.clicked.connect(self._run_full_pipeline)
        layout.addSpacing(12)
        layout.addWidget(self.run_button)
        return header

    def _sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(242)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 12, 0, 10)
        label = QLabel("  分析流程")
        label.setObjectName("Muted")
        layout.addWidget(label)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for step in STEPS:
            button = QPushButton(f"{step.title}\n    {step.subtitle}")
            button.setObjectName("StepButton")
            button.setCheckable(True)
            button.setProperty("status", step.status)
            button.clicked.connect(lambda checked=False, key=step.key: self._select_step(key))
            group.addButton(button)
            layout.addWidget(button)
            self.step_buttons[step.key] = button
        layout.addStretch()
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
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)
        title_row = QHBoxLayout()
        title_box = QVBoxLayout()
        self.page_title = QLabel()
        self.page_title.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("Muted")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_subtitle)
        title_row.addLayout(title_box)
        title_row.addStretch()
        self.unit_selector = QComboBox()
        self.unit_selector.setMinimumWidth(140)
        self.unit_selector.currentIndexChanged.connect(self._refresh_figure)
        self.unit_selector.setVisible(False)
        title_row.addWidget(self.unit_selector)
        self.run_step_button = QPushButton("运行此节点")
        self.run_step_button.clicked.connect(self._run_current_step)
        title_row.addWidget(self.run_step_button)
        layout.addLayout(title_row)

        metrics = QHBoxLayout()
        self.metric_source = MetricBox("数据源", "SIM")
        self.metric_channels = MetricBox("通道", str(self.state.channel_count))
        self.metric_duration = MetricBox("时长", f"{self.state.duration_seconds:.0f}s")
        self.metric_units = MetricBox("检出Unit", "—")
        for metric in (
            self.metric_source,
            self.metric_channels,
            self.metric_duration,
            self.metric_units,
        ):
            metrics.addWidget(metric)
        layout.addLayout(metrics)

        self.canvas = FigureCanvasQTAgg(raw_overview_figure(self.state))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(STEPS))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("演示项目已就绪")
        self.status_label.setObjectName("Muted")
        layout.addWidget(self.status_label)
        return widget

    def _assistant(self) -> QWidget:
        assistant = QWidget()
        assistant.setObjectName("Assistant")
        assistant.setFixedWidth(300)
        layout = QVBoxLayout(assistant)
        layout.setContentsMargins(16, 16, 16, 14)
        title = QLabel("分析助手")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)
        mode = QLabel("离线规则模式 · AI接口未连接")
        mode.setObjectName("Muted")
        layout.addWidget(mode)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #dce3e0;")
        layout.addWidget(line)
        self.help_title = QLabel()
        self.help_title.setStyleSheet("font-weight: 700; color: #1f7a63;")
        layout.addWidget(self.help_title)
        self.help_text = QLabel()
        self.help_text.setWordWrap(True)
        self.help_text.setAlignment(Qt.AlignTop)
        layout.addWidget(self.help_text)
        layout.addSpacing(10)
        warning_title = QLabel("当前证据与提醒")
        warning_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(warning_title)
        self.warning_text = QLabel("尚未运行质控。")
        self.warning_text.setWordWrap(True)
        self.warning_text.setObjectName("Muted")
        layout.addWidget(self.warning_text)
        layout.addSpacing(10)
        log_title = QLabel("运行记录")
        log_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(log_title)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(200)
        layout.addWidget(self.log_view, 1)
        return assistant

    def _refresh_environment(self) -> None:
        env = kilosort_environment()
        if env["cuda_available"]:
            text = (
                f"GPU就绪\n{env['device_name']}\n"
                f"{env['gpu_memory_gb']:.1f} GB显存"
            )
        else:
            text = "GPU未就绪\nKilosort将使用CPU或提示配置环境"
        self.environment_label.setText(text)

    def _select_step(self, key: str) -> None:
        self.current_step = key
        step = next(item for item in STEPS if item.key == key)
        self.step_buttons[key].setChecked(True)
        self.page_title.setText(step.title)
        self.page_subtitle.setText(step.subtitle)
        help_title, help_text = STEP_HELP[key]
        self.help_title.setText(help_title)
        self.help_text.setText(help_text)
        self.unit_selector.setVisible(key in {"analysis", "statistics"} and bool(self.state.sorted_spikes))
        self._refresh_figure()
        self._refresh_warnings()

    def _replace_figure(self, figure) -> None:
        old = self.canvas
        parent_layout = old.parentWidget().layout()
        index = parent_layout.indexOf(old)
        parent_layout.removeWidget(old)
        old.setParent(None)
        old.deleteLater()
        self.canvas = FigureCanvasQTAgg(figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        parent_layout.insertWidget(index, self.canvas, 1)
        self.canvas.draw_idle()

    def _refresh_figure(self) -> None:
        if not hasattr(self, "canvas"):
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
        elif key in {"analysis", "statistics"} and self.state.analysis:
            unit_id = self.unit_selector.currentData()
            figure = event_analysis_figure(self.state, unit_id)
        else:
            figure = raw_overview_figure(self.state)
        self._replace_figure(figure)

    def _refresh_warnings(self) -> None:
        messages = []
        if self.state.qc:
            bad = self.state.qc.get("bad_channels", [])
            if bad:
                messages.append(f"高噪声通道：{', '.join(map(str, bad))}")
            messages.append(f"50 Hz比值：{self.state.qc.get('line_noise_ratio', 0):.2f}")
        if self.state.sorted_spikes:
            messages.append(f"Kilosort已检出{len(self.state.sorted_spikes)}个Unit")
        if self.state.analysis:
            messages.append(f"FDR显著Unit：{self.state.analysis['responsive_units']}")
        self.warning_text.setText("\n".join(messages) if messages else "尚未运行质控。")
        self.log_view.setPlainText("\n".join(self.state.run_log))
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def _set_step_status(self, key: str, status: str) -> None:
        button = self.step_buttons[key]
        button.setProperty("status", status)
        button.style().unpolish(button)
        button.style().polish(button)

    def _run_full_pipeline(self) -> None:
        self._start_worker(None)

    def _run_current_step(self) -> None:
        self._start_worker(self.current_step)

    def _start_worker(self, start_key: str | None) -> None:
        if self.worker and self.worker.isRunning():
            return
        if start_key == "sorting":
            results = self.state.root / "results" / "kilosort4"
            if results.exists():
                answer = QMessageBox.question(
                    self,
                    "重新运行Kilosort4",
                    "已有sorting结果。是否重新执行真实Kilosort计算？",
                )
                if answer != QMessageBox.Yes:
                    return
        self.run_button.setEnabled(False)
        self.run_step_button.setEnabled(False)
        self.progress_bar.setFormat("正在运行… %v/%m")
        self.worker = PipelineWorker(self.state, start_key)
        self.worker.progress.connect(self._on_progress)
        self.worker.step_done.connect(self._on_step_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.succeeded.connect(self._on_succeeded)
        self.worker.start()

    def _on_progress(self, message: str) -> None:
        self.status_label.setText(message)
        self.state.log(message)
        self._refresh_warnings()

    def _on_step_done(self, key: str, value: object) -> None:
        self._set_step_status(key, "completed")
        index = [step.key for step in STEPS].index(key)
        self.progress_bar.setValue(index + 1)
        if key == "preprocess":
            self.preview = value
        elif key == "sorting":
            self.matches = match_ground_truth(self.state.ground_truth, self.state.sorted_spikes)
            self.metric_units.value_label.setText(str(len(self.state.sorted_spikes)))
            self.unit_selector.blockSignals(True)
            self.unit_selector.clear()
            for unit_id in sorted(self.state.sorted_spikes):
                self.unit_selector.addItem(f"Unit {unit_id}", unit_id)
            self.unit_selector.blockSignals(False)
        if key == self.current_step or key in {"sorting", "analysis"}:
            self._select_step(key)
        self._refresh_warnings()

    def _on_failed(self, key: str, details: str) -> None:
        self._set_step_status(key, "failed")
        self.run_button.setEnabled(True)
        self.run_step_button.setEnabled(True)
        self.progress_bar.setFormat("运行失败")
        self.status_label.setText(details.splitlines()[0])
        self.state.log(f"{key}失败：{details.splitlines()[0]}")
        self._refresh_warnings()
        QMessageBox.critical(
            self,
            "节点运行失败",
            f"{details.splitlines()[0]}\n\n详细日志已保留在右侧运行记录中。",
        )

    def _on_succeeded(self) -> None:
        self.run_button.setEnabled(True)
        self.run_step_button.setEnabled(True)
        self.progress_bar.setFormat("完整流程已完成")
        self.status_label.setText("从原始电压到论文图与复现记录的完整链路已完成")
        self._select_step("analysis")
        self._refresh_warnings()


def run_app(workspace: Path) -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("NeuroFlow AI")
    app.setFont(QFont("Microsoft YaHei", 10))
    window = NeuroFlowWindow(workspace)
    window.show()
    return app.exec()
