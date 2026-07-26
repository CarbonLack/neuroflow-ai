from __future__ import annotations

import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import mplcursors
import numpy as np
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)
from matplotlib.transforms import Bbox
from PySide6.QtCore import QEvent, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont
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
    import_binary_recording,
    import_device_recording,
    import_ibl_alf,
    import_ibl_trials_aggregate,
    import_kilosort_results,
    import_nwb_units,
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
from .figure_studio import FigureStudioDialog
from .help_content import REFERENCES, control_help, page_controls
from .i18n import LANGUAGES, step_text, tr
from .ibl import download_bwm_trials_aggregate
from .models import ProjectState, WorkflowStep
from .project import MANIFEST_NAME, load_project, save_project
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
from .tutorials import TUTORIALS, tutorial_value

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
            "选择记录系统和对应文件/文件夹；NeuroFlow 调用 SpikeInterface 读取器",
            "数据与项目",
            "有原始电压时可以",
            "保留源文件只读，建立统一缓存后进入质控、预处理和 sorting。",
        ),
        "ibl_alf": (
            "公开数据验证",
            "想复现 IBL 或 Buzsáki 公开会话，或验证下游分析",
            "选择 IBL ALF/BWM，或带 Units、行为/事件的 DANDI/NWB 文件",
            "Unit/行为检查",
            "通常不可以",
            "公开文件多为已排序数据；可运行 Unit QC、同步检查、PSTH、统计与解码。",
        ),
        "kilosort": (
            "已有 sorting 结果",
            "已经在 Kilosort/Phy 或其他工具中完成了 sorting",
            "选择含 spike_times.npy 与 cluster 分配的结果文件夹，并填写原采样率",
            "Unit 质控",
            "无需重跑",
            "统一为秒制 Unit/spike 接口，可与本项目其他 sorter 结果并列比较。",
        ),
    },
    "en_US": {
        "simulated": (
            "Guided simulation",
            "Learn the workflow, test the computer, or compare sorters",
            "Choose a probe scenario; NeuroFlow creates raw voltage, probe, behavior, TTL, and ground truth",
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
            "Public validation data",
            "Reproduce an IBL or Buzsáki session, or validate downstream analysis",
            "Choose IBL ALF/BWM or DANDI/NWB containing Units and behavior/events",
            "Unit/behavior checks",
            "Usually no",
            "Most public files are already sorted; continue with QC, PSTH, statistics, and decoding.",
        ),
        "kilosort": (
            "Existing sorting results",
            "Sorting was completed in Kilosort/Phy or another tool",
            "Choose a folder with spike_times and cluster assignments and specify the original rate",
            "Unit QC",
            "No rerun needed",
            "Normalize to the seconds-based Unit/spike interface and compare with other sorter results.",
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


APP_STYLE = """
QMainWindow, QWidget {
    background: #f5f7f6;
    color: #17211e;
    font-family: "Microsoft YaHei", "Segoe UI";
    font-size: 13px;
}
#Header, #HomeHeader { background: #ffffff; border-bottom: 1px solid #d8e0dc; }
#Brand { font-size: 22px; font-weight: 700; color: #14211d; }
#Hero { font-size: 30px; font-weight: 700; color: #14211d; }
#Sidebar, #Assistant { background: #ffffff; }
#Sidebar { border-right: 1px solid #d8e0dc; }
#Assistant { border-left: 1px solid #d8e0dc; }
#RunFooter {
    background: #ffffff;
    border-top: 1px solid #cfd8d4;
}
QPushButton {
    min-height: 36px;
    border: 1px solid #c9d4cf;
    background: #ffffff;
    padding: 0 14px;
    border-radius: 5px;
}
QPushButton:hover { border-color: #1f7a63; background: #eff6f3; }
QPushButton:disabled { color: #96a09b; background: #f1f3f2; border-color: #dce1df; }
QPushButton:checked, QPushButton#Primary {
    color: #ffffff; background: #1f7a63; border-color: #1f7a63; font-weight: 600;
}
QPushButton#StepButton {
    text-align: left; min-height: 53px; border: none; border-left: 3px solid transparent;
    border-radius: 0; padding: 2px 12px 2px 14px;
}
QPushButton#StepButton:checked {
    color: #17221f; background: #e7f0ec; border-left: 3px solid #1f7a63; font-weight: 650;
}
QPushButton#StepButton[status="completed"] { color: #1f7a63; }
QPushButton#StepButton[status="failed"] { color: #b34f36; }
QFrame#Card, QFrame#Metric, QFrame#SortingWorkbench, QFrame#TraceControls {
    background: #ffffff; border: 1px solid #d8e0dc; border-radius: 6px;
}
QFrame#InsetPanel {
    background: #f7f9f8; border: 1px solid #e0e6e3; border-radius: 5px;
}
QLabel#MetricValue { font-size: 19px; font-weight: 700; }
QLabel#Muted, QLabel#MetricLabel { color: #69756f; }
QLabel#PanelTitle { font-size: 15px; font-weight: 700; }
QLabel#FieldLabel { color: #4e5d57; font-weight: 600; }
QLabel#StatusBadge {
    color: #8d3e2d; background: #fff1ec; border: 1px solid #f0c1b2;
    border-radius: 4px; padding: 3px 8px; font-weight: 600;
}
QLabel#StatusBadge[available="true"] {
    color: #17634f; background: #eaf5f0; border-color: #b7d9cb;
}
QLineEdit, QPlainTextEdit, QTextBrowser, QTableWidget, QComboBox, QSpinBox, QDoubleSpinBox, QListWidget {
    background: #ffffff; border: 1px solid #d2dbd7; border-radius: 4px; min-height: 31px;
    selection-background-color: #cfe5dc;
}
QComboBox { padding: 0 8px; }
QTableWidget { gridline-color: #e5ebe8; }
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background: #dcece5; color: #17211e; }
QHeaderView::section {
    background: #edf1ef; border: none; border-bottom: 1px solid #d2dcd7; padding: 7px; font-weight: 600;
}
QProgressBar {
    border: 1px solid #cfd8d4; border-radius: 4px; background: #ffffff;
    text-align: center; min-height: 18px;
}
QProgressBar::chunk { background: #1f7a63; border-radius: 3px; }
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
            "只检测 NeuroFlow 明确支持的 sorter。某个后端检测失败时，其他后端和主界面仍可使用。"
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
        note = QLabel(
            "Kilosort4、SpyKING CIRCUS 2、Tridesclous2、Simple 和 Lupin 随当前发行版运行。"
            "MountainSort5 在 Windows/Python 3.12 上需要 Microsoft C++ Build Tools 编译 isosplit6；"
            "NeuroFlow 会明确显示该限制，不会把它误报为已安装。"
            if language == "zh_CN"
            else "Kilosort4, SpyKING CIRCUS 2, Tridesclous2, Simple, and Lupin run with this release. "
            "MountainSort5 needs Microsoft C++ Build Tools to compile isosplit6 on Windows/Python 3.12; "
            "NeuroFlow reports that limitation instead of claiming it is installed."
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        layout.addWidget(note)
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


class ImportDialog(QDialog):
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
        self.setWindowTitle(
            "Import your electrophysiology data" if english else "导入自己的电生理数据"
        )
        self.resize(920, 720)
        layout = QVBoxLayout(self)
        title = QLabel(
            "Create a NeuroFlow project" if english else "建立 NeuroFlow 项目"
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
        self.import_formats = list(SUPPORTED_FORMATS)
        for item in self.import_formats:
            name = FORMAT_TEXT_EN[item.key][0] if english else item.name
            self.source_combo.addItem(name, item.key)
        source_form.addRow("Data source" if english else "数据来源", self.source_combo)
        self.project_name = QLineEdit("NeuroFlow project")
        self.project_name.setToolTip(
            "Names the NeuroFlow project folder; source files are not renamed."
            if english
            else "用于 NeuroFlow 项目文件夹；不会重命名源文件。"
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
        layout.addWidget(self.pages, 1)
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
                "Kilosort/Phy 导入通常只有处理后的 spike，因此从下游阶段接入。"
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

    def _source_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(max(index, 0))
        if index < 0 or index >= len(self.import_formats):
            return
        item = self.import_formats[index]
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
                "NeuroFlow uses SpikeInterface extractors and creates a normalized "
                "interleaved int16 cache. Source files are never modified."
            )
            if english
            else (
                "NeuroFlow 使用 SpikeInterface 的官方 extractor 读取源格式，并在项目缓存中"
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
    def __init__(
        self,
        initial_key: str = "import",
        parent: QWidget | None = None,
        language: str = "zh_CN",
    ):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(tr("tutorial", language))
        self.resize(940, 650)
        layout = QHBoxLayout(self)
        self.list = QListWidget()
        self.list.setFixedWidth(250)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
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
            self.list.addItem(tutorial_value(chapter, "title", language))
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
        english = self.language == "en_US"
        controls = page_controls(item["key"], self.language)
        controls_html = "".join(
            (
                "<tr>"
                f"<td style='padding:8px;vertical-align:top'><b>{name}</b></td>"
                f"<td style='padding:8px'>{description}</td>"
                "</tr>"
            )
            for name, description in controls
        )
        references_html = "".join(
            f"<li><a href='{reference['url']}'>{reference['name']}</a></li>"
            for reference in REFERENCES
        )
        self.browser.setHtml(
            f"<h1>{tutorial_value(item, 'title', self.language)}</h1>"
            f"<h3>{'Why' if english else '为什么做'}</h3>"
            f"<p>{tutorial_value(item, 'why', self.language)}</p>"
            f"<h3>{'Input' if english else '输入'}</h3>"
            f"<p>{tutorial_value(item, 'input', self.language)}</p>"
            f"<h3>{'Output' if english else '输出'}</h3>"
            f"<p>{tutorial_value(item, 'output', self.language)}</p>"
            f"<h3>{'What to check' if english else '必须检查'}</h3>"
            f"<p>{tutorial_value(item, 'checks', self.language)}</p>"
            f"<h3>{'Controls and consequences' if english else '页面控件与操作后果'}</h3>"
            "<table style='border-collapse:collapse;width:100%' border='1' "
            f"cellpadding='0'>{controls_html}</table>"
            f"<h3>{'Methods and sources' if english else '方法来源'}</h3>"
            f"<p>{item['reference']}</p>"
            f"<ul>{references_html}</ul>"
            + (
                "<p><b>Principle:</b> tutorials explain decisions; the user confirms and records final parameters.</p>"
                if english
                else "<p><b>原则：</b>教程解释决策依据，最终参数仍由用户确认并记录。</p>"
            )
        )

    def _open_full_manual(self) -> None:
        manual = _documentation_index().with_name("manual.html")
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
                "system. NeuroFlow fits a linear clock map and reports residuals."
            )
            if english
            else (
                "行为文件描述 trial、条件和行为设备时间；可选 TTL 文件提供电生理系统"
                "记录到的一一对应脉冲。NeuroFlow 会拟合线性时钟映射并报告残差。"
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
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
                    filter="CSV (*.csv)",
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
    ):
        super().__init__()
        self.state = state
        self.keys = keys
        self.sorter_name = sorter_name
        self.sorter_settings = sorter_settings
        self.model_name = model_name
        self.analysis_selection = analysis_selection
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

    def run(self) -> None:
        key = self.keys[0] if self.keys else "import"
        try:
            for key in self.keys:
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
                            run_raw_qc(self.state),
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
                        self._emit(
                            key,
                            preprocessing_preview(self.state),
                            self._message(
                                "预处理预览完成", "Preprocessing preview completed"
                            ),
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
                                "Event analysis requires timestamps; import events.csv "
                                "or ALF trials",
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
                        "trial_count": len(self.state.trials or self.state.events),
                    }
                    self._emit(
                        key,
                        self.state.trials or self.state.events,
                        self._message(
                            "行为摘要已生成", "Behavior summary generated"
                        ),
                    )
                elif key == "analysis":
                    selection = self.analysis_selection
                    if len(self.keys) > 1 or not selection:
                        value = run_neural_toolkit(self.state)
                    elif selection.startswith("event:"):
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
                    completed = self.state.metadata.setdefault(
                        "completed_analyses", []
                    )
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
                        run_statistical_suite(self.state),
                        self._message(
                            "统计套件完成", "Statistical suite completed"
                        ),
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
                        value = run_decoding_suite(self.state, model_name)
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
        self.current_step = "import"
        self.step_buttons: dict[str, QPushButton] = {}
        self.figure_cursor = None
        self.setWindowTitle(tr("app_title", self.language))
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
        brand = QLabel("NeuroFlow")
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
        self.hero_label = QLabel("从自己的原始数据开始，\n逐步走到可复现的论文图。")
        self.hero_label.setObjectName("Hero")
        layout.addWidget(self.hero_label)
        self.hero_subtitle = QLabel(
            "本地优先 · 模块可替换 · 每一步可解释 · Kilosort4 真实运行 · AI 非必需"
        )
        self.hero_subtitle.setObjectName("Muted")
        self.hero_subtitle.setStyleSheet("font-size: 15px;")
        layout.addWidget(self.hero_subtitle)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.sample_button = QPushButton("打开示例数据")
        self.sample_button.setObjectName("Primary")
        self.sample_button.setMinimumHeight(48)
        self.sample_button.setMinimumWidth(210)
        self.sample_button.setProperty("neuroflow_help_key", "home.demo")
        self.sample_button.clicked.connect(self._open_sample)
        self.import_button = QPushButton("导入自己的数据")
        self.import_button.setMinimumHeight(48)
        self.import_button.setMinimumWidth(210)
        self.import_button.setProperty("neuroflow_help_key", "home.import")
        self.import_button.clicked.connect(self._show_import)
        self.project_button = QPushButton("恢复 NeuroFlow 项目")
        self.project_button.setProperty("neuroflow_help_key", "home.restore")
        self.project_button.clicked.connect(self._open_project)
        actions.addWidget(self.sample_button)
        actions.addWidget(self.import_button)
        actions.addWidget(self.project_button)
        self.demo_folder_button = QPushButton("查看示例数据文件夹")
        self.demo_folder_button.clicked.connect(self._open_demo_folder)
        actions.addWidget(self.demo_folder_button)
        actions.addStretch()
        layout.addLayout(actions)

        capability = QFrame()
        capability.setObjectName("Card")
        cap_layout = QVBoxLayout(capability)
        self.cap_title = QLabel("数据入口与接入位置")
        self.cap_title.setStyleSheet("font-size: 17px; font-weight: 700;")
        cap_layout.addWidget(self.cap_title)
        self.cap_intro = QLabel(
            "下面五行不是五种算法，而是五条进入 NeuroFlow 的路径。"
            "先按“我手里有什么”选择入口；流程起点和能否重新 sorting 由文件中是否包含原始电压决定。"
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
            lambda row, _column: self._show_import(
                str(self.input_table.item(row, 0).data(Qt.UserRole))
            )
        )
        cap_layout.addWidget(self.input_table)
        self.entry_hint = QLabel(
            "操作：双击任意一行会打开相应的导入向导；公开数据和已有 sorting 结果不会伪装成原始电压。"
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
        self.home_button = QPushButton("首页")
        self.home_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.home_page)
        )
        layout.addWidget(self.home_button)
        title_box = QVBoxLayout()
        brand = QLabel("NeuroFlow")
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
        self.tutorial_button = QPushButton("教程")
        self.tutorial_button.clicked.connect(self._open_context_tutorial)
        self.docs_button = QPushButton("产品文档")
        self.docs_button.clicked.connect(self._open_documentation)
        self.run_button = QPushButton("运行完整流程")
        self.run_button.setObjectName("Primary")
        self.run_button.setProperty("neuroflow_help_key", "global.run_all")
        self.run_button.clicked.connect(self._run_full_pipeline)
        layout.addWidget(self.workspace_language_combo)
        layout.addWidget(self.sorter_manager_button)
        layout.addWidget(self.save_button)
        layout.addWidget(self.tutorial_button)
        layout.addWidget(self.docs_button)
        layout.addWidget(self.run_button)
        return header

    def _sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(310)
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
        self.run_step_button = QPushButton("运行此节点")
        self.run_step_button.setProperty("neuroflow_help_key", "global.run_step")
        self.run_step_button.clicked.connect(self._run_current_step)
        title_row.addWidget(self.run_step_button)
        layout.addLayout(title_row)

        self.sorting_workbench = SortingWorkbench(self.language)
        self.sorting_workbench.selection_changed.connect(self._on_sorter_selected)
        self.sorting_workbench.diagnostic_changed.connect(
            self._on_sorting_diagnostic_changed
        )
        self.sorting_workbench.setVisible(False)
        layout.addWidget(self.sorting_workbench)
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
        footer.setFixedHeight(58)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(16, 7, 16, 7)
        self.status_label = QLabel("请从首页打开或创建项目")
        self.status_label.setObjectName("Muted")
        self.status_label.setMinimumWidth(280)
        layout.addWidget(self.status_label, 1)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(STEPS))
        self.progress_bar.setMinimumWidth(320)
        layout.addWidget(self.progress_bar, 2)
        return footer

    def _assistant(self) -> QWidget:
        assistant = QWidget()
        assistant.setObjectName("Assistant")
        assistant.setFixedWidth(310)
        layout = QVBoxLayout(assistant)
        layout.setContentsMargins(16, 15, 16, 13)
        self.assistant_title = QLabel("引导与证据")
        self.assistant_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(self.assistant_title)
        self.assistant_mode = QLabel("离线规则与教程 · 不依赖大模型")
        self.assistant_mode.setObjectName("Muted")
        layout.addWidget(self.assistant_mode)
        self.help_title = QLabel("先选择数据来源")
        self.help_title.setStyleSheet("font-weight: 700; color: #1f7a63;")
        layout.addWidget(self.help_title)
        self.help_text = QLabel("NeuroFlow 不会替你隐藏数据结构和关键参数。")
        self.help_text.setWordWrap(True)
        self.help_text.setAlignment(Qt.AlignTop)
        layout.addWidget(self.help_text)
        self.open_tutorial_button = QPushButton("打开本章完整教程")
        self.open_tutorial_button.clicked.connect(self._open_context_tutorial)
        layout.addWidget(self.open_tutorial_button)
        self.warning_heading = QLabel("当前检查")
        self.warning_heading.setStyleSheet("font-weight: 700;")
        layout.addWidget(self.warning_heading)
        self.warning_text = QLabel("尚未打开项目。")
        self.warning_text.setWordWrap(True)
        self.warning_text.setObjectName("Muted")
        layout.addWidget(self.warning_text)
        self.log_title = QLabel("运行与审计记录")
        self.log_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(self.log_title)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(300)
        layout.addWidget(self.log_view, 1)
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
            (self.sample_button, standard.SP_MediaPlay),
            (self.import_button, standard.SP_DialogOpenButton),
            (self.project_button, standard.SP_DialogOpenButton),
            (self.demo_folder_button, standard.SP_DirOpenIcon),
            (self.home_button, standard.SP_DirHomeIcon),
            (self.sorter_manager_button, standard.SP_ComputerIcon),
            (self.save_button, standard.SP_DialogSaveButton),
            (self.tutorial_button, standard.SP_DialogHelpButton),
            (self.docs_button, standard.SP_FileDialogInfoView),
            (self.run_button, standard.SP_MediaPlay),
            (self.run_step_button, standard.SP_MediaPlay),
            (self.figure_settings_button, standard.SP_FileDialogDetailedView),
            (self.panel_focus_button, standard.SP_TitleBarMaxButton),
            (self.panel_edit_button, standard.SP_FileDialogDetailedView),
            (self.panel_save_button, standard.SP_DialogSaveButton),
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

    def _set_language(self, language: str | None) -> None:
        if language not in LANGUAGES or language == self.language:
            return
        self.language = language
        if self.state:
            self.state.metadata["language"] = language
        self._apply_language()

    def _apply_language(self) -> None:
        language = self.language
        self.setWindowTitle(tr("app_title", language))
        for combo in (self.home_language_combo, self.workspace_language_combo):
            combo.blockSignals(True)
            index = combo.findData(language)
            if index >= 0:
                combo.setCurrentIndex(index)
            combo.blockSignals(False)
        self.home_tutorial_button.setText(tr("tutorial", language))
        self.hero_label.setText(tr("hero", language))
        self.hero_subtitle.setText(tr("hero_subtitle", language))
        self.import_button.setText(tr("import_data", language))
        self.sample_button.setText(tr("sample", language))
        self.project_button.setText(tr("restore", language))
        self.demo_folder_button.setText(
            "Open demo data folder" if language == "en_US" else "查看示例数据文件夹"
        )
        self.cap_title.setText(tr("verified_inputs", language))
        self.flow_title.setText(tr("full_chain", language))
        self.cap_intro.setText(
            (
                "下面五行不是五种算法，而是五条进入 NeuroFlow 的路径。"
                "先按“我手里有什么”选择入口；流程起点和能否重新 sorting 由文件中是否包含原始电压决定。"
            )
            if language == "zh_CN"
            else (
                "These are five entry routes, not five algorithms. Choose by what "
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
                "操作：双击任意一行会打开相应的导入向导；公开数据和已有 sorting 结果"
                "不会伪装成原始电压。"
            )
            if language == "zh_CN"
            else (
                "Double-click a row to open that import route. Public processed data "
                "and existing sorting results are never presented as raw voltage."
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
        self.assistant_title.setText(tr("assistant", language))
        self.assistant_mode.setText(tr("assistant_mode", language))
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
        self._refresh_environment()
        if not self.state:
            self.project_label.setText(tr("no_project", language))
            self.status_label.setText(tr("open_project_first", language))
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

    def _show_import(self, source_key: str | None = None) -> None:
        dialog = ImportDialog(self.workspace, self, self.language)
        if source_key:
            index = dialog.source_combo.findData(source_key)
            if index >= 0:
                dialog.source_combo.setCurrentIndex(index)
        if dialog.exec() == QDialog.Accepted and dialog.state:
            self._load_state(dialog.state)

    def _import_behavior_sync(self) -> None:
        if not self.state:
            return
        dialog = BehaviorSyncDialog(self.state, self, self.language)
        if dialog.exec() == QDialog.Accepted and dialog.result:
            self._set_step_status("sync", "completed")
            self._set_step_status("behavior", "pending")
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
        index = _documentation_index()
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
            "选择 NeuroFlow 项目",
            str(self.workspace),
            f"NeuroFlow ({MANIFEST_NAME})",
        )[0]
        if not path:
            return
        try:
            self._load_state(load_project(Path(path)))
        except Exception as exc:  # noqa: BLE001 - project parse errors are user-facing
            QMessageBox.warning(self, "无法打开项目", str(exc))

    def _load_state(self, state: ProjectState) -> None:
        self.state = state
        stored_language = state.metadata.get("language")
        if stored_language in LANGUAGES:
            self.language = stored_language
        state.metadata["language"] = self.language
        self.preview = None
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
        self.pages.setCurrentWidget(self.workspace_page)
        self._apply_language()
        self._select_step("import")
        self.status_label.setText(
            "Project opened; run one step or the full workflow"
            if self.language == "en_US"
            else "项目已打开；可逐节点运行，也可执行完整流程"
        )
        self._refresh_warnings()

    def _save(self) -> None:
        if self.state:
            path = save_project(self.state)
            self.status_label.setText(f"项目已保存：{path.name}")

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
                    f"Event · Unit {unit_id}",
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
        self.sync_workbench.setVisible(key == "sync")
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
        self._update_page_option_help()
        self._refresh_figure()
        self._refresh_table()
        self._refresh_warnings()

    def _on_option_changed(self) -> None:
        self._update_page_option_help()
        self._refresh_figure()

    def _on_sorter_selected(self, sorter_key: str) -> None:
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
        self.state.unit_metrics = []
        self.state.unit_diagnostics = {}
        self.state.analysis = {}
        self.state.statistics = {}
        self.state.decoding = {}
        self.state.regression = {}
        for key in ("unit_qc", "analysis", "statistics", "decoding", "export"):
            self.state.workflow_status[key] = "pending"
            self._set_step_status(key, "pending")
        self.metric_units.value_label.setText(str(len(self.state.sorted_spikes)))
        self.state.log(f"Active sorting result changed to {sorter_key}")
        self.sorting_workbench.set_results(
            set(self.state.sorting_results),
            self.state.active_sorter_key,
        )
        save_project(self.state)
        self._refresh_figure()
        self._refresh_table()
        self._refresh_warnings()

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
                    "\n\n该案例使用 NeuroFlow 模拟数据验证方法结构，不复制原论文图，"
                    "也不声称复现论文数值。"
                    if self.language == "zh_CN"
                    else "\n\nThis case validates the method structure on NeuroFlow "
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
                f"Events/trials: {len(self.state.trials or self.state.events)}"
                if self.language == "en_US"
                else f"事件/trial：{len(self.state.trials or self.state.events)}"
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
        sorter_name = self.sorting_workbench.selected_sorter()
        sorter_settings = self.sorting_workbench.settings()
        model_name = "classification:Logistic regression"
        if self.current_step == "decoding" and self.option_combo.currentData():
            model_name = self.option_combo.currentData()
        analysis_selection = (
            str(self.option_combo.currentData() or "")
            if self.current_step == "analysis"
            else ""
        )
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
        )
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
                self.metric_units.value_label.setText(
                    str(len(self.state.sorted_spikes))
                )
                self.sorting_workbench.set_results(
                    set(self.state.sorting_results),
                    self.state.active_sorter_key,
                )
        if self.state:
            save_project(self.state)
        self._select_step(key)

    def _on_failed(self, key: str, details: str) -> None:
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
        self._refresh_warnings()
        QMessageBox.critical(
            self,
            "Step failed" if self.language == "en_US" else "节点运行失败",
            (
                f"{details.splitlines()[0]}\n\nDetails were written to the run log. "
                "Completed results were retained."
                if self.language == "en_US"
                else f"{details.splitlines()[0]}\n\n"
                "详细信息已写入运行记录，已完成结果不会被删除。"
            ),
        )

    def _on_succeeded(self) -> None:
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
    app.setApplicationName("NeuroFlow")
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
            "NeuroFlow",
            "NeuroFlow encountered an unexpected error, but the process was isolated.\n\n"
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
