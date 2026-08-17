from __future__ import annotations

import json
import re
import sys
import traceback
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import mplcursors
import numpy as np
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)
from matplotlib.transforms import Bbox
from PySide6.QtCore import QEvent, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QPixmap
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
    QHeaderView,
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
    QStyle,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .ai import STAGE_LABELS, AIResponse
from .ai_tools import AIMode
from .ai_ui import AIAssistantDialog, load_ai_settings, save_ai_preferences
from .analysis import (
    compute_unit_metrics,
    event_aligned_analysis,
    export_reproducible_bundle,
    match_ground_truth,
    preprocessing_preview,
    run_raw_qc,
)
from .audit import audited_stage
from .data_import import (
    DEVICE_READERS,
    SUPPORTED_FORMATS,
    attach_kilosort_results,
    import_binary_recording,
    import_device_recording,
    import_ibl_alf,
    import_ibl_trials_aggregate,
    import_kilosort_results,
    import_nwb_units,
)
from .nex5_adapter import (
    import_nex5_sorting_into_project,
    inspect_nex5_source,
)
from .decoding import (
    MODEL_DESCRIPTIONS,
    MODELS,
    REGRESSION_DESCRIPTIONS,
    REGRESSION_MODELS,
    run_decoding_suite,
    run_regression_suite,
)
from .ephys_toolkit import (
    METHOD_CATALOG,
    provider_status,
    run_lfp_suite,
    run_neural_toolkit,
    run_respiration_case,
    run_spike_field_suite,
    run_spike_train_suite,
)
from .figure_studio import FigureStudioDialog
from .figures import (
    behavior_figure,
    decoding_figure,
    neural_toolkit_figure,
    pending_step_figure,
    preprocessing_diagnostics_figure,
    qc_diagnostics_figure,
    raw_overview_figure,
    regression_figure,
    sorting_diagnostics_figure,
    sorting_figure,
    statistics_figure,
    synchronization_figure,
    unit_metrics_figure,
)
from .help_content import REFERENCES, control_help, page_controls
from .i18n import LANGUAGES, step_text, tr
from .ibl import download_bwm_trials_aggregate
from .models import ProjectState, WorkflowStep
from .medpc import import_medpc_behavior
from .project import MANIFEST_NAME, load_project, save_project
from .product import PRODUCT_NAME, PRODUCT_VERSION
from .public_examples import (
    PUBLIC_EXAMPLES,
    download_public_example,
    open_or_create_public_example,
    public_example_status,
    public_validation_root,
)
from .simulation import (
    DEMO_PROFILES,
    demo_profile_catalog,
    generate_demo_recording,
    load_or_generate_demo,
)
from .sorting import (
    kilosort_environment,
    refresh_sorter_catalog,
    run_sorter,
    sorter_catalog,
)
from .sorting_results import activate_sorting_result
from .sorting_workbench import SortingWorkbench
from .statistics import run_statistical_suite
from .synchronization import import_behavior_events, synchronize_existing_events
from .trace_controls import TraceControls
from .tutorial_details import TUTORIAL_DETAILS, localized, localized_rows
from .tutorials import TUTORIALS, tutorial_value
from .unit_curation import curation_summary
from .unit_curation_ui import UnitCurationDialog

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
    "import": "import",
    "qc": "qc",
    "preprocess": "preprocess",
    "sorting": "sorting",
    "unit_qc": "unit_qc",
    "sync": "sync",
    "behavior": "behavior",
    "analysis": "analysis",
    "statistics": "statistics",
    "decoding": "decoding",
    "export": "export",
}

FORMAT_TEXT_EN = {
    "simulated": (
        "Demo/simulated multichannel recording",
        "Neuropixels-like, tetrode, or linear probe",
    ),
    "binary": ("Generic binary", "Interleaved int16/int32/float32 raw recording"),
    "device": (
        "Acquisition-system data",
        "Intan, Open Ephys, SpikeGLX, Blackrock, Plexon, TDT, NWB",
    ),
    "ibl_alf": (
        "Public validation data",
        "IBL ALF/BWM or Buzsáki/DANDI NWB with Units and behavior",
    ),
    "kilosort": (
        "Kilosort/Phy output",
        "Spike times, cluster assignments, and parameters",
    ),
    "nex5": (
        "NeuroExplorer / Offline Sorter output",
        "Candidate units, spike timestamps, and waveforms stored in .nex5",
    ),
}

ENTRY_ROUTE_TEXT = {
    "zh_CN": {
        "simulated": (
            "教学模拟项目",
            "想先学习、测试电脑或比较 sorter",
            "选择探针场景；系统生成原始电压、探针、行为、TTL 与 ground truth",
            "数据与项目",
            "可以",
            "唯一已知真实 spike 的入口，可定量计算 sorting 的准确率、召回率和 F1。",
        ),
        "binary": (
            "我的通用二进制",
            "手里有交错存储的 .bin/.dat 原始电压",
            "选择文件并填写采样率、通道数、dtype、μV/bit；可同时选择事件 CSV",
            "数据与项目",
            "可以",
            "适用于自定义采集程序；参数填错会改变数据重排或时间换算。",
        ),
        "device": (
            "我的记录系统文件",
            "手里有 Intan、Open Ephys、SpikeGLX、Blackrock、Plexon、TDT 或 NWB 原始记录",
            "选择记录系统和对应文件/文件夹；NeuroEphys AI 调用 SpikeInterface 读取器",
            "数据与项目",
            "有原始电压时可以",
            "保留源文件只读，建立统一缓存后进入质控、预处理和 sorting。",
        ),
        "ibl_alf": (
            "已验证公开项目（2 套）",
            "直接打开 NeuroEphys AI 已实际跑通的固定公开会话",
            "IBL BWM EID 4ecb… 与 Buzsáki DANDI 000552；双击查看下载状态并打开",
            "Unit/行为检查",
            "通常不可以",
            "锁定来源编号、固定版本和本地缓存；可运行 Unit QC、事件分析、统计与解码。",
        ),
        "kilosort": (
            "已有 sorting 结果",
            "已经在 Kilosort/Phy 或其他工具中完成了 sorting",
            "选择含 spike_times.npy 与 cluster 分配的结果文件夹，并填写原采样率",
            "Unit 质控",
            "无需重跑",
            "统一为秒制 Unit/spike 接口，可与本项目其他 sorter 结果并列比较。",
        ),
        "nex5": (
            "Offline Sorter / NeuroExplorer 结果",
            "手里有人工或半自动筛选后导出的 .nex5",
            "选择一个 .nex5 文件或包含多个文件的文件夹；可按文件名筛选同一动物",
            "Unit 质控",
            "无需重跑",
            "保留原始 unit 名称、通道、spike 时间和波形摘要，并与其他 sorter 并列比较。",
        ),
    },
    "en_US": {
        "simulated": (
            "Guided simulation",
            "Learn the workflow, test the computer, or compare sorters",
            "Choose a probe scenario; NeuroEphys AI creates raw voltage, probe, behavior, TTL, and ground truth",
            "Data and project",
            "Yes",
            "The only entry with known spikes, enabling precision, recall, and F1 validation.",
        ),
        "binary": (
            "My generic binary",
            "You have interleaved .bin/.dat raw voltage",
            "Choose the file and specify rate, channels, dtype, and μV/bit; events CSV is optional",
            "Data and project",
            "Yes",
            "Use for custom acquisition; wrong metadata changes reshaping or the time base.",
        ),
        "device": (
            "My acquisition files",
            "You have Intan, Open Ephys, SpikeGLX, Blackrock, Plexon, TDT, or raw NWB",
            "Choose the acquisition system and its file/folder; SpikeInterface reads the source",
            "Data and project",
            "With raw voltage",
            "Sources remain read-only and enter QC, preprocessing, and sorting through a normalized cache.",
        ),
        "ibl_alf": (
            "Verified public projects (2)",
            "Open fixed public sessions already exercised by NeuroEphys AI",
            "IBL BWM EID 4ecb… and Buzsáki DANDI 000552; double-click to inspect and open",
            "Unit/behavior checks",
            "Usually no",
            "Locks identifiers, versions, and local cache; continue with QC, event analysis, statistics, and decoding.",
        ),
        "kilosort": (
            "Existing sorting results",
            "Sorting was completed in Kilosort/Phy or another tool",
            "Choose a folder with spike_times and cluster assignments and specify the original rate",
            "Unit QC",
            "No rerun needed",
            "Normalize to the seconds-based Unit/spike interface and compare with other sorter results.",
        ),
        "nex5": (
            "Offline Sorter / NeuroExplorer results",
            "You have manually or semi-automatically curated .nex5 output",
            "Choose one .nex5 file or a folder; optionally filter filenames for one subject",
            "Unit QC",
            "No rerun needed",
            "Preserve unit names, channels, spike times, and waveform summaries for side-by-side comparison.",
        ),
    },
}

STATISTICAL_METHODS = (
    "paired t-test",
    "Wilcoxon signed-rank",
    "paired permutation",
    "bootstrap 95% CI",
    "Shapiro-Wilk",
    "Welch t-test",
    "Mann-Whitney U",
    "Levene test",
    "one-way ANOVA",
    "Kruskal-Wallis",
    "Pearson / Spearman",
    "mixed-effects model",
    "Rayleigh phase-locking approximation",
    "circular-shift surrogate test",
    "FDR / Holm / Bonferroni",
)


def _documentation_index() -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return bundle_root / "neuroflow_docs" / "index.html"
    return Path(__file__).resolve().parents[1] / "docs" / "site" / "index.html"


def _documentation_page(language: str, page: str = "index.html") -> Path:
    language_folder = "en" if language == "en_US" else "zh"
    return _documentation_index().parent / language_folder / page


def _brand_asset(name: str) -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return bundle_root / "neuroephys_brand" / name
    return Path(__file__).resolve().parents[1] / "assets" / "brand" / name


APP_STYLE = """
QMainWindow, QWidget {
    background: #0d0c14;
    color: #f7f3fa;
    font-family: "Microsoft YaHei", "Segoe UI";
    font-size: 13px;
}
#Header, #HomeHeader {
    background: #0d0c14;
    color: #f7f3fa;
    border-bottom: 1px solid #3b354a;
}
#Header QLabel, #HomeHeader QLabel, #HeroPanel QLabel,
#Sidebar QLabel, #Assistant QLabel, #RunFooter QLabel {
    background: transparent;
}
#Brand { font-size: 22px; font-weight: 700; color: #f7f3fa; }
#Hero { font-size: 32px; font-weight: 700; color: #f7f3fa; }
#HeroPanel {
    background: #171521;
    color: #f7f3fa;
    border: 1px solid #3b354a;
    border-radius: 7px;
}
#HeroPanel QLabel#Muted { color: #bdb3cc; }
#Sidebar, #Assistant {
    background: #121019;
    color: #f2edf5;
}
#Sidebar { border-right: 1px solid #3b354a; }
#Assistant { border-left: 1px solid #3b354a; }
#Sidebar QLabel, #Assistant QLabel { color: #dcd5e4; }
#Sidebar QLabel#Muted, #Assistant QLabel#Muted { color: #9e94ad; }
#RunFooter {
    background: #0d0c14;
    color: #f2edf5;
    border-top: 1px solid #3b354a;
}
QPushButton {
    min-height: 36px;
    color: #f7f3fa;
    border: 1px solid #4a425b;
    background: #211d2b;
    padding: 0 14px;
    border-radius: 5px;
}
QPushButton:hover { border-color: #d885e9; background: #2b2537; }
QPushButton:disabled { color: #766e82; background: #171521; border-color: #332d3f; }
QPushButton:checked, QPushButton#Primary {
    color: #140d17; background: #d885e9; border-color: #d885e9; font-weight: 700;
}
QPushButton#StepButton {
    text-align: left; min-height: 53px; border: none; border-left: 3px solid transparent;
    border-radius: 0; padding: 2px 12px 2px 14px; color: #c9c1d2; background: #121019;
}
QPushButton#StepButton:checked {
    color: #f7f3fa; background: #292333; border-left: 3px solid #d885e9; font-weight: 650;
}
QPushButton#StepButton[status="completed"] { color: #62d8a4; }
QPushButton#StepButton[status="failed"] { color: #f58b82; }
QFrame#Card, QFrame#Metric, QFrame#SortingWorkbench, QFrame#TraceControls {
    background: #171521; border: 1px solid #3b354a; border-radius: 6px;
}
QFrame#InsetPanel {
    background: #211d2b; border: 1px solid #3b354a; border-radius: 5px;
}
QLabel#MetricValue { font-size: 19px; font-weight: 700; }
QLabel#Muted, QLabel#MetricLabel { color: #a79db5; }
QLabel#PanelTitle { font-size: 15px; font-weight: 700; }
QLabel#FieldLabel { color: #d0c8d8; font-weight: 600; }
QLabel#StatusBadge {
    color: #f3aaa3; background: #342128; border: 1px solid #75414c;
    border-radius: 4px; padding: 3px 8px; font-weight: 600;
}
QLabel#StatusBadge[available="true"] {
    color: #8ce2bd; background: #183127; border-color: #3d7a62;
}
QLineEdit, QPlainTextEdit, QTextBrowser, QTableWidget, QComboBox, QSpinBox, QDoubleSpinBox, QListWidget {
    background: #13111a; color: #f2edf5; border: 1px solid #4a425b; border-radius: 4px; min-height: 31px;
    selection-background-color: #5c3567;
}
QComboBox { padding: 0 8px; }
QComboBox QAbstractItemView {
    background: #171521; color: #f2edf5; selection-background-color: #5c3567;
}
QTableWidget { gridline-color: #342f3e; }
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background: #5c3567; color: #ffffff; }
QHeaderView::section {
    background: #26212f; color: #eee8f2; border: none; border-bottom: 1px solid #4a425b; padding: 7px; font-weight: 600;
}
QProgressBar {
    border: 1px solid #4a425b; border-radius: 4px; background: #171521; color: #f2edf5;
    text-align: center; min-height: 18px;
}
QProgressBar::chunk { background: #d885e9; border-radius: 3px; }
QTabWidget::pane { border: 1px solid #3b354a; background: #171521; }
QTabBar::tab {
    background: #171521; color: #bdb3cc; padding: 7px 12px;
    border: 1px solid #3b354a; border-bottom: none;
}
QTabBar::tab:selected { color: #f7f3fa; border-top: 2px solid #d885e9; }
QToolBar {
    background: #f7f3fa; border: 1px solid #d8d1dd; spacing: 2px;
}
QToolBar QToolButton {
    background: #f7f3fa; color: #16242c; border: none; padding: 3px;
}
QToolBar QToolButton:hover { background: #eee8f2; }
QScrollBar:vertical {
    background: #121019; width: 12px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #4a425b; min-height: 28px; border-radius: 5px;
}
QScrollBar::handle:vertical:hover { background: #6a5d7a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class AxisEditorDialog(QDialog):
    def __init__(self, axis, language: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.axis = axis
        self.language = language
        self.setWindowTitle(tr("plot_settings", language))
        self.resize(470, 370)
        layout = QVBoxLayout(self)
        axis_index = axis.figure.axes.index(axis) + 1
        heading = QLabel(f"{'坐标轴' if language == 'zh_CN' else 'Axis'} {axis_index}")
        heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(heading)
        form = QFormLayout()
        self.title = QLineEdit(axis.get_title())
        self.xlabel = QLineEdit(axis.get_xlabel())
        self.ylabel = QLineEdit(axis.get_ylabel())
        self.xmin = QDoubleSpinBox()
        self.xmax = QDoubleSpinBox()
        self.ymin = QDoubleSpinBox()
        self.ymax = QDoubleSpinBox()
        for widget in (self.xmin, self.xmax, self.ymin, self.ymax):
            widget.setRange(-1e12, 1e12)
            widget.setDecimals(6)
        self.xmin.setValue(axis.get_xlim()[0])
        self.xmax.setValue(axis.get_xlim()[1])
        self.ymin.setValue(axis.get_ylim()[0])
        self.ymax.setValue(axis.get_ylim()[1])
        self.grid = QCheckBox("显示网格" if language == "zh_CN" else "Show grid")
        visible_grid = any(line.get_visible() for line in axis.get_xgridlines())
        self.grid.setChecked(visible_grid)
        labels = (
            (
                "标题",
                "X 轴标签",
                "Y 轴标签",
                "X 最小值",
                "X 最大值",
                "Y 最小值",
                "Y 最大值",
            )
            if language == "zh_CN"
            else (
                "Title",
                "X label",
                "Y label",
                "X minimum",
                "X maximum",
                "Y minimum",
                "Y maximum",
            )
        )
        for label, widget in zip(
            labels,
            (
                self.title,
                self.xlabel,
                self.ylabel,
                self.xmin,
                self.xmax,
                self.ymin,
                self.ymax,
            ),
        ):
            form.addRow(label, widget)
        form.addRow(self.grid)
        layout.addLayout(form)
        note = QLabel(
            "修改只影响当前图；导出 SVG 后仍可在矢量软件中继续编辑。"
            if language == "zh_CN"
            else "Changes affect the current figure only. Export SVG for further vector editing."
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText(tr("apply", language))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("cancel", language))
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self) -> None:
        if (
            self.xmin.value() >= self.xmax.value()
            or self.ymin.value() >= self.ymax.value()
        ):
            QMessageBox.warning(
                self,
                tr("plot_settings", self.language),
                "最小值必须小于最大值。"
                if self.language == "zh_CN"
                else "Minimum values must be smaller than maximum values.",
            )
            return
        self.axis.set_title(self.title.text(), loc="left")
        self.axis.set_xlabel(self.xlabel.text())
        self.axis.set_ylabel(self.ylabel.text())
        self.axis.set_xlim(self.xmin.value(), self.xmax.value())
        self.axis.set_ylim(self.ymin.value(), self.ymax.value())
        self.axis.grid(self.grid.isChecked())
        self.axis.figure.canvas.draw_idle()
        self.accept()


class SorterManagerDialog(QDialog):
    def __init__(self, language: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(tr("sorter_manager", language))
        self.resize(980, 520)
        layout = QVBoxLayout(self)
        heading = QLabel(tr("sorter_manager", language))
        heading.setStyleSheet("font-size: 21px; font-weight: 700;")
        layout.addWidget(heading)
        explanation = QLabel(
            "只检测 NeuroEphys AI 明确支持的 sorter。某个后端检测失败时，其他后端和主界面仍可使用。"
            if language == "zh_CN"
            else "Only explicitly supported sorters are probed. A failed backend never blocks the application or other sorters."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Sorter", "状态", "版本", "硬件", "适用记录", "检测信息"]
            if language == "zh_CN"
            else ["Sorter", "Status", "Version", "Hardware", "Best for", "Probe detail"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.note = QLabel(
            "以上环境探测结果是当前电脑的实际可运行状态。便携核心版可能未包含数 GiB 的 "
            "Kilosort/CUDA 运行库；GPU 组件可通过受管理的完整分析环境配置。缺失后端会保持不可用，"
            "不会自动替换成其他 sorter。"
            if language == "zh_CN"
            else "The environment probes above are authoritative for this computer. "
            "The portable core edition may omit the several-GiB Kilosort/CUDA runtime; "
            "a managed full analysis environment can provide the GPU component. "
            "A missing backend remains unavailable and is never replaced silently."
        )
        self.note.setWordWrap(True)
        self.note.setObjectName("Muted")
        layout.addWidget(self.note)
        row = QHBoxLayout()
        refresh = QPushButton(tr("refresh", language))
        refresh.clicked.connect(self._refresh)
        close = QPushButton(tr("close", language))
        close.clicked.connect(self.accept)
        row.addStretch()
        row.addWidget(refresh)
        row.addWidget(close)
        layout.addLayout(row)
        self._refresh()

    def _refresh(self) -> None:
        catalog = refresh_sorter_catalog()
        self.table.setRowCount(len(catalog))
        for row, item in enumerate(catalog):
            status = (
                tr("available", self.language)
                if item["installed"]
                else tr("unavailable", self.language)
            )
            values = [
                item["name"],
                status,
                item["version"],
                item["hardware"],
                item["best_for"],
                item.get("error") or "OK",
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()


class DemoLibraryDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        language: str = "zh_CN",
    ):
        super().__init__(parent)
        self.language = language
        self.profile_key = "neuropixels_decision"
        english = language == "en_US"
        self.setWindowTitle(
            "Choose a complete demo dataset" if english else "选择一套完整模拟数据"
        )
        self.resize(980, 520)
        layout = QVBoxLayout(self)
        title = QLabel(
            "Probe geometry + raw voltage + behavior + TTL + ground truth"
            if english
            else "探针几何 + 原始电压 + 行为事件 + TTL + ground truth"
        )
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)
        summary = QLabel(
            (
                "Each dataset follows the same auditable import contract, but uses a "
                "different electrode geometry, behavior paradigm, and recommended "
                "sorter comparison. These are synthetic teaching datasets, not claims "
                "about biological findings."
            )
            if english
            else (
                "每套数据使用同一套可审计导入规范，但电极几何、行为范式和推荐 sorter "
                "不同。它们用于教学、流程验证和算法比较，不代表真实生物学结论。"
            )
        )
        summary.setWordWrap(True)
        summary.setObjectName("Muted")
        layout.addWidget(summary)
        catalog = demo_profile_catalog()
        self.table = QTableWidget(len(catalog), 5)
        self.table.setHorizontalHeaderLabels(
            ["Dataset", "Channels", "Behavior", "Recommended sorters", "Included challenge"]
            if english
            else ["数据集", "通道", "行为范式", "推荐 sorter", "包含的分析挑战"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        for row, item in enumerate(catalog):
            values = [
                item["name"] if english else item["name_zh"],
                str(item["channel_count"]),
                (
                    item["behavior_paradigm"]
                    if english
                    else item["behavior_paradigm_zh"]
                ),
                ", ".join(item["recommended_sorters"]),
                item["scenario"] if english else item["scenario_zh"],
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.UserRole, item["key"])
                self.table.setItem(row, column, cell)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.selectRow(0)
        layout.addWidget(self.table, 1)
        self.details = QLabel()
        self.details.setObjectName("InsetPanel")
        self.details.setWordWrap(True)
        self.details.setContentsMargins(12, 9, 12, 9)
        layout.addWidget(self.details)
        self.table.currentCellChanged.connect(
            lambda row, _column, _old_row, _old_column: self._show_details(row)
        )
        self._show_details(0)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText(
            "Generate and open" if english else "生成并打开"
        )
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _show_details(self, row: int) -> None:
        if row < 0:
            return
        key = str(self.table.item(row, 0).data(Qt.UserRole))
        profile = DEMO_PROFILES[key]
        self.details.setText(
            (
                f"Included challenge: {profile['scenario']}\n"
                "Files created: raw voltage, metadata and geometry, behavior CSV, "
                "ephys TTL CSV, respiration/state reference, import configuration, "
                "and ground-truth spike times."
            )
            if self.language == "en_US"
            else (
                f"包含的分析挑战：{profile['scenario_zh']}\n"
                "生成文件：原始电压、元数据与探针几何、行为 CSV、电生理 TTL CSV、"
                "呼吸/状态参考、精确导入配置和 ground-truth spike 时间。"
            )
        )

    def _accept_selection(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.profile_key = str(self.table.item(row, 0).data(Qt.UserRole))
        self.accept()


class NewProjectDialog(QDialog):
    def __init__(
        self,
        workspace: Path,
        parent: QWidget | None = None,
        language: str = "zh_CN",
    ):
        super().__init__(parent)
        self.workspace = workspace
        self.language = language
        self.state: ProjectState | None = None
        english = language == "en_US"
        self.setWindowTitle("Create project" if english else "新建 NeuroEphys AI 项目")
        self.resize(700, 330)
        layout = QVBoxLayout(self)
        title = QLabel(
            "Create an empty project first" if english else "先创建项目，再导入数据"
        )
        title.setStyleSheet("font-size: 21px; font-weight: 700;")
        layout.addWidget(title)
        summary = QLabel(
            (
                "A project stores source links, parameters, intermediate results, "
                "figures, and provenance. Creating it does not generate simulated data."
            )
            if english
            else (
                "项目用于保存数据来源索引、参数、中间结果、图和审计记录。"
                "新建项目不会自动生成模拟数据。"
            )
        )
        summary.setWordWrap(True)
        summary.setObjectName("Muted")
        layout.addWidget(summary)
        form = QFormLayout()
        self.name_edit = QLineEdit(
            "My electrophysiology project" if english else "我的电生理项目"
        )
        folder_holder = QWidget()
        folder_row = QHBoxLayout(folder_holder)
        folder_row.setContentsMargins(0, 0, 0, 0)
        self.folder_edit = QLineEdit(str(workspace / "projects"))
        browse = QPushButton("Browse…" if english else "选择位置…")
        browse.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(browse)
        form.addRow("Project name" if english else "项目名称", self.name_edit)
        form.addRow("Save under" if english else "保存到", folder_holder)
        layout.addLayout(form)
        next_note = QLabel(
            (
                "After opening the empty project, use “Import my data” on the Data "
                "and project page. You can choose generic binary, an acquisition-system "
                "file, or an existing sorting result."
            )
            if english
            else (
                "创建后会进入“数据与项目”页面。点击“导入我的数据”，再选择通用二进制、"
                "记录系统文件或已有 sorting 结果。"
            )
        )
        next_note.setObjectName("InsetPanel")
        next_note.setWordWrap(True)
        next_note.setContentsMargins(12, 9, 12, 9)
        layout.addWidget(next_note)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText(
            "Create project" if english else "创建项目"
        )
        buttons.accepted.connect(self._create)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choose project parent folder"
            if self.language == "en_US"
            else "选择项目上级文件夹",
            self.folder_edit.text(),
        )
        if selected:
            self.folder_edit.setText(selected)

    def _create(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                self.windowTitle(),
                "Enter a project name"
                if self.language == "en_US"
                else "请输入项目名称",
            )
            return
        parent = Path(self.folder_edit.text()).expanduser()
        parent.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]+", "_", name).strip("_")
        stamp = datetime.now(timezone.utc).astimezone()
        root = parent / f"{slug or 'NeuroEphys_AI_project'}_{stamp:%Y%m%d_%H%M%S}"
        self.state = ProjectState(
            root=root,
            name=name,
            source_type="unconfigured",
            metadata={
                "language": self.language,
                "data_imported": False,
                "project_created_without_data": True,
            },
            workflow_status={step.key: "pending" for step in STEPS},
        )
        self.state.log("Empty project created; waiting for data import")
        save_project(self.state)
        self.accept()


class PublicExampleDialog(QDialog):
    def __init__(
        self,
        workspace: Path,
        parent: QWidget | None = None,
        language: str = "zh_CN",
    ):
        super().__init__(parent)
        self.workspace = workspace
        self.language = language
        self.example_key = PUBLIC_EXAMPLES[0].key
        english = language == "en_US"
        self.setWindowTitle(
            "Verified public projects" if english else "已验证公开数据项目"
        )
        self.resize(1060, 500)
        layout = QVBoxLayout(self)
        title = QLabel(
            "Two fixed, versioned validation projects"
            if english
            else "两套固定版本、已经过 NeuroEphys AI 验证的公开项目"
        )
        title.setStyleSheet("font-size: 21px; font-weight: 700;")
        layout.addWidget(title)
        summary = QLabel(
            (
                "These entries are not generic public-data importers. Each row locks "
                "the dataset identifier, local cache path, and expected content. "
                "Double-click a downloaded row to open it directly."
            )
            if english
            else (
                "这里不是泛泛的“公开数据”导入器。每一行都锁定数据编号、本地缓存路径"
                "和预期内容；已下载的数据可双击直接建立或打开验证项目。"
            )
        )
        summary.setWordWrap(True)
        summary.setObjectName("Muted")
        layout.addWidget(summary)
        self.table = QTableWidget(len(PUBLIC_EXAMPLES), 6)
        self.table.setHorizontalHeaderLabels(
            ["Project", "Official source", "Fixed identifier", "Contents", "Downloaded", "Project cache"]
            if english
            else ["验证项目", "官方来源", "固定编号", "实际内容", "数据已下载", "项目缓存"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        for row, example in enumerate(PUBLIC_EXAMPLES):
            status = public_example_status(workspace, example.key)
            values = [
                example.name_en if english else example.name_zh,
                example.source_en if english else example.source_zh,
                example.identifier,
                example.contents_en if english else example.contents_zh,
                (
                    "Yes"
                    if status["downloaded"] and english
                    else "是"
                    if status["downloaded"]
                    else "No"
                    if english
                    else "否"
                ),
                (
                    "Ready"
                    if status["project_ready"] and english
                    else "已建立"
                    if status["project_ready"]
                    else "Create on first open"
                    if english
                    else "首次打开时建立"
                ),
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.UserRole, example.key)
                self.table.setItem(row, column, cell)
        header = self.table.horizontalHeader()
        for column in range(6):
            header.setSectionResizeMode(
                column,
                QHeaderView.Stretch
                if column in {0, 2, 3}
                else QHeaderView.ResizeToContents,
            )
        self.table.selectRow(0)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self._accept())
        layout.addWidget(self.table, 1)
        local_path = QLabel(
            f"Local library: {public_validation_root(workspace)}"
            if english
            else f"本地公开数据资料库：{public_validation_root(workspace)}"
        )
        local_path.setWordWrap(True)
        local_path.setObjectName("InsetPanel")
        local_path.setContentsMargins(12, 9, 12, 9)
        layout.addWidget(local_path)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText(
            "Open selected project" if english else "打开所选验证项目"
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.example_key = str(self.table.item(row, 0).data(Qt.UserRole))
        self.accept()


class ImportDialog(QDialog):
    def __init__(
        self,
        workspace: Path,
        parent: QWidget | None = None,
        language: str = "zh_CN",
        project_root: Path | None = None,
        project_name: str | None = None,
        own_data_only: bool = False,
    ):
        super().__init__(parent)
        self.workspace = workspace
        self.language = language
        self.target_project_root = project_root
        self.state: ProjectState | None = None
        english = language == "en_US"
        self.setWindowTitle(
            "Import your electrophysiology data" if english else "导入自己的电生理数据"
        )
        self.resize(920, 720)
        layout = QVBoxLayout(self)
        title = QLabel(
            "Create a NeuroEphys AI project" if english else "建立 NeuroEphys AI 项目"
        )
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)
        subtitle = QLabel(
            "Source files remain read-only; the project stores parameters, derived data, and provenance."
            if english
            else "原始文件保持只读；项目只保存参数、中间结果与来源索引。"
        )
        subtitle.setObjectName("Muted")
        layout.addWidget(subtitle)

        source_form = QFormLayout()
        self.source_combo = QComboBox()
        self.source_combo.setToolTip(
            "Choose the adapter that matches the files you have."
            if english
            else "选择与你手头文件相匹配的读取适配器；不会修改源文件。"
        )
        self.import_formats = [
            item
            for item in SUPPORTED_FORMATS
            if not own_data_only
            or item.key in {"binary", "device", "kilosort", "nex5"}
        ]
        for item in self.import_formats:
            name = FORMAT_TEXT_EN[item.key][0] if english else item.name
            self.source_combo.addItem(name, item.key)
        source_form.addRow("Data source" if english else "数据来源", self.source_combo)
        self.project_name = QLineEdit(project_name or "NeuroEphys AI project")
        self.project_name.setReadOnly(project_root is not None)
        self.project_name.setToolTip(
            "Names the NeuroEphys AI project folder; source files are not renamed."
            if english
            else "用于 NeuroEphys AI 项目文件夹；不会重命名源文件。"
        )
        source_form.addRow("Project name" if english else "项目名称", self.project_name)
        layout.addLayout(source_form)

        self.source_explanation = QLabel()
        self.source_explanation.setObjectName("InsetPanel")
        self.source_explanation.setWordWrap(True)
        self.source_explanation.setContentsMargins(12, 9, 12, 9)
        layout.addWidget(self.source_explanation)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._simulation_page())
        self.pages.addWidget(self._binary_page())
        self.pages.addWidget(self._device_page())
        self.pages.addWidget(self._alf_page())
        self.pages.addWidget(self._kilosort_page())
        self.pages.addWidget(self._nex5_page())
        layout.addWidget(self.pages, 1)

        self.metadata_panel = self._metadata_and_behavior_panel()
        layout.addWidget(self.metadata_panel)
        self.source_combo.currentIndexChanged.connect(self._source_changed)
        self._source_changed(0)

        note = QLabel(
            (
                "Raw-voltage inputs can run the complete workflow including sorting. "
                "IBL/ALF and Kilosort/Phy imports begin downstream because they contain "
                "processed spikes rather than the original broadband voltage."
            )
            if english
            else (
                "带原始电压的数据可运行包含 sorting 的完整链路。IBL/ALF 与 "
                "Kilosort/Phy 与 NEX5 导入通常只有处理后的 spike，因此从下游阶段接入。"
            )
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText(
            "Create and open" if english else "创建并打开"
        )
        buttons.accepted.connect(self._create)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _metadata_and_behavior_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("InsetPanel")
        form = QFormLayout(panel)
        english = self.language == "en_US"

        heading = QLabel(
            "Recording metadata and behavior (optional)"
            if english
            else "记录元数据与行为（可选）"
        )
        heading.setStyleSheet("font-weight: 700;")
        form.addRow(heading)

        self.electrode_type_edit = QComboBox()
        self.electrode_type_edit.setEditable(True)
        self.electrode_type_edit.addItems(
            [
                "independent microwires",
                "tetrode array",
                "linear silicon probe",
                "Neuropixels",
                "custom extracellular probe",
            ]
        )
        self.electrode_type_edit.setCurrentText("custom extracellular probe")
        self.brain_region_edit = QLineEdit()
        self.brain_region_edit.setPlaceholderText(
            "Optional, e.g. OFC, hippocampus"
            if english
            else "可选，例如 OFC、海马"
        )
        self.geometry_mode_combo = QComboBox()
        geometry_options = [
            (
                "Independent contacts" if english else "独立 contact（不推断空间邻接）",
                "independent_contacts",
            ),
            (
                "Linear geometry" if english else "线性排列",
                "linear",
            ),
            (
                "Tetrode groups" if english else "Tetrode 分组",
                "tetrode_groups",
            ),
            (
                "Neuropixels geometry" if english else "Neuropixels 几何",
                "neuropixels",
            ),
            (
                "Unknown / provide later" if english else "未知／稍后补充",
                "unknown",
            ),
        ]
        for label, value in geometry_options:
            self.geometry_mode_combo.addItem(label, value)
        self.reference_edit = QLineEdit()
        self.reference_edit.setPlaceholderText(
            "Acquisition reference/ground; mark whether stored as channels"
            if english
            else "采集时的参考／地线，并注明是否保存为数据通道"
        )
        self.known_bad_channels_edit = QLineEdit()
        self.known_bad_channels_edit.setPlaceholderText(
            "Optional, e.g. 7,18 or CH7,CH18"
            if english
            else "可选，例如 7,18 或 CH7,CH18；无已知坏道时留空"
        )
        form.addRow(
            "Electrode/probe type" if english else "电极／探针类型",
            self.electrode_type_edit,
        )
        form.addRow(
            "Brain region" if english else "脑区",
            self.brain_region_edit,
        )
        form.addRow(
            "Contact geometry" if english else "contact 结构",
            self.geometry_mode_combo,
        )
        form.addRow(
            "Reference and ground" if english else "参考与地线",
            self.reference_edit,
        )
        form.addRow(
            "Known bad channels" if english else "预先已知坏道",
            self.known_bad_channels_edit,
        )

        self.behavior_format_combo = QComboBox()
        self.behavior_format_combo.addItem(
            "No behavior file" if english else "暂不导入行为文件",
            "none",
        )
        self.behavior_format_combo.addItem(
            "MED-PC C/D arrays" if english else "MED-PC C/D 数组",
            "medpc",
        )
        self.behavior_format_combo.addItem(
            "Generic event CSV" if english else "通用事件 CSV",
            "csv",
        )
        behavior_holder, self.import_behavior_path = self._path_row()
        ttl_holder, self.import_ttl_path = self._path_row()
        self.import_ttl_channel = QSpinBox()
        self.import_ttl_channel.setRange(0, 255)
        self.import_ttl_channel.setValue(0)
        self.import_sync_code = QSpinBox()
        self.import_sync_code.setRange(0, 9999)
        self.import_sync_code.setValue(11)
        self.import_behavior_path.setPlaceholderText(
            "MED-PC text or event CSV"
            if english
            else "选择 MED-PC 文本或事件 CSV"
        )
        self.import_ttl_path.setPlaceholderText(
            "Optional external TTL CSV; Open Ephys digital inputs need no file"
            if english
            else "可选外部 TTL CSV；Open Ephys 数字输入无需另选文件"
        )
        form.addRow(
            "Behavior format" if english else "行为文件格式",
            self.behavior_format_combo,
        )
        form.addRow(
            "Behavior file" if english else "行为文件",
            behavior_holder,
        )
        form.addRow(
            "External TTL file" if english else "外部 TTL 文件",
            ttl_holder,
        )
        form.addRow(
            "Recorded TTL channel" if english else "采集系统 TTL 通道",
            self.import_ttl_channel,
        )
        form.addRow(
            "Synchronization event code" if english else "行为同步事件码",
            self.import_sync_code,
        )
        explanation = QLabel(
            (
                "MED-PC import pairs C event codes with D times and aligns the selected "
                "synchronization code to one recorded digital input. Generic CSV import "
                "expects time_seconds and may use a separate TTL CSV. These settings are "
                "stored with the project and can be changed before re-running alignment."
            )
            if english
            else (
                "MED-PC 导入把 C 数组事件码与 D 数组时间配对，再把指定同步码与采集系统"
                "的一路数字输入对齐。通用 CSV 至少需要 time_seconds，可另选 TTL CSV。"
                "这些设置会保存到项目中，重新对齐前仍可修改。"
            )
        )
        explanation.setWordWrap(True)
        explanation.setObjectName("Muted")
        form.addRow(explanation)
        return panel

    def _source_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.import_formats):
            return
        item = self.import_formats[index]
        page_index = {
            "simulated": 0,
            "binary": 1,
            "device": 2,
            "ibl_alf": 3,
            "kilosort": 4,
            "nex5": 5,
        }[item.key]
        self.pages.setCurrentIndex(page_index)
        english = self.language == "en_US"
        raw_text = "includes raw voltage" if item.raw_signal else "processed data only"
        route_text = (
            "Complete route: import → QC → preprocessing → sorting → downstream analysis."
            if item.raw_signal
            else "Entry route: import → unit/behavior checks → downstream analysis."
        )
        if english:
            name, description = FORMAT_TEXT_EN[item.key]
            text = f"<b>{name}</b> · {raw_text}<br>{description}<br>{route_text}"
        else:
            raw_text = "包含原始电压" if item.raw_signal else "仅含处理后数据"
            route_text = (
                "可运行：导入 → 原始质控 → 预处理 → sorting → 下游分析。"
                if item.raw_signal
                else "接入位置：导入 → Unit/行为检查 → 下游分析。"
            )
            text = (
                f"<b>{item.name}</b> · {raw_text}<br>{item.description}<br>{route_text}"
            )
        self.source_explanation.setText(text)
        self.metadata_panel.setVisible(
            item.key in {"simulated", "binary", "device", "kilosort"}
        )

    @staticmethod
    def _identifier_list(text: str) -> list[str]:
        values: list[str] = []
        for token in text.replace("，", ",").split(","):
            normalized = token.strip()
            if normalized:
                values.append(normalized)
        return values

    def _apply_import_metadata_and_behavior(self, source_key: str) -> None:
        if self.state is None:
            return
        electrode_type = self.electrode_type_edit.currentText().strip() or "generic"
        probe = {
            "type": electrode_type,
            "contact_count": int(self.state.channel_count),
            "geometry_mode": str(self.geometry_mode_combo.currentData()),
            "brain_region": self.brain_region_edit.text().strip() or None,
            "reference_configuration": self.reference_edit.text().strip() or None,
            "known_hardware_bad_channels": self._identifier_list(
                self.known_bad_channels_edit.text()
            ),
        }
        self.state.electrode_type = electrode_type
        self.state.metadata["probe"] = probe
        self.state.metadata["import_configuration"] = {
            "source_kind": source_key,
            "channel_selection": (
                self.device_channels.text().strip()
                if source_key == "device"
                else None
            ),
            "probe": probe,
        }
        self.state.log(
            "Recording metadata saved: "
            f"probe={electrode_type}, geometry={probe['geometry_mode']}, "
            f"region={probe['brain_region'] or 'unspecified'}"
        )

        behavior_format = str(self.behavior_format_combo.currentData())
        behavior_text = self.import_behavior_path.text().strip()
        if behavior_format == "none" and not behavior_text:
            self.state.metadata["behavior_import_configuration"] = {
                "format": "none",
                "status": "not_configured",
            }
            return
        if behavior_format == "none":
            raise ValueError(
                "Select the behavior-file format or clear the behavior-file path"
            )
        behavior_path = Path(behavior_text)
        if not behavior_path.is_file():
            raise ValueError("The selected behavior file does not exist")
        if behavior_format == "medpc":
            import_medpc_behavior(
                self.state,
                behavior_path,
                ttl_channel=int(self.import_ttl_channel.value()),
                sync_event_code=int(self.import_sync_code.value()),
            )
            ttl_source = (
                f"recorded digital input {self.import_ttl_channel.value()}"
            )
        else:
            ttl_text = self.import_ttl_path.text().strip()
            ttl_path = Path(ttl_text) if ttl_text else None
            if ttl_path is not None and not ttl_path.is_file():
                raise ValueError("The selected external TTL file does not exist")
            import_behavior_events(
                self.state,
                behavior_path,
                ttl_path=ttl_path,
                time_unit="seconds",
            )
            ttl_source = str(ttl_path) if ttl_path else "shared behavior clock"
        self.state.metadata["behavior_import_configuration"] = {
            "format": behavior_format,
            "behavior_file": str(behavior_path),
            "ttl_source": ttl_source,
            "ttl_channel": (
                int(self.import_ttl_channel.value())
                if behavior_format == "medpc"
                else None
            ),
            "sync_event_code": (
                int(self.import_sync_code.value())
                if behavior_format == "medpc"
                else None
            ),
            "status": "imported",
        }

    def _simulation_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        english = self.language == "en_US"
        self.electrode_combo = QComboBox()
        for item in demo_profile_catalog():
            label = item["name"] if english else item["name_zh"]
            self.electrode_combo.addItem(label, item["key"])
        self.electrode_combo.currentIndexChanged.connect(
            self._simulation_profile_changed
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
        form.addRow(
            "Electrode geometry" if english else "电极结构", self.electrode_combo
        )
        form.addRow("Duration" if english else "模拟时长", self.sim_duration)
        form.addRow("Sampling rate" if english else "采样率", self.sim_rate)
        form.addRow("Channels" if english else "通道数", self.sim_channels)
        explanation = QLabel(
            (
                "Generate an int16 recording with event-locked units, broadband and "
                "50 Hz common noise, a bad channel, and transient artifacts. Ground truth "
                "is retained for quantitative sorter validation."
            )
            if english
            else (
                "生成包含事件锁定神经元、宽带噪声、50 Hz 共同噪声、坏通道和瞬时伪迹的 "
                "int16 原始记录，并保存 ground truth 用于定量验证 sorting。"
            )
        )
        explanation.setWordWrap(True)
        form.addRow(explanation)
        self._simulation_profile_changed(0)
        return page

    def _simulation_profile_changed(self, _index: int) -> None:
        profile = DEMO_PROFILES[self.electrode_combo.currentData()]
        self.sim_rate.setValue(int(profile["sampling_rate"]))
        self.sim_channels.setValue(int(profile["channel_count"]))

    def _path_row(self, directory: bool = False) -> tuple[QWidget, QLineEdit]:
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        line = QLineEdit()
        button = QPushButton("Browse…" if self.language == "en_US" else "浏览…")
        if directory:
            button.clicked.connect(
                lambda: line.setText(
                    QFileDialog.getExistingDirectory(
                        self,
                        "Select folder" if self.language == "en_US" else "选择文件夹",
                    )
                )
            )
        else:
            button.clicked.connect(
                lambda: line.setText(
                    QFileDialog.getOpenFileName(
                        self,
                        "Select file" if self.language == "en_US" else "选择文件",
                    )[0]
                )
            )
        row.addWidget(line, 1)
        row.addWidget(button)
        return holder, line

    def _binary_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        english = self.language == "en_US"
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
        self.copy_source = QCheckBox(
            "Copy source into project (default: read-only link)"
            if english
            else "复制原始文件到项目（默认只建立只读索引）"
        )
        self.binary_rate.setToolTip(
            "Required. Converts sample index to seconds."
            if english
            else "必填。用于把采样点换算为秒；填写错误会使所有时间结果失真。"
        )
        self.binary_channels.setToolTip(
            "Required. A wrong value reshapes an interleaved file incorrectly."
            if english
            else "必填。错误的通道数会错误重排交错二进制，常表现为重复或斜纹波形。"
        )
        self.binary_dtype.setToolTip(
            "Storage type of each sample, not the analysis precision."
            if english
            else "每个原始样本的存储类型，不是后续分析精度。"
        )
        self.binary_scale.setToolTip(
            "Microvolts represented by one stored integer step."
            if english
            else "一个整数步长所代表的微伏数；用于 ADC 值到电压的换算。"
        )
        form.addRow("Raw binary" if english else "原始二进制", holder)
        form.addRow(
            "Events CSV (optional)" if english else "事件 CSV（可选）", event_holder
        )
        form.addRow("Sampling rate" if english else "采样率", self.binary_rate)
        form.addRow("Channels" if english else "通道数", self.binary_channels)
        form.addRow("Data type" if english else "数据类型", self.binary_dtype)
        form.addRow("μV / bit", self.binary_scale)
        form.addRow(self.copy_source)
        binary_help = QLabel(
            (
                "<b>Expected layout</b>: time-major interleaved samples "
                "[sample0_ch0, sample0_ch1, …, sample1_ch0, …]. "
                "File size must be divisible by channels × bytes-per-sample.<br>"
                "<b>Optional events CSV</b>: must contain <code>time_seconds</code>; "
                "<code>trial</code> and <code>condition</code> are recommended."
            )
            if english
            else (
                "<b>文件结构</b>：按时间优先交错存储 "
                "[sample0_ch0, sample0_ch1, …, sample1_ch0, …]。文件大小必须能被"
                "“通道数 × 每样本字节数”整除。<br><b>可选事件 CSV</b>：必须包含 "
                "<code>time_seconds</code>，建议同时包含 <code>trial</code> 和 "
                "<code>condition</code>。"
            )
        )
        binary_help.setWordWrap(True)
        binary_help.setObjectName("Muted")
        form.addRow(binary_help)
        return page

    def _alf_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        english = self.language == "en_US"
        self.public_kind = QComboBox()
        self.public_kind.addItem(
            "IBL ALF session (spikes + trials)"
            if english
            else "IBL ALF 会话（spikes + trials）",
            "ibl_alf",
        )
        self.public_kind.addItem(
            "IBL BWM aggregate trials (behavior only)"
            if english
            else "IBL BWM 汇总 trials（仅行为）",
            "ibl_trials",
        )
        self.public_kind.addItem(
            "DANDI / Buzsáki NWB (Units + behavior)"
            if english
            else "DANDI / Buzsáki NWB（Units + 行为）",
            "nwb_units",
        )
        self.public_kind.currentIndexChanged.connect(self._public_kind_changed)
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        self.alf_path = QLineEdit()
        folder_button = QPushButton("ALF folder…" if english else "ALF 文件夹…")
        file_button = QPushButton("Aggregate .pqt…")
        nwb_button = QPushButton("NWB file…" if english else "NWB 文件…")
        folder_button.clicked.connect(
            lambda: self._choose_public_source("ibl_alf")
        )
        file_button.clicked.connect(
            lambda: self._choose_public_source("ibl_trials")
        )
        nwb_button.clicked.connect(lambda: self._choose_public_source("nwb_units"))
        row.addWidget(self.alf_path, 1)
        row.addWidget(folder_button)
        row.addWidget(file_button)
        row.addWidget(nwb_button)
        download_button = QPushButton(
            "Download official example" if english else "下载官方示例"
        )
        download_button.clicked.connect(self._download_ibl_aggregate)
        self.ibl_eid = QLineEdit()
        self.ibl_eid.setPlaceholderText(
            "Leave blank to select a BWM session automatically"
            if english
            else "留空时自动选择一个 BWM session"
        )
        form.addRow(
            "Public-data structure" if english else "公开数据结构",
            self.public_kind,
        )
        form.addRow("Data path" if english else "数据路径", holder)
        form.addRow(
            "Session eID (optional for aggregate)"
            if english
            else "Session eID（aggregate 可选）",
            self.ibl_eid,
        )
        form.addRow(download_button)
        text = QLabel(
            (
                "<b>IBL ALF</b> reads trials plus spikes.times/spikes.clusters. "
                "<b>BWM aggregate</b> contains behavior only. "
                "<b>DANDI/NWB</b> reads a Units table and available reward, position, "
                "state, or ripple objects. These processed entries start after sorting; "
                "use acquisition-system NWB when raw ElectricalSeries must be sorted."
            )
            if english
            else (
                "<b>IBL ALF</b> 读取 trials 与 spikes.times/spikes.clusters；"
                "<b>BWM aggregate</b> 只有行为汇总；<b>DANDI/NWB</b> 读取 Units 表，"
                "并接入可用的奖励、位置、状态或 ripple 对象。它们是处理后入口，从 "
                "sorting 之后继续；若 NWB 内含待排序的原始 ElectricalSeries，应从"
                "“记录系统文件”入口导入。"
            )
        )
        text.setWordWrap(True)
        form.addRow(text)
        self._public_kind_changed(0)
        return page

    def _public_kind_changed(self, _index: int) -> None:
        kind = self.public_kind.currentData()
        placeholders = {
            "ibl_alf": "Select an IBL ALF session/probe folder"
            if self.language == "en_US"
            else "选择包含 trials 和 probe/spikes 的 IBL ALF 文件夹",
            "ibl_trials": "Select aggregate_trials.pqt"
            if self.language == "en_US"
            else "选择 IBL BWM aggregate_trials.pqt",
            "nwb_units": "Select a .nwb file containing a Units table"
            if self.language == "en_US"
            else "选择包含 Units 表的 .nwb 文件",
        }
        self.alf_path.setPlaceholderText(placeholders[str(kind)])
        self.ibl_eid.setEnabled(kind == "ibl_trials")

    def _choose_public_source(self, kind: str) -> None:
        index = self.public_kind.findData(kind)
        if index >= 0:
            self.public_kind.setCurrentIndex(index)
        if kind == "ibl_alf":
            selected = QFileDialog.getExistingDirectory(
                self, "选择 IBL ALF 文件夹"
            )
        elif kind == "ibl_trials":
            selected = QFileDialog.getOpenFileName(
                self,
                "选择 IBL trials aggregate",
                filter="Parquet (*.pqt *.parquet)",
            )[0]
        else:
            selected = QFileDialog.getOpenFileName(
                self,
                "选择含 Units 与行为的 NWB",
                filter="Neurodata Without Borders (*.nwb)",
            )[0]
        if selected:
            self.alf_path.setText(selected)

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
        english = self.language == "en_US"
        self.device_combo = QComboBox()
        self.device_combo.addItems(DEVICE_READERS)
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        self.device_path = QLineEdit()
        file_button = QPushButton("File…" if english else "文件…")
        folder_button = QPushButton("Folder…" if english else "文件夹…")
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
        self.device_channels = QLineEdit()
        self.device_channels.setPlaceholderText(
            "Optional, e.g. 1-32 or 1-16,25,27"
            if english
            else "可选，例如 1-32 或 1-16,25,27"
        )
        self.device_channels.setToolTip(
            "Link only the selected acquisition channels. Leave empty to import all."
            if english
            else "只链接所选采集通道；留空则导入全部通道。"
        )
        form.addRow(
            "Channels (optional)" if english else "通道范围（可选）",
            self.device_channels,
        )
        self.stream_id.setPlaceholderText(
            "For multi-stream recordings, e.g. imec0.ap"
            if english
            else "多流记录时填写，例如 imec0.ap"
        )
        form.addRow("Acquisition system" if english else "记录系统", self.device_combo)
        form.addRow("File or folder" if english else "文件或文件夹", holder)
        form.addRow(
            "Stream ID (optional)" if english else "Stream ID（可选）", self.stream_id
        )
        text = QLabel(
            (
                "NeuroEphys AI uses SpikeInterface extractors and creates a normalized "
                "interleaved int16 cache. Source files are never modified."
            )
            if english
            else (
                "NeuroEphys AI 使用 SpikeInterface 的官方 extractor 读取源格式，并在项目缓存中"
                "生成统一的 int16 交错二进制；源文件不会被修改。"
            )
        )
        text.setWordWrap(True)
        form.addRow(text)
        return page

    def _kilosort_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        english = self.language == "en_US"
        holder, self.ks_path = self._path_row(directory=True)
        self.ks_rate = QSpinBox()
        self.ks_rate.setRange(1000, 100_000)
        self.ks_rate.setValue(30_000)
        form.addRow("Kilosort/Phy folder" if english else "Kilosort/Phy 文件夹", holder)
        form.addRow(
            "Original sampling rate" if english else "原记录采样率", self.ks_rate
        )
        text = QLabel(
            "Requires spike_times.npy and spike_clusters.npy or spike_templates.npy."
            if english
            else "要求至少包含 spike_times.npy 和 spike_clusters.npy 或 spike_templates.npy。"
        )
        text.setWordWrap(True)
        form.addRow(text)
        return page

    def _nex5_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        english = self.language == "en_US"
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        self.nex5_path = QLineEdit()
        nex5_file_button = QPushButton("NEX5 file…" if english else "NEX5 文件…")
        nex5_folder_button = QPushButton(
            "Folder…" if english else "包含 NEX5 的文件夹…"
        )
        nex5_file_button.clicked.connect(
            lambda: self.nex5_path.setText(
                QFileDialog.getOpenFileName(
                    self,
                    "Select NeuroExplorer file"
                    if english
                    else "选择 NeuroExplorer 文件",
                    filter="NeuroExplorer 5 (*.nex5)",
                )[0]
            )
        )
        nex5_folder_button.clicked.connect(
            lambda: self.nex5_path.setText(
                QFileDialog.getExistingDirectory(
                    self,
                    "Select NEX5 folder" if english else "选择 NEX5 文件夹",
                )
            )
        )
        row.addWidget(self.nex5_path, 1)
        row.addWidget(nex5_file_button)
        row.addWidget(nex5_folder_button)
        self.nex5_filter = QLineEdit()
        self.nex5_filter.setPlaceholderText(
            "Optional, e.g. SW#1"
            if english
            else "可选，例如 SW#1；仅导入文件名包含该文本的结果"
        )
        self.nex5_sorter_key = QLineEdit("offline_sorter_nex5")
        self.nex5_alignment = QComboBox()
        self.nex5_alignment.addItem(
            "Align file end to the current recording"
            if english
            else "自动：把 NEX5 结束时间对齐到当前记录结束时间",
            "auto_project_duration",
        )
        self.nex5_alignment.addItem(
            "Keep source timestamps" if english else "保留 NEX5 原始时间",
            "preserve",
        )
        self.nex5_alignment.addItem(
            "Subtract a manual offset" if english else "手动减去固定时间偏移",
            "manual",
        )
        self.nex5_manual_offset = QDoubleSpinBox()
        self.nex5_manual_offset.setRange(-1_000_000, 1_000_000)
        self.nex5_manual_offset.setDecimals(6)
        self.nex5_manual_offset.setSuffix(" s")
        self.nex5_manual_offset.setValue(0.0)
        self.nex5_preview = QLabel(
            "The source is inspected when the project is created."
            if english
            else "创建前会检查文件数、unit 名称、记录时长和波形变量。"
        )
        self.nex5_preview.setWordWrap(True)
        self.nex5_preview.setObjectName("Muted")
        form.addRow("NEX5 source" if english else "NEX5 来源", holder)
        form.addRow(
            "Filename filter" if english else "文件名筛选",
            self.nex5_filter,
        )
        form.addRow(
            "Result key" if english else "结果名称",
            self.nex5_sorter_key,
        )
        form.addRow(
            "Time alignment" if english else "时间对齐方式",
            self.nex5_alignment,
        )
        form.addRow(
            "Manual offset" if english else "手动时间偏移",
            self.nex5_manual_offset,
        )
        form.addRow(self.nex5_preview)
        explanation = QLabel(
            (
                "NeuroEphys AI reads candidate units and waveform summaries through "
                "the official nex5file Python package. Original files remain read-only. "
                "When added to an existing raw project, the result appears beside "
                "Kilosort and other sorters for Unit QC and manual curation. The imported "
                "result is a comparison reference, not ground truth."
            )
            if english
            else (
                "NeuroEphys AI 通过 NeuroExplorer 官方 nex5file Python 包读取候选 unit、"
                "spike 时间和波形摘要，源文件保持只读。导入已有原始记录项目后，该结果"
                "会与 Kilosort 等结果并列进入 Unit 质控、人工复核和一致性比较。外部"
                "结果属于对照参考，不能自动当作 ground truth。"
            )
        )
        explanation.setWordWrap(True)
        form.addRow(explanation)
        return page

    def _project_root(self) -> Path:
        if self.target_project_root is not None:
            return self.target_project_root
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", self.project_name.text()).strip("_")
        slug = slug or "project"
        stamp = datetime.now(timezone.utc).astimezone()
        return self.workspace / "projects" / f"{slug}_{stamp:%Y%m%d_%H%M%S}"

    def _create(self) -> None:
        try:
            key = self.source_combo.currentData()
            root = self._project_root()
            if key == "simulated":
                self.state = generate_demo_recording(
                    root,
                    duration_seconds=float(self.sim_duration.value()),
                    channel_count=int(self.sim_channels.value()),
                    sampling_rate=float(self.sim_rate.value()),
                    profile_key=str(self.electrode_combo.currentData()),
                )
            elif key == "binary":
                source = Path(self.binary_path.text())
                if not source.is_file():
                    raise ValueError("请选择有效的原始二进制文件")
                events = (
                    Path(self.events_path.text()) if self.events_path.text() else None
                )
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
                    self.device_channels.text().strip() or None,
                )
            elif key == "ibl_alf":
                source = Path(self.alf_path.text())
                public_kind = self.public_kind.currentData()
                if public_kind == "ibl_alf" and source.is_dir():
                    self.state = import_ibl_alf(root, source)
                elif (
                    public_kind == "ibl_trials"
                    and source.is_file()
                    and source.suffix.lower() in {".pqt", ".parquet"}
                ):
                    self.state = import_ibl_trials_aggregate(
                        root, source, self.ibl_eid.text().strip() or None
                    )
                elif (
                    public_kind == "nwb_units"
                    and source.is_file()
                    and source.suffix.lower() == ".nwb"
                ):
                    self.state = import_nwb_units(root, source)
                else:
                    raise ValueError(
                        "所选文件与公开数据结构不匹配：请按上方类型选择 "
                        "ALF 文件夹、aggregate .pqt 或含 Units 的 .nwb"
                    )
            elif key == "kilosort":
                source = Path(self.ks_path.text())
                if not source.is_dir():
                    raise ValueError("请选择有效的 Kilosort/Phy 文件夹")
                manifest = root / MANIFEST_NAME
                if self.target_project_root is not None and manifest.exists():
                    self.state = load_project(manifest)
                    attach_kilosort_results(
                        self.state,
                        source,
                        float(self.ks_rate.value()),
                    )
                else:
                    self.state = import_kilosort_results(
                        root, source, float(self.ks_rate.value())
                    )
            else:
                source = Path(self.nex5_path.text())
                filename_filter = self.nex5_filter.text().strip() or None
                preview = inspect_nex5_source(
                    source,
                    filename_filter=filename_filter,
                )
                manifest = root / MANIFEST_NAME
                if self.target_project_root is not None and manifest.exists():
                    self.state = load_project(manifest)
                else:
                    first_file = preview["files"][0]
                    self.state = ProjectState(
                        root=root,
                        name=self.project_name.text().strip()
                        or "Imported NEX5 sorting",
                        source_type="nex5_output",
                        source_path=source,
                        sampling_rate=float(
                            first_file["timestamp_frequency_hz"]
                        ),
                        duration_seconds=max(
                            float(item["end_seconds"])
                            for item in preview["files"]
                        ),
                        metadata={
                            "raw_signal_available": False,
                            "data_imported": True,
                        },
                    )
                sorter_key = (
                    self.nex5_sorter_key.text().strip()
                    or "offline_sorter_nex5"
                )
                import_nex5_sorting_into_project(
                    self.state,
                    source,
                    sorter_key=sorter_key,
                    filename_filter=filename_filter,
                    alignment_mode=str(self.nex5_alignment.currentData()),
                    manual_offset_seconds=float(
                        self.nex5_manual_offset.value()
                    ),
                )
            self.state.name = self.project_name.text().strip() or self.state.name
            if key in {"simulated", "binary", "device", "kilosort"}:
                self._apply_import_metadata_and_behavior(str(key))
            save_project(self.state)
            self.accept()
        except Exception as exc:  # noqa: BLE001 - UI boundary reports adapter errors
            QMessageBox.warning(self, "无法创建项目", str(exc))


class TutorialDialog(QDialog):
    def __init__(
        self,
        initial_key: str = "import",
        parent: QWidget | None = None,
        language: str = "zh_CN",
    ):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(tr("tutorial", language))
        self.resize(1280, 820)
        layout = QHBoxLayout(self)
        self.list = QListWidget()
        self.list.setFixedWidth(360)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.document().setDefaultStyleSheet(
            """
            body { color: #17211e; font-family: "Microsoft YaHei", "Segoe UI";
                   font-size: 14px; line-height: 1.65; }
            h1 { font-size: 27px; margin: 0 0 12px 0; }
            h2 { font-size: 19px; margin: 24px 0 8px 0; color: #185f4d; }
            h3 { font-size: 16px; margin: 14px 0 5px 0; }
            p { margin: 6px 0 10px 0; }
            table { border-collapse: collapse; width: 100%; margin: 8px 0 14px 0; }
            th { background: #edf3f0; text-align: left; }
            th, td { border: 1px solid #cfd9d4; padding: 8px; vertical-align: top; }
            .intro { background: #f1f6f4; border-left: 4px solid #1f7a63;
                     padding: 12px 14px; }
            .warning { background: #fff7ed; border-left: 4px solid #c06b34;
                       padding: 10px 14px; }
            .next { background: #eef5ff; border-left: 4px solid #4a77a8;
                    padding: 10px 14px; }
            code { background: #f1f3f2; padding: 1px 4px; }
            """
        )
        layout.addWidget(self.list)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.browser, 1)
        full_manual = QPushButton(
            "在浏览器打开详细操作手册"
            if language == "zh_CN"
            else "Open the detailed operation manual"
        )
        full_manual.clicked.connect(self._open_full_manual)
        right_layout.addWidget(full_manual)
        layout.addWidget(right, 1)
        for chapter in TUTORIALS:
            title = tutorial_value(chapter, "title", language)
            self.list.addItem(title)
            self.list.item(self.list.count() - 1).setToolTip(title)
        self.list.currentRowChanged.connect(self._show)
        index = next(
            (
                index
                for index, item in enumerate(TUTORIALS)
                if item["key"] == initial_key
            ),
            0,
        )
        self.list.setCurrentRow(index)

    def _show(self, index: int) -> None:
        if index < 0:
            return
        item = TUTORIALS[index]
        detail = TUTORIAL_DETAILS[item["key"]]
        english = self.language == "en_US"
        controls = page_controls(item["key"], self.language)
        operations = localized_rows(detail, "operations", self.language)
        parameters = localized_rows(detail, "parameters", self.language)
        recommended = localized(detail, "recommended", self.language)
        pitfalls = localized(detail, "pitfalls", self.language)
        controls_html = "".join(
            (
                "<tr>"
                f"<td><b>{escape(name)}</b></td>"
                f"<td>{escape(description)}</td>"
                "</tr>"
            )
            for name, description in controls
        )
        operations_html = "".join(
            (
                "<tr>"
                f"<td><b>{escape(row['name'])}</b></td>"
                f"<td>{escape(row['action'])}</td>"
                f"<td>{escape(row['purpose'])}</td>"
                f"<td>{escape(row['result'])}</td>"
                "</tr>"
            )
            for row in operations
        )
        parameters_html = "".join(
            (
                "<tr>"
                f"<td><b><code>{escape(row['name'])}</code></b></td>"
                f"<td>{escape(row['meaning'])}</td>"
                f"<td>{escape(row['default'])}</td>"
                f"<td>{escape(row['recommended'])}</td>"
                f"<td>{escape(row['effect'])}</td>"
                "</tr>"
            )
            for row in parameters
        )
        recommended_html = "".join(
            f"<li>{escape(text)}</li>" for text in recommended
        )
        pitfalls_html = "".join(
            f"<li>{escape(text)}</li>" for text in pitfalls
        )
        references_html = "".join(
            f"<li><a href='{escape(reference['url'])}'>{escape(reference['name'])}</a></li>"
            for reference in REFERENCES
        )
        headings = (
            {
                "problem": "What this stage is solving",
                "before": "Before you begin",
                "operations": "Operations: what to do and why",
                "op_headers": ("Operation", "What you do", "Purpose", "Result"),
                "parameters": "Parameter reference",
                "param_headers": (
                    "Parameter",
                    "Meaning",
                    "Default",
                    "Recommendation",
                    "Effect of changing it",
                ),
                "controls": "Every control on this page",
                "recommended": "Recommended path",
                "pitfalls": "Common mistakes",
                "io": "Inputs and outputs",
                "checks": "Acceptance checks",
                "sources": "Methods and sources",
                "next": "What happens next",
            }
            if english
            else {
                "problem": "这一阶段在解决什么问题",
                "before": "开始前要准备什么",
                "operations": "可以做哪些操作，为什么这样做",
                "op_headers": ("操作", "你要做什么", "目的", "运行后得到什么"),
                "parameters": "参数逐项说明",
                "param_headers": (
                    "参数",
                    "含义",
                    "默认值",
                    "推荐设置",
                    "改变参数会发生什么",
                ),
                "controls": "本页每个控件的作用",
                "recommended": "推荐操作顺序",
                "pitfalls": "常见错误",
                "io": "输入与输出",
                "checks": "完成本阶段前必须检查",
                "sources": "方法与资料来源",
                "next": "下一步",
            }
        )
        op_headers = "".join(f"<th>{text}</th>" for text in headings["op_headers"])
        param_headers = "".join(
            f"<th>{text}</th>" for text in headings["param_headers"]
        )
        self.browser.setHtml(
            f"<h1>{tutorial_value(item, 'title', self.language)}</h1>"
            f"<h2>{headings['problem']}</h2>"
            f"<div class='intro'>{escape(localized(detail, 'narrative', self.language))}</div>"
            f"<h2>{headings['before']}</h2>"
            f"<p>{escape(localized(detail, 'before', self.language))}</p>"
            f"<h2>{headings['operations']}</h2>"
            f"<table><thead><tr>{op_headers}</tr></thead><tbody>{operations_html}</tbody></table>"
            f"<h2>{headings['parameters']}</h2>"
            f"<table><thead><tr>{param_headers}</tr></thead><tbody>{parameters_html}</tbody></table>"
            f"<h2>{headings['controls']}</h2>"
            f"<table><tbody>{controls_html}</tbody></table>"
            f"<h2>{headings['recommended']}</h2><ol>{recommended_html}</ol>"
            f"<h2>{headings['pitfalls']}</h2><div class='warning'><ul>{pitfalls_html}</ul></div>"
            f"<h2>{headings['io']}</h2>"
            f"<p><b>{'Input' if english else '输入'}：</b>"
            f"{escape(tutorial_value(item, 'input', self.language))}</p>"
            f"<p><b>{'Output' if english else '输出'}：</b>"
            f"{escape(tutorial_value(item, 'output', self.language))}</p>"
            f"<h2>{headings['checks']}</h2>"
            f"<p>{escape(tutorial_value(item, 'checks', self.language))}</p>"
            f"<h2>{headings['sources']}</h2>"
            f"<p>{escape(item['reference'])}</p>"
            f"<ul>{references_html}</ul>"
            f"<h2>{headings['next']}</h2>"
            f"<div class='next'>{escape(localized(detail, 'next', self.language))}</div>"
        )
        self.browser.verticalScrollBar().setValue(0)

    def _open_full_manual(self) -> None:
        manual = _documentation_page(self.language, "workflow.html")
        if manual.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(manual)))


class BehaviorSyncDialog(QDialog):
    def __init__(
        self,
        state: ProjectState,
        parent: QWidget | None = None,
        language: str = "zh_CN",
    ):
        super().__init__(parent)
        self.state = state
        self.language = language
        self.result: dict | None = None
        english = language == "en_US"
        self.setWindowTitle(
            "Import behavior and synchronization events"
            if english
            else "导入行为与同步事件"
        )
        self.resize(780, 520)
        layout = QVBoxLayout(self)
        title = QLabel(
            "Behavior clock → electrophysiology clock"
            if english
            else "行为设备时钟 → 电生理时钟"
        )
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)
        intro = QLabel(
            (
                "The behavior file describes trials and event times. The optional TTL "
                "file contains matching pulse times recorded by the electrophysiology "
                "system. NeuroEphys AI fits a linear clock map and reports residuals."
            )
            if english
            else (
                "行为文件描述 trial、条件和行为设备时间；可选 TTL 文件提供电生理系统"
                "记录到的一一对应脉冲。NeuroEphys AI 会拟合线性时钟映射并报告残差。"
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.behavior_format = QComboBox()
        self.behavior_format.addItem(
            "CSV event table" if english else "CSV 事件表",
            "csv",
        )
        self.behavior_format.addItem(
            "MED-PC text export" if english else "MED-PC 文本导出",
            "medpc",
        )
        self.ttl_channel = QSpinBox()
        self.ttl_channel.setRange(0, 255)
        self.ttl_channel.setValue(
            int(state.metadata.get("synchronization", {}).get("ttl_channel", 0))
        )
        self.sync_event_code = QSpinBox()
        self.sync_event_code.setRange(0, 9999)
        self.sync_event_code.setValue(11)
        self.behavior_path = QLineEdit(
            str(state.metadata.get("behavior_source", ""))
        )
        behavior_holder = QWidget()
        behavior_row = QHBoxLayout(behavior_holder)
        behavior_row.setContentsMargins(0, 0, 0, 0)
        behavior_button = QPushButton("Browse…" if english else "浏览…")
        behavior_button.clicked.connect(
            lambda: self.behavior_path.setText(
                QFileDialog.getOpenFileName(
                    self,
                    "Behavior CSV" if english else "选择行为事件 CSV",
                    filter="Behavior files (*.csv *.txt);;All files (*.*)",
                )[0]
            )
        )
        behavior_row.addWidget(self.behavior_path, 1)
        behavior_row.addWidget(behavior_button)
        self.ttl_path = QLineEdit(str(state.metadata.get("ttl_source", "")))
        ttl_holder = QWidget()
        ttl_row = QHBoxLayout(ttl_holder)
        ttl_row.setContentsMargins(0, 0, 0, 0)
        ttl_button = QPushButton("Browse…" if english else "浏览…")
        ttl_button.clicked.connect(
            lambda: self.ttl_path.setText(
                QFileDialog.getOpenFileName(
                    self,
                    "TTL CSV" if english else "选择 TTL CSV",
                    filter="CSV (*.csv)",
                )[0]
            )
        )
        ttl_row.addWidget(self.ttl_path, 1)
        ttl_row.addWidget(ttl_button)
        self.time_unit = QComboBox()
        for label, value in (
            ("Seconds / 秒", "seconds"),
            ("Milliseconds / 毫秒", "milliseconds"),
            ("Sample indices / 采样点", "samples"),
        ):
            self.time_unit.addItem(label, value)
        form.addRow("Behavior CSV" if english else "行为事件 CSV", behavior_holder)
        form.addRow(
            "TTL CSV (optional)" if english else "TTL CSV（可选）",
            ttl_holder,
        )
        form.addRow("Input time unit" if english else "输入时间单位", self.time_unit)
        form.addRow(
            "Behavior format" if english else "行为文件格式",
            self.behavior_format,
        )
        form.addRow(
            "Open Ephys TTL channel" if english else "Open Ephys TTL 通道",
            self.ttl_channel,
        )
        form.addRow(
            "MED-PC synchronization code" if english else "MED-PC 同步事件码",
            self.sync_event_code,
        )
        layout.addLayout(form)

        schema = QLabel(
            (
                "<b>Behavior CSV</b>: required time column "
                "<code>behavior_time_seconds</code> or <code>time_seconds</code>; "
                "recommended <code>trial</code>, <code>condition</code>, "
                "<code>event_type</code>, <code>reaction_time</code>.<br><br>"
                "<b>TTL CSV</b>: one row per matching pulse with "
                "<code>ttl_time_seconds</code> or <code>time_seconds</code>. Rows are "
                "paired in order. If no TTL file is supplied, behavior times are "
                "treated as already sharing the electrophysiology clock."
            )
            if english
            else (
                "<b>行为 CSV</b>：时间列使用 <code>behavior_time_seconds</code> 或 "
                "<code>time_seconds</code>；建议包含 <code>trial</code>、"
                "<code>condition</code>、<code>event_type</code> 和 "
                "<code>reaction_time</code>。<br><br><b>TTL CSV</b>：每个匹配脉冲"
                "一行，时间列使用 <code>ttl_time_seconds</code> 或 "
                "<code>time_seconds</code>，按行顺序配对。未提供 TTL 时，系统会把"
                "行为时间视为已经处在电生理时钟中。"
            )
        )
        schema.setWordWrap(True)
        schema.setObjectName("InsetPanel")
        schema.setContentsMargins(12, 10, 12, 10)
        layout.addWidget(schema)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText(
            "Import and align" if english else "导入并对齐"
        )
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self) -> None:
        try:
            behavior = Path(self.behavior_path.text())
            if not behavior.is_file():
                raise ValueError(
                    "Select a valid behavior CSV"
                    if self.language == "en_US"
                    else "请选择有效的行为事件 CSV"
                )
            ttl = Path(self.ttl_path.text()) if self.ttl_path.text() else None
            if ttl and not ttl.is_file():
                raise ValueError(
                    "Select a valid TTL CSV"
                    if self.language == "en_US"
                    else "请选择有效的 TTL CSV"
                )
            if self.behavior_format.currentData() == "medpc":
                self.result = import_medpc_behavior(
                    self.state,
                    behavior,
                    ttl_channel=int(self.ttl_channel.value()),
                    sync_event_code=int(self.sync_event_code.value()),
                )
            else:
                self.result = import_behavior_events(
                    self.state,
                    behavior,
                    ttl,
                    str(self.time_unit.currentData()),
                )
            save_project(self.state)
            self.accept()
        except Exception as exc:  # noqa: BLE001 - validation is shown to the user
            QMessageBox.warning(
                self,
                "Import failed" if self.language == "en_US" else "导入失败",
                str(exc),
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
        sorter_settings: dict,
        model_name: str,
        analysis_selection: str = "",
        tool_arguments: dict | None = None,
    ):
        super().__init__()
        self.state = state
        self.keys = keys
        self.sorter_name = sorter_name
        self.sorter_settings = sorter_settings
        self.model_name = model_name
        self.analysis_selection = analysis_selection
        self.tool_arguments = dict(tool_arguments or {})
        self.language = str(state.metadata.get("language", "zh_CN"))

    def _message(self, zh: str, en: str) -> str:
        return en if self.language == "en_US" else zh

    def _emit(self, key: str, value: object, message: str) -> None:
        self.progress.emit(message)
        self.step_done.emit(key, value)

    def _skip(self, key: str, reason_zh: str, reason_en: str) -> None:
        reason = self._message(reason_zh, reason_en)
        self._emit(
            key,
            {"skipped": True, "reason": reason},
            self._message(f"{key} 已跳过：{reason}", f"{key} skipped: {reason}"),
        )

    def _audit_context(self, key: str) -> dict:
        adapter = self.state.metadata.get("recording_adapter", {})
        input_files: list[str | Path] = []
        if self.state.recording_path:
            input_files.append(self.state.recording_path)
        behavior = self.state.metadata.get("behavior_import_configuration", {})
        for name in ("behavior_path", "ttl_path"):
            value = behavior.get(name)
            if value:
                input_files.append(value)
        channels = (
            adapter.get("selected_channel_ids")
            or adapter.get("selected_channels")
            or self.state.metadata.get("validation_case", {}).get("selected_channels")
            or f"all {self.state.channel_count} imported channels"
        )
        start_frame = int(adapter.get("start_frame", 0) or 0)
        end_frame = int(
            adapter.get(
                "end_frame",
                start_frame
                + round(self.state.duration_seconds * self.state.sampling_rate),
            )
            or 0
        )
        segment = {
            "start_seconds": start_frame / max(self.state.sampling_rate, 1.0),
            "end_seconds": end_frame / max(self.state.sampling_rate, 1.0),
            "duration_seconds": self.state.duration_seconds,
        }
        tool = {
            "import": "NeuroEphys AI project inventory",
            "qc": "NeuroEphys AI raw QC",
            "preprocess": "NeuroEphys AI preprocessing preview",
            "sorting": self.sorter_name,
            "unit_qc": "SpikeInterface-compatible Unit QC",
            "sync": "NeuroEphys AI synchronization",
            "behavior": "NeuroEphys AI behavior summary",
            "analysis": "Elephant/NeuroEphys AI analysis adapters",
            "statistics": "SciPy/statsmodels statistical suite",
            "decoding": "scikit-learn decoding suite",
            "export": "NeuroEphys AI reproducible export",
        }.get(key, PRODUCT_NAME)
        parameters: dict = {}
        if key == "sorting":
            parameters = dict(self.sorter_settings)
        elif key == "analysis":
            parameters = {"selection": self.analysis_selection or "full"}
            parameters.update(self.tool_arguments)
        elif key == "decoding":
            parameters = {
                "selection": self.model_name,
                **self.tool_arguments,
            }
        expected_outputs: list[Path] = [self.state.root / MANIFEST_NAME]
        if key == "sorting":
            expected_outputs.append(self.state.root / "results" / self.sorter_name)
        elif key == "export":
            expected_outputs.append(self.state.root / "exports")
        return {
            "input_files": input_files,
            "channel_selection": channels,
            "segment": segment,
            "tool": tool,
            "parameters": parameters,
            "expected_outputs": expected_outputs,
            "recovery": self._message(
                "重新打开项目后，从失败或未完成节点继续；已完成结果保留。",
                "Reopen the project and resume at the failed or incomplete stage; "
                "completed results are retained.",
            ),
        }

    def _execute_stage(self, key: str) -> None:
        if key == "import":
            self._emit(
                key,
                self.state,
                self._message(
                    "项目来源、格式与事件清单已确认",
                    "Project source, format, and event inventory confirmed",
                ),
            )
        elif key == "qc":
            if self.state.ready:
                self._emit(
                    key,
                    run_raw_qc(
                        self.state,
                        seconds=float(
                            self.tool_arguments.get("preview_seconds", 8.0)
                        ),
                    ),
                    self._message("原始质控完成", "Raw QC completed"),
                )
            else:
                self._skip(
                    key,
                    "当前项目只有处理后数据，没有原始电压",
                    "the project contains processed data but no raw voltage",
                )
        elif key == "preprocess":
            if self.state.ready:
                preview = preprocessing_preview(
                    self.state,
                    duration_seconds=float(
                        self.tool_arguments.get("preview_seconds", 2.0)
                    ),
                    highpass_hz=float(
                        self.tool_arguments.get("highpass_hz", 300.0)
                    ),
                    lowpass_hz=(
                        float(self.tool_arguments["lowpass_hz"])
                        if self.tool_arguments.get("lowpass_hz") is not None
                        else None
                    ),
                    reference=str(
                        self.tool_arguments.get(
                            "reference",
                            "common_median",
                        )
                    ),
                )
                self.state.preprocessing = preview
                self._emit(
                    key,
                    preview,
                    self._message("预处理预览完成", "Preprocessing preview completed"),
                )
            else:
                self._skip(
                    key,
                    "当前项目没有原始电压",
                    "the project has no raw voltage",
                )
        elif key == "sorting":
            if self.state.ready:
                value = run_sorter(
                    self.state,
                    self.sorter_name,
                    self.state.root / "results" / self.sorter_name,
                    self.progress.emit,
                    settings=self.sorter_settings,
                )
                self._emit(
                    key,
                    value,
                    self._message(
                        f"{self.sorter_name} sorting 完成",
                        f"{self.sorter_name} sorting completed",
                    ),
                )
            elif self.state.sorted_spikes:
                self._skip(
                    key,
                    "已导入外部 sorting 结果",
                    "external sorting results are already imported",
                )
            else:
                raise RuntimeError(
                    self._message(
                        "没有可用于 sorting 的原始记录",
                        "No raw recording is available for sorting",
                    )
                )
        elif key == "unit_qc":
            self._emit(
                key,
                compute_unit_metrics(self.state),
                self._message("Unit 质控完成", "Unit QC completed"),
            )
        elif key == "sync":
            if not self.state.events:
                raise RuntimeError(
                    self._message(
                        "事件相关分析需要事件时间；请导入 events.csv 或 ALF trials",
                        "Event analysis requires timestamps; import events.csv or "
                        "ALF trials",
                    )
                )
            synchronized = synchronize_existing_events(self.state)
            self._emit(
                key,
                synchronized,
                self._message(
                    "行为时钟与电生理时间轴已对齐",
                    "Behavior and electrophysiology clocks aligned",
                ),
            )
        elif key == "behavior":
            self.state.metadata["behavior_analysis"] = {
                "status": "completed",
                "event_count": len(self.state.events),
                "trial_count": len(self.state.trials),
                "trial_definition": self.state.metadata.get(
                    "trial_definition",
                    {
                        "status": (
                            "defined" if self.state.trials else "not_defined"
                        )
                    },
                ),
            }
            self._emit(
                key,
                self.state.metadata["behavior_analysis"],
                self._message("行为摘要已生成", "Behavior summary generated"),
            )
        elif key == "analysis":
            selection = self.analysis_selection
            if len(self.keys) > 1 or not selection:
                value = run_neural_toolkit(self.state)
            elif selection.startswith("event:"):
                if self.tool_arguments.get("event_codes"):
                    value = {
                        "event_aligned": event_aligned_analysis(
                            self.state,
                            window=(
                                float(
                                    self.tool_arguments.get(
                                        "window_start_s",
                                        -0.5,
                                    )
                                ),
                                float(
                                    self.tool_arguments.get(
                                        "window_end_s",
                                        1.0,
                                    )
                                ),
                            ),
                            bin_size=float(
                                self.tool_arguments.get("bin_size_s", 0.025)
                            ),
                            event_codes=[
                                int(value)
                                for value in self.tool_arguments["event_codes"]
                            ],
                            baseline_window=(
                                float(
                                    self.tool_arguments.get(
                                        "baseline_start_s",
                                        -0.5,
                                    )
                                ),
                                float(
                                    self.tool_arguments.get(
                                        "baseline_end_s",
                                        0.0,
                                    )
                                ),
                            ),
                        )
                    }
                else:
                    value = {"event_aligned": event_aligned_analysis(self.state)}
            elif selection.startswith("spike:"):
                value = {"spike_train": run_spike_train_suite(self.state)}
            elif selection.startswith("lfp:"):
                value = {"lfp": run_lfp_suite(self.state)}
            elif selection.startswith("coupling:"):
                value = {"spike_field": run_spike_field_suite(self.state)}
            elif selection.startswith("case:"):
                value = {"respiration_case": run_respiration_case(self.state)}
            else:
                value = run_neural_toolkit(self.state)
            completed = self.state.metadata.setdefault("completed_analyses", [])
            completed_key = selection or "full"
            if completed_key not in completed:
                completed.append(completed_key)
            self._emit(
                key,
                value,
                self._message(
                    f"所选神经分析已完成：{selection or '完整套件'}",
                    f"Selected neural analysis completed: {selection or 'full suite'}",
                ),
            )
        elif key == "statistics":
            self._emit(
                key,
                run_statistical_suite(
                    self.state,
                    alpha=float(self.tool_arguments.get("alpha", 0.05)),
                    multiple_comparison=str(
                        self.tool_arguments.get(
                            "multiple_comparison",
                            "bh_fdr",
                        )
                    ),
                    requested_method=str(
                        self.tool_arguments.get("method", "permutation")
                    ),
                ),
                self._message("统计套件完成", "Statistical suite completed"),
            )
        elif key == "decoding":
            task, model_name = self.model_name.split(":", 1)
            if task == "regression":
                value = run_regression_suite(self.state, model_name)
                self._emit(
                    key,
                    value,
                    self._message(
                        f"{model_name} 回归完成",
                        f"{model_name} regression completed",
                    ),
                )
            else:
                value = run_decoding_suite(
                    self.state,
                    model_name,
                    n_splits=int(self.tool_arguments.get("cv_folds", 5)),
                    n_permutations=int(
                        self.tool_arguments.get("permutations", 200)
                    ),
                )
                self._emit(
                    key,
                    value,
                    self._message(
                        f"{model_name} 解码完成",
                        f"{model_name} decoding completed",
                    ),
                )
        elif key == "export":
            output = export_reproducible_bundle(
                self.state, self.state.root / "exports"
            )
            save_project(self.state)
            self._emit(
                key,
                output,
                self._message(
                    "可复现分析包与项目已保存",
                    "Reproducible analysis bundle and project saved",
                ),
            )

    def run(self) -> None:
        key = self.keys[0] if self.keys else "import"
        try:
            for key in self.keys:
                context = self._audit_context(key)
                self.progress.emit(
                    self._message(
                        f"正在运行 {key}｜工具：{context['tool']}｜"
                        f"数据片段：{context['segment']['duration_seconds']:.1f} 秒",
                        f"Running {key} | Tool: {context['tool']} | Segment: "
                        f"{context['segment']['duration_seconds']:.1f} s",
                    )
                )
                with audited_stage(self.state, key, **context):
                    self._execute_stage(key)
                save_project(self.state)
            self.succeeded.emit()
        except Exception as exc:  # noqa: BLE001 - worker forwards full tool failure
            save_project(self.state)
            self.failed.emit(key, f"{exc}\n\n{traceback.format_exc()}")


class MetricBox(QFrame):
    def __init__(self, label: str, value: str):
        super().__init__()
        self.setObjectName("Metric")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 9, 13, 9)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")
        self.label_widget = QLabel(label)
        self.label_widget.setObjectName("MetricLabel")
        layout.addWidget(self.value_label)
        layout.addWidget(self.label_widget)


class NeuroFlowWindow(QMainWindow):
    def __init__(self, workspace: Path):
        super().__init__()
        self.workspace = workspace
        self.language = "zh_CN"
        self.state: ProjectState | None = None
        self.preview: dict | None = None
        self.matches: list[dict] = []
        self.worker: PipelineWorker | None = None
        self.active_run_keys: list[str] = []
        self.active_run_started: datetime | None = None
        self.run_elapsed_timer = QTimer(self)
        self.run_elapsed_timer.setInterval(1_000)
        self.run_elapsed_timer.timeout.connect(self._update_run_elapsed)
        self.current_step = "import"
        self.project_dirty = False
        self._restoring_project = False
        self.ai_dialog: AIAssistantDialog | None = None
        self.step_buttons: dict[str, QPushButton] = {}
        self.figure_cursor = None
        self._update_window_title()
        application_icon = _brand_asset("neuroephys-ai-mark.png")
        if application_icon.exists():
            self.setWindowIcon(QIcon(str(application_icon)))
        self.resize(1500, 920)
        self.setMinimumSize(1180, 720)
        self.pages = QStackedWidget()
        self.home_page = self._home_page()
        self.workspace_page = self._workspace_page()
        self.pages.addWidget(self.home_page)
        self.pages.addWidget(self.workspace_page)
        self.setCentralWidget(self.pages)
        self.setStyleSheet(APP_STYLE)
        self._apply_icons()
        self._register_help_controls()
        QApplication.instance().installEventFilter(self)
        self._apply_language()

    def _home_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        header = QWidget()
        header.setObjectName("HomeHeader")
        header.setFixedHeight(68)
        row = QHBoxLayout(header)
        row.setContentsMargins(24, 10, 24, 10)
        brand = QLabel(PRODUCT_NAME)
        brand.setObjectName("Brand")
        row.addWidget(brand)
        row.addStretch()
        self.home_language_combo = QComboBox()
        self.home_language_combo.setProperty("neuroflow_help_key", "global.language")
        for key, label in LANGUAGES.items():
            self.home_language_combo.addItem(label, key)
        self.home_language_combo.currentIndexChanged.connect(
            lambda: self._set_language(self.home_language_combo.currentData())
        )
        row.addWidget(self.home_language_combo)
        self.home_ai_button = QPushButton("AI 助手")
        self.home_ai_button.setProperty("neuroflow_help_key", "global.ai")
        self.home_ai_button.clicked.connect(self._open_ai_assistant)
        row.addWidget(self.home_ai_button)
        self.home_tutorial_button = QPushButton("教程中心")
        self.home_tutorial_button.clicked.connect(
            lambda: TutorialDialog(parent=self, language=self.language).exec()
        )
        row.addWidget(self.home_tutorial_button)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(70, 45, 70, 50)
        layout.setSpacing(18)
        hero_panel = QFrame()
        hero_panel.setObjectName("HeroPanel")
        hero_layout = QVBoxLayout(hero_panel)
        hero_layout.setContentsMargins(36, 28, 36, 30)
        hero_layout.setSpacing(14)
        self.home_brand_mark = QLabel()
        mark_path = _brand_asset("neuroephys-ai-mark.png")
        if mark_path.exists():
            self.home_brand_mark.setPixmap(
                QPixmap(str(mark_path)).scaled(
                    112,
                    112,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        self.home_brand_mark.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.home_brand_mark)
        self.hero_label = QLabel("从自己的原始数据开始，\n逐步走到可复现的论文图。")
        self.hero_label.setObjectName("Hero")
        self.hero_label.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.hero_label)
        self.hero_subtitle = QLabel(
            "本地优先 · 模块可替换 · 每一步可解释 · Kilosort4 真实运行 · AI 非必需"
        )
        self.hero_subtitle.setObjectName("Muted")
        self.hero_subtitle.setStyleSheet("font-size: 15px;")
        self.hero_subtitle.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.hero_subtitle)

        primary_actions = QHBoxLayout()
        primary_actions.setSpacing(12)
        self.new_project_button = QPushButton("新建空白项目")
        self.new_project_button.setObjectName("Primary")
        self.new_project_button.setMinimumHeight(48)
        self.new_project_button.setMinimumWidth(210)
        self.new_project_button.setProperty(
            "neuroflow_help_key", "home.new_project"
        )
        self.new_project_button.clicked.connect(self._create_blank_project)
        self.import_button = QPushButton("导入自己的数据")
        self.import_button.setMinimumHeight(48)
        self.import_button.setMinimumWidth(210)
        self.import_button.setProperty("neuroflow_help_key", "home.import")
        self.import_button.clicked.connect(
            lambda: self._show_import("binary", own_data_only=True)
        )
        self.project_button = QPushButton("恢复 NeuroEphys AI 项目")
        self.project_button.setProperty("neuroflow_help_key", "home.restore")
        self.project_button.clicked.connect(self._open_project)
        primary_actions.addStretch()
        primary_actions.addWidget(self.new_project_button)
        primary_actions.addWidget(self.import_button)
        primary_actions.addWidget(self.project_button)
        primary_actions.addStretch()
        hero_layout.addLayout(primary_actions)

        secondary_actions = QHBoxLayout()
        secondary_actions.setSpacing(12)
        self.public_button = QPushButton("打开已验证公开项目")
        self.public_button.setMinimumHeight(42)
        self.public_button.setProperty("neuroflow_help_key", "home.public")
        self.public_button.clicked.connect(self._open_public_examples)
        self.sample_button = QPushButton("生成教学模拟项目")
        self.sample_button.setMinimumHeight(42)
        self.sample_button.setProperty("neuroflow_help_key", "home.demo")
        self.sample_button.clicked.connect(self._open_sample)
        self.demo_folder_button = QPushButton("查看示例数据文件夹")
        self.demo_folder_button.clicked.connect(self._open_demo_folder)
        secondary_actions.addStretch()
        secondary_actions.addWidget(self.public_button)
        secondary_actions.addWidget(self.sample_button)
        secondary_actions.addWidget(self.demo_folder_button)
        secondary_actions.addStretch()
        hero_layout.addLayout(secondary_actions)
        layout.addWidget(hero_panel)

        capability = QFrame()
        capability.setObjectName("Card")
        cap_layout = QVBoxLayout(capability)
        self.cap_title = QLabel("数据入口与接入位置")
        self.cap_title.setStyleSheet("font-size: 17px; font-weight: 700;")
        cap_layout.addWidget(self.cap_title)
        self.cap_intro = QLabel(
            "下面列出六条数据入口。先按“我手里有什么”选择；"
            "流程起点和能否重新sorting由文件中是否包含原始电压决定。"
        )
        self.cap_intro.setWordWrap(True)
        self.cap_intro.setObjectName("Muted")
        cap_layout.addWidget(self.cap_intro)
        self.input_table = QTableWidget(len(SUPPORTED_FORMATS), 6)
        self.input_table.setHorizontalHeaderLabels(
            ["入口", "什么时候选它", "实际要选择什么", "流程起点", "能否 sorting", "导入后会发生什么"]
        )
        self.input_table.verticalHeader().setVisible(False)
        self.input_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.input_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.input_table.setSelectionMode(QTableWidget.SingleSelection)
        self.input_table.setWordWrap(True)
        self.input_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for row_index, item in enumerate(SUPPORTED_FORMATS):
            values = ENTRY_ROUTE_TEXT["zh_CN"][item.key]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.UserRole, item.key)
                self.input_table.setItem(row_index, column, cell)
        header = self.input_table.horizontalHeader()
        header.setMinimumSectionSize(88)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self._resize_input_route_table()
        self.input_table.cellDoubleClicked.connect(
            lambda row, _column: self._activate_entry_route(
                str(self.input_table.item(row, 0).data(Qt.UserRole))
            )
        )
        cap_layout.addWidget(self.input_table)
        self.entry_hint = QLabel(
            "操作：双击公开数据行会打开两套固定验证项目；双击模拟行会打开模拟资料库；"
            "其他行进入对应的数据导入器。"
        )
        self.entry_hint.setWordWrap(True)
        self.entry_hint.setObjectName("Muted")
        cap_layout.addWidget(self.entry_hint)
        layout.addWidget(capability)

        flow = QFrame()
        flow.setObjectName("Card")
        flow_layout = QVBoxLayout(flow)
        self.flow_title = QLabel("完整纵向链路")
        self.flow_title.setStyleSheet("font-size: 17px; font-weight: 700;")
        flow_layout.addWidget(self.flow_title)
        self.flow_text = QLabel(
            "数据与项目  →  原始质控  →  预处理  →  Spike sorting  →  Unit 质控  →  "
            "事件同步  →  行为分析  →  Raster/PSTH  →  统计检验  →  神经解码  →  论文与复现"
        )
        self.flow_text.setWordWrap(True)
        self.flow_text.setStyleSheet("font-size: 15px; color: #1f7a63;")
        flow_layout.addWidget(self.flow_text)
        layout.addWidget(flow)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        return page

    def _resize_input_route_table(self) -> None:
        self.input_table.resizeRowsToContents()
        for row in range(self.input_table.rowCount()):
            self.input_table.setRowHeight(row, max(self.input_table.rowHeight(row), 66))
        height = (
            self.input_table.horizontalHeader().sizeHint().height()
            + sum(
                self.input_table.rowHeight(row)
                for row in range(self.input_table.rowCount())
            )
            + self.input_table.frameWidth() * 2
            + 6
        )
        self.input_table.setFixedHeight(height)

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
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setFrameShape(QFrame.NoFrame)
        self.main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_scroll.setWidget(self._main_area())
        main_column = QWidget()
        main_column_layout = QVBoxLayout(main_column)
        main_column_layout.setContentsMargins(0, 0, 0, 0)
        main_column_layout.setSpacing(0)
        main_column_layout.addWidget(self.main_scroll, 1)
        main_column_layout.addWidget(self._run_footer())
        content.addWidget(main_column, 1)
        self.assistant_panel = self._assistant()
        content.addWidget(self.assistant_panel)
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
        self.home_button = QPushButton("首页")
        self.home_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.home_page)
        )
        layout.addWidget(self.home_button)
        title_box = QVBoxLayout()
        brand = QLabel(PRODUCT_NAME)
        brand.setObjectName("Brand")
        self.project_label = QLabel("尚未打开项目")
        self.project_label.setObjectName("Muted")
        title_box.addWidget(brand)
        title_box.addWidget(self.project_label)
        layout.addLayout(title_box)
        layout.addStretch()
        self.workspace_language_combo = QComboBox()
        self.workspace_language_combo.setProperty(
            "neuroflow_help_key", "global.language"
        )
        for key, label in LANGUAGES.items():
            self.workspace_language_combo.addItem(label, key)
        self.workspace_language_combo.currentIndexChanged.connect(
            lambda: self._set_language(self.workspace_language_combo.currentData())
        )
        self.sorter_manager_button = QPushButton("Sorter 管理")
        self.sorter_manager_button.clicked.connect(
            lambda: SorterManagerDialog(self.language, self).exec()
        )
        self.save_button = QPushButton("保存项目")
        self.save_button.setProperty("neuroflow_help_key", "global.save")
        self.save_button.clicked.connect(self._save)
        self.ai_button = QPushButton("AI 助手")
        self.ai_button.setProperty("neuroflow_help_key", "global.ai")
        self.ai_button.clicked.connect(self._open_ai_assistant)
        self.ai_panel_toggle = QPushButton("AI panel")
        self.ai_panel_toggle.clicked.connect(self._toggle_ai_panel)
        self.tutorial_button = QPushButton("教程")
        self.tutorial_button.clicked.connect(self._open_context_tutorial)
        self.docs_button = QPushButton("产品文档")
        self.docs_button.clicked.connect(self._open_documentation)
        self.run_button = QPushButton("运行完整流程")
        self.run_button.setObjectName("Primary")
        self.run_button.setProperty("neuroflow_help_key", "global.run_all")
        self.run_button.clicked.connect(self._run_full_pipeline)
        self.run_button.setEnabled(False)
        layout.addWidget(self.workspace_language_combo)
        layout.addWidget(self.sorter_manager_button)
        layout.addWidget(self.save_button)
        layout.addWidget(self.ai_button)
        layout.addWidget(self.ai_panel_toggle)
        layout.addWidget(self.tutorial_button)
        layout.addWidget(self.docs_button)
        layout.addWidget(self.run_button)
        return header

    def _sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(340)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 10, 0, 10)
        self.workflow_label = QLabel("  分析流程")
        self.workflow_label.setObjectName("Muted")
        layout.addWidget(self.workflow_label)
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
            button.clicked.connect(
                lambda checked=False, key=step.key: self._select_step(key)
            )
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
        self.option_combo.setMinimumWidth(260)
        self.option_combo.setProperty("neuroflow_help_key", "page.option")
        self.option_combo.currentIndexChanged.connect(self._on_option_changed)
        title_row.addWidget(self.option_combo)
        layout.addLayout(title_row)

        self.project_data_panel = QFrame()
        self.project_data_panel.setObjectName("SortingWorkbench")
        project_data_layout = QVBoxLayout(self.project_data_panel)
        project_data_layout.setContentsMargins(14, 12, 14, 12)
        project_data_heading = QHBoxLayout()
        self.project_data_title = QLabel("项目数据")
        self.project_data_title.setObjectName("PanelTitle")
        project_data_heading.addWidget(self.project_data_title)
        project_data_heading.addStretch()
        project_data_layout.addLayout(project_data_heading)
        self.project_data_summary = QLabel()
        self.project_data_summary.setWordWrap(True)
        self.project_data_summary.setObjectName("InsetPanel")
        self.project_data_summary.setContentsMargins(12, 9, 12, 9)
        project_data_layout.addWidget(self.project_data_summary)
        project_data_actions = QHBoxLayout()
        self.project_import_button = QPushButton("导入我的电生理数据")
        self.project_import_button.setObjectName("Primary")
        self.project_import_button.setProperty(
            "neuroflow_help_key", "home.import"
        )
        self.project_import_button.clicked.connect(self._import_into_current_project)
        self.project_public_button = QPushButton("打开已验证公开项目")
        self.project_public_button.setProperty(
            "neuroflow_help_key", "home.public"
        )
        self.project_public_button.clicked.connect(self._open_public_examples)
        self.project_simulation_button = QPushButton("生成教学模拟项目")
        self.project_simulation_button.clicked.connect(self._open_sample)
        self.project_source_folder_button = QPushButton("打开项目文件夹")
        self.project_source_folder_button.clicked.connect(self._open_current_project_folder)
        project_data_actions.addWidget(self.project_import_button)
        project_data_actions.addWidget(self.project_public_button)
        project_data_actions.addWidget(self.project_simulation_button)
        project_data_actions.addWidget(self.project_source_folder_button)
        project_data_actions.addStretch()
        project_data_layout.addLayout(project_data_actions)
        layout.addWidget(self.project_data_panel)

        self.sorting_workbench = SortingWorkbench(self.language)
        self.sorting_workbench.selection_changed.connect(self._on_sorter_selected)
        self.sorting_workbench.diagnostic_changed.connect(
            self._on_sorting_diagnostic_changed
        )
        self.sorting_workbench.setVisible(False)
        layout.addWidget(self.sorting_workbench)
        self.unit_curation_panel = QFrame()
        self.unit_curation_panel.setObjectName("SortingWorkbench")
        unit_curation_layout = QHBoxLayout(self.unit_curation_panel)
        unit_curation_layout.setContentsMargins(14, 10, 14, 10)
        self.unit_curation_summary = QLabel()
        self.unit_curation_summary.setWordWrap(True)
        unit_curation_layout.addWidget(self.unit_curation_summary, 1)
        self.unit_curation_button = QPushButton("打开人工 Unit 复核工作台")
        self.unit_curation_button.setObjectName("Primary")
        self.unit_curation_button.clicked.connect(self._open_unit_curation)
        unit_curation_layout.addWidget(self.unit_curation_button)
        self.unit_curation_panel.setVisible(False)
        layout.addWidget(self.unit_curation_panel)
        self.sync_workbench = QFrame()
        self.sync_workbench.setObjectName("SortingWorkbench")
        sync_layout = QVBoxLayout(self.sync_workbench)
        sync_layout.setContentsMargins(12, 10, 12, 10)
        sync_heading_row = QHBoxLayout()
        self.sync_heading = QLabel("行为数据与电生理时钟")
        self.sync_heading.setObjectName("PanelTitle")
        sync_heading_row.addWidget(self.sync_heading)
        sync_heading_row.addStretch()
        self.import_behavior_button = QPushButton("导入 / 替换行为与 TTL")
        self.import_behavior_button.clicked.connect(self._import_behavior_sync)
        sync_heading_row.addWidget(self.import_behavior_button)
        self.open_behavior_folder_button = QPushButton("打开当前数据文件夹")
        self.open_behavior_folder_button.clicked.connect(
            self._open_behavior_data_folder
        )
        sync_heading_row.addWidget(self.open_behavior_folder_button)
        sync_layout.addLayout(sync_heading_row)
        self.sync_inventory_label = QLabel()
        self.sync_inventory_label.setWordWrap(True)
        self.sync_inventory_label.setObjectName("Muted")
        sync_layout.addWidget(self.sync_inventory_label)
        self.sync_schema_label = QLabel(
            "行为 CSV 提供 trial、condition、event_type 和行为时钟；TTL CSV 提供电生理"
            "时钟中的对应脉冲。按顺序配对后拟合 offset + slope × behavior_time。"
        )
        self.sync_schema_label.setWordWrap(True)
        sync_layout.addWidget(self.sync_schema_label)
        self.sync_workbench.setVisible(False)
        layout.addWidget(self.sync_workbench)

        plot_controls = QHBoxLayout()
        self.plot_help_label = QLabel()
        self.plot_help_label.setObjectName("Muted")
        self.plot_help_label.setWordWrap(True)
        plot_controls.addWidget(self.plot_help_label, 1)
        self.plot_style_combo = QComboBox()
        self.plot_style_combo.setProperty("neuroflow_help_key", "plot.style")
        for key in ("standard", "points", "step", "grayscale", "high_contrast"):
            self.plot_style_combo.addItem(tr(key, self.language), key)
        self.plot_style_combo.currentIndexChanged.connect(self._apply_plot_style)
        plot_controls.addWidget(self.plot_style_combo)
        self.figure_settings_button = QPushButton("图形设置")
        self.figure_settings_button.setProperty("neuroflow_help_key", "plot.settings")
        self.figure_settings_button.clicked.connect(self._open_figure_settings)
        plot_controls.addWidget(self.figure_settings_button)
        layout.addLayout(plot_controls)

        panel_controls = QHBoxLayout()
        self.panel_label = QLabel()
        self.panel_label.setObjectName("Muted")
        panel_controls.addWidget(self.panel_label)
        self.panel_combo = QComboBox()
        self.panel_combo.setMinimumWidth(250)
        self.panel_combo.setMaximumWidth(460)
        self.panel_combo.setProperty("neuroflow_help_key", "plot.panel")
        panel_controls.addWidget(self.panel_combo)
        self.panel_focus_button = QPushButton()
        self.panel_focus_button.setProperty("neuroflow_help_key", "plot.panel_focus")
        self.panel_focus_button.clicked.connect(self._toggle_panel_focus)
        panel_controls.addWidget(self.panel_focus_button)
        self.panel_edit_button = QPushButton()
        self.panel_edit_button.setProperty("neuroflow_help_key", "plot.panel_edit")
        self.panel_edit_button.clicked.connect(self._edit_selected_panel)
        panel_controls.addWidget(self.panel_edit_button)
        self.panel_save_button = QPushButton()
        self.panel_save_button.setProperty("neuroflow_help_key", "plot.panel_save")
        self.panel_save_button.clicked.connect(self._save_selected_panel)
        panel_controls.addWidget(self.panel_save_button)
        panel_controls.addStretch()
        layout.addLayout(panel_controls)

        self.trace_controls = TraceControls(self.language)
        self.trace_controls.changed.connect(self._refresh_figure)
        self.trace_controls.setVisible(False)
        layout.addWidget(self.trace_controls)

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
        placeholder.metadata["language"] = self.language
        self.canvas = FigureCanvasQTAgg(raw_overview_figure_empty(placeholder))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.figure_host = QWidget()
        self.figure_layout = QVBoxLayout(self.figure_host)
        self.figure_layout.setContentsMargins(0, 0, 0, 0)
        self.figure_layout.setSpacing(2)
        self.toolbar = NavigationToolbar2QT(self.canvas, self.figure_host)
        self.figure_layout.addWidget(self.toolbar)
        self.figure_layout.addWidget(self.canvas, 1)
        self.figure_host.setMinimumHeight(600)
        layout.addWidget(self.figure_host)
        self.plot_info_label = QLabel()
        self.plot_info_label.setObjectName("Muted")
        self.plot_info_label.setMinimumHeight(22)
        layout.addWidget(self.plot_info_label)
        self._connect_figure_interactions()
        self.detail_table = QTableWidget()
        self.detail_table.setVisible(False)
        self.detail_table.setMaximumHeight(190)
        layout.addWidget(self.detail_table)
        layout.addStretch()
        self._refresh_panel_controls()
        return widget

    def _run_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("RunFooter")
        footer.setFixedHeight(72)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(16, 8, 16, 8)
        self.status_label = QLabel("请从首页打开或创建项目")
        self.status_label.setObjectName("Muted")
        self.status_label.setMinimumWidth(220)
        layout.addWidget(self.status_label, 1)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(STEPS))
        self.progress_bar.setMinimumWidth(260)
        layout.addWidget(self.progress_bar, 1)
        run_box = QVBoxLayout()
        run_box.setContentsMargins(8, 0, 0, 0)
        run_box.setSpacing(2)
        self.run_context_label = QLabel("当前：尚未选择分析")
        self.run_context_label.setObjectName("Muted")
        run_box.addWidget(self.run_context_label)
        layout.addLayout(run_box)
        self.run_step_button = QPushButton("运行当前所选分析")
        self.run_step_button.setObjectName("Primary")
        self.run_step_button.setMinimumWidth(210)
        self.run_step_button.setProperty("neuroflow_help_key", "global.run_step")
        self.run_step_button.clicked.connect(self._run_current_step)
        self.run_step_button.setEnabled(False)
        layout.addWidget(self.run_step_button)
        return footer

    def _assistant(self) -> QWidget:
        assistant = QWidget()
        assistant.setObjectName("Assistant")
        assistant.setMinimumWidth(340)
        assistant.setMaximumWidth(460)
        assistant.resize(390, assistant.height())
        layout = QVBoxLayout(assistant)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)
        title_row = QHBoxLayout()
        self.assistant_title = QLabel("AI、引导与证据")
        self.assistant_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        title_row.addWidget(self.assistant_title)
        title_row.addStretch()
        self.close_ai_panel_button = QPushButton()
        self.close_ai_panel_button.setFixedSize(34, 34)
        self.close_ai_panel_button.setToolTip("关闭右侧面板")
        self.close_ai_panel_button.clicked.connect(self._toggle_ai_panel)
        title_row.addWidget(self.close_ai_panel_button)
        layout.addLayout(title_row)

        self.assistant_tabs = QTabWidget()
        self.assistant_tabs.setDocumentMode(True)
        layout.addWidget(self.assistant_tabs, 1)

        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        ai_layout.setContentsMargins(4, 8, 4, 4)
        ai_layout.setSpacing(8)
        mode_row = QHBoxLayout()
        self.assistant_mode = QLabel("AI 模式")
        self.assistant_mode.setObjectName("Muted")
        mode_row.addWidget(self.assistant_mode)
        self.sidebar_ai_mode_combo = QComboBox()
        self.sidebar_ai_mode_combo.addItem("手动", AIMode.MANUAL.value)
        self.sidebar_ai_mode_combo.addItem("助手", AIMode.ASSISTANT.value)
        self.sidebar_ai_mode_combo.addItem("协作", AIMode.COLLABORATIVE.value)
        sidebar_settings = load_ai_settings()
        self.sidebar_ai_mode_combo.setCurrentIndex(
            max(
                self.sidebar_ai_mode_combo.findData(sidebar_settings.mode),
                0,
            )
        )
        self.sidebar_ai_mode_combo.currentIndexChanged.connect(
            self._sidebar_ai_mode_changed
        )
        mode_row.addWidget(self.sidebar_ai_mode_combo, 1)
        ai_layout.addLayout(mode_row)
        self.ai_context_label = QLabel("尚未打开项目")
        self.ai_context_label.setObjectName("Muted")
        self.ai_context_label.setWordWrap(True)
        ai_layout.addWidget(self.ai_context_label)
        ai_quick_row = QHBoxLayout()
        self.sidebar_ai_review_button = QPushButton("审查项目")
        self.sidebar_ai_review_button.clicked.connect(
            lambda: self._sidebar_ai_quick("review")
        )
        self.sidebar_ai_plan_button = QPushButton("建议流程")
        self.sidebar_ai_plan_button.clicked.connect(
            lambda: self._sidebar_ai_quick("plan")
        )
        ai_quick_row.addWidget(self.sidebar_ai_review_button)
        ai_quick_row.addWidget(self.sidebar_ai_plan_button)
        ai_layout.addLayout(ai_quick_row)
        self.ai_sidebar_conversation = QTextBrowser()
        self.ai_sidebar_conversation.setOpenExternalLinks(False)
        self.ai_sidebar_conversation.setPlaceholderText("AI 对话会显示在这里。")
        ai_layout.addWidget(self.ai_sidebar_conversation, 1)
        self.ai_sidebar_question = QPlainTextEdit()
        self.ai_sidebar_question.setMaximumHeight(92)
        self.ai_sidebar_question.setPlaceholderText(
            "询问当前数据、参数、结果或下一步。发送前可预览云端字段。"
        )
        ai_layout.addWidget(self.ai_sidebar_question)
        ai_action_row = QHBoxLayout()
        self.sidebar_ai_settings_button = QPushButton("设置")
        self.sidebar_ai_settings_button.clicked.connect(self._sidebar_ai_settings)
        self.open_ai_button = QPushButton("展开")
        self.open_ai_button.setProperty("neuroflow_help_key", "global.ai")
        self.open_ai_button.clicked.connect(self._open_ai_assistant)
        self.sidebar_ai_send_button = QPushButton("发送")
        self.sidebar_ai_send_button.setObjectName("Primary")
        self.sidebar_ai_send_button.clicked.connect(self._sidebar_ai_send)
        ai_action_row.addWidget(self.sidebar_ai_settings_button)
        ai_action_row.addWidget(self.open_ai_button)
        ai_action_row.addWidget(self.sidebar_ai_send_button, 1)
        ai_layout.addLayout(ai_action_row)
        self.ai_sidebar_status = QLabel("AI 服务尚未配置。")
        self.ai_sidebar_status.setObjectName("Muted")
        self.ai_sidebar_status.setWordWrap(True)
        ai_layout.addWidget(self.ai_sidebar_status)
        self.assistant_tabs.addTab(ai_tab, "AI")

        guide_tab = QWidget()
        guide_layout = QVBoxLayout(guide_tab)
        guide_layout.setContentsMargins(4, 8, 4, 4)
        guide_layout.setSpacing(8)
        self.help_title = QLabel("先选择数据来源")
        self.help_title.setStyleSheet("font-weight: 700; color: #62dbc9;")
        guide_layout.addWidget(self.help_title)
        self.help_text = QLabel(f"{PRODUCT_NAME} 会展示数据结构和关键参数。")
        self.help_text.setWordWrap(True)
        self.help_text.setAlignment(Qt.AlignTop)
        guide_layout.addWidget(self.help_text, 1)
        self.open_tutorial_button = QPushButton("打开本章完整教程")
        self.open_tutorial_button.clicked.connect(self._open_context_tutorial)
        guide_layout.addWidget(self.open_tutorial_button)
        self.warning_heading = QLabel("当前检查")
        self.warning_heading.setStyleSheet("font-weight: 700;")
        guide_layout.addWidget(self.warning_heading)
        self.warning_text = QLabel("尚未打开项目。")
        self.warning_text.setWordWrap(True)
        self.warning_text.setObjectName("Muted")
        guide_layout.addWidget(self.warning_text)
        self.assistant_tabs.addTab(guide_tab, "帮助")

        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        log_layout.setContentsMargins(4, 8, 4, 4)
        log_layout.setSpacing(8)
        self.log_title = QLabel("运行与审计记录")
        self.log_title.setStyleSheet("font-weight: 700;")
        log_layout.addWidget(self.log_title)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(300)
        log_layout.addWidget(self.log_view, 1)
        self.assistant_tabs.addTab(log_tab, "日志")
        return assistant

    def _register_help_controls(self) -> None:
        for widget in self.findChildren(QWidget):
            key = widget.property("neuroflow_help_key")
            if not key:
                continue
            widget.installEventFilter(self)
            title, description = control_help(str(key), self.language)
            widget.setToolTip(f"{title}\n{description}")

    def _apply_icons(self) -> None:
        icon = self.style().standardIcon
        standard = QStyle.StandardPixmap
        for button, icon_name in (
            (self.new_project_button, standard.SP_FileIcon),
            (self.sample_button, standard.SP_MediaPlay),
            (self.import_button, standard.SP_DialogOpenButton),
            (self.public_button, standard.SP_DriveNetIcon),
            (self.project_button, standard.SP_DialogOpenButton),
            (self.demo_folder_button, standard.SP_DirOpenIcon),
            (self.home_button, standard.SP_DirHomeIcon),
            (self.home_ai_button, standard.SP_MessageBoxInformation),
            (self.sorter_manager_button, standard.SP_ComputerIcon),
            (self.save_button, standard.SP_DialogSaveButton),
            (self.ai_button, standard.SP_MessageBoxInformation),
            (self.tutorial_button, standard.SP_DialogHelpButton),
            (self.docs_button, standard.SP_FileDialogInfoView),
            (self.run_button, standard.SP_MediaPlay),
            (self.run_step_button, standard.SP_MediaPlay),
            (self.figure_settings_button, standard.SP_FileDialogDetailedView),
            (self.project_import_button, standard.SP_DialogOpenButton),
            (self.project_public_button, standard.SP_DriveNetIcon),
            (self.project_simulation_button, standard.SP_MediaPlay),
            (self.project_source_folder_button, standard.SP_DirOpenIcon),
            (self.panel_focus_button, standard.SP_TitleBarMaxButton),
            (self.panel_edit_button, standard.SP_FileDialogDetailedView),
            (self.panel_save_button, standard.SP_DialogSaveButton),
            (self.open_ai_button, standard.SP_MessageBoxInformation),
            (self.sidebar_ai_settings_button, standard.SP_FileDialogDetailedView),
            (self.sidebar_ai_send_button, standard.SP_ArrowForward),
            (self.close_ai_panel_button, standard.SP_TitleBarCloseButton),
        ):
            button.setIcon(icon(icon_name))

    def _update_control_tooltips(self) -> None:
        for widget in self.findChildren(QWidget):
            key = widget.property("neuroflow_help_key")
            if key:
                title, description = control_help(str(key), self.language)
                widget.setToolTip(f"{title}\n{description}")

    def eventFilter(self, watched, event) -> bool:
        if (
            event.type() == QEvent.Wheel
            and hasattr(self, "main_scroll")
            and isinstance(watched, QWidget)
            and self.pages.currentWidget() is self.workspace_page
        ):
            scroll_owner = watched
            keep_native_scroll = False
            while scroll_owner is not None and scroll_owner is not self:
                if scroll_owner is self.main_scroll:
                    break
                if isinstance(
                    scroll_owner,
                    (
                        QComboBox,
                        QSpinBox,
                        QDoubleSpinBox,
                        QTableWidget,
                        QListWidget,
                        QPlainTextEdit,
                        QTextBrowser,
                        QScrollArea,
                    ),
                ):
                    keep_native_scroll = True
                    break
                scroll_owner = scroll_owner.parentWidget()
            inside_window = watched is self or self.isAncestorOf(watched)
            if inside_window and not keep_native_scroll:
                bar = self.main_scroll.verticalScrollBar()
                pixel_delta = event.pixelDelta().y()
                angle_delta = event.angleDelta().y()
                delta = pixel_delta if pixel_delta else angle_delta / 120 * 72
                if delta:
                    bar.setValue(int(bar.value() - delta))
                    event.accept()
                    return True
        if event.type() in {QEvent.Enter, QEvent.FocusIn}:
            key = watched.property("neuroflow_help_key")
            if key:
                self._show_control_help(str(key))
        return super().eventFilter(watched, event)

    def _show_control_help(self, key: str) -> None:
        title, description = control_help(key, self.language)
        self.help_title.setText(title)
        self.help_text.setText(description)

    def _update_window_title(self) -> None:
        suffix = " *" if self.project_dirty else ""
        self.setWindowTitle(
            f"{tr('app_title', self.language)} · v{PRODUCT_VERSION}{suffix}"
        )

    def _mark_project_dirty(self) -> None:
        if not self.state or self._restoring_project:
            return
        self.project_dirty = True
        self._update_window_title()

    def _set_project_clean(self) -> None:
        self.project_dirty = False
        self._update_window_title()

    def _set_language(self, language: str | None) -> None:
        if language not in LANGUAGES or language == self.language:
            return
        self.language = language
        if self.state:
            self.state.metadata["language"] = language
            self._mark_project_dirty()
        self._apply_language()

    def _apply_language(self) -> None:
        language = self.language
        self._update_window_title()
        for combo in (self.home_language_combo, self.workspace_language_combo):
            combo.blockSignals(True)
            index = combo.findData(language)
            if index >= 0:
                combo.setCurrentIndex(index)
            combo.blockSignals(False)
        self.home_ai_button.setText(
            "AI assistant" if language == "en_US" else "AI 助手"
        )
        self.ai_button.setText(
            "AI assistant" if language == "en_US" else "AI 助手"
        )
        self.ai_panel_toggle.setText(
            "Hide/show AI panel"
            if language == "en_US"
            else "隐藏/显示 AI 侧栏"
        )
        self.assistant_title.setText(
            "AI, guidance and evidence"
            if language == "en_US"
            else "AI、引导与证据"
        )
        self.assistant_mode.setText(
            "AI mode" if language == "en_US" else "AI 模式"
        )
        current_mode = self.sidebar_ai_mode_combo.currentData()
        self.sidebar_ai_mode_combo.blockSignals(True)
        self.sidebar_ai_mode_combo.clear()
        for label, value in (
            (("Manual" if language == "en_US" else "手动"), AIMode.MANUAL.value),
            (("Assistant" if language == "en_US" else "助手"), AIMode.ASSISTANT.value),
            (
                ("Collaborative" if language == "en_US" else "协作"),
                AIMode.COLLABORATIVE.value,
            ),
        ):
            self.sidebar_ai_mode_combo.addItem(label, value)
        self.sidebar_ai_mode_combo.setCurrentIndex(
            max(self.sidebar_ai_mode_combo.findData(current_mode), 0)
        )
        self.sidebar_ai_mode_combo.blockSignals(False)
        self.home_tutorial_button.setText(tr("tutorial", language))
        self.hero_label.setText(tr("hero", language))
        self.hero_subtitle.setText(tr("hero_subtitle", language))
        self.new_project_button.setText(
            "Create empty project" if language == "en_US" else "新建空白项目"
        )
        self.import_button.setText(
            "Import my data" if language == "en_US" else "导入自己的数据"
        )
        self.public_button.setText(
            "Open verified public project"
            if language == "en_US"
            else "打开已验证公开项目"
        )
        self.sample_button.setText(
            "Generate teaching simulation"
            if language == "en_US"
            else "生成教学模拟项目"
        )
        self.project_button.setText(tr("restore", language))
        self.demo_folder_button.setText(
            "Open demo data folder" if language == "en_US" else "查看示例数据文件夹"
        )
        self.cap_title.setText(tr("verified_inputs", language))
        self.flow_title.setText(tr("full_chain", language))
        self.cap_intro.setText(
            (
                "下面列出六条数据入口。先按“我手里有什么”选择；"
                "流程起点和能否重新sorting由文件中是否包含原始电压决定。"
            )
            if language == "zh_CN"
            else (
                "These are six entry routes, not six algorithms. Choose by what "
                "you actually have; raw voltage determines the starting stage and "
                "whether sorting can run."
            )
        )
        self.input_table.setHorizontalHeaderLabels(
            ["入口", "什么时候选它", "实际要选择什么", "流程起点", "能否 sorting", "导入后会发生什么"]
            if language == "zh_CN"
            else [
                "Entry",
                "Choose it when",
                "What to select",
                "Starts at",
                "Can sort?",
                "What happens next",
            ]
        )
        for row, item in enumerate(SUPPORTED_FORMATS):
            values = ENTRY_ROUTE_TEXT[language][item.key]
            for column, value in enumerate(values):
                self.input_table.item(row, column).setText(value)
        self._resize_input_route_table()
        self.entry_hint.setText(
            (
                "操作：双击公开数据行会打开两套固定验证项目；双击模拟行会打开"
                "模拟资料库；其他行进入对应的数据导入器。"
            )
            if language == "zh_CN"
            else (
                "Double-click Public validation to open the two fixed verified projects; "
                "double-click Simulation for the teaching library; other rows open "
                "their matching data importer."
            )
        )
        self.flow_text.setText(
            "数据与项目  →  原始质控  →  预处理  →  Spike sorting  →  Unit 质控  →  "
            "事件同步  →  行为分析  →  Raster/PSTH  →  统计检验  →  神经解码  →  论文与复现"
            if language == "zh_CN"
            else "Data  →  Raw QC  →  Preprocessing  →  Spike sorting  →  Unit QC  →  "
            "Synchronization  →  Behavior  →  Raster/PSTH  →  Statistics  →  Decoding  →  Export"
        )
        self.home_button.setText(tr("home", language))
        self.save_button.setText(tr("save", language))
        self.ai_button.setText(
            "AI assistant" if language == "en_US" else "AI 助手"
        )
        self.tutorial_button.setText(tr("tutorial", language))
        self.docs_button.setText(
            "Product docs" if language == "en_US" else "产品文档"
        )
        self.sorter_manager_button.setText(tr("sorter_manager", language))
        self.run_button.setText(tr("run_all", language))
        self.workflow_label.setText(f"  {tr('workflow', language)}")
        for step in STEPS:
            title, subtitle = step_text(step.key, language)
            self.step_buttons[step.key].setText(f"{title}\n    {subtitle}")
            chapter = next(
                item for item in TUTORIALS if item["key"] == STEP_TUTORIAL[step.key]
            )
            self.step_buttons[step.key].setToolTip(
                tutorial_value(chapter, "why", language)
            )
        self.run_step_button.setText(tr("run_step", language))
        self._update_run_context()
        self.project_data_title.setText(
            "Project data" if language == "en_US" else "项目数据"
        )
        self.project_import_button.setText(
            "Import my electrophysiology data"
            if language == "en_US"
            else "导入我的电生理数据"
        )
        self.project_public_button.setText(
            "Open verified public project"
            if language == "en_US"
            else "打开已验证公开项目"
        )
        self.project_simulation_button.setText(
            "Generate teaching simulation"
            if language == "en_US"
            else "生成教学模拟项目"
        )
        self.project_source_folder_button.setText(
            "Open project folder" if language == "en_US" else "打开项目文件夹"
        )
        self.unit_curation_button.setText(
            "Open manual Unit curation"
            if language == "en_US"
            else "打开人工 Unit 复核工作台"
        )
        self._refresh_unit_curation_summary()
        self.plot_help_label.setText(tr("plot_help", language))
        self.figure_settings_button.setText(tr("plot_settings", language))
        self._update_panel_control_text()
        current_style = self.plot_style_combo.currentData()
        self.plot_style_combo.blockSignals(True)
        self.plot_style_combo.clear()
        for key in ("standard", "points", "step", "grayscale", "high_contrast"):
            self.plot_style_combo.addItem(tr(key, language), key)
        self.plot_style_combo.setCurrentIndex(
            max(self.plot_style_combo.findData(current_style), 0)
        )
        self.plot_style_combo.blockSignals(False)
        self.metric_source.label_widget.setText(tr("source", language))
        self.metric_channels.label_widget.setText(tr("channels", language))
        self.metric_duration.label_widget.setText(tr("duration", language))
        self.metric_units.label_widget.setText(tr("units", language))
        self.assistant_title.setText(
            "AI, guidance and evidence"
            if language == "en_US"
            else "AI、引导与证据"
        )
        self.assistant_mode.setText(
            "AI mode" if language == "en_US" else "AI 模式"
        )
        self.open_ai_button.setText(
            "Expand" if language == "en_US" else "展开"
        )
        self.sidebar_ai_settings_button.setText(
            "Settings" if language == "en_US" else "设置"
        )
        self.sidebar_ai_send_button.setText(
            "Send" if language == "en_US" else "发送"
        )
        self.sidebar_ai_review_button.setText(
            "Review project" if language == "en_US" else "审查项目"
        )
        self.sidebar_ai_plan_button.setText(
            "Propose workflow" if language == "en_US" else "建议流程"
        )
        self.ai_sidebar_question.setPlaceholderText(
            (
                "Ask about the current data, parameters, result, or next step. "
                "Cloud fields are previewed before sending."
            )
            if language == "en_US"
            else "询问当前数据、参数、结果或下一步。发送前可预览云端字段。"
        )
        self.ai_sidebar_conversation.setPlaceholderText(
            "AI conversation appears here."
            if language == "en_US"
            else "AI 对话会显示在这里。"
        )
        self.close_ai_panel_button.setToolTip(
            "Close right panel" if language == "en_US" else "关闭右侧面板"
        )
        self.assistant_tabs.setTabText(0, "AI")
        self.assistant_tabs.setTabText(
            1, "Guide" if language == "en_US" else "帮助"
        )
        self.assistant_tabs.setTabText(
            2, "Audit log" if language == "en_US" else "日志"
        )
        self.open_tutorial_button.setText(tr("open_chapter", language))
        self.warning_heading.setText(tr("current_checks", language))
        self.log_title.setText(tr("audit_log", language))
        self.trace_controls.set_language(language)
        self.sorting_workbench.set_language(language)
        self.sync_heading.setText(
            "Behavior data and electrophysiology clock"
            if language == "en_US"
            else "行为数据与电生理时钟"
        )
        self.import_behavior_button.setText(
            "Import / replace behavior and TTL"
            if language == "en_US"
            else "导入 / 替换行为与 TTL"
        )
        self.open_behavior_folder_button.setText(
            "Open current data folder"
            if language == "en_US"
            else "打开当前数据文件夹"
        )
        self.sync_schema_label.setText(
            (
                "The behavior CSV supplies trial, condition, event_type, and the "
                "behavior-device clock. The TTL CSV supplies matching pulses in the "
                "ephys clock. Rows are paired before fitting offset + slope × behavior_time."
            )
            if language == "en_US"
            else (
                "行为 CSV 提供 trial、condition、event_type 和行为时钟；TTL CSV 提供"
                "电生理时钟中的对应脉冲。按顺序配对后拟合 "
                "offset + slope × behavior_time。"
            )
        )
        self._update_control_tooltips()
        self._update_project_data_panel()
        self._refresh_environment()
        if self.ai_dialog is not None:
            self.ai_dialog.set_language(language)
        if not self.state:
            self.project_label.setText(tr("no_project", language))
            self.status_label.setText(tr("open_project_first", language))
        else:
            configured = self.state.source_type not in {"unknown", "unconfigured"}
            self.status_label.setText(
                (
                    "Project opened; run one step or the full workflow"
                    if language == "en_US"
                    else "项目已打开；可逐节点运行，也可执行完整流程"
                )
                if configured
                else (
                    "Empty project opened; import your data on this page"
                    if language == "en_US"
                    else "空白项目已建立；请在本页导入自己的电生理数据"
                )
            )
        if self.current_step in self.step_buttons:
            self._select_step(self.current_step)

    def _connect_figure_interactions(self) -> None:
        self.figure_cursor = mplcursors.cursor(self.canvas.figure, hover=False)

        @self.figure_cursor.connect("add")
        def _on_add(selection) -> None:
            target = np.asarray(selection.target).reshape(-1)
            axis = getattr(selection.artist, "axes", None)
            x_name = axis.get_xlabel() if axis is not None else "x"
            y_name = axis.get_ylabel() if axis is not None else "y"
            gid = getattr(selection.artist, "get_gid", lambda: None)()
            if gid and str(gid).startswith("neuroflow-trace:") and len(target) >= 2:
                _, channel, offset, gain = str(gid).split(":")
                voltage = (target[1] - float(offset)) / max(float(gain), 1e-12)
                coordinates = (
                    f"{x_name or 'Time'}={target[0]:.5g}, "
                    f"{'电压' if self.language == 'zh_CN' else 'Voltage'}="
                    f"{voltage:.5g} µV"
                )
                label = f"Ch {channel}"
            elif len(target) >= 2:
                coordinates = (
                    f"{x_name or 'x'}={target[0]:.5g}, {y_name or 'y'}={target[1]:.5g}"
                )
                label = selection.artist.get_label()
            else:
                coordinates = ", ".join(f"{value:.5g}" for value in target[:3])
                label = selection.artist.get_label()
            if not label or str(label).startswith("_"):
                label = type(selection.artist).__name__
            text = (
                f"{label}：{coordinates}"
                if self.language == "zh_CN"
                else f"{label}: {coordinates}"
            )
            selection.annotation.set_text(text)
            self.plot_info_label.setText(text)

        self.canvas.mpl_connect("button_press_event", self._on_plot_press)

    def _on_plot_press(self, event) -> None:
        if event.dblclick and event.inaxes is not None:
            FigureStudioDialog(
                self.canvas.figure,
                self.language,
                self,
                initial_axis=event.inaxes,
            ).exec()

    def _open_figure_settings(self) -> None:
        FigureStudioDialog(self.canvas.figure, self.language, self).exec()

    def _figure_panel_axes(self) -> list:
        return [
            axis
            for axis in self.canvas.figure.axes
            if axis.get_visible() and axis.get_label() != "<colorbar>"
        ]

    def _panel_axis_group(self, axis) -> list:
        group = [axis]
        for candidate in self.canvas.figure.axes:
            colorbar = getattr(candidate, "_colorbar", None)
            mappable = getattr(colorbar, "mappable", None)
            if candidate.get_label() == "<colorbar>" and getattr(
                mappable, "axes", None
            ) is axis:
                group.append(candidate)
        return group

    def _refresh_panel_controls(self) -> None:
        if not hasattr(self, "panel_combo") or not hasattr(self, "canvas"):
            return
        self._panel_layout_snapshot = None
        self._panel_axes = self._figure_panel_axes()
        self.panel_combo.blockSignals(True)
        self.panel_combo.clear()
        for index, axis in enumerate(self._panel_axes):
            name = (
                axis.get_title(loc="left")
                or axis.get_title()
                or axis.get_title(loc="right")
                or axis.get_xlabel()
                or axis.get_ylabel()
            )
            fallback = "子图" if self.language == "zh_CN" else "Panel"
            self.panel_combo.addItem(f"{index + 1}. {name or fallback}", index)
        self.panel_combo.blockSignals(False)
        enabled = bool(self._panel_axes)
        self.panel_combo.setEnabled(enabled)
        self.panel_focus_button.setEnabled(enabled)
        self.panel_edit_button.setEnabled(enabled)
        self.panel_save_button.setEnabled(enabled)
        self._update_panel_control_text()

    def _update_panel_control_text(self) -> None:
        if not hasattr(self, "panel_label"):
            return
        focused = bool(getattr(self, "_panel_layout_snapshot", None))
        if self.language == "zh_CN":
            self.panel_label.setText("图表面板")
            self.panel_focus_button.setText("显示全部" if focused else "单独放大")
            self.panel_edit_button.setText("编辑子图")
            self.panel_save_button.setText("保存子图")
        else:
            self.panel_label.setText("Figure panels")
            self.panel_focus_button.setText("Show all" if focused else "Expand panel")
            self.panel_edit_button.setText("Edit panel")
            self.panel_save_button.setText("Save panel")

    def _selected_panel_axis(self):
        index = self.panel_combo.currentData()
        if index is None or not 0 <= int(index) < len(self._panel_axes):
            return None
        return self._panel_axes[int(index)]

    def _toggle_panel_focus(self) -> None:
        snapshot = getattr(self, "_panel_layout_snapshot", None)
        if snapshot:
            for axis, position, visible in snapshot:
                axis.set_position(position)
                axis.set_visible(visible)
            self._panel_layout_snapshot = None
            self.panel_combo.setEnabled(True)
            self._update_panel_control_text()
            self.canvas.draw_idle()
            return
        axis = self._selected_panel_axis()
        if axis is None:
            return
        figure_axes = list(self.canvas.figure.axes)
        self._panel_layout_snapshot = [
            (item, item.get_position().frozen(), item.get_visible())
            for item in figure_axes
        ]
        group = self._panel_axis_group(axis)
        for item in figure_axes:
            item.set_visible(item in group)
        if len(group) > 1:
            axis.set_position([0.10, 0.14, 0.70, 0.76])
            for colorbar in group[1:]:
                colorbar.set_position([0.84, 0.16, 0.025, 0.72])
        else:
            axis.set_position([0.10, 0.14, 0.84, 0.76])
        self.panel_combo.setEnabled(False)
        self._update_panel_control_text()
        self.canvas.draw_idle()

    def _edit_selected_panel(self) -> None:
        axis = self._selected_panel_axis()
        if axis is not None:
            FigureStudioDialog(
                self.canvas.figure,
                self.language,
                self,
                initial_axis=axis,
            ).exec()

    def _save_selected_panel(self) -> None:
        axis = self._selected_panel_axis()
        if axis is None:
            return
        output_root = (
            self.state.root / "exports" if self.state is not None else self.workspace
        )
        output_root.mkdir(parents=True, exist_ok=True)
        title = re.sub(r"[^A-Za-z0-9_-]+", "_", axis.get_title()).strip("_")
        default_name = f"{title or 'neuroflow_panel'}.svg"
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "保存子图" if self.language == "zh_CN" else "Save selected panel",
            str(output_root / default_name),
            "SVG (*.svg);;PDF (*.pdf);;PNG (*.png)",
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in {".svg", ".pdf", ".png"}:
            path = path.with_suffix(".svg")
        path.parent.mkdir(parents=True, exist_ok=True)
        group = self._panel_axis_group(axis)
        visibility = [(item, item.get_visible()) for item in self.canvas.figure.axes]
        try:
            for item, _ in visibility:
                item.set_visible(item in group)
            self.canvas.draw()
            renderer = self.canvas.get_renderer()
            boxes = []
            for item in group:
                box = item.get_tightbbox(renderer)
                if box is not None:
                    boxes.append(box)
            if not boxes:
                boxes.append(axis.get_window_extent(renderer))
            extent = Bbox.union(boxes).transformed(
                self.canvas.figure.dpi_scale_trans.inverted()
            )
            self.canvas.figure.savefig(
                path,
                bbox_inches=extent.expanded(1.06, 1.10),
                dpi=300,
            )
        finally:
            for item, visible in visibility:
                item.set_visible(visible)
            self.canvas.draw_idle()
        self.status_label.setText(
            f"子图已保存：{path}"
            if self.language == "zh_CN"
            else f"Panel saved: {path}"
        )

    def _apply_plot_style(self) -> None:
        if not hasattr(self, "canvas"):
            return
        style = self.plot_style_combo.currentData()
        if style == "standard":
            self._refresh_figure()
            return
        colors = ["#000000", "#0072b2", "#d55e00", "#009e73", "#cc79a7"]
        color_index = 0
        for axis in self.canvas.figure.axes:
            for line in axis.lines:
                if style == "points":
                    line.set_marker("o")
                    line.set_markersize(4)
                    line.set_markevery(max(len(line.get_xdata()) // 80, 1))
                elif style == "step":
                    line.set_drawstyle("steps-mid")
                elif style == "grayscale":
                    line.set_color("#303030")
                elif style == "high_contrast":
                    line.set_color(colors[color_index % len(colors)])
                    line.set_linewidth(max(line.get_linewidth(), 1.5))
                    color_index += 1
            for image in axis.images:
                if style == "grayscale":
                    image.set_cmap("gray")
                elif style == "high_contrast":
                    image.set_cmap("viridis")
            for patch in axis.patches:
                if style == "grayscale":
                    patch.set_facecolor("#777777")
                elif style == "high_contrast":
                    patch.set_facecolor(colors[color_index % len(colors)])
                    color_index += 1
        self.canvas.draw_idle()

    def _activate_entry_route(self, source_key: str) -> None:
        if source_key == "simulated":
            self._open_sample()
        elif source_key == "ibl_alf":
            self._open_public_examples()
        else:
            self._show_import(
                source_key,
                own_data_only=source_key
                in {"binary", "device", "kilosort", "nex5"},
            )

    def _create_blank_project(self) -> None:
        dialog = NewProjectDialog(self.workspace, self, self.language)
        if dialog.exec() == QDialog.Accepted and dialog.state:
            self._load_state(dialog.state)

    def _show_import(
        self,
        source_key: str | None = None,
        *,
        own_data_only: bool = False,
        project_root: Path | None = None,
        project_name: str | None = None,
    ) -> None:
        dialog = ImportDialog(
            self.workspace,
            self,
            self.language,
            project_root=project_root,
            project_name=project_name,
            own_data_only=own_data_only,
        )
        if source_key:
            index = dialog.source_combo.findData(source_key)
            if index >= 0:
                dialog.source_combo.setCurrentIndex(index)
        if dialog.exec() == QDialog.Accepted and dialog.state:
            self._load_state(dialog.state)

    def _import_into_current_project(self) -> None:
        if not self.state:
            self._create_blank_project()
            return
        self._show_import(
            "binary",
            own_data_only=True,
            project_root=self.state.root,
            project_name=self.state.name,
        )

    def _open_public_examples(self) -> None:
        dialog = PublicExampleDialog(self.workspace, self, self.language)
        if dialog.exec() != QDialog.Accepted:
            return
        key = dialog.example_key
        status = public_example_status(self.workspace, key)
        if not status["downloaded"]:
            answer = QMessageBox.question(
                self,
                "Download public example"
                if self.language == "en_US"
                else "下载公开验证数据",
                (
                    "The fixed source is not in the local NeuroEphys AI library. Download "
                    "the official version now and open it after validation?"
                    if self.language == "en_US"
                    else (
                        "本机 NeuroEphys AI 资料库中还没有这套固定数据。是否立即从官方来源"
                        "下载，完成文件检查后打开？"
                    )
                ),
            )
            if answer != QMessageBox.Yes:
                return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if not status["downloaded"]:
                download_public_example(
                    self.workspace,
                    key,
                    progress=lambda text: self.status_label.setText(text),
                )
            self.status_label.setText(
                "Preparing verified project…"
                if self.language == "en_US"
                else "正在建立已验证公开项目…"
            )
            QApplication.processEvents()
            state = open_or_create_public_example(self.workspace, key)
            state.metadata["language"] = self.language
            save_project(state)
            self._load_state(state)
        except Exception as exc:  # noqa: BLE001 - download/import errors are user-facing
            QMessageBox.warning(
                self,
                "Public project unavailable"
                if self.language == "en_US"
                else "公开验证项目不可用",
                str(exc),
            )
        finally:
            QApplication.restoreOverrideCursor()

    def _open_current_project_folder(self) -> None:
        if not self.state:
            return
        self.state.root.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.state.root)))

    def _update_project_data_panel(self) -> None:
        if not hasattr(self, "project_data_summary"):
            return
        if not self.state:
            self.project_data_summary.setText(
                "No project is open."
                if self.language == "en_US"
                else "尚未打开项目。"
            )
            self.project_import_button.setEnabled(False)
            self.project_source_folder_button.setEnabled(False)
            return
        self.project_import_button.setEnabled(True)
        self.project_source_folder_button.setEnabled(True)
        configured = self.state.source_type not in {"unknown", "unconfigured"}
        source = str(self.state.source_path or self.state.recording_path or "—")
        if self.language == "en_US":
            self.project_data_summary.setText(
                f"<b>{self.state.name}</b><br>No data have been imported yet. "
                "Choose <b>Import my electrophysiology data</b> to select generic "
                "binary, acquisition-system files, or an existing sorting result."
                if not configured
                else (
                    f"<b>{self.state.name}</b><br>Source type: "
                    f"{self.state.source_type}<br>Read-only source: {source}<br>"
                    f"Channels: {self.state.channel_count or '—'} · "
                    f"Duration: {self.state.duration_seconds:.2f} s · "
                    f"Units: {len(self.state.sorted_spikes)}"
                )
            )
        else:
            self.project_data_summary.setText(
                f"<b>{self.state.name}</b><br>当前是空白项目，尚未导入任何数据。"
                "点击<b>导入我的电生理数据</b>，选择通用二进制、记录系统文件或"
                "已有 sorting 结果。"
                if not configured
                else (
                    f"<b>{self.state.name}</b><br>数据类型："
                    f"{self.state.source_type}<br>只读来源：{source}<br>"
                    f"通道：{self.state.channel_count or '—'} · "
                    f"时长：{self.state.duration_seconds:.2f} 秒 · "
                    f"Unit：{len(self.state.sorted_spikes)}"
                )
            )

    def _import_behavior_sync(self) -> None:
        if not self.state:
            return
        dialog = BehaviorSyncDialog(self.state, self, self.language)
        if dialog.exec() == QDialog.Accepted and dialog.result:
            self._set_step_status("sync", "completed")
            self._set_step_status("behavior", "pending")
            self.state.metadata["last_open_step"] = "sync"
            save_project(self.state)
            self._set_project_clean()
            self._refresh_sync_inventory()
            self._refresh_figure()
            self._refresh_warnings()
            result = dialog.result
            self.status_label.setText(
                (
                    f"Behavior/TTL imported: {result['matched_count']} paired events, "
                    f"max residual {result['max_abs_residual_ms']:.3f} ms"
                )
                if self.language == "en_US"
                else (
                    f"行为/TTL 已导入：{result['matched_count']} 个配对事件，"
                    f"最大残差 {result['max_abs_residual_ms']:.3f} ms"
                )
            )

    def _open_behavior_data_folder(self) -> None:
        if not self.state:
            return
        behavior = self.state.metadata.get("behavior_source")
        target = Path(behavior).parent if behavior else self.state.root
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _refresh_sync_inventory(self) -> None:
        if not hasattr(self, "sync_inventory_label"):
            return
        if not self.state:
            self.sync_inventory_label.setText(
                "No project is open"
                if self.language == "en_US"
                else "尚未打开项目"
            )
            return
        result = self.state.metadata.get("synchronization", {})
        behavior_path = self.state.metadata.get("behavior_source")
        ttl_path = self.state.metadata.get("ttl_source")
        if self.language == "en_US":
            lines = [
                f"Behavior events in project: {len(self.state.events)}",
                f"Behavior CSV: {behavior_path or 'not selected'}",
                f"TTL CSV: {ttl_path or 'not selected; assumes a shared clock'}",
            ]
            if result:
                lines.append(
                    f"Aligned: {result.get('matched_count', 0)} pairs · "
                    f"drift {result.get('drift_ppm', 0.0):.2f} ppm · "
                    f"max residual {result.get('max_abs_residual_ms', 0.0):.3f} ms"
                )
        else:
            lines = [
                f"项目中的行为事件：{len(self.state.events)}",
                f"行为 CSV：{behavior_path or '未选择'}",
                f"TTL CSV：{ttl_path or '未选择；将假设已共用时钟'}",
            ]
            if result:
                lines.append(
                    f"已对齐：{result.get('matched_count', 0)} 对 · "
                    f"漂移 {result.get('drift_ppm', 0.0):.2f} ppm · "
                    f"最大残差 {result.get('max_abs_residual_ms', 0.0):.3f} ms"
                )
        self.sync_inventory_label.setText("\n".join(lines))

    def _open_sample(self) -> None:
        try:
            dialog = DemoLibraryDialog(self, self.language)
            if dialog.exec() != QDialog.Accepted:
                return
            profile = DEMO_PROFILES[dialog.profile_key]
            root = self.workspace / "DemoData" / str(profile["folder"])
            state = load_or_generate_demo(root, dialog.profile_key)
            state.metadata["language"] = self.language
            save_project(state)
            self._load_state(state)
        except Exception as exc:  # noqa: BLE001 - user-facing dataset creation
            QMessageBox.warning(
                self,
                "Demo data unavailable"
                if self.language == "en_US"
                else "示例数据不可用",
                str(exc),
            )

    def _open_demo_folder(self) -> None:
        library_root = self.workspace / "DemoData"
        library_root.mkdir(parents=True, exist_ok=True)
        for key, profile in DEMO_PROFILES.items():
            root = library_root / str(profile["folder"])
            if not (root / MANIFEST_NAME).exists():
                state = load_or_generate_demo(root, key)
                save_project(state)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(library_root)))

    def _open_documentation(self) -> None:
        index = _documentation_page(self.language)
        if not index.exists():
            QMessageBox.warning(
                self,
                "Documentation unavailable"
                if self.language == "en_US"
                else "产品文档不可用",
                str(index),
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(index)))

    def _open_project(self) -> None:
        path = QFileDialog.getOpenFileName(
            self,
            "选择 NeuroEphys AI 项目",
            str(self.workspace),
            f"NeuroEphys AI ({MANIFEST_NAME})",
        )[0]
        if not path:
            return
        try:
            self._load_state(load_project(Path(path)))
        except Exception as exc:  # noqa: BLE001 - project parse errors are user-facing
            QMessageBox.warning(self, "无法打开项目", str(exc))

    def _load_state(self, state: ProjectState) -> None:
        self._restoring_project = True
        self.state = state
        stored_language = state.metadata.get("language")
        if stored_language in LANGUAGES:
            self.language = stored_language
        state.metadata["language"] = self.language
        self.preview = state.preprocessing or None
        self.matches = []
        self.project_label.setText(f"{state.name}  ·  {state.root}")
        self.metric_source.value_label.setText(state.source_type.upper())
        self.metric_channels.value_label.setText(str(state.channel_count or "—"))
        self.metric_duration.value_label.setText(f"{state.duration_seconds:.1f}s")
        self.metric_units.value_label.setText(str(len(state.sorted_spikes) or "—"))
        self.trace_controls.set_recording(
            state.duration_seconds,
            state.channel_count,
        )
        self.sorting_workbench.set_catalog(sorter_catalog())
        self.sorting_workbench.set_results(
            set(state.sorting_results),
            state.active_sorter_key,
        )
        for key, status in state.workflow_status.items():
            if key in self.step_buttons:
                self._set_step_status(key, status)
        if state.sorted_spikes:
            self._set_step_status("sorting", "completed")
            if state.ground_truth:
                self.matches = match_ground_truth(
                    state.ground_truth,
                    state.sorted_spikes,
                )
        restored_step = str(state.metadata.get("last_open_step", "import"))
        if restored_step not in self.step_buttons:
            restored_step = next(
                (
                    step.key
                    for step in reversed(STEPS)
                    if state.workflow_status.get(step.key) == "completed"
                ),
                "import",
            )
        self.current_step = restored_step
        self.pages.setCurrentWidget(self.workspace_page)
        self._apply_language()
        self._select_step(restored_step)
        configured = state.source_type not in {"unknown", "unconfigured"}
        self.run_button.setEnabled(configured)
        self.run_step_button.setEnabled(configured)
        self.status_label.setText(
            (
                "Empty project opened; import your data on this page"
                if self.language == "en_US"
                else "空白项目已建立；请在本页点击“导入我的电生理数据”"
            )
            if not configured
            else (
                "Project opened; run one step or the full workflow"
                if self.language == "en_US"
                else "项目已打开；可逐节点运行，也可执行完整流程"
            )
        )
        self._refresh_warnings()
        self._refresh_ai_sidebar()
        self._restoring_project = False
        self._set_project_clean()

    def _save(self, _checked: bool = False, *, notify: bool = True) -> bool:
        if not self.state:
            return True
        try:
            self.state.metadata["last_open_step"] = self.current_step
            self.state.metadata["last_saved_at"] = (
                datetime.now(timezone.utc).astimezone().isoformat()
            )
            path = save_project(self.state)
            self._set_project_clean()
            self.status_label.setText(
                f"Project saved: {path.name}"
                if self.language == "en_US"
                else f"项目已保存：{path.name}"
            )
            if notify:
                QMessageBox.information(
                    self,
                    "Project saved" if self.language == "en_US" else "项目已保存",
                    (
                        f"Project manifest:\n{path}\n\nThe project can be reopened "
                        "from the home page to resume at the last saved stage."
                        if self.language == "en_US"
                        else (
                            f"项目清单：\n{path}\n\n之后可从首页重新打开该文件，"
                            "从上次保存的阶段继续。"
                        )
                    ),
                )
            return True
        except Exception as exc:  # noqa: BLE001 - save failures are user-facing
            QMessageBox.critical(
                self,
                "Project save failed"
                if self.language == "en_US"
                else "项目保存失败",
                str(exc),
            )
            return False

    def closeEvent(self, event) -> None:
        if (
            self.ai_dialog is not None
            and self.ai_dialog.worker is not None
            and self.ai_dialog.worker.isRunning()
        ):
            QMessageBox.warning(
                self,
                "AI request is running"
                if self.language == "en_US"
                else "AI 请求仍在进行",
                (
                    "Wait for the current AI response before closing NeuroEphys AI. "
                    "The AI request cannot modify analysis results."
                    if self.language == "en_US"
                    else "请等待当前 AI 回复完成后再关闭 NeuroEphys AI；AI 请求不会修改分析结果。"
                ),
            )
            event.ignore()
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Analysis is running"
                if self.language == "en_US"
                else "分析仍在运行",
                (
                    "Wait for the current analysis to finish before closing NeuroEphys AI. "
                    "Completed results will then be saved to the project."
                    if self.language == "en_US"
                    else "请等待当前分析完成后再关闭 NeuroEphys AI；完成结果会自动保存到项目。"
                ),
            )
            event.ignore()
            return
        if not self.state or not self.project_dirty:
            event.accept()
            return
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle(
            "Unsaved project" if self.language == "en_US" else "项目尚未保存"
        )
        dialog.setText(
            f'"{self.state.name}" has changes that have not been saved.'
            if self.language == "en_US"
            else f"当前项目“{self.state.name}”还有未保存的修改。"
        )
        dialog.setInformativeText(
            "Save before closing so the data source, workflow stage, parameters, "
            "results, and audit log can be restored next time."
            if self.language == "en_US"
            else (
                "建议保存后再退出，以便下次恢复数据来源、当前阶段、参数、"
                "已有结果和审计记录。"
            )
        )
        dialog.setStandardButtons(
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        dialog.setDefaultButton(QMessageBox.Save)
        choice = dialog.exec()
        if choice == QMessageBox.Save:
            event.accept() if self._save(notify=False) else event.ignore()
        elif choice == QMessageBox.Discard:
            event.accept()
        else:
            event.ignore()

    def _refresh_environment(self) -> None:
        env = kilosort_environment()
        sorters = sorter_catalog()
        toolkit = provider_status()
        installed = [item["name"] for item in sorters if item["installed"]]
        gpu = (
            env["device_name"]
            if env["cuda_available"]
            else (
                "未检测到 CUDA GPU"
                if self.language == "zh_CN"
                else "No CUDA GPU detected"
            )
        )
        self.environment_label.setText(
            f"计算环境\n{gpu}\n可运行 sorter：{', '.join(installed) or '无'}\n"
            f"Elephant {toolkit['elephant']} · Neo {toolkit['neo']}"
            if self.language == "zh_CN"
            else f"Environment\n{gpu}\nAvailable sorters: {', '.join(installed) or 'None'}\n"
            f"Elephant {toolkit['elephant']} · Neo {toolkit['neo']}"
        )

    def _select_step(self, key: str) -> None:
        previous_option = (
            self.option_combo.currentData()
            if getattr(self, "current_step", None) == key and key != "sorting"
            else None
        )
        self.current_step = key
        step = next(item for item in STEPS if item.key == key)
        self.step_buttons[key].setChecked(True)
        title, subtitle = step_text(step.key, self.language)
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)
        tutorial_key = STEP_TUTORIAL[key]
        chapter = next(item for item in TUTORIALS if item["key"] == tutorial_key)
        self.help_title.setText(tutorial_value(chapter, "title", self.language))
        check_label = "检查：" if self.language == "zh_CN" else "Check: "
        self.help_text.setText(
            tutorial_value(chapter, "why", self.language)
            + "\n\n"
            + check_label
            + tutorial_value(chapter, "checks", self.language)
        )
        self.option_combo.blockSignals(True)
        self.option_combo.clear()
        if key == "qc":
            views = (
                [
                    ("多通道原始波形", "traces"),
                    ("质控指标总览", "summary"),
                    ("通道 × 频率功率图", "psd"),
                    ("记录期间质量时间线", "timeline"),
                ]
                if self.language == "zh_CN"
                else [
                    ("Multichannel raw traces", "traces"),
                    ("QC metric summary", "summary"),
                    ("Channel-by-frequency power", "psd"),
                    ("Quality timeline", "timeline"),
                ]
            )
            for label, value in views:
                self.option_combo.addItem(label, value)
        elif key == "preprocess":
            views = (
                [
                    ("AP / sorting 分支", "ap"),
                    ("LFP 分支", "lfp"),
                    ("可审计处理链与安全检查", "pipeline"),
                ]
                if self.language == "zh_CN"
                else [
                    ("AP / sorting branch", "ap"),
                    ("LFP branch", "lfp"),
                    ("Auditable chain and safeguards", "pipeline"),
                ]
            )
            for label, value in views:
                self.option_combo.addItem(label, value)
        elif key == "unit_qc" and self.state:
            self.option_combo.addItem(
                "Unit 指标总览" if self.language == "zh_CN" else "Unit metric overview",
                "overview",
            )
            for unit_id in sorted(self.state.sorted_spikes):
                self.option_combo.addItem(
                    f"Unit {unit_id} · "
                    + ("波形/ACG/ISI/稳定性" if self.language == "zh_CN" else "waveform/ACG/ISI/stability"),
                    f"unit:{unit_id}",
                )
        elif key == "decoding":
            for model in MODELS:
                label = (
                    f"分类 · {model}"
                    if self.language == "zh_CN"
                    else f"Classification · {model}"
                )
                self.option_combo.addItem(label, f"classification:{model}")
                self.option_combo.setItemData(
                    self.option_combo.count() - 1,
                    MODEL_DESCRIPTIONS.get(model, model),
                    Qt.ToolTipRole,
                )
            for model in REGRESSION_MODELS:
                label = (
                    f"回归 · {model}"
                    if self.language == "zh_CN"
                    else f"Regression · {model}"
                )
                self.option_combo.addItem(label, f"regression:{model}")
                self.option_combo.setItemData(
                    self.option_combo.count() - 1,
                    REGRESSION_DESCRIPTIONS.get(model, model),
                    Qt.ToolTipRole,
                )
        elif key == "statistics":
            views = (
                [
                    ("效应量与多重比较", "effects"),
                    ("条件检验与效应量", "conditions"),
                    ("分布、相关与混合模型", "diagnostics"),
                    ("相位锁定与 circular surrogate", "circular"),
                    ("样本层级与检验决策", "design"),
                ]
                if self.language == "zh_CN"
                else [
                    ("Effects and multiplicity", "effects"),
                    ("Condition tests and effects", "conditions"),
                    ("Distribution, correlation, and mixed model", "diagnostics"),
                    ("Phase locking and circular surrogate", "circular"),
                    ("Sampling hierarchy and test decisions", "design"),
                ]
            )
            for label, value in views:
                self.option_combo.addItem(label, value)
        elif key == "analysis" and self.state:
            for unit_id in sorted(self.state.sorted_spikes):
                self.option_combo.addItem(
                    (
                        f"事件 · Unit {unit_id}"
                        if self.language == "zh_CN"
                        else f"Event · Unit {unit_id}"
                    ),
                    f"event:{unit_id}",
                )
            analysis_views = (
                [
                    ("Spike train · 放电统计与 CCH", "spike:statistics"),
                    ("Spike train · 相关、STTC 与距离", "spike:relationships"),
                    ("LFP · PSD 与频段功率", "lfp:psd"),
                    ("LFP · coherence 与相位延迟", "lfp:coherence"),
                    ("LFP · 时频图", "lfp:spectrogram"),
                    ("Spike-field · 相位锁定", "coupling:phase"),
                    ("案例 · 呼吸频谱与 LFP coherence", "case:respiration"),
                    ("案例 · 呼吸相位-gamma 振幅耦合", "case:pac"),
                ]
                if self.language == "zh_CN"
                else [
                    ("Spike train · statistics and CCH", "spike:statistics"),
                    ("Spike train · correlation, STTC, distances", "spike:relationships"),
                    ("LFP · PSD and band power", "lfp:psd"),
                    ("LFP · coherence and phase lag", "lfp:coherence"),
                    ("LFP · time-frequency map", "lfp:spectrogram"),
                    ("Spike-field · phase locking", "coupling:phase"),
                    ("Case · respiration PSD and LFP coherence", "case:respiration"),
                    ("Case · respiration phase-gamma amplitude", "case:pac"),
                ]
            )
            for label, value in analysis_views:
                self.option_combo.addItem(label, value)
        if previous_option is not None:
            previous_index = self.option_combo.findData(previous_option)
            if previous_index >= 0:
                self.option_combo.setCurrentIndex(previous_index)
        self.sorting_workbench.setVisible(key == "sorting")
        self.unit_curation_panel.setVisible(key == "unit_qc")
        self.sync_workbench.setVisible(key == "sync")
        self.project_data_panel.setVisible(key == "import")
        self._update_project_data_panel()
        self._refresh_sync_inventory()
        for metric in (
            self.metric_source,
            self.metric_channels,
            self.metric_duration,
            self.metric_units,
        ):
            metric.setVisible(key != "sorting")
        if key == "sorting":
            self.sorting_workbench.set_catalog(sorter_catalog())
            self.sorting_workbench.set_results(
                set(self.state.sorting_results) if self.state else set(),
                self.state.active_sorter_key if self.state else None,
            )
        self.trace_controls.setVisible(key in {"import", "qc"})
        self.option_combo.setVisible(key != "sorting" and self.option_combo.count() > 0)
        self.run_step_button.setText(
            (
                "Run selected analysis"
                if self.language == "en_US"
                else "运行当前所选分析"
            )
            if key in {"qc", "preprocess", "analysis", "statistics", "decoding"}
            else tr("run_step", self.language)
        )
        self.option_combo.blockSignals(False)
        self._update_run_context()
        self._update_page_option_help()
        self._refresh_unit_curation_summary()
        self._refresh_ai_sidebar()
        self._refresh_figure()
        self._refresh_table()
        self._refresh_warnings()

    def _open_unit_curation(self) -> None:
        if not self.state or not self.state.sorted_spikes:
            QMessageBox.information(
                self,
                "No candidate Units"
                if self.language == "en_US"
                else "尚无候选 Unit",
                (
                    "Run or load a sorting result, then compute Unit QC before "
                    "starting manual curation."
                    if self.language == "en_US"
                    else "请先运行或载入 sorting 结果并计算 Unit 质控，再开始人工复核。"
                ),
            )
            return
        if not self.state.unit_metrics:
            QMessageBox.information(
                self,
                "Unit QC required"
                if self.language == "en_US"
                else "需要先计算 Unit 质控",
                (
                    "Compute Unit QC so that waveform, ACG, ISI and stability "
                    "evidence are available."
                    if self.language == "en_US"
                    else "请先计算 Unit 质控，生成波形、ACG、ISI 和稳定性证据。"
                ),
            )
            return
        dialog = UnitCurationDialog(
            self.state,
            self.language,
            saved_handler=self._unit_curation_saved,
            parent=self,
        )
        dialog.exec()
        self._refresh_unit_curation_summary()
        self._refresh_table()

    def _unit_curation_saved(self) -> None:
        self._mark_project_dirty()
        self._refresh_unit_curation_summary()
        self._refresh_table()

    def _refresh_unit_curation_summary(self) -> None:
        if not hasattr(self, "unit_curation_summary"):
            return
        if not self.state or not self.state.sorted_spikes:
            self.unit_curation_summary.setText(
                "No candidate Units are loaded."
                if self.language == "en_US"
                else "尚未载入候选 Unit。"
            )
            self.unit_curation_button.setEnabled(False)
            return
        self.unit_curation_button.setEnabled(bool(self.state.unit_metrics))
        summary = curation_summary(self.state)
        self.unit_curation_summary.setText(
            (
                f"Manual review: {summary['reviewed_unit_count']} / "
                f"{summary['candidate_unit_count']} candidate clusters. "
                "Automatic metrics screen candidates; the final label requires "
                "waveform, refractory-period, amplitude, stability and "
                "channel/spatial review."
                if self.language == "en_US"
                else (
                    f"人工复核：{summary['reviewed_unit_count']} / "
                    f"{summary['candidate_unit_count']} 个候选 cluster。自动指标用于初筛；"
                    "最终标签需要结合波形、不应期、振幅、稳定性和通道/空间分布判断。"
                )
            )
        )

    def _on_option_changed(self) -> None:
        self._update_run_context()
        self._update_page_option_help()
        self._refresh_ai_sidebar()
        self._refresh_figure()

    def _update_run_context(self) -> None:
        if not hasattr(self, "run_context_label"):
            return
        title = step_text(self.current_step, self.language)[0]
        if self.current_step == "sorting" and hasattr(self, "sorting_workbench"):
            selection = self.sorting_workbench.selected_sorter()
        else:
            selection = (
                self.option_combo.currentText()
                if hasattr(self, "option_combo") and self.option_combo.isVisible()
                else ""
            )
        separator = " · " if selection else ""
        prefix = "Current" if self.language == "en_US" else "当前"
        self.run_context_label.setText(
            f"{prefix}：{title}{separator}{selection}"
            if self.language == "zh_CN"
            else f"{prefix}: {title}{separator}{selection}"
        )

    def _on_sorter_selected(self, sorter_key: str) -> None:
        self._update_run_context()
        self.help_title.setText(
            f"{sorter_key} · "
            + (
                "input, preprocessing, and outputs"
                if self.language == "en_US"
                else "输入、预处理与输出"
            )
        )
        self.help_text.setText(self.sorting_workbench.selected_description())
        if not self.state or sorter_key not in self.state.sorting_results:
            if self.state:
                self._refresh_figure()
                self._refresh_table()
            return
        if self.state.active_sorter_key == sorter_key:
            return
        activate_sorting_result(self.state, sorter_key)
        self.matches = (
            match_ground_truth(self.state.ground_truth, self.state.sorted_spikes)
            if self.state.ground_truth
            else []
        )
        self.state.analysis = {}
        self.state.statistics = {}
        self.state.decoding = {}
        self.state.regression = {}
        unit_qc_status = "completed" if self.state.unit_metrics else "pending"
        self.state.workflow_status["unit_qc"] = unit_qc_status
        self._set_step_status("unit_qc", unit_qc_status)
        for key in ("analysis", "statistics", "decoding", "export"):
            self.state.workflow_status[key] = "pending"
            self._set_step_status(key, "pending")
        self.metric_units.value_label.setText(str(len(self.state.sorted_spikes)))
        self.state.log(f"Active sorting result changed to {sorter_key}")
        self.sorting_workbench.set_results(
            set(self.state.sorting_results),
            self.state.active_sorter_key,
        )
        save_project(self.state)
        self._set_project_clean()
        self._refresh_figure()
        self._refresh_table()
        self._refresh_warnings()
        self._refresh_ai_sidebar()

    def _on_sorting_diagnostic_changed(self, _: str) -> None:
        self._refresh_figure()
        self._refresh_table()

    def _update_page_option_help(self) -> None:
        chapter = next(
            item
            for item in TUTORIALS
            if item["key"] == STEP_TUTORIAL[self.current_step]
        )
        check_label = "检查：" if self.language == "zh_CN" else "Check: "
        text = (
            tutorial_value(chapter, "why", self.language)
            + "\n\n"
            + check_label
            + tutorial_value(chapter, "checks", self.language)
        )
        if self.current_step == "statistics":
            heading = (
                "\n\n已集成方法："
                if self.language == "zh_CN"
                else "\n\nIntegrated methods: "
            )
            text += heading + "\n" + " · ".join(STATISTICAL_METHODS)
        elif self.current_step == "decoding":
            selection = str(self.option_combo.currentData() or "")
            task, _, model = selection.partition(":")
            descriptions = (
                REGRESSION_DESCRIPTIONS if task == "regression" else MODEL_DESCRIPTIONS
            )
            description = descriptions.get(model, "")
            validation = (
                "运行后报告分层交叉验证、置换基线、混淆矩阵/误差、特征重要性和群体降维。"
                if self.language == "zh_CN"
                else "The run reports stratified cross-validation, a permutation baseline, "
                "confusion/error metrics, feature importance, and population reduction."
            )
            text += f"\n\n{model}\n{description}\n{validation}"
        elif self.current_step == "analysis":
            selection = str(self.option_combo.currentData() or "")
            method = next(
                (
                    item
                    for item in METHOD_CATALOG
                    if selection.startswith(
                        {
                            "spike_train": "spike:",
                            "lfp": "lfp:",
                            "combined": "coupling:",
                        }.get(item["stage"], "__none__")
                    )
                ),
                None,
            )
            if method:
                text += (
                    f"\n\n{method['provider']} · {method['status']}\n"
                    f"{method['methods']}\nRequires: {method['requires']}"
                )
            elif selection.startswith("case:"):
                text += (
                    "\n\n该案例使用 NeuroEphys AI 模拟数据验证方法结构，未复制原论文图，"
                    "也不声称复现论文数值。"
                    if self.language == "zh_CN"
                    else "\n\nThis case validates the method structure on NeuroEphys AI "
                    "simulation data. It neither copies paper figures nor claims to "
                    "reproduce the paper's numerical findings."
                )
        self.help_text.setText(text)

    def _replace_figure(self, figure) -> None:
        self.figure_layout.removeWidget(self.toolbar)
        self.figure_layout.removeWidget(self.canvas)
        self.toolbar.setParent(None)
        self.toolbar.deleteLater()
        self.canvas.setParent(None)
        self.canvas.deleteLater()
        self.canvas = FigureCanvasQTAgg(figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = NavigationToolbar2QT(self.canvas, self.figure_host)
        self.figure_layout.addWidget(self.toolbar)
        self.figure_layout.addWidget(self.canvas, 1)
        self._connect_figure_interactions()
        self._refresh_panel_controls()
        self.canvas.draw_idle()
        if self.plot_style_combo.currentData() != "standard":
            self._apply_plot_style()

    def _refresh_figure(self) -> None:
        if not self.state:
            return
        key = self.current_step
        trace_values = self.trace_controls.values()
        option = str(self.option_combo.currentData() or "")
        if key == "import":
            figure = raw_overview_figure(
                self.state,
                show_ground_truth=True,
                **trace_values,
            )
        elif key == "qc" and option == "traces":
            figure = raw_overview_figure(
                self.state,
                show_ground_truth=False,
                **trace_values,
            )
        elif key == "qc" and self.state.qc:
            figure = qc_diagnostics_figure(
                self.state, option or "summary"
            )
        elif key == "preprocess" and self.preview:
            figure = preprocessing_diagnostics_figure(
                self.preview,
                self.state,
                option or "ap",
            )
        elif key == "sorting":
            selected_sorter = self.sorting_workbench.selected_sorter()
            diagnostic = self.sorting_workbench.selected_diagnostic()
            if selected_sorter not in self.state.sorting_results:
                figure = pending_step_figure(
                    self.state,
                    "Spike sorting",
                    (
                        f"Run the selected sorter ({selected_sorter}) on the current "
                        "raw recording. Results are stored separately and normalized "
                        "to seconds for comparison."
                        if self.language == "en_US"
                        else (
                            f"在当前原始记录上实际运行所选 sorter（{selected_sorter}）。"
                            "每个 sorter 的原生结果单独保存，再统一为秒级接口用于比较。"
                        )
                    ),
                    [
                        (
                            f"Recording: {self.state.channel_count} channels, "
                            f"{self.state.duration_seconds:.1f} s"
                            if self.language == "en_US"
                            else (
                                f"记录：{self.state.channel_count} 通道，"
                                f"{self.state.duration_seconds:.1f} 秒"
                            )
                        ),
                        (
                            f"Selected sorter: {selected_sorter}"
                            if self.language == "en_US"
                            else f"当前选择：{selected_sorter}"
                        ),
                    ],
                    (
                        "Native output, run log, parameters, normalized Unit/spike "
                        "times, and optional cross-sorter comparison."
                        if self.language == "en_US"
                        else "原生输出、运行日志、参数、统一 Unit/spike 时间和跨 sorter 比较。"
                    ),
                )
            elif diagnostic == "comparison" and len(self.state.sorting_results) >= 2:
                figure = sorting_diagnostics_figure(self.state, "comparison")
            else:
                if self.state.active_sorter_key != selected_sorter:
                    activate_sorting_result(self.state, selected_sorter)
                if diagnostic == "validation" and self.matches:
                    figure = sorting_figure(self.matches, self.state)
                else:
                    figure = sorting_diagnostics_figure(self.state, diagnostic)
        elif key == "unit_qc" and self.state.unit_metrics:
            figure = unit_metrics_figure(
                self.state, option or "overview"
            )
        elif key == "sync":
            figure = synchronization_figure(self.state)
        elif key == "behavior":
            figure = behavior_figure(self.state)
        elif key == "analysis" and (
            (option.startswith("event:") and self.state.analysis)
            or (option.startswith("spike:") and self.state.spike_train_analysis)
            or (option.startswith("lfp:") and self.state.lfp_analysis)
            or (option.startswith("coupling:") and self.state.spike_field_analysis)
            or (
                option.startswith("case:")
                and self.state.case_studies.get("respiration")
            )
        ):
            figure = neural_toolkit_figure(
                self.state, option or "event:0"
            )
        elif key == "statistics" and self.state.statistics:
            figure = statistics_figure(
                self.state, option or "effects"
            )
        elif key == "decoding":
            selection = option
            if selection.startswith("regression:") and self.state.regression:
                figure = regression_figure(self.state)
            elif self.state.decoding:
                figure = decoding_figure(self.state)
            else:
                figure = self._pending_current_step(option)
        else:
            figure = self._pending_current_step(option)
        self._replace_figure(figure)

    def _pending_current_step(self, option: str = ""):
        if not self.state:
            return raw_overview_figure_empty(
                ProjectState(root=self.workspace)
            )
        step = next(item for item in STEPS if item.key == self.current_step)
        chapter = next(
            item
            for item in TUTORIALS
            if item["key"] == STEP_TUTORIAL[self.current_step]
        )
        inputs = [
            (
                f"Raw voltage: {'available' if self.state.ready else 'unavailable'}"
                if self.language == "en_US"
                else f"原始电压：{'可用' if self.state.ready else '不可用'}"
            ),
            (
                f"Units: {len(self.state.sorted_spikes)}"
                if self.language == "en_US"
                else f"Unit：{len(self.state.sorted_spikes)}"
            ),
            (
                f"Events: {len(self.state.events)}"
                if self.language == "en_US"
                else f"事件：{len(self.state.events)}"
            ),
            (
                f"Defined trials: {len(self.state.trials)}"
                if self.language == "en_US"
                else f"已定义trial：{len(self.state.trials)}"
            ),
            (
                f"Selected analysis: {option or self.current_step}"
                if self.language == "en_US"
                else f"当前所选分析：{option or self.current_step}"
            ),
        ]
        return pending_step_figure(
            self.state,
            step_text(step.key, self.language)[0] + " · ",
            tutorial_value(chapter, "why", self.language),
            inputs,
            tutorial_value(chapter, "output", self.language),
        )

    def _refresh_table(self) -> None:
        if not self.state:
            return
        rows: list[dict] = []
        if self.current_step == "unit_qc":
            rows = self.state.unit_metrics
        elif self.current_step == "analysis":
            selection = str(self.option_combo.currentData() or "")
            if selection == "spike:statistics":
                rows = self.state.spike_train_analysis.get("rows", [])
            elif selection == "coupling:phase":
                rows = self.state.spike_field_analysis.get("rows", [])
            elif selection.startswith("case:"):
                rows = self.state.case_studies.get("respiration", {}).get("rows", [])
        elif self.current_step == "statistics":
            rows = (
                self.state.spike_field_analysis.get("rows", [])
                if self.option_combo.currentData() == "circular"
                else self.state.statistics.get("rows", [])
            )
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
        english = self.language == "en_US"
        messages = (
            [
                f"Source: {self.state.source_type}",
                f"Raw voltage: {'available' if self.state.ready else 'unavailable'}",
                f"Events: {len(self.state.events)}",
                f"Project: {self.state.name}",
            ]
            if english
            else [
                f"来源：{self.state.source_type}",
                f"原始电压：{'可用' if self.state.ready else '不可用'}",
                f"事件：{len(self.state.events)}",
                f"项目：{self.state.root}",
            ]
        )
        if self.state.qc:
            messages.append(
                f"Bad channels: {self.state.qc.get('bad_channels', []) or 'none detected'}"
                if english
                else f"坏通道：{self.state.qc.get('bad_channels', []) or '未检出'}"
            )
            messages.append(
                f"50 Hz ratio: {self.state.qc.get('line_noise_ratio', 0):.2f}"
                if english
                else f"50 Hz 比值：{self.state.qc.get('line_noise_ratio', 0):.2f}"
            )
        if self.state.sorted_spikes:
            messages.append(
                f"Units: {len(self.state.sorted_spikes)}"
                if english
                else f"Unit：{len(self.state.sorted_spikes)}"
            )
        if self.state.statistics:
            messages.append(
                f"FDR significant: {self.state.statistics['significant_count']}"
                if english
                else f"FDR 显著：{self.state.statistics['significant_count']}"
            )
        if self.state.decoding:
            messages.append(
                f"Decoding: {self.state.decoding['balanced_accuracy']:.3f}, "
                f"permutation p={self.state.decoding['permutation_p']:.4f}"
                if english
                else f"解码：{self.state.decoding['balanced_accuracy']:.3f}，"
                f"置换 p={self.state.decoding['permutation_p']:.4f}"
            )
        if self.state.regression:
            messages.append(
                f"Regression: R²={self.state.regression['r2']:.3f}, "
                f"MAE={self.state.regression['mae_seconds']:.3f}s"
                if english
                else f"回归：R²={self.state.regression['r2']:.3f}，"
                f"MAE={self.state.regression['mae_seconds']:.3f}s"
            )
        self.warning_text.setText("\n".join(messages))
        self.log_view.setPlainText("\n".join(self.state.run_log))
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def _set_step_status(self, key: str, status: str) -> None:
        button = self.step_buttons[key]
        button.setProperty("status", status)
        button.style().unpolish(button)
        button.style().polish(button)
        if self.state:
            self.state.workflow_status[key] = status
            self._mark_project_dirty()

    def _run_full_pipeline(self) -> None:
        self._start_worker([step.key for step in STEPS])

    def _run_current_step(self) -> None:
        self._start_worker([self.current_step])

    def _start_worker(
        self,
        keys: list[str],
        *,
        tool_arguments: dict | None = None,
    ) -> None:
        if not self.state:
            QMessageBox.information(self, "没有项目", "请先从首页导入或生成数据。")
            return
        if self.state.source_type in {"unknown", "unconfigured"}:
            QMessageBox.information(
                self,
                "Import data first"
                if self.language == "en_US"
                else "请先导入数据",
                (
                    "This is an empty project. Open the Data and project page and "
                    "choose Import my electrophysiology data."
                    if self.language == "en_US"
                    else (
                        "当前是空白项目。请在“数据与项目”页面点击"
                        "“导入我的电生理数据”。"
                    )
                ),
            )
            return
        if self.worker and self.worker.isRunning():
            return
        sorter_name = self.sorting_workbench.selected_sorter()
        sorter_settings = self.sorting_workbench.settings()
        selected_provenance = self.state.sorting_provenance.get(
            sorter_name,
            {},
        )
        if "sorting" in keys and selected_provenance.get(
            "source_files_read_only"
        ):
            keys = [key for key in keys if key != "sorting"]
            if not keys:
                QMessageBox.information(
                    self,
                    (
                        "Imported sorting result"
                        if self.language == "en_US"
                        else "已导入 sorting 结果"
                    ),
                    (
                        "This result is already loaded through the common Unit/spike "
                        "interface. Select Unit QC to compute diagnostics, or select "
                        "an executable sorter row to create a new sorting result."
                        if self.language == "en_US"
                        else (
                            "该结果已经通过统一 Unit/spike 接口载入。请进入 Unit 质控"
                            "计算诊断，或选择一个可运行 sorter 生成新的 sorting 结果。"
                        )
                    ),
                )
                return
        model_name = "classification:Logistic regression"
        if self.current_step == "decoding" and self.option_combo.currentData():
            model_name = self.option_combo.currentData()
        analysis_selection = (
            str(self.option_combo.currentData() or "")
            if self.current_step == "analysis"
            else ""
        )
        step_names = [
            step_text(key, self.language)[0]
            for key in keys
        ]
        details = "\n".join(f"• {name}" for name in step_names)
        expensive_note = ""
        if "sorting" in keys:
            expensive_note += (
                f"\n\nSorter: {sorter_name}"
                if self.language == "en_US"
                else f"\n\nSorter：{sorter_name}"
            )
        if "decoding" in keys:
            expensive_note += (
                f"\nModel: {model_name}"
                if self.language == "en_US"
                else f"\n模型：{model_name}"
            )
        answer = QMessageBox.question(
            self,
            "Confirm analysis run"
            if self.language == "en_US"
            else "确认运行分析",
            (
                f"Project: {self.state.name}\nThe following steps will run:\n"
                f"{details}{expensive_note}\n\nExisting results remain in the audit "
                "record; new results will be saved to this project. Continue?"
                if self.language == "en_US"
                else (
                    f"项目：{self.state.name}\n即将运行：\n{details}{expensive_note}\n\n"
                    "已有结果会保留在审计记录中，新结果将保存到当前项目。是否继续？"
                )
            ),
        )
        if answer != QMessageBox.Yes:
            return
        self.active_run_keys = list(keys)
        self.active_run_started = datetime.now(timezone.utc).astimezone()
        self.run_button.setEnabled(False)
        self.run_step_button.setEnabled(False)
        self.progress_bar.setFormat(
            "Running… %v/%m" if self.language == "en_US" else "正在运行… %v/%m"
        )
        self.worker = PipelineWorker(
            self.state,
            keys,
            sorter_name,
            sorter_settings,
            model_name,
            analysis_selection,
            tool_arguments,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.step_done.connect(self._on_step_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.succeeded.connect(self._on_succeeded)
        self.run_elapsed_timer.start()
        self.worker.start()

    def _update_run_elapsed(self) -> None:
        if self.active_run_started is None:
            return
        elapsed = int(
            (
                datetime.now(timezone.utc).astimezone() - self.active_run_started
            ).total_seconds()
        )
        self.progress_bar.setFormat(
            f"Running {elapsed} s · %v/%m"
            if self.language == "en_US"
            else f"正在运行 {elapsed} 秒 · %v/%m"
        )

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
                self.metric_units.value_label.setText(
                    str(len(self.state.sorted_spikes))
                )
                self.sorting_workbench.set_results(
                    set(self.state.sorting_results),
                    self.state.active_sorter_key,
                )
        if self.state:
            self.state.metadata["last_open_step"] = key
            save_project(self.state)
            self._set_project_clean()
        self._select_step(key)

    def _on_failed(self, key: str, details: str) -> None:
        self.run_elapsed_timer.stop()
        self._set_step_status(key, "failed")
        self.run_button.setEnabled(True)
        self.run_step_button.setEnabled(True)
        self.progress_bar.setFormat(
            "Failed" if self.language == "en_US" else "运行失败"
        )
        self.status_label.setText(details.splitlines()[0])
        if self.state:
            self.state.log(
                f"{key} failed: {details.splitlines()[0]}"
                if self.language == "en_US"
                else f"{key} 失败：{details.splitlines()[0]}"
            )
            self._mark_project_dirty()
            pending = self.state.metadata.get("pending_ai_tool_call")
            if isinstance(pending, dict):
                pending["status"] = "failed"
                pending["failed_stage"] = key
                pending["error"] = details.splitlines()[0]
                save_project(self.state)
                self._set_project_clean()
        self._refresh_warnings()
        self._refresh_ai_sidebar()
        failed_record = {}
        if self.state:
            failed_records = [
                record
                for record in self.state.metadata.get("structured_run_log", [])
                if record.get("stage") == key and record.get("status") == "failed"
            ]
            if failed_records:
                failed_record = failed_records[-1]
        retained = "\n".join(
            f"• {path}" for path in failed_record.get("outputs", [])
        ) or ("• Project state and completed prior stages" if self.language == "en_US" else "• 项目状态及此前已完成节点")
        recovery = failed_record.get("recovery") or (
            "Review the error, correct the input or parameters, and rerun this stage."
            if self.language == "en_US"
            else "核对错误、修正输入或参数后重新运行当前节点。"
        )
        QMessageBox.critical(
            self,
            "Step failed" if self.language == "en_US" else "节点运行失败",
            (
                f"Failed stage: {step_text(key, self.language)[0]}\n"
                f"Tool: {failed_record.get('tool') or '—'}\n"
                f"Reason: {details.splitlines()[0]}\n\n"
                f"Retained outputs:\n{retained}\n\n"
                f"Recovery: {recovery}\n\n"
                "Full details were written to the structured audit log."
                if self.language == "en_US"
                else (
                    f"失败位置：{step_text(key, self.language)[0]}\n"
                    f"执行工具：{failed_record.get('tool') or '—'}\n"
                    f"错误原因：{details.splitlines()[0]}\n\n"
                    f"已保留结果：\n{retained}\n\n"
                    f"恢复方式：{recovery}\n\n"
                    "完整信息已写入结构化审计日志。"
                )
            ),
        )
        self.active_run_keys = []
        self.active_run_started = None

    def _on_succeeded(self) -> None:
        self.run_elapsed_timer.stop()
        self.run_button.setEnabled(True)
        self.run_step_button.setEnabled(True)
        self.progress_bar.setFormat(
            "Completed" if self.language == "en_US" else "运行完成"
        )
        self.status_label.setText(
            "Selected steps completed; results, parameters, and logs were saved"
            if self.language == "en_US"
            else "所选节点已完成，结果、参数与日志已经保存"
        )
        self._refresh_figure()
        self._refresh_table()
        self._refresh_warnings()
        elapsed = 0.0
        if self.active_run_started is not None:
            elapsed = (
                datetime.now(timezone.utc).astimezone() - self.active_run_started
            ).total_seconds()
        completed_names = [
            step_text(key, self.language)[0] for key in self.active_run_keys
        ]
        completed_text = "\n".join(f"• {name}" for name in completed_names)
        recent_records: list[dict] = []
        if self.state:
            all_records = self.state.metadata.get("structured_run_log", [])
            for key in self.active_run_keys:
                matching = [
                    record
                    for record in all_records
                    if record.get("stage") == key
                    and record.get("status") == "completed"
                ]
                if matching:
                    recent_records.append(matching[-1])
            pending = self.state.metadata.get("pending_ai_tool_call")
            if isinstance(pending, dict) and pending.get("status") == "user_confirmed":
                pending["status"] = "completed"
                pending["run_ids"] = [
                    record.get("run_id") for record in recent_records
                ]
                pending["artifact_ids"] = [
                    artifact.get("id")
                    for record in recent_records
                    for artifact in record.get("artifacts", [])
                    if isinstance(artifact, dict)
                ]
                pending["completed_at"] = (
                    datetime.now(timezone.utc).astimezone().isoformat()
                )
                save_project(self.state)
                self._set_project_clean()
        inputs = list(
            dict.fromkeys(
                str(path)
                for record in recent_records
                for path in record.get("input_files", [])
            )
        )
        tools = list(
            dict.fromkeys(
                str(record.get("tool"))
                for record in recent_records
                if record.get("tool")
            )
        )
        outputs = list(
            dict.fromkeys(
                str(path)
                for record in recent_records
                for path in record.get("outputs", [])
            )
        )
        warning_count = sum(
            len(record.get("warnings", [])) for record in recent_records
        )
        input_text = "\n".join(f"• {path}" for path in inputs) or "• —"
        tool_text = ", ".join(tools) or "—"
        output_text = "\n".join(f"• {path}" for path in outputs) or (
            f"• {self.state.root if self.state else '—'}"
        )
        current_indices = [
            index
            for index, step in enumerate(STEPS)
            if step.key in self.active_run_keys
        ]
        next_step = "—"
        if current_indices and max(current_indices) + 1 < len(STEPS):
            next_step = step_text(
                STEPS[max(current_indices) + 1].key, self.language
            )[0]
        QMessageBox.information(
            self,
            "Analysis completed"
            if self.language == "en_US"
            else "分析运行完成",
            (
                f"Project: {self.state.name if self.state else '—'}\n"
                f"Input:\n{input_text}\n\n"
                f"Processing tool: {tool_text}\n"
                f"Completed:\n{completed_text}\n"
                f"Elapsed: {elapsed:.1f} s\n\n"
                f"Output:\n{output_text}\n\n"
                f"Warnings captured: {warning_count}\n"
                f"Suggested next step: {next_step}"
                if self.language == "en_US"
                else (
                    f"项目：{self.state.name if self.state else '—'}\n"
                    f"输入：\n{input_text}\n\n"
                    f"处理工具：{tool_text}\n"
                    f"结果：\n{completed_text}\n"
                    f"用时：{elapsed:.1f} 秒\n\n"
                    f"输出位置：\n{output_text}\n\n"
                    f"记录到的警告：{warning_count} 条\n"
                    f"建议下一步：{next_step}"
                )
            ),
        )
        self.active_run_keys = []
        self.active_run_started = None
        self._refresh_ai_sidebar()

    def _toggle_ai_panel(self) -> None:
        visible = not self.assistant_panel.isVisible()
        self.assistant_panel.setVisible(visible)
        if visible:
            self.assistant_tabs.setCurrentIndex(0)
            self.ai_sidebar_question.setFocus()

    def _sidebar_ai_mode_changed(self) -> None:
        settings = (
            self.ai_dialog.settings
            if self.ai_dialog is not None
            else load_ai_settings()
        )
        settings.mode = str(self.sidebar_ai_mode_combo.currentData())
        save_ai_preferences(settings)
        if self.ai_dialog is not None:
            self.ai_dialog.settings.mode = settings.mode
            self.ai_dialog.mode_combo.blockSignals(True)
            self.ai_dialog.mode_combo.setCurrentIndex(
                max(self.ai_dialog.mode_combo.findData(settings.mode), 0)
            )
            self.ai_dialog.mode_combo.blockSignals(False)
            self.ai_dialog._refresh_status()
        self._refresh_ai_sidebar()

    def _refresh_ai_sidebar(self) -> None:
        if not hasattr(self, "ai_context_label"):
            return
        english = self.language == "en_US"
        settings = (
            self.ai_dialog.settings
            if self.ai_dialog is not None
            else load_ai_settings()
        )
        if settings.ai_mode == AIMode.MANUAL:
            service_text = (
                "Manual mode · no online request will be sent."
                if english
                else "手动模式 · 不会发送在线请求。"
            )
        elif settings.configured:
            service_text = (
                (
                    f"Ready · {settings.provider_label} · {settings.model}"
                    if english
                    else f"服务就绪 · {settings.provider_label} · {settings.model}"
                )
            )
        else:
            service_text = (
                "AI is not configured. Open Settings to add an online API or Ollama."
                if english
                else "AI 尚未配置。请在“设置”中添加在线 API 或 Ollama。"
            )
        self.ai_sidebar_status.setText(service_text)
        if self.state is None:
            self.ai_context_label.setText(
                "No project context"
                if english
                else "尚未打开项目"
            )
            self.ai_sidebar_conversation.setHtml(
                (
                    "<p><b>AI assistant</b></p><p>Create or open a project to let "
                    "the assistant inspect a path-free structured summary.</p>"
                    if english
                    else (
                        "<p><b>AI 助手</b></p><p>创建或打开项目后，助手可读取"
                        "不含本地路径的结构化摘要。</p>"
                    )
                )
            )
            return
        self.state.metadata["ui_context"] = {
            "current_stage": self.current_step,
            "selected_view": (
                str(self.option_combo.currentData() or "")
                if hasattr(self, "option_combo")
                else ""
            ),
            "selected_sorter": (
                self.sorting_workbench.selected_sorter()
                if hasattr(self, "sorting_workbench")
                else None
            ),
        }
        self.ai_context_label.setText(
            (
                f"Context: {self.state.name}\n"
                f"Stage: {step_text(self.current_step, self.language)[0]}\n"
                f"Units: {len(self.state.sorted_spikes)} · "
                f"Events: {len(self.state.events)}"
                if english
                else (
                    f"上下文：{self.state.name}\n"
                    f"阶段：{step_text(self.current_step, self.language)[0]}\n"
                    f"Unit：{len(self.state.sorted_spikes)} · "
                    f"事件：{len(self.state.events)}"
                )
            )
        )
        history = self.state.metadata.get("ai_history", [])
        if history:
            blocks = []
            for record in history[-5:]:
                question = escape(str(record.get("question", "")).strip())
                answer = escape(str(record.get("answer", "")).strip())
                if question:
                    blocks.append(
                        (
                            '<div class="message user"><b>You</b><br>'
                            if english
                            else '<div class="message user"><b>你</b><br>'
                        )
                        + question.replace("\n", "<br>")
                        + "</div>"
                    )
                if answer:
                    calls = record.get("tool_calls", [])
                    action_text = ""
                    if calls:
                        names = ", ".join(
                            escape(str(item.get("name", ""))) for item in calls
                        )
                        action_text = (
                            f"<br><span class='actions'>Proposed: {names}</span>"
                            if english
                            else f"<br><span class='actions'>建议操作：{names}</span>"
                        )
                    blocks.append(
                        '<div class="message assistant"><b>NeuroEphys AI</b><br>'
                        + answer.replace("\n", "<br>")
                        + action_text
                        + "</div>"
                    )
            self.ai_sidebar_conversation.setHtml(
                """
                <style>
                  body { color:#f6f2fa; font-family:'Segoe UI'; }
                  .message { margin:8px 2px; padding:9px 10px; border-radius:5px; }
                  .user { background:#211d2d; border:1px solid #3b354a; }
                  .assistant { background:#171521; border:1px solid #5c4968; }
                  .actions { color:#62d8a4; }
                </style>
                """
                + "".join(blocks)
            )
            scroll = self.ai_sidebar_conversation.verticalScrollBar()
            scroll.setValue(scroll.maximum())
        else:
            self.ai_sidebar_conversation.setHtml(
                (
                    "<p><b>No conversation yet.</b></p><p>Ask about the current "
                    "recording, a parameter, an error, or the next evidence-producing "
                    "step.</p>"
                    if english
                    else (
                        "<p><b>尚无对话。</b></p><p>可以询问当前记录、参数、"
                        "报错，或下一项能够产生证据的分析步骤。</p>"
                    )
                )
            )

    def _ensure_ai_dialog(self) -> AIAssistantDialog:
        if self.ai_dialog is None:
            self.ai_dialog = AIAssistantDialog(
                state_getter=lambda: self.state,
                stage_getter=lambda: self.current_step,
                language_getter=lambda: self.language,
                response_handler=self._record_ai_response,
                plan_handler=self._apply_ai_plan,
                tool_handler=self._handle_ai_tool_call,
                manual_handler=self._open_ai_documentation,
                parent=self,
            )
        self.ai_dialog.set_language(self.language)
        self.sidebar_ai_mode_combo.blockSignals(True)
        self.sidebar_ai_mode_combo.setCurrentIndex(
            max(
                self.sidebar_ai_mode_combo.findData(
                    self.ai_dialog.settings.mode
                ),
                0,
            )
        )
        self.sidebar_ai_mode_combo.blockSignals(False)
        records = (
            list(self.state.metadata.get("ai_history", []))
            if self.state
            else []
        )
        token = str(self.state.root) if self.state else "<no-project>"
        self.ai_dialog.load_project_history(records, token)
        return self.ai_dialog

    def _sidebar_ai_settings(self) -> None:
        dialog = self._ensure_ai_dialog()
        dialog._open_settings()
        self._refresh_ai_sidebar()

    def _sidebar_ai_send(self) -> None:
        question = self.ai_sidebar_question.toPlainText().strip()
        if not question:
            return
        dialog = self._ensure_ai_dialog()
        dialog.question_edit.setPlainText(question)
        self.ai_sidebar_status.setText(
            "Waiting for the configured provider..."
            if self.language == "en_US"
            else "正在等待已配置的模型服务……"
        )
        dialog._submit("ask")
        self.ai_sidebar_question.clear()

    def _sidebar_ai_quick(self, task: str) -> None:
        dialog = self._ensure_ai_dialog()
        dialog._quick_request(task)
        self.ai_sidebar_status.setText(
            "Waiting for the configured provider..."
            if self.language == "en_US"
            else "正在等待已配置的模型服务……"
        )

    def _open_ai_assistant(self) -> None:
        self.assistant_panel.setVisible(True)
        self.assistant_tabs.setCurrentIndex(0)
        self._refresh_ai_sidebar()
        self.ai_dialog = self._ensure_ai_dialog()
        self.ai_dialog.show()
        self.ai_dialog.raise_()
        self.ai_dialog.activateWindow()

    def _open_ai_documentation(self) -> None:
        page = _documentation_page(self.language, "ai-assistant.html")
        if not page.exists():
            QMessageBox.warning(
                self,
                "AI manual unavailable"
                if self.language == "en_US"
                else "AI 操作手册不可用",
                str(page),
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(page)))

    def _record_ai_response(
        self,
        response: AIResponse,
        question: str,
        task: str,
    ) -> None:
        if not self.state:
            return
        history = list(self.state.metadata.get("ai_history", []))
        history.append(response.audit_record(question, task))
        self.state.metadata["ai_history"] = history[-20:]
        self.state.metadata["ai_last_model"] = response.model
        self.state.metadata["ai_last_provider"] = response.provider
        self.state.log(
            f"AI advisory response recorded: {task} · "
            f"{response.provider} · {response.model}"
        )
        self._mark_project_dirty()
        self.status_label.setText(

                "AI advice received; no analysis was executed or changed"
                if self.language == "en_US"
                else "已收到 AI 建议；没有自动执行或修改任何分析"

        )
        self._refresh_warnings()
        self._refresh_ai_sidebar()

    def _handle_ai_tool_call(self, call: dict) -> None:
        if not self.state:
            return
        name = str(call.get("name", ""))
        arguments = dict(call.get("arguments", {}))
        record = {
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "name": name,
            "arguments": arguments,
            "status": "user_confirmed",
            "source": "AI collaborative proposal",
        }
        self.state.metadata.setdefault("ai_tool_audit", []).append(record)
        self.state.metadata["pending_ai_tool_call"] = record
        self._mark_project_dirty()

        if name in {"inspect_project", "summarize_recording"}:
            summary = {
                "source_type": self.state.source_type,
                "sampling_rate_hz": self.state.sampling_rate,
                "channel_count": self.state.channel_count,
                "duration_seconds": self.state.duration_seconds,
                "active_sorter": self.state.active_sorter_key,
                "unit_count": len(self.state.sorted_spikes),
                "event_count": len(self.state.events),
                "workflow_status": self.state.workflow_status,
            }
            record["status"] = "completed"
            QMessageBox.information(
                self,
                "Project inspection"
                if self.language == "en_US"
                else "项目检查",
                json.dumps(summary, ensure_ascii=False, indent=2),
            )
            return
        if name == "load_sorting_result":
            self._select_step("import")
            self._import_into_current_project()
            return
        if name == "import_behavior":
            self._select_step("sync")
            self._import_behavior_sync()
            return
        if name == "edit_figure":
            self._open_figure_settings()
            record["status"] = "editor_opened"
            return

        stage_by_tool = {
            "run_raw_qc": "qc",
            "preview_preprocessing": "preprocess",
            "run_sorter": "sorting",
            "compute_unit_qc": "unit_qc",
            "align_events": "sync",
            "generate_psth": "analysis",
            "run_statistics": "statistics",
            "run_decoding": "decoding",
            "export_project": "export",
        }
        stage = stage_by_tool.get(name)
        if stage is None:
            record["status"] = "blocked"
            record["error"] = "No local executor is registered."
            return
        self._select_step(stage)
        if name == "run_sorter":
            sorter = str(arguments.get("sorter", "kilosort4"))
            parameters = dict(arguments.get("parameters", {}))
            if not self.sorting_workbench.select_sorter(sorter, parameters):
                record["status"] = "blocked"
                record["error"] = f"Sorter is not present in the local catalog: {sorter}"
                QMessageBox.warning(
                    self,
                    "Sorter unavailable"
                    if self.language == "en_US"
                    else "Sorter 不可用",
                    record["error"],
                )
                return
        if name == "run_decoding":
            model = str(arguments.get("model", "Logistic regression"))
            option = f"classification:{model}"
            index = self.option_combo.findData(option)
            if index >= 0:
                self.option_combo.setCurrentIndex(index)
        if name == "generate_psth":
            event_option = next(
                (
                    index
                    for index in range(self.option_combo.count())
                    if str(self.option_combo.itemData(index)).startswith("event:")
                ),
                -1,
            )
            if event_option >= 0:
                self.option_combo.setCurrentIndex(event_option)
        self._start_worker([stage], tool_arguments=arguments)

    def _apply_ai_plan(
        self,
        plan: list[dict],
        suggested_next_stage: str,
    ) -> None:
        if not self.state:
            QMessageBox.information(
                self,
                "Open a project first"
                if self.language == "en_US"
                else "请先打开项目",
                (
                    "A workflow plan can be discussed without a project, but it can "
                    "only be stored after a NeuroEphys AI project is open."
                    if self.language == "en_US"
                    else "可以在没有项目时讨论流程，但只有打开项目后才能保存候选方案。"
                ),
            )
            return
        labels = STAGE_LABELS[self.language]
        details = "\n".join(
            f"• {labels.get(item['stage'], item['stage'])}: {item.get('reason', '')}"
            for item in plan
        )
        answer = QMessageBox.question(
            self,
            "Apply AI plan"
            if self.language == "en_US"
            else "应用 AI 候选方案",
            (
                "This stores the following advisory plan in the project and moves "
                f"the interface to {labels.get(suggested_next_stage, suggested_next_stage)}."
                "\n\nNo analysis will run and no existing result will be replaced.\n\n"
                f"{details}\n\nContinue?"
                if self.language == "en_US"
                else (
                    "这会把以下候选方案保存到项目，并把界面跳转到"
                    f"“{labels.get(suggested_next_stage, suggested_next_stage)}”。"
                    "\n\n不会运行任何分析，也不会覆盖已有结果。\n\n"
                    f"{details}\n\n是否继续？"
                )
            ),
        )
        if answer != QMessageBox.Yes:
            return
        self.state.metadata["ai_workflow_plan"] = {
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "stages": plan,
            "suggested_next_stage": suggested_next_stage,
            "status": "advisory_not_executed",
        }
        self.state.log(
            "AI candidate workflow accepted for review; no analysis executed"
        )
        self._mark_project_dirty()
        if suggested_next_stage in self.step_buttons:
            self._select_step(suggested_next_stage)
        self.status_label.setText(

                "AI plan stored for review; run steps manually after checking parameters"
                if self.language == "en_US"
                else "AI 候选方案已保存；请复核参数后手动运行各阶段"

        )
        QMessageBox.information(
            self,
            "Plan stored" if self.language == "en_US" else "候选方案已保存",
            (
                "The plan is now part of the project audit trail. It remains advisory "
                "until you confirm and run each analysis stage."
                if self.language == "en_US"
                else "候选方案已进入项目审计记录；只有你确认并运行后，分析阶段才会执行。"
            ),
        )

    def _open_context_tutorial(self) -> None:
        TutorialDialog(
            STEP_TUTORIAL.get(self.current_step, "import"),
            self,
            self.language,
        ).exec()


def raw_overview_figure_empty(state: ProjectState):
    from matplotlib.figure import Figure

    figure = Figure(figsize=(9, 5), facecolor="#ffffff")
    axis = figure.subplots()
    axis.axis("off")
    axis.text(
        0.5,
        0.55,
        (
            "Import your own data or open the sorting-ready demo dataset"
            if state.metadata.get("language") == "en_US"
            else "从首页导入自己的数据，或打开可运行 Kilosort4 的示例数据"
        ),
        ha="center",
        va="center",
        fontsize=15,
        color="#44534d",
    )
    axis.text(
        0.5,
        0.43,
        (
            "Data structure, parameters, results, and tutorials remain traceable in one project"
            if state.metadata.get("language") == "en_US"
            else "数据结构、参数、分析结果和教程会在同一个项目中保持可追溯"
        ),
        ha="center",
        va="center",
        fontsize=10,
        color="#718079",
    )
    return figure


def run_app(workspace: Path) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    runtime_log = workspace / "neuroflow_runtime.log"
    runtime_stream = runtime_log.open("a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = runtime_stream
    if sys.stderr is None:
        sys.stderr = runtime_stream
    app = QApplication.instance() or QApplication([])
    app.setApplicationName(PRODUCT_NAME)
    app.setFont(QFont("Microsoft YaHei", 10))
    crash_log = workspace / "neuroflow_crash.log"

    def handle_exception(exc_type, value, trace) -> None:
        details = "".join(traceback.format_exception(exc_type, value, trace))
        try:
            crash_log.write_text(details, encoding="utf-8")
        except OSError:
            pass
        QMessageBox.critical(
            None,
            PRODUCT_NAME,
            f"{PRODUCT_NAME} encountered an unexpected error, but the process was isolated.\n\n"
            f"{value}\n\nCrash log: {crash_log}",
        )

    sys.excepthook = handle_exception
    try:
        window = NeuroFlowWindow(workspace)
    except Exception:  # noqa: BLE001 - package startup boundary
        handle_exception(*sys.exc_info())
        return 1
    window.show()
    return app.exec()
