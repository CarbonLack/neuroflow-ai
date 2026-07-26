from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neuroflow.help_content import PAGE_CONTROLS, PAGE_CONTROLS_EN
from neuroflow.tutorial_details import (
    TUTORIAL_DETAILS,
    localized,
    localized_rows,
)
from neuroflow.tutorials import TUTORIALS, tutorial_value

SITE = ROOT / "docs" / "site"

PAGES = (
    ("index.html", "概览", "Overview", "getting_started"),
    ("installation.html", "安装与运行", "Installation and runtime", "getting_started"),
    ("gui-guide.html", "界面与基本操作", "Interface and basic operation", "getting_started"),
    ("tutorials.html", "完整逐步教程", "Complete step-by-step tutorial", "tutorials"),
    ("data-inputs.html", "导入自己的数据", "Import your own data", "tutorials"),
    ("sorting.html", "Spike sorting 指南", "Spike sorting guide", "guides"),
    ("parameters.html", "参数参考", "Parameter reference", "guides"),
    ("figure-studio.html", "图形编辑与导出", "Figure editing and export", "guides"),
    ("troubleshooting.html", "故障排查", "Troubleshooting", "reference"),
    ("sources.html", "方法与来源", "Methods and sources", "reference"),
)

GROUP_TITLES = {
    "zh_CN": {
        "getting_started": "开始使用",
        "tutorials": "教程",
        "guides": "专项指南",
        "reference": "参考资料",
    },
    "en_US": {
        "getting_started": "Getting started",
        "tutorials": "Tutorials",
        "guides": "Guides",
        "reference": "Reference",
    },
}


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _sidebar(language: str, active: str) -> str:
    items: list[str] = []
    current_group = ""
    for filename, zh, en, group in PAGES:
        if group != current_group:
            current_group = group
            items.append(
                f'<div class="sidebar-label">{GROUP_TITLES[language][group]}</div>'
            )
        label = en if language == "en_US" else zh
        class_name = ' class="active"' if filename == active else ""
        items.append(f'<a{class_name} href="{filename}">{e(label)}</a>')
    return "\n".join(items)


def _layout(
    language: str,
    filename: str,
    title: str,
    lead: str,
    body: str,
    *,
    eyebrow: str | None = None,
) -> str:
    folder = "en" if language == "en_US" else "zh"
    other = "zh" if folder == "en" else "en"
    other_label = "Chinese" if folder == "en" else "英文"
    page_lang = "en" if language == "en_US" else "zh-CN"
    search = "Search this page" if language == "en_US" else "搜索本页"
    menu = "Open navigation" if language == "en_US" else "打开目录"
    intro = eyebrow or ("NeuroFlow operation manual" if language == "en_US" else "NeuroFlow 操作手册")
    document = f"""<!doctype html>
<html lang="{page_lang}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{e(title)} · NeuroFlow</title>
    <link rel="stylesheet" href="../styles.css?v=0.7.0">
  </head>
  <body>
    <header class="topbar">
      <button class="icon-button" type="button" data-menu-toggle aria-label="{e(menu)}">☰</button>
      <a class="brand" href="index.html">NeuroFlow <small>{'Documentation' if language == 'en_US' else '操作手册'}</small></a>
      <input class="search" data-doc-search type="search" placeholder="{e(search)}">
      <div class="topbar-actions">
        <a class="language-button language-link" data-language-link="{other}" href="../{other}/{filename}">{other_label}</a>
      </div>
    </header>
    <div class="layout">
      <aside class="sidebar">
        {_sidebar(language, filename)}
      </aside>
      <main class="content">
        <div class="page-intro" data-searchable>
          <p class="eyebrow">{e(intro)}</p>
          <h1>{e(title)}</h1>
          <p class="lead">{e(lead)}</p>
        </div>
        {body}
        <footer class="footer">NeuroFlow · {'Original explanatory text with cited method sources' if language == 'en_US' else '原创说明文字，方法来源逐项标注'}</footer>
      </main>
    </div>
    <script src="../app.js?v=0.7.0"></script>
  </body>
</html>
"""
    return "\n".join(line.rstrip() for line in document.splitlines()) + "\n"


def _chapter_card(chapter: dict[str, str], language: str) -> str:
    detail = TUTORIAL_DETAILS[chapter["key"]]
    recommended = localized(detail, "recommended", language)
    next_text = localized(detail, "next", language)
    return f"""
<article class="stage-card" data-searchable>
  <div class="stage-number">{e(chapter['title'][:2])}</div>
  <div>
    <h3><a href="tutorials.html#{e(chapter['key'])}">{e(tutorial_value(chapter, 'title', language)[3:])}</a></h3>
    <p>{e(localized(detail, 'narrative', language))}</p>
    <p><b>{'Recommended first action' if language == 'en_US' else '推荐先做'}：</b> {e(recommended[0])}</p>
    <p class="muted"><b>{'Then' if language == 'en_US' else '之后'}：</b> {e(next_text)}</p>
  </div>
</article>
"""


def build_index(language: str) -> str:
    english = language == "en_US"
    title = "A visible, replaceable, and restorable electrophysiology workflow" if english else "看得见、换得掉、接得上、能恢复的电生理工作流"
    lead = (
        "NeuroFlow connects raw multichannel recordings, replaceable spike sorters, behavior, neural analyses, statistics, machine learning, and publication export in one local-first project."
        if english
        else "NeuroFlow 把原始多通道记录、可替换的 spike sorter、行为、神经分析、统计、机器学习和论文导出组织在一个本地优先的项目中。"
    )
    principles = (
        (
            ("Visible", "Every stage exposes input, parameters, method, evidence, and limitations."),
            ("Replaceable", "Sorters and stage outputs can be changed without hiding native files."),
            ("Restorable", "The project manifest restores sources, completed stages, results, and audit history."),
        )
        if english
        else (
            ("看得见", "每个阶段都显示输入、参数、方法、证据和能力边界。"),
            ("换得掉", "sorter 和阶段结果可以替换，同时保留各工具原生文件。"),
            ("能恢复", "项目清单保存来源、已完成阶段、结果和审计历史。"),
        )
    )
    quick = (
        [
            "Create an empty project and import your own data, or open a teaching simulation.",
            "Verify data structure and raw traces before preprocessing.",
            "Run each selected analysis from the fixed bottom action bar.",
            "Inspect figures, tables, parameters, and the audit log after every run.",
            "Save the project and reopen neuroflow_project.json to resume.",
        ]
        if english
        else [
            "创建空项目并导入自己的数据，或打开教学模拟项目。",
            "先核对数据结构和原始波形，再进入预处理。",
            "从底部固定操作栏运行当前所选分析。",
            "每次运行后检查图、表、参数和右侧审计记录。",
            "保存项目，之后重新打开 neuroflow_project.json 继续。",
        ]
    )
    body = f"""
<section data-searchable>
  <h2>{'Product principles' if english else '产品原则'}</h2>
  <div class="grid-3">
    {''.join(f'<article class="panel"><h3>{e(name)}</h3><p>{e(text)}</p></article>' for name, text in principles)}
  </div>
</section>
<section data-searchable>
  <h2>{'Start in five minutes' if english else '五分钟开始'}</h2>
  <ol class="steps">{''.join(f'<li>{e(item)}</li>' for item in quick)}</ol>
  <div class="callout method">{'AI is optional. Manual and guided workflows remain fully usable without a local model.' if english else 'AI 是可选助手；没有本地模型时，手动模式和引导模式仍可完整使用。'}</div>
</section>
<section data-searchable>
  <h2>{'The complete workflow' if english else '完整工作流'}</h2>
  <div class="stage-list">{''.join(_chapter_card(chapter, language) for chapter in TUTORIALS)}</div>
</section>
"""
    return _layout(language, "index.html", title, lead, body)


def build_installation(language: str) -> str:
    english = language == "en_US"
    title = "Installation and runtime" if english else "安装与运行"
    lead = (
        "The desktop application, scientific environments, sorter backends, and project data are separated so one failed tool does not prevent NeuroFlow from opening."
        if english
        else "桌面程序、科学计算环境、sorter 后端和项目数据彼此分离，单个工具安装失败不会阻止 NeuroFlow 打开。"
    )
    sections = (
        [
            ("System requirements", ["Windows 10/11, macOS, or Linux for the interface.", "Sufficient disk space for source data, normalized caches, sorter output, and exports.", "An NVIDIA GPU is recommended for Kilosort4; CPU sorters remain separate alternatives."]),
            ("Desktop installation", ["Install or unpack the NeuroFlow release.", "Start NeuroFlow without opening a Python console.", "Open Sorter Manager to inspect actual backends, versions, hardware requirements, and probe suitability."]),
            ("Project storage", ["The source is read-only. Generic binary data can be linked or copied into the project.", "A project contains neuroflow_project.json, derived results, sorter-native folders, exports, and audit logs.", "Keep the source path stable when using a link; copy the source for a self-contained archive."]),
            ("External sorter environments", ["A sorter is shown as runnable only after a real environment probe.", "Kilosort4 uses its installed Python/GPU stack; other sorters may use CPU, containers, or separate environments.", "NeuroFlow preserves exact failures and never substitutes another sorter silently."]),
        ]
        if english
        else [
            ("系统要求", ["界面支持 Windows 10/11、macOS 或 Linux。", "磁盘需要同时容纳原始数据、标准缓存、sorter 输出和导出文件。", "Kilosort4 推荐 NVIDIA GPU；CPU sorter 作为独立备选，不是假装执行 Kilosort。"]),
            ("桌面软件安装", ["安装或解压 NeuroFlow 发行版。", "直接启动 NeuroFlow，不要求用户先打开 Python 终端。", "在“Sorter 管理”中查看真实后端、版本、硬件要求和适用探针。"]),
            ("项目存储", ["原始数据保持只读；通用二进制可只建立索引，也可复制到项目。", "项目包含 neuroflow_project.json、派生结果、sorter 原生目录、导出和审计记录。", "使用索引时保持源路径稳定；需要独立归档时复制原始数据。"]),
            ("外部 sorter 环境", ["只有通过实际环境检测的 sorter 才显示“可运行”。", "Kilosort4 使用其 Python/GPU 环境；其他 sorter 可使用 CPU、容器或独立环境。", "NeuroFlow 保存真实错误，绝不静默换用另一个 sorter。"]),
        ]
    )
    body = "".join(
        f'<section data-searchable><h2>{e(heading)}</h2><ol class="steps">'
        + "".join(f"<li>{e(item)}</li>" for item in items)
        + "</ol></section>"
        for heading, items in sections
    )
    return _layout(language, "installation.html", title, lead, body)


def build_gui_guide(language: str) -> str:
    english = language == "en_US"
    title = "Interface and basic operation" if english else "界面与基本操作"
    lead = (
        "Use the workspace in a consistent order: select a stage, choose a sub-analysis, inspect its explanation and inputs, run it from the fixed footer, then review evidence."
        if english
        else "按照固定顺序使用工作区：选择阶段、选择子分析、阅读目的与输入、从底部固定栏运行，再检查结果证据。"
    )
    rows = (
        [
            ("Top bar", "Return home, switch language, inspect sorter environments, save the project, open tutorials, and run the complete workflow."),
            ("Left workflow", "Select one of 11 stages. Status color indicates pending, completed, skipped, or failed; it does not certify scientific validity."),
            ("Stage header", "Select the exact view or sub-analysis. The page below shows input or previously saved results for that selection."),
            ("Figure area", "Click marks for values, use toolbar zoom/pan, double-click an axis to edit it, or open one panel independently."),
            ("Right guidance", "Shows the current purpose, checks, control help, data inventory, and append-only run/audit log."),
            ("Fixed bottom bar", "Always remains visible during vertical scrolling. It names the current selection, shows progress, and runs only that selection."),
        ]
        if english
        else [
            ("顶部栏", "返回首页、切换语言、检查 sorter 环境、保存项目、打开教程和运行完整流程。"),
            ("左侧工作流", "选择 11 个阶段之一。颜色只表示待运行、已完成、跳过或失败，不代表科学有效性。"),
            ("阶段标题区", "选择当前具体视图或子分析；下方只显示该选择的输入预览或已保存结果。"),
            ("图形区", "单击图元查看数值，工具栏缩放/平移，双击坐标轴编辑，或单独放大一个子图。"),
            ("右侧引导", "显示当前目的、检查项、控件帮助、数据清单和只追加的运行/审计记录。"),
            ("底部固定操作栏", "上下滚动时始终可见，显示当前选择和进度，只运行当前所选分析。"),
        ]
    )
    sequence = (
        ["Read the stage purpose.", "Confirm that required inputs are available.", "Choose the view and settings.", "Run from the fixed footer and confirm the dialog.", "Inspect figures, tables, warnings, and logs.", "Save the project."]
        if english
        else ["阅读本阶段目的。", "确认所需输入确实存在。", "选择视图和参数。", "在底部固定栏运行并确认弹窗。", "检查图、表、警告和日志。", "保存项目。"]
    )
    body = f"""
<section data-searchable>
  <h2>{'Workspace anatomy' if english else '工作区组成'}</h2>
  <table><thead><tr><th>{'Area' if english else '区域'}</th><th>{'What it does' if english else '作用'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><b>{e(a)}</b></td><td>{e(b)}</td></tr>' for a,b in rows)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'One-analysis operating sequence' if english else '运行一个分析的标准顺序'}</h2>
  <ol class="steps">{''.join(f'<li>{e(item)}</li>' for item in sequence)}</ol>
  <img class="product-shot" src="../assets/neuroflow-analysis.png" alt="NeuroFlow analysis workspace">
</section>
<section data-searchable>
  <h2>{'Tutorial center' if english else '教程中心'}</h2>
  <p>{'Every workflow chapter uses the same structure: scientific purpose, prerequisites, operations, parameter reference, page controls, recommended sequence, common mistakes, checks, sources, and the next stage.' if english else '每个工作流章节都使用同一结构：科学目的、开始前准备、具体操作、参数说明、页面控件、推荐顺序、常见错误、验收检查、方法来源和下一步。'}</p>
  <img class="product-shot" src="../assets/neuroflow-tutorial.png" alt="NeuroFlow tutorial center">
</section>
<section data-searchable>
  <h2>{'Save, close, and resume' if english else '保存、退出与恢复'}</h2>
  <p>{'A star in the title indicates unsaved project state. Closing prompts Save, Discard, or Cancel. Save stores the current page, workflow status, parameters, results, sorter registry, and audit log. Reopen neuroflow_project.json from the home page to resume.' if english else '标题中的星号表示项目存在未保存修改。关闭时会提供“保存、放弃、取消”。保存会记录当前页面、工作流状态、参数、结果、sorter 注册表和审计日志；之后从首页打开 neuroflow_project.json 即可继续。'}</p>
</section>
"""
    return _layout(language, "gui-guide.html", title, lead, body)


def _tutorial_chapter(chapter: dict[str, str], language: str) -> str:
    english = language == "en_US"
    detail = TUTORIAL_DETAILS[chapter["key"]]
    operations = localized_rows(detail, "operations", language)
    parameters = localized_rows(detail, "parameters", language)
    controls = (
        PAGE_CONTROLS_EN.get(chapter["key"], [])
        if english
        else PAGE_CONTROLS.get(chapter["key"], [])
    )
    recommendations = localized(detail, "recommended", language)
    pitfalls = localized(detail, "pitfalls", language)
    return f"""
<section id="{e(chapter['key'])}" class="manual-chapter" data-searchable>
  <p class="chapter-kicker">{e(chapter['title'][:2])}</p>
  <h2>{e(tutorial_value(chapter, 'title', language)[3:])}</h2>
  <div class="callout method">{e(localized(detail, 'narrative', language))}</div>
  <h3>{'Before you begin' if english else '开始前准备'}</h3>
  <p>{e(localized(detail, 'before', language))}</p>
  <h3>{'Operations and purpose' if english else '可执行操作与目的'}</h3>
  <table><thead><tr><th>{'Operation' if english else '操作'}</th><th>{'What you do' if english else '怎么做'}</th><th>{'Purpose' if english else '目的'}</th><th>{'Result' if english else '结果'}</th></tr></thead>
  <tbody>{''.join(f"<tr><td><b>{e(row['name'])}</b></td><td>{e(row['action'])}</td><td>{e(row['purpose'])}</td><td>{e(row['result'])}</td></tr>" for row in operations)}</tbody></table>
  <h3>{'Parameters' if english else '参数说明'}</h3>
  <table class="parameter-table"><thead><tr><th>{'Parameter' if english else '参数'}</th><th>{'Meaning' if english else '含义'}</th><th>{'Default' if english else '默认值'}</th><th>{'Recommendation' if english else '推荐设置'}</th><th>{'Effect of changing it' if english else '改变后的影响'}</th></tr></thead>
  <tbody>{''.join(f"<tr><td><code>{e(row['name'])}</code></td><td>{e(row['meaning'])}</td><td>{e(row['default'])}</td><td>{e(row['recommended'])}</td><td>{e(row['effect'])}</td></tr>" for row in parameters)}</tbody></table>
  <h3>{'Every page control' if english else '本页每个控件'}</h3>
  <dl class="control-list">{''.join(f'<dt>{e(name)}</dt><dd>{e(description)}</dd>' for name,description in controls)}</dl>
  <div class="grid-2">
    <article class="panel"><h3>{'Recommended sequence' if english else '推荐顺序'}</h3><ol>{''.join(f'<li>{e(item)}</li>' for item in recommendations)}</ol></article>
    <article class="panel warning-panel"><h3>{'Common mistakes' if english else '常见错误'}</h3><ul>{''.join(f'<li>{e(item)}</li>' for item in pitfalls)}</ul></article>
  </div>
  <h3>{'Inputs, outputs, and acceptance check' if english else '输入、输出与验收检查'}</h3>
  <p><b>{'Input' if english else '输入'}：</b>{e(tutorial_value(chapter, 'input', language))}</p>
  <p><b>{'Output' if english else '输出'}：</b>{e(tutorial_value(chapter, 'output', language))}</p>
  <p><b>{'Check' if english else '检查'}：</b>{e(tutorial_value(chapter, 'checks', language))}</p>
  <div class="callout next"><b>{'Next' if english else '下一步'}：</b> {e(localized(detail, 'next', language))}</div>
</section>
"""


def build_tutorials(language: str) -> str:
    english = language == "en_US"
    title = "Complete step-by-step tutorial" if english else "完整逐步教程"
    lead = (
        "Follow all 11 stages from data structure to a restorable publication bundle. Each chapter explains purpose, operation, every exposed parameter, default, recommendation, consequence, and acceptance check."
        if english
        else "沿 11 个阶段从数据结构走到可恢复的论文复现包；每章都解释目的、操作、页面参数、默认值、推荐设置、修改影响和验收检查。"
    )
    toc = "".join(
        f'<a class="toc-chip" href="#{e(chapter["key"])}">{e(tutorial_value(chapter, "title", language))}</a>'
        for chapter in TUTORIALS
    )
    body = f'<section class="chapter-toc">{toc}</section>' + "".join(
        _tutorial_chapter(chapter, language) for chapter in TUTORIALS
    )
    return _layout(language, "tutorials.html", title, lead, body)


def build_data_inputs(language: str) -> str:
    english = language == "en_US"
    title = "Import your own data" if english else "导入自己的数据"
    lead = (
        "Create a project first, then choose the route that matches the files you actually have. Raw voltage and processed unit data enter at different workflow stages."
        if english
        else "先创建项目，再按手中真实文件选择入口。含原始电压的数据与只有处理后 unit 的数据会从不同阶段进入工作流。"
    )
    routes = (
        [
            ("Generic binary", ".bin/.dat/.raw plus rate, total channels, dtype, µV/bit, and optional events CSV.", "Raw QC", "Yes"),
            ("Acquisition system", "Intan, Open Ephys, SpikeGLX, Blackrock, Plexon, TDT, or NWB ElectricalSeries.", "Raw QC", "Yes"),
            ("Existing sorting", "Kilosort/Phy output with spike_times and cluster assignments.", "Unit QC", "No, unless raw voltage is also supplied"),
            ("IBL ALF / BWM", "Processed spikes and trials, or a behavior aggregate.", "Unit/behavior", "No"),
            ("NWB Units", "Units table and available behavior/state objects.", "Unit/behavior", "Only if a raw ElectricalSeries is imported separately"),
            ("Teaching simulation", "Neuropixels-like, tetrode, or microwire-style deterministic recording with behavior and ground truth.", "Raw QC", "Yes"),
        ]
        if english
        else [
            ("通用二进制", ".bin/.dat/.raw，加采样率、总通道数、dtype、µV/bit 和可选事件 CSV。", "原始质控", "可以"),
            ("记录系统文件", "Intan、Open Ephys、SpikeGLX、Blackrock、Plexon、TDT 或 NWB ElectricalSeries。", "原始质控", "可以"),
            ("已有 sorting", "含 spike_times 和 cluster 分配的 Kilosort/Phy 输出。", "Unit 质控", "不可以，除非另有原始电压"),
            ("IBL ALF / BWM", "处理后 spike 与 trials，或行为汇总。", "Unit/行为", "不可以"),
            ("NWB Units", "Units 表和可用行为/状态对象。", "Unit/行为", "只有另行导入原始 ElectricalSeries 才可以"),
            ("教学模拟", "带行为和 ground truth 的 Neuropixels-like、tetrode 或微丝风格确定性记录。", "原始质控", "可以"),
        ]
    )
    checklist = (
        ["Source path remains readable.", "File size, duration, channels, and dtype are internally consistent.", "Probe geometry and channel groups match the recording.", "Event units and clocks are explicit.", "Decide whether to link or copy the raw source."]
        if english
        else ["源路径保持可读取。", "文件大小、时长、通道数和 dtype 相互一致。", "探针几何和通道分组与记录匹配。", "事件单位和设备时钟明确。", "决定只索引还是把原始数据复制进项目。"]
    )
    body = f"""
<section data-searchable>
  <h2>{'Choose by what you have' if english else '按手中数据选择入口'}</h2>
  <table><thead><tr><th>{'Route' if english else '入口'}</th><th>{'Required files' if english else '需要提供'}</th><th>{'Workflow starts at' if english else '从哪里开始'}</th><th>{'Can run sorting?' if english else '能否 sorting'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><b>{e(a)}</b></td><td>{e(b)}</td><td>{e(c)}</td><td>{e(d)}</td></tr>' for a,b,c,d in routes)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Generic binary checklist' if english else '通用二进制导入检查'}</h2>
  <ol class="steps">{''.join(f'<li>{e(item)}</li>' for item in checklist)}</ol>
  <div class="callout warning">{'A file that opens is not necessarily interpreted correctly. A wrong channel count or dtype can produce plausible-looking but invalid traces.' if english else '文件能够打开不等于解释正确；错误通道数或 dtype 可能产生看似有波形、实际完全错误的数据。'}</div>
</section>
<section data-searchable>
  <h2>{'Behavior CSV example' if english else '行为 CSV 示例结构'}</h2>
  <pre><code>trial,time_seconds,event_type,condition,choice,reaction_time
1,12.450,stimulus_onset,A,left,0.620
1,13.070,response,A,left,0.620</code></pre>
  <p>{'A separate TTL CSV may contain ephys-clock pulse times. NeuroFlow pairs the pulse sequence and reports offset, drift, residuals, and missing events.' if english else '另一个 TTL CSV 可提供电生理时钟中的脉冲时间。NeuroFlow 会匹配脉冲序列，并报告起始偏移、漂移、残差和缺失事件。'}</p>
</section>
"""
    return _layout(language, "data-inputs.html", title, lead, body)


def build_sorting(language: str) -> str:
    english = language == "en_US"
    title = "Spike sorting guide" if english else "Spike sorting 指南"
    lead = (
        "Select a real backend, review backend-specific parameters, run it with confirmation, inspect its native diagnostics, and normalize only the common output needed downstream."
        if english
        else "选择真实后端、核对该工具专属参数、确认后运行、检查原生诊断，最后只把下游共用结果统一格式化。"
    )
    sorters = (
        [
            ("Kilosort4", "GPU template matching", "Dense silicon probes and Neuropixels", "Inspect preprocessed heatmap, drift, depth-time, amplitude, templates, similarity, and logs."),
            ("MountainSort5", "CPU schemes 1/2/3", "Tetrode and sparse/medium-channel recordings", "Inspect scheme, detection threshold, training duration, waveforms, and unit output."),
            ("SpyKING CIRCUS 2", "SpikeInterface backend", "General multichannel extracellular recordings", "Keep its own logs and parameters; do not show Kilosort-only stages."),
            ("Tridesclous 2", "CPU backend", "Low-to-medium channel counts", "Review detector/clustering settings and native output."),
            ("Internal teaching sorters", "Controlled internal algorithms", "Workflow teaching and smoke tests", "Never present them as Kilosort or a production benchmark."),
        ]
        if english
        else [
            ("Kilosort4", "GPU 模板匹配", "高密度硅探针和 Neuropixels", "检查预处理热图、漂移、深度-时间、振幅、模板、相似度和日志。"),
            ("MountainSort5", "CPU Scheme 1/2/3", "tetrode 和稀疏/中等通道记录", "检查 scheme、检测阈值、训练时长、波形和 unit 输出。"),
            ("SpyKING CIRCUS 2", "SpikeInterface 后端", "通用多通道细胞外记录", "保留自己的日志和参数，不显示 Kilosort 专属阶段。"),
            ("Tridesclous 2", "CPU 后端", "低到中等通道数", "检查检测/聚类参数和原生输出。"),
            ("内部教学 sorter", "受控内部算法", "工作流教学和冒烟测试", "不得冒充 Kilosort 或生产基准。"),
        ]
    )
    ks_params = localized_rows(TUTORIAL_DETAILS["sorting"], "parameters", language)
    body = f"""
<section data-searchable>
  <h2>{'Backend selection' if english else '后端选择'}</h2>
  <table><thead><tr><th>Sorter</th><th>{'Execution' if english else '执行方式'}</th><th>{'Best fit' if english else '适用记录'}</th><th>{'Evidence to inspect' if english else '必须检查的证据'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><b>{e(a)}</b></td><td>{e(b)}</td><td>{e(c)}</td><td>{e(d)}</td></tr>' for a,b,c,d in sorters)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Kilosort4 operating sequence' if english else 'Kilosort4 操作顺序'}</h2>
  <ol class="steps">
    {''.join(f'<li>{e(item)}</li>' for item in (["Confirm binary layout and total channel count.", "Confirm probe geometry and preview it.", "Inspect raw and preprocessed input before running.", "Run with default settings on a representative segment.", "Inspect drift, depth-time, amplitudes, templates, similarity, exported files, and log.", "Run the full session and continue to Unit QC."] if english else ["确认二进制布局和文件总通道数。", "确认并预览探针几何。", "运行前检查原始与预处理输入。", "先用默认参数运行代表性片段。", "检查漂移、深度-时间、振幅、模板、相似度、导出文件和日志。", "运行整段记录并进入 Unit 质控。"]))}
  </ol>
  <img class="product-shot" src="../assets/neuroflow-sorting.png" alt="NeuroFlow sorting workbench">
</section>
<section data-searchable>
  <h2>{'Kilosort4 settings exposed by NeuroFlow' if english else 'NeuroFlow 中的 Kilosort4 参数'}</h2>
  <table class="parameter-table"><thead><tr><th>{'Parameter' if english else '参数'}</th><th>{'Meaning' if english else '含义'}</th><th>{'Default' if english else '默认值'}</th><th>{'Recommendation' if english else '推荐设置'}</th><th>{'Consequence' if english else '改变后的影响'}</th></tr></thead>
  <tbody>{''.join(f"<tr><td><code>{e(row['name'])}</code></td><td>{e(row['meaning'])}</td><td>{e(row['default'])}</td><td>{e(row['recommended'])}</td><td>{e(row['effect'])}</td></tr>" for row in ks_params)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Unified result and comparison' if english else '统一结果与比较'}</h2>
  <p>{'Every backend keeps its native folder. NeuroFlow additionally records unit IDs, spike times in seconds, sampling rate, versions, parameters, logs, and optional channel/template fields in a common downstream schema. Sorter comparison reports matched, split, merged, unique, and consensus units. On real data this is agreement, not accuracy.' if english else '每个后端保留原生目录。NeuroFlow 额外把 unit ID、秒级 spike times、采样率、版本、参数、日志和可用通道/模板字段写入统一下游结构。sorter 比较报告匹配、拆分、合并、独有和共识 unit；真实数据上这叫一致度，不叫准确率。'}</p>
</section>
"""
    return _layout(language, "sorting.html", title, lead, body)


def build_parameters(language: str) -> str:
    english = language == "en_US"
    title = "Parameter reference" if english else "参数参考"
    lead = (
        "Defaults are starting points, not universal truth. Change one setting at a time, preserve the reason, and compare evidence before and after."
        if english
        else "默认值只是起点，不是通用真值。每次只改一个参数，记录原因，并比较修改前后的证据。"
    )
    sections = []
    for chapter in TUTORIALS:
        rows = localized_rows(TUTORIAL_DETAILS[chapter["key"]], "parameters", language)
        sections.append(
            f"""<section id="{e(chapter['key'])}" data-searchable>
<h2>{e(tutorial_value(chapter, 'title', language))}</h2>
<table class="parameter-table"><thead><tr><th>{'Parameter' if english else '参数'}</th><th>{'Meaning' if english else '含义'}</th><th>{'Default' if english else '默认值'}</th><th>{'Recommendation' if english else '推荐设置'}</th><th>{'Effect of changing it' if english else '改变后的影响'}</th></tr></thead>
<tbody>{''.join(f"<tr><td><code>{e(row['name'])}</code></td><td>{e(row['meaning'])}</td><td>{e(row['default'])}</td><td>{e(row['recommended'])}</td><td>{e(row['effect'])}</td></tr>" for row in rows)}</tbody></table>
</section>"""
        )
    return _layout(language, "parameters.html", title, lead, "".join(sections))


def build_figure_studio(language: str) -> str:
    english = language == "en_US"
    title = "Figure editing and export" if english else "图形编辑与导出"
    lead = (
        "Edit individual artists and axes without changing the underlying analysis. Keep publication styling, plotted data, statistics, and provenance connected."
        if english
        else "逐个编辑图元和坐标轴，但不改变底层分析。论文样式、绘图数据、统计和来源始终保持关联。"
    )
    items = (
        [
            ("Inspect values", "Click a line, point, bar, image, or trace to display its coordinates and associated label."),
            ("Zoom and pan", "Use the Matplotlib toolbar for local inspection; Home restores the original limits."),
            ("Edit axes", "Double-click an axis to edit title, labels, limits, grid, ticks, spine visibility, width, and extent."),
            ("Edit artists", "Change line width/style/color, marker shape/size/fill, bar fill/edge, image colormap/range, and text."),
            ("Edit layout", "Set exact width/height, margins, panel spacing, legend position, background, font family, and font size."),
            ("Export one panel", "Select a panel and save SVG, PDF, or PNG without screenshot cropping."),
        ]
        if english
        else [
            ("查看数值", "单击线、点、柱、热图或波形，显示坐标和对应标签。"),
            ("缩放和平移", "使用 Matplotlib 工具栏局部观察；Home 恢复原始范围。"),
            ("编辑坐标轴", "双击坐标轴，修改标题、标签、范围、网格、刻度、边框显示、粗细和长度。"),
            ("编辑图元", "修改线宽/线型/颜色、点形/大小/填充、柱填充/边缘、热图色表/范围和文字。"),
            ("编辑布局", "设置精确宽高、页边距、panel 间距、图例位置、背景、字体和字号。"),
            ("导出一个子图", "选择 panel，直接保存 SVG、PDF 或 PNG，不使用截图裁剪。"),
        ]
    )
    body = f"""
<section data-searchable>
  <h2>{'Editing controls' if english else '编辑能力'}</h2>
  <div class="grid-2">{''.join(f'<article class="panel"><h3>{e(a)}</h3><p>{e(b)}</p></article>' for a,b in items)}</div>
</section>
<section data-searchable>
  <h2>{'Publication checklist' if english else '论文图检查清单'}</h2>
  <ol class="steps">{''.join(f'<li>{e(item)}</li>' for item in (["Axis labels include units.", "Sample size and error-bar definitions are explicit.", "Statistical annotations link to a saved table.", "Colors remain distinguishable in print and for color-vision deficiencies.", "Text fits the final physical dimensions.", "SVG/PDF and plotted CSV are saved together."] if english else ["坐标标签包含单位。", "样本量和误差线定义明确。", "统计标注能追溯到已保存统计表。", "颜色在打印和常见色觉条件下可区分。", "文字在最终物理尺寸下仍能完整显示。", "SVG/PDF 与绘图 CSV 一起保存。"]))}</ol>
  <img class="product-shot" src="../assets/neuroflow-figure-studio.png" alt="NeuroFlow Figure Studio">
</section>
"""
    return _layout(language, "figure-studio.html", title, lead, body)


def build_troubleshooting(language: str) -> str:
    english = language == "en_US"
    title = "Troubleshooting" if english else "故障排查"
    lead = (
        "Identify whether a failure comes from data structure, missing input, environment, resource limits, or analysis assumptions. Never hide a failure by showing an unrelated saved result."
        if english
        else "先判断失败来自数据结构、缺失输入、环境、资源还是分析假设；绝不能用无关旧结果掩盖运行失败。"
    )
    rows = (
        [
            ("Diagonal/repeated traces", "Wrong total channel count or dtype.", "Return to Data, verify the acquisition configuration, and re-import."),
            ("Selected sorter cannot run", "Backend or dependency is not installed, hardware is incompatible, or environment probing failed.", "Open Sorter Manager and follow that backend's exact diagnostic. Choose another sorter only as an explicit new decision."),
            ("A run shows another sorter's result", "The selected result was not activated or the run failed.", "Check active sorter, run log, native output folder, and result timestamp. NeuroFlow must show pending/failed rather than substitute."),
            ("No event-aligned analysis", "No events, wrong time units, or synchronization has not run.", "Import behavior/TTL, verify counts and residuals, then rerun the selected event analysis."),
            ("Completed stage has no restored figure", "The project was saved with an older schema or a linked source is missing.", "Open the audit log, verify source paths, then rerun only the missing derived stage."),
            ("Application close warning", "The project has unsaved navigation, parameters, decisions, or logs.", "Choose Save to update neuroflow_project.json, Discard to close without those changes, or Cancel to return."),
        ]
        if english
        else [
            ("波形重复或出现斜纹", "文件总通道数或 dtype 错误。", "返回数据页，核对采集配置后重新导入。"),
            ("所选 sorter 无法运行", "后端/依赖未安装、硬件不兼容或环境检测失败。", "打开 Sorter 管理查看该后端的具体诊断。若改用其他 sorter，必须作为新的明确选择。"),
            ("运行后出现另一个 sorter 的结果", "所选结果未激活或运行已失败。", "检查 active sorter、运行日志、原生输出目录和时间戳；软件应显示待运行/失败，不能替换。"),
            ("无法做事件对齐分析", "没有事件、时间单位错误或尚未同步。", "导入行为/TTL，核对数量和残差，再单独运行所选事件分析。"),
            ("已完成阶段恢复后没有图", "项目由旧 schema 保存，或只读源路径已失效。", "查看审计日志并核对源路径，只重跑缺失的派生阶段。"),
            ("关闭软件出现保存提示", "项目存在未保存的页面、参数、决定或日志。", "选择保存更新 neuroflow_project.json；放弃则不保存这些修改；取消返回程序。"),
        ]
    )
    body = f"""
<section data-searchable>
  <table><thead><tr><th>{'Symptom' if english else '现象'}</th><th>{'Likely cause' if english else '可能原因'}</th><th>{'Action' if english else '处理方法'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><b>{e(a)}</b></td><td>{e(b)}</td><td>{e(c)}</td></tr>' for a,b,c in rows)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'What to include in a bug report' if english else '反馈问题时需要提供'}</h2>
  <ul>{''.join(f'<li>{e(item)}</li>' for item in (["NeuroFlow version and operating system", "Project manifest with private paths redacted", "Current stage, selection, and parameters", "Exact first error line and audit-log tail", "Sorter name, backend version, GPU/CPU status", "Whether the issue reproduces on a teaching simulation"] if english else ["NeuroFlow 版本和操作系统", "隐去敏感路径后的项目清单", "当前阶段、具体选项和参数", "第一行真实错误与审计日志末尾", "sorter 名称、后端版本和 GPU/CPU 状态", "教学模拟项目能否复现"]))}</ul>
</section>
"""
    return _layout(language, "troubleshooting.html", title, lead, body)


def build_sources(language: str) -> str:
    english = language == "en_US"
    title = "Methods and sources" if english else "方法与来源"
    lead = (
        "NeuroFlow reuses established open-source computation and writes original interface, interoperability, tutorial, and audit layers. The summaries below are original paraphrases, not copied documentation."
        if english
        else "NeuroFlow 复用成熟开源计算能力，自主编写界面、兼容、教程和审计层。以下内容为原创概括，不复制原文。"
    )
    sources = [
        ("Kilosort4 documentation", "https://kilosort.readthedocs.io/en/latest/", "Documentation organization, GUI operating order, parameters, exported files, drift checks, sample-data tutorial."),
        ("Kilosort4 GUI guide", "https://kilosort.readthedocs.io/en/latest/gui_guide.html", "Data/probe selection, input preview, channel-count checks, run sequence."),
        ("Kilosort4 parameter guide", "https://kilosort.readthedocs.io/en/latest/parameters.html", "n_chan_bin, batch_size, nblocks, thresholds, time range, geometry, and duplicate-spike cautions."),
        ("SpikeInterface", "https://spikeinterface.readthedocs.io/en/stable/", "Extractors, preprocessing, sorter wrappers, postprocessing, quality metrics, and comparison interfaces."),
        ("SpikeInterface sorters", "https://spikeinterface.readthedocs.io/en/stable/modules/sorters.html", "Common sorter wrappers, native dependencies, and container execution."),
        ("Elephant", "https://elephant.readthedocs.io/en/stable/modules.html", "Spike-train statistics, spectral analysis, correlation, phase, and signal-analysis APIs on Neo objects."),
        ("Neo", "https://neo.readthedocs.io/en/stable/read_and_analyze.html", "Unit-aware SpikeTrain, AnalogSignal, Event, Epoch, Segment, and Block objects."),
        ("Phy", "https://phy.readthedocs.io/en/latest/quickstart/", "Manual review of spike-sorting output."),
        ("MountainSort5", "https://pypi.org/project/mountainsort5/", "CPU-oriented sorting schemes and package interface."),
        ("Respiration/PFC study", "https://pmc.ncbi.nlm.nih.gov/articles/PMC10312056/", "Method structure for behavioral-state, respiration, spike, LFP, phase, and surrogate analyses."),
        ("GraphPad Prism graph controls", "https://www.graphpad.com/guides/prism/latest/user-guide/how_to_change_a_graph.htm", "Interaction expectations for editable graph objects, axes, grids, ticks, and exact size."),
        ("IBL Brain-Wide Map", "https://www.internationalbrainlab.com/brainwidemap", "Public neural and behavioral validation context."),
        ("DANDI Archive", "https://docs.dandiarchive.org/introduction/", "Versioned NWB public-data access and provenance."),
    ]
    body = f"""
<section data-searchable>
  <h2>{'Attribution table' if english else '来源与借鉴范围'}</h2>
  <table><thead><tr><th>{'Source' if english else '来源'}</th><th>{'How NeuroFlow uses it' if english else 'NeuroFlow 借鉴或调用的范围'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><a href="{e(url)}">{e(name)}</a></td><td>{e(scope if english else {"Documentation organization, GUI operating order, parameters, exported files, drift checks, sample-data tutorial.":"文档层级、GUI 操作顺序、参数、导出文件、漂移检查和示例教程结构。","Data/probe selection, input preview, channel-count checks, run sequence.":"数据/探针选择、输入预览、通道数检查和运行顺序。","n_chan_bin, batch_size, nblocks, thresholds, time range, geometry, and duplicate-spike cautions.":"n_chan_bin、batch_size、nblocks、阈值、时间范围、几何和重复 spike 注意事项。","Extractors, preprocessing, sorter wrappers, postprocessing, quality metrics, and comparison interfaces.":"数据读取、预处理、sorter 适配、后处理、质量指标和比较接口。","Common sorter wrappers, native dependencies, and container execution.":"统一 sorter wrapper、原生依赖和容器执行机制。","Spike-train statistics, spectral analysis, correlation, phase, and signal-analysis APIs on Neo objects.":"基于 Neo 对象的 spike train 统计、频谱、相关、相位和信号分析 API。","Unit-aware SpikeTrain, AnalogSignal, Event, Epoch, Segment, and Block objects.":"带单位的 SpikeTrain、AnalogSignal、Event、Epoch、Segment 和 Block 对象。","Manual review of spike-sorting output.":"spike sorting 输出的人工复核工作流。","CPU-oriented sorting schemes and package interface.":"面向 CPU 的 sorting scheme 和包接口。","Method structure for behavioral-state, respiration, spike, LFP, phase, and surrogate analyses.":"行为状态、呼吸、spike、LFP、相位和 surrogate 分析的方法结构。","Interaction expectations for editable graph objects, axes, grids, ticks, and exact size.":"图元、坐标轴、网格、刻度和精确尺寸的可编辑交互预期。","Public neural and behavioral validation context.":"公开神经与行为数据的验证背景。","Versioned NWB public-data access and provenance.":"版本化 NWB 公开数据访问与来源记录。"}[scope])}</td></tr>' for name,url,scope in sources)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Non-copying rule' if english else '不直接抄袭原则'}</h2>
  <div class="callout warning">{'NeuroFlow does not reproduce another product’s prose, screenshots, figures, numerical conclusions, or visual identity. It uses official method definitions and documentation patterns as references, then writes original product text, workflows, adapters, and interface behavior.' if english else 'NeuroFlow 不复制其他产品的原文、截图、论文图、数值结论或视觉识别；只把官方方法定义和文档组织方式作为参考，再自主编写产品文字、工作流、适配器和界面行为。'}</div>
</section>
"""
    return _layout(language, "sources.html", title, lead, body)


BUILDERS = {
    "index.html": build_index,
    "installation.html": build_installation,
    "gui-guide.html": build_gui_guide,
    "tutorials.html": build_tutorials,
    "data-inputs.html": build_data_inputs,
    "sorting.html": build_sorting,
    "parameters.html": build_parameters,
    "figure-studio.html": build_figure_studio,
    "troubleshooting.html": build_troubleshooting,
    "sources.html": build_sources,
}


def build() -> None:
    for language, folder in (("zh_CN", "zh"), ("en_US", "en")):
        output = SITE / folder
        output.mkdir(parents=True, exist_ok=True)
        for filename, builder in BUILDERS.items():
            (output / filename).write_text(builder(language), encoding="utf-8")
    (SITE / "index.html").write_text(
        """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>NeuroFlow Documentation</title>
    <link rel="stylesheet" href="styles.css?v=0.7.0">
  </head>
  <body class="language-gateway">
    <main class="gateway-panel">
      <p class="eyebrow">NeuroFlow Documentation</p>
      <h1>选择操作手册语言</h1>
      <p class="lead">每套手册只显示一种语言；专有软件名和参数名保持原名。</p>
      <div class="gateway-actions">
        <a class="gateway-button primary" data-language-link="zh" href="zh/index.html">中文</a>
        <a class="gateway-button" data-language-link="en" href="en/index.html">English</a>
      </div>
    </main>
    <script>
      const preferred = localStorage.getItem("neuroflow-docs-language");
      if (preferred === "zh" || preferred === "en") {
        location.replace(`${preferred}/index.html`);
      }
      document.querySelectorAll("[data-language-link]").forEach((link) => {
        link.addEventListener("click", () => localStorage.setItem("neuroflow-docs-language", link.dataset.languageLink));
      });
    </script>
  </body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
