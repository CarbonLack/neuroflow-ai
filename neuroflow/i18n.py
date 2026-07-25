from __future__ import annotations

LANGUAGES = {"zh_CN": "中文", "en_US": "English"}

TEXT = {
    "app_title": {
        "zh_CN": "NeuroFlow - 在体电生理全流程工作台",
        "en_US": "NeuroFlow - In-vivo electrophysiology workbench",
    },
    "home": {"zh_CN": "首页", "en_US": "Home"},
    "save": {"zh_CN": "保存项目", "en_US": "Save project"},
    "tutorial": {"zh_CN": "教程中心", "en_US": "Tutorial center"},
    "run_all": {"zh_CN": "运行完整流程", "en_US": "Run full workflow"},
    "run_step": {"zh_CN": "运行此节点", "en_US": "Run this step"},
    "workflow": {"zh_CN": "分析流程", "en_US": "Analysis workflow"},
    "language": {"zh_CN": "语言", "en_US": "Language"},
    "import_data": {"zh_CN": "导入我的数据", "en_US": "Import my data"},
    "sample": {"zh_CN": "打开示例数据", "en_US": "Open demo data"},
    "restore": {"zh_CN": "恢复 NeuroFlow 项目", "en_US": "Restore NeuroFlow project"},
    "hero": {
        "zh_CN": "从自己的原始数据开始，\n逐步走到可复现的论文图。",
        "en_US": "Start with your own raw data,\nand reach reproducible publication figures.",
    },
    "hero_subtitle": {
        "zh_CN": "本地优先 · 模块可替换 · 每一步可解释 · 多 sorter 真实运行 · AI 非必需",
        "en_US": "Local-first · Replaceable modules · Explainable steps · Real sorters · AI optional",
    },
    "verified_inputs": {
        "zh_CN": "当前可验证的数据入口",
        "en_US": "Validated data inputs",
    },
    "full_chain": {"zh_CN": "完整纵向链路", "en_US": "Complete vertical workflow"},
    "assistant": {"zh_CN": "引导与证据", "en_US": "Guidance and evidence"},
    "assistant_mode": {
        "zh_CN": "离线规则与教程 · 不依赖大模型",
        "en_US": "Offline rules and tutorials · No LLM required",
    },
    "open_chapter": {
        "zh_CN": "打开本章完整教程",
        "en_US": "Open full chapter",
    },
    "current_checks": {"zh_CN": "当前检查", "en_US": "Current checks"},
    "audit_log": {"zh_CN": "运行与审计记录", "en_US": "Run and audit log"},
    "plot_help": {
        "zh_CN": "单击图中元素查看数值；双击坐标轴打开编辑器；工具栏可缩放、平移和保存。",
        "en_US": "Click an element to inspect values; double-click an axis to edit it; use the toolbar to zoom, pan, and save.",
    },
    "plot_settings": {"zh_CN": "图形设置", "en_US": "Figure settings"},
    "plot_style": {"zh_CN": "呈现形式", "en_US": "Presentation"},
    "standard": {"zh_CN": "标准", "en_US": "Standard"},
    "points": {"zh_CN": "突出数据点", "en_US": "Emphasize points"},
    "step": {"zh_CN": "阶梯线", "en_US": "Step lines"},
    "grayscale": {"zh_CN": "灰度", "en_US": "Grayscale"},
    "high_contrast": {"zh_CN": "高对比", "en_US": "High contrast"},
    "source": {"zh_CN": "数据源", "en_US": "Source"},
    "channels": {"zh_CN": "通道", "en_US": "Channels"},
    "duration": {"zh_CN": "时长", "en_US": "Duration"},
    "units": {"zh_CN": "Unit", "en_US": "Units"},
    "no_project": {"zh_CN": "尚未打开项目", "en_US": "No project open"},
    "open_project_first": {
        "zh_CN": "请从首页打开或创建项目",
        "en_US": "Open or create a project from Home",
    },
    "sorter_manager": {"zh_CN": "Sorter 管理", "en_US": "Sorter manager"},
    "available": {"zh_CN": "可运行", "en_US": "Available"},
    "unavailable": {"zh_CN": "不可用", "en_US": "Unavailable"},
    "refresh": {"zh_CN": "重新检测", "en_US": "Refresh status"},
    "close": {"zh_CN": "关闭", "en_US": "Close"},
    "apply": {"zh_CN": "应用", "en_US": "Apply"},
    "cancel": {"zh_CN": "取消", "en_US": "Cancel"},
}


STEP_TEXT = {
    "import": {
        "zh_CN": ("01  数据与项目", "格式、探针、事件和来源"),
        "en_US": ("01  Data and project", "Format, probe, events, and provenance"),
    },
    "qc": {
        "zh_CN": ("02  原始质控", "噪声、坏通道、饱和与工频"),
        "en_US": ("02  Raw QC", "Noise, bad channels, saturation, and line noise"),
    },
    "preprocess": {
        "zh_CN": ("03  预处理", "滤波与参考的处理前后预览"),
        "en_US": ("03  Preprocessing", "Preview filtering and referencing"),
    },
    "sorting": {
        "zh_CN": ("04  Spike sorting", "六种 sorter 的检测、选择与运行"),
        "en_US": ("04  Spike sorting", "Detect, select, and run six sorters"),
    },
    "unit_qc": {
        "zh_CN": ("05  Unit 质控", "放电率、ISI、波形与 SNR"),
        "en_US": ("05  Unit QC", "Firing rate, ISI, waveform, and SNR"),
    },
    "sync": {
        "zh_CN": ("06  事件同步", "统一时间轴、trial 与条件"),
        "en_US": (
            "06  Event synchronization",
            "Common timeline, trials, and conditions",
        ),
    },
    "behavior": {
        "zh_CN": ("07  行为分析", "条件、反应时与心理测量曲线"),
        "en_US": ("07  Behavior", "Conditions, reaction time, and psychometrics"),
    },
    "analysis": {
        "zh_CN": ("08  神经活动", "Raster、PSTH、热图与群体响应"),
        "en_US": (
            "08  Neural activity",
            "Raster, PSTH, heatmap, and population response",
        ),
    },
    "statistics": {
        "zh_CN": ("09  统计检验", "参数、非参数、效应量、混合模型与校正"),
        "en_US": (
            "09  Statistics",
            "Parametric, nonparametric, effects, mixed models, correction",
        ),
    },
    "decoding": {
        "zh_CN": ("10  机器学习", "分类、聚类、交叉验证、置换与 PCA"),
        "en_US": (
            "10  Machine learning",
            "Classification, clustering, CV, permutation, and PCA",
        ),
    },
    "export": {
        "zh_CN": ("11  论文与复现", "可编辑图、表、Methods、环境与项目"),
        "en_US": (
            "11  Publication and reproducibility",
            "Editable figures, tables, methods, and environment",
        ),
    },
}


def tr(key: str, language: str = "zh_CN") -> str:
    values = TEXT.get(key)
    if values is None:
        return key
    return values.get(language, values["zh_CN"])


def step_text(key: str, language: str = "zh_CN") -> tuple[str, str]:
    values = STEP_TEXT[key]
    return values.get(language, values["zh_CN"])
