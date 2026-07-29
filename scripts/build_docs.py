from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neuroflow.help_content import PAGE_CONTROLS, PAGE_CONTROLS_EN  # noqa: E402
from neuroflow.tutorial_details import (  # noqa: E402
    TUTORIAL_DETAILS,
    localized,
    localized_rows,
)
from neuroflow.tutorials import TUTORIALS, tutorial_value  # noqa: E402

SITE = ROOT / "docs" / "site"

PAGES = (
    ("index.html", "概览", "Overview", "getting_started"),
    ("installation.html", "安装与运行", "Installation and runtime", "getting_started"),
    ("gui-guide.html", "界面与基本操作", "Interface and basic operation", "getting_started"),
    ("tutorials.html", "完整逐步教程", "Complete step-by-step tutorial", "tutorials"),
    ("data-inputs.html", "导入自己的数据", "Import your own data", "tutorials"),
    ("sorting.html", "Spike sorting 指南", "Spike sorting guide", "guides"),
    ("unit-curation.html", "Unit 人工复核", "Manual unit curation", "guides"),
    ("ai-assistant.html", "AI 助手", "AI assistant", "guides"),
    ("parameters.html", "参数参考", "Parameter reference", "guides"),
    ("figure-studio.html", "图形编辑与导出", "Figure editing and export", "guides"),
    ("provenance.html", "中间产物与溯源", "Artifacts and provenance", "reference"),
    ("real-data-validation.html", "真实数据验证", "Real-data validation", "reference"),
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
    intro = eyebrow or ("NeuroEphys AI operation manual" if language == "en_US" else "NeuroEphys AI 操作手册")
    document = f"""<!doctype html>
<html lang="{page_lang}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{e(title)} · NeuroEphys AI</title>
    <link rel="stylesheet" href="../styles.css?v=0.8.0">
  </head>
  <body>
    <header class="topbar">
      <button class="icon-button" type="button" data-menu-toggle aria-label="{e(menu)}">☰</button>
      <a class="brand" href="index.html">NeuroEphys AI <small>{'Documentation' if language == 'en_US' else '操作手册'}</small></a>
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
        <footer class="footer">NeuroEphys AI · {'Original explanatory text with cited method sources' if language == 'en_US' else '原创说明文字，方法来源逐项标注'}</footer>
      </main>
    </div>
    <script src="../app.js?v=0.8.0"></script>
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
        "NeuroEphys AI connects raw multichannel recordings, replaceable spike sorters, behavior, neural analyses, statistics, machine learning, and publication export in one local-first project."
        if english
        else "NeuroEphys AI 把原始多通道记录、可替换的 spike sorter、行为、神经分析、统计、机器学习和论文导出组织在一个本地优先的项目中。"
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
        "The desktop application, scientific environments, sorter backends, and project data are separated so one failed tool does not prevent NeuroEphys AI from opening."
        if english
        else "桌面程序、科学计算环境、sorter 后端和项目数据彼此分离，单个工具安装失败不会阻止 NeuroEphys AI 打开。"
    )
    sections = (
        [
            ("System requirements", ["Windows 10/11, macOS, or Linux for the interface.", "Sufficient disk space for source data, normalized caches, sorter output, and exports.", "An NVIDIA GPU is recommended for Kilosort4; CPU sorters remain separate alternatives."]),
            ("Desktop installation", ["Install or unpack the NeuroEphys AI release.", "Start NeuroEphys AI without opening a Python console.", "Open Sorter Manager to inspect actual backends, versions, hardware requirements, and probe suitability."]),
            ("Project storage", ["The source is read-only. Generic binary data can be linked or copied into the project.", "A project contains neuroflow_project.json, derived results, sorter-native folders, exports, and audit logs.", "Keep the source path stable when using a link; copy the source for a self-contained archive."]),
            ("External sorter environments", ["A sorter is shown as runnable only after a real environment probe.", "Kilosort4 uses its installed Python/GPU stack; other sorters may use CPU, containers, or separate environments.", "NeuroEphys AI preserves exact failures and never substitutes another sorter silently."]),
        ]
        if english
        else [
            ("系统要求", ["界面支持 Windows 10/11、macOS 或 Linux。", "磁盘需要同时容纳原始数据、标准缓存、sorter 输出和导出文件。", "Kilosort4 推荐 NVIDIA GPU；CPU sorter 作为独立备选，并明确显示实际执行工具。"]),
            ("桌面软件安装", ["安装或解压 NeuroEphys AI 发行版。", "直接启动 NeuroEphys AI，不要求用户先打开 Python 终端。", "在“Sorter 管理”中查看真实后端、版本、硬件要求和适用探针。"]),
            ("项目存储", ["原始数据保持只读；通用二进制可只建立索引，也可复制到项目。", "项目包含 neuroflow_project.json、派生结果、sorter 原生目录、导出和审计记录。", "使用索引时保持源路径稳定；需要独立归档时复制原始数据。"]),
            ("外部 sorter 环境", ["只有通过实际环境检测的 sorter 才显示“可运行”。", "Kilosort4 使用其 Python/GPU 环境；其他 sorter 可使用 CPU、容器或独立环境。", "NeuroEphys AI 保存真实错误，绝不静默换用另一个 sorter。"]),
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
  <img class="product-shot" src="../assets/neuroflow-analysis.png" alt="NeuroEphys AI analysis workspace">
</section>
<section data-searchable>
  <h2>{'Tutorial center' if english else '教程中心'}</h2>
  <p>{'Every workflow chapter uses the same structure: scientific purpose, prerequisites, operations, parameter reference, page controls, recommended sequence, common mistakes, checks, sources, and the next stage.' if english else '每个工作流章节都使用同一结构：科学目的、开始前准备、具体操作、参数说明、页面控件、推荐顺序、常见错误、验收检查、方法来源和下一步。'}</p>
  <img class="product-shot" src="../assets/neuroflow-tutorial.png" alt="NeuroEphys AI tutorial center">
</section>
<section data-searchable>
  <h2>{'Save, close, and resume' if english else '保存、退出与恢复'}</h2>
  <p>{'A star in the title indicates unsaved project state. Closing prompts Save, Discard, or Cancel. Save stores the current page, workflow status, parameters, results, sorter registry, and audit log. Reopen neuroflow_project.json from the home page to resume.' if english else '标题中的星号表示项目存在未保存修改。关闭时会提供“保存、放弃、取消”。保存会记录当前页面、工作流状态、参数、结果、sorter 注册表和审计日志；之后从首页打开 neuroflow_project.json 即可继续。'}</p>
</section>
"""
    return _layout(language, "gui-guide.html", title, lead, body)


def build_ai_assistant(language: str) -> str:
    english = language == "en_US"
    title = (
        "Controlled AI assistant"
        if english
        else "受控 AI 助手"
    )
    lead = (
        "The assistant works from the active project's structured evidence. It can "
        "explain, plan, and propose validated local tool calls while the deterministic "
        "analysis pipeline remains available at all times."
        if english
        else "助手依据当前项目的结构化证据工作，可解释、规划并提出经本地校验的工具调用；确定性分析管线始终可独立使用。"
    )
    modes = (
        [
            (
                "Manual",
                "Cloud AI is disabled. Data import, QC, sorting, curation, statistics, decoding, figure export, and project recovery remain available.",
            ),
            (
                "Assistant",
                "The model explains the project, parameters, warnings, and candidate workflows. It cannot request execution.",
            ),
            (
                "Collaborative",
                "The model may propose a whitelisted local tool call. NeuroEphys AI validates prerequisites and parameters, then shows a confirmation dialog before execution.",
            ),
        ]
        if english
        else [
            (
                "手动模式",
                "关闭云端 AI。数据导入、质控、sorting、人工复核、统计、解码、图表导出和项目恢复均可继续使用。",
            ),
            (
                "助手模式",
                "模型解释项目、参数、警告和候选工作流，没有执行权限。",
            ),
            (
                "协作模式",
                "模型可提出白名单本地工具调用。NeuroEphys AI先检查前置条件和参数，再弹出确认窗口，由用户决定是否执行。",
            ),
        ]
    )
    setup = (
        [
            "Open the collapsible AI panel on the right side of the workspace.",
            "Choose Manual, Assistant, or Collaborative mode.",
            "Open AI settings. DeepSeek is the first configured provider; OpenAI-compatible, laboratory, and local-compatible endpoints are also accepted.",
            "Enter the endpoint and model. The current DeepSeek defaults are https://api.deepseek.com and deepseek-v4-flash.",
            "Store the API key for the session or in the operating-system credential store. Project files never contain the key.",
            "Open Context preview. Remove any optional field that should not be sent.",
            "Enter a question or request a candidate workflow. Review every proposed node and parameter.",
        ]
        if english
        else [
            "在工作区右侧展开 AI 面板。",
            "选择手动、助手或协作模式。",
            "打开 AI 设置。首个配置入口为 DeepSeek，同时支持 OpenAI 兼容接口、实验室服务和本地兼容服务。",
            "填写服务地址和模型。当前 DeepSeek 默认地址为 https://api.deepseek.com，默认模型为 deepseek-v4-flash。",
            "API 密钥可只保留在当前会话，或写入操作系统凭据区；项目文件不会保存密钥。",
            "打开“上下文预览”，逐项检查并删除无需发送的可选字段。",
            "输入问题或请求候选工作流；逐项核对节点、前置条件和参数。",
        ]
    )
    context_rows = (
        [
            ("Raw voltage and large arrays", "Stay local and are excluded before request construction."),
            ("Local paths and identity fields", "Removed from the online context."),
            ("Acquisition structure", "Format, sample rate, channels, duration, units, probe, region, reference, and online filtering."),
            ("Derived evidence", "QC metrics, sorter provenance, unit metrics, synchronization residuals, statistics, decoding, and warnings."),
            ("Workflow state", "Completed, failed, skipped, pending stages, selected page, figure, sorter, and unit."),
            ("Intermediate artifacts", "Only labels, stage, parameters, size, checksum, and artifact IDs; binary contents remain local."),
            ("API key", "Used in the authorization header and stored only through the selected credential option."),
        ]
        if english
        else [
            ("原始电压与大型数组", "保留在本机，请求构造前即排除。"),
            ("本地路径与身份字段", "从在线上下文中移除。"),
            ("采集结构", "格式、采样率、通道、时长、单位、电极、脑区、参考和在线滤波。"),
            ("派生证据", "质控指标、sorter来源、unit指标、同步残差、统计、解码和警告。"),
            ("工作流状态", "已完成、失败、跳过、待运行阶段，以及当前页面、图表、sorter和unit。"),
            ("中间产物", "仅发送标签、阶段、参数、大小、校验值和产物ID；二进制内容留在本机。"),
            ("API 密钥", "仅用于授权请求头，并按用户选择写入会话或系统凭据区。"),
        ]
    )
    capabilities = (
        [
            "Explain recognized data and missing metadata after import.",
            "Create an editable workflow from a scientific question using registered nodes only.",
            "Compare compatible sorters while preserving their native requirements and outputs.",
            "Detect duplicate filtering, missing events, invalid LFP requests, and leakage risks.",
            "Read redacted errors and propose a recovery path.",
            "Propose previews or analyses through the local tool whitelist in Collaborative mode.",
            "Summarize figures with observed result, statistical evidence, interpretations, unsupported claims, limitations, and validation steps.",
            "Generate Methods drafts, output indexes, and audit-oriented summaries from actual project evidence.",
        ]
        if english
        else [
            "导入后解释已识别的数据与缺失元数据。",
            "把研究问题转换为可编辑工作流，节点限定在本地注册表内。",
            "比较可用sorter，同时保留各工具的原生要求与输出。",
            "检查重复滤波、事件缺失、无效LFP请求和数据泄漏风险。",
            "阅读脱敏错误并提出恢复路径。",
            "在协作模式中通过本地白名单提出预览或分析请求。",
            "按观察结果、统计证据、可考虑解释、当前无法支持的结论、限制和验证建议组织图表解释。",
            "根据项目中的真实证据生成Methods草稿、输出索引和审计摘要。",
        ]
    )
    body = f"""
<section data-searchable>
  <h2>{'Three operating modes' if english else '三种工作模式'}</h2>
  <table><thead><tr><th>{'Mode' if english else '模式'}</th><th>{'Permission boundary' if english else '权限边界'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><b>{e(name)}</b></td><td>{e(text)}</td></tr>' for name,text in modes)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Provider setup' if english else '模型服务设置'}</h2>
  <ol class="steps">{''.join(f'<li>{e(item)}</li>' for item in setup)}</ol>
  <div class="callout method">{'Provider settings include streaming, timeout, retries, cancellation, and service health. A provider change does not modify project data or analysis code.' if english else '设置项包含流式回复、超时、重试、取消和服务状态检测。更换模型服务不会改动项目数据与分析代码。'}</div>
  <img class="product-shot" src="../assets/neuroflow-ai-assistant.png" alt="NeuroEphys AI assistant panel">
</section>
<section data-searchable>
  <h2>{'Available assistance' if english else '可用能力'}</h2>
  <ul class="checks">{''.join(f'<li>{e(item)}</li>' for item in capabilities)}</ul>
</section>
<section data-searchable>
  <h2>{'Context sent to an online provider' if english else '在线请求使用的上下文'}</h2>
  <table><thead><tr><th>{'Information' if english else '信息'}</th><th>{'Handling' if english else '处理方式'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><b>{e(name)}</b></td><td>{e(text)}</td></tr>' for name,text in context_rows)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Tool-call lifecycle' if english else '工具调用过程'}</h2>
  <ol class="steps">
    <li>{'The provider returns a structured tool name and arguments.' if english else '模型返回结构化工具名和参数。'}</li>
    <li>{'The local registry rejects unknown tools, invalid fields, missing prerequisites, wrong workflow order, and unsafe segment lengths.' if english else '本地注册表拒绝未知工具、非法字段、缺失前提、错误顺序和不安全的数据片段。'}</li>
    <li>{'The confirmation dialog shows input, parameters, expected cost, data sent online, and output location.' if english else '确认窗口展示输入、参数、预计开销、在线发送内容和输出位置。'}</li>
    <li>{'The user accepts, edits, or cancels. Sorting and other long tasks always require confirmation.' if english else '用户可以接受、修改或取消；sorting等长任务始终需要确认。'}</li>
    <li>{'Completed or failed calls are linked to run IDs and artifact IDs in the project audit history.' if english else '完成或失败的调用通过run ID和artifact ID写入项目审计历史。'}</li>
  </ol>
</section>
<section data-searchable>
  <h2>{'Scientific interpretation format' if english else '科学解释格式'}</h2>
  <p>{'Every result explanation is separated into observed result, statistical evidence, possible biological interpretations, unsupported conclusions, limitations, and recommended validation. Candidate units retain their candidate status until manual review.' if english else '每次结果解释均分为观察结果、统计证据、可考虑的生物学解释、当前无法支持的结论、数据与方法限制、建议增加的验证。候选unit在人工复核前持续保留候选状态。'}</p>
</section>
<section data-searchable>
  <h2>{'Offline and failure behavior' if english else '断网与失败处理'}</h2>
  <p>{'A provider failure stops the AI request, preserves the project, and leaves every manual analysis control active. Check the endpoint, model, key, network, quota, timeout, and provider response format. The failure record excludes the key and raw data.' if english else '模型服务失败时，AI请求停止，项目保持原状，全部手动分析控件仍可使用。请检查服务地址、模型、密钥、网络、额度、超时和返回格式；失败记录不会包含密钥和原始数据。'}</p>
</section>
<section data-searchable>
  <h2>{'Implementation sources' if english else '实现依据'}</h2>
  <ul class="source-list">
    <li><a href="https://api-docs.deepseek.com/api/create-chat-completion">DeepSeek chat completion API</a></li>
    <li><a href="https://api-docs.deepseek.com/guides/function_calling/">DeepSeek function calling</a></li>
    <li><a href="https://api-docs.deepseek.com/guides/tool_calls">DeepSeek tool calls</a></li>
  </ul>
</section>
"""
    return _layout(language, "ai-assistant.html", title, lead, body)


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
            ("Existing Kilosort/Phy sorting", "Kilosort/Phy output directory with spike_times and cluster assignments.", "Unit QC", "Only when the project also has raw voltage"),
            ("Existing NeuroExplorer NEX5 sorting", "One .nex5 file or a folder containing several .nex5 files; filenames may be filtered by subject.", "Unit QC and sorter comparison", "Only when the project also has raw voltage"),
            ("IBL ALF / BWM", "Processed spikes and trials, or a behavior aggregate.", "Unit/behavior", "No"),
            ("NWB Units", "Units table and available behavior/state objects.", "Unit/behavior", "Only if a raw ElectricalSeries is imported separately"),
            ("Teaching simulation", "Neuropixels-like, tetrode, or microwire-style deterministic recording with behavior and ground truth.", "Raw QC", "Yes"),
        ]
        if english
        else [
            ("通用二进制", ".bin/.dat/.raw，加采样率、总通道数、dtype、µV/bit 和可选事件 CSV。", "原始质控", "可以"),
            ("记录系统文件", "Intan、Open Ephys、SpikeGLX、Blackrock、Plexon、TDT 或 NWB ElectricalSeries。", "原始质控", "可以"),
            ("已有 Kilosort/Phy sorting", "含 spike_times 和 cluster 分配的 Kilosort/Phy 输出目录。", "Unit 质控", "仅在项目另有原始电压时可重新 sorting"),
            ("已有 NeuroExplorer NEX5 sorting", "一个 .nex5 文件或包含多个 .nex5 文件的文件夹；可用文件名过滤同一动物。", "Unit 质控与 sorter 对比", "仅在项目另有原始电压时可重新 sorting"),
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
    nex5_section = (
        """
<section data-searchable>
  <h2>Attach NEX5 offline sorting to an existing project</h2>
  <ol class="steps">
    <li>Open the project that contains the raw voltage. From Home, choose “Import my data,” then “Existing NeuroExplorer NEX5 sorting.”</li>
    <li>Select one <code>.nex5</code> file or a folder searched recursively. Use the filename filter to select one subject, session, or batch, such as <code>SW#1</code>.</li>
    <li>Enter a unique result key. This keeps several external results side by side without overwriting an existing result.</li>
    <li>Select time alignment. End alignment is available for a full recording; preserve timestamps when both sources already share one clock; enter a manual offset for a segment.</li>
    <li>Review the preview for file count, Neuron variables, waveform variables, time range, and sampling rate before attaching the result.</li>
    <li>Open Spike sorting and select the new read-only result. Continue to Unit QC for waveform, refractory, stability, and duplicate review.</li>
  </ol>
  <table class="parameter-table"><thead><tr><th>Control</th><th>Purpose</th><th>Default</th><th>When to change it</th></tr></thead>
  <tbody>
    <tr><td><b>Filename filter</b></td><td>Reads only NEX5 files whose path contains the supplied text.</td><td>Empty; read all</td><td>Required when one folder contains several subjects or sessions.</td></tr>
    <tr><td><b>Result key</b></td><td>Unique sorter/result identifier stored in the project.</td><td>offline_sorter_nex5</td><td>Use a descriptive unique key when comparing several external results.</td></tr>
    <tr><td><b>Automatic end alignment</b></td><td>Estimates clock offset from the NEX5 and raw-recording end times.</td><td>Preferred for a full recording</td><td>Use only for the same complete recording. The program rejects this inference for a clipped segment.</td></tr>
    <tr><td><b>Preserve timestamps</b></td><td>Leaves NEX5 timestamps unchanged.</td><td>Off</td><td>Use when both results already use the same clock.</td></tr>
    <tr><td><b>Manual offset</b></td><td>Subtracts the specified seconds from every NEX5 spike, then clips to the project range.</td><td>0 s</td><td>Use for a 30-minute segment, a known acquisition-start difference, or a sync-derived offset.</td></tr>
  </tbody></table>
  <div class="callout warning">Candidate counts and agreement metrics are not ground truth. Import keeps source files read-only and preserves original names, source groups, waveform summaries, and alignment evidence. Manual decisions are stored as separate project audit records.</div>
</section>
"""
        if english
        else """
<section data-searchable>
  <h2>把 NEX5 离线 sorting 接入已有项目</h2>
  <ol class="steps">
    <li>先打开含原始电压的项目；在首页选择“导入自己的数据”，再选择“已有 NeuroExplorer NEX5 sorting”。</li>
    <li>选择单个 <code>.nex5</code> 文件，或选择递归包含多个 NEX5 文件的文件夹。文件名过滤框用于限定动物、session 或记录批次，例如 <code>SW#1</code>。</li>
    <li>填写结果键。结果键用于区分多个来源，例如 <code>offline_sorter_nex5_sw1</code>；已有结果不会被覆盖。</li>
    <li>选择时间对齐。完整记录可使用“结束时间自动对齐”；NEX5 已经使用项目时钟时选择“保留原始时间”；短片段或截取项目必须填写人工偏移秒数。</li>
    <li>查看识别预览，核对文件数、Neuron 变量数、波形变量数、时间范围和采样率后再创建或接入项目。</li>
    <li>进入“Spike sorting”页选择新增的只读结果。页面会显示来源文件、候选 Unit 数和 spike 数；随后进入“Unit 质控”逐个复核。</li>
  </ol>
  <table class="parameter-table"><thead><tr><th>控件</th><th>作用</th><th>默认值</th><th>需要调整的情况</th></tr></thead>
  <tbody>
    <tr><td><b>文件名过滤</b></td><td>只读取路径中名称含指定文字的 NEX5 文件。</td><td>空，读取全部</td><td>一个目录含多只动物或多个 session 时必须填写。</td></tr>
    <tr><td><b>结果键</b></td><td>保存到项目中的唯一 sorter/result 标识。</td><td>offline_sorter_nex5</td><td>要同时比较多个外部结果时改成有含义的唯一名称。</td></tr>
    <tr><td><b>自动结束对齐</b></td><td>用 NEX5 结束时间减去原始记录结束时间估计时钟偏移。</td><td>完整记录入口的首选</td><td>只适用于同一次完整记录。程序会拒绝对截取片段自动推断。</td></tr>
    <tr><td><b>保留原始时间</b></td><td>不改变 NEX5 中的秒时间戳。</td><td>关闭</td><td>两个结果已经使用同一时钟时使用。</td></tr>
    <tr><td><b>人工偏移</b></td><td>从每个 NEX5 spike 时间中减去指定秒数，再裁剪到项目范围。</td><td>0 s</td><td>分析 30 分钟片段、已知记录起点差或通过同步脉冲估计出偏移时使用。</td></tr>
  </tbody></table>
  <div class="callout warning">候选 Unit 数和匹配一致度没有 ground truth 含义。导入过程保持源文件只读，保留原名称、来源分组、波形摘要和时间对齐证据；人工复核结果另存为项目内的审计记录。</div>
</section>
"""
    ).strip()
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
{nex5_section}
<section data-searchable>
  <h2>{'Behavior CSV example' if english else '行为 CSV 示例结构'}</h2>
  <pre><code>trial,time_seconds,event_type,condition,choice,reaction_time
1,12.450,stimulus_onset,A,left,0.620
1,13.070,response,A,left,0.620</code></pre>
  <p>{'A separate TTL CSV may contain ephys-clock pulse times. NeuroEphys AI pairs the pulse sequence and reports offset, drift, residuals, and missing events.' if english else '另一个 TTL CSV 可提供电生理时钟中的脉冲时间。NeuroEphys AI 会匹配脉冲序列，并报告起始偏移、漂移、残差和缺失事件。'}</p>
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
    comparison_details = (
        """
  <h3>Attach read-only external results</h3>
  <p>Kilosort/Phy and NeuroExplorer NEX5 results can be attached to a raw-data project. The importer preserves external unit names, source files, timestamps in seconds, waveform summaries, and source labels, then assigns stable internal unit IDs. Imported entries appear in the sorter list with a read-only badge. Running that entry does not create a substitute result; select an executable sorter to recompute the data.</p>
  <h3>How to read the comparison</h3>
  <table><thead><tr><th>Metric</th><th>Meaning</th><th>Limitation</th></tr></thead>
  <tbody><tr><td><b>Precision</b></td><td>Fraction of tested-unit spikes paired one-to-one with the reference unit inside the tolerance.</td><td>A high-rate or contaminated cluster lowers this value.</td></tr><tr><td><b>Recall</b></td><td>Fraction of reference-unit spikes recovered by the tested unit.</td><td>A large merged cluster can have high recall and very low precision.</td></tr><tr><td><b>F1</b></td><td>Harmonic mean of precision and recall.</td><td>Measures timestamp agreement only.</td></tr><tr><td><b>Estimated lag</b></td><td>Fixed clock offset estimated inside a bounded lag search.</td><td>Does not replace sync pulses or a full clock audit.</td></tr><tr><td><b>Chance-corrected agreement</b></td><td>Coincidence after subtracting the expectation from both firing rates.</td><td>Waveform, channel, ISI, and stability evidence remain necessary.</td></tr></tbody></table>
  <h3>Manual review</h3>
  <p>After sorting, open Unit QC. Review each candidate's mean waveform, channel profile, ACG and refractory evidence, amplitude distribution, recording stability, native sorter diagnostics, and cross-unit timestamp overlap. The reviewer can assign Candidate single unit, Multi-unit activity, Noise, Artifact, or Uncertain, with confidence, checklist, and notes. Every candidate and decision remains in the audit trail; automatic thresholds do not silently delete units.</p>
"""
        if english
        else """
  <h3>接入只读外部结果</h3>
  <p>Kilosort/Phy 和 NeuroExplorer NEX5 结果可附加到已有原始数据项目。程序保留外部 Unit 名称、原始文件、秒时间、波形摘要和来源标签，再生成内部连续 Unit ID。导入条目会出现在 sorter 列表中并标记为“只读结果”；点击运行不会伪造新的 sorting，用户可切换到可执行 sorter 后重新计算。</p>
  <h3>比较指标怎么读</h3>
  <table><thead><tr><th>指标</th><th>含义</th><th>使用限制</th></tr></thead>
  <tbody><tr><td><b>Precision</b></td><td>测试 Unit 的 spike 中有多少能在容差窗口内与参考 Unit 一一匹配。</td><td>高放电率或污染 cluster 会降低该值。</td></tr><tr><td><b>Recall</b></td><td>参考 Unit 的 spike 中有多少被测试 Unit 找到。</td><td>一个大 cluster 可具有很高 recall，同时 precision 很低。</td></tr><tr><td><b>F1</b></td><td>Precision 与 recall 的调和平均。</td><td>只评价时间戳一致度。</td></tr><tr><td><b>Estimated lag</b></td><td>在受限时间窗内估计两份结果的固定时钟偏移。</td><td>不能替代同步脉冲或完整时钟审计。</td></tr><tr><td><b>Chance-corrected agreement</b></td><td>扣除由两列放电率预期产生的随机重合。</td><td>仍然需要波形、通道、ISI 和稳定性证据。</td></tr></tbody></table>
  <h3>人工复核</h3>
  <p>排序结束后进入“Unit 质控”。每个候选 Unit 依次查看平均波形、通道轮廓、ACG 与不应期、振幅分布、记录稳定性、sorter 原生诊断和跨 Unit 时间戳重合。审核者可标记“候选单 Unit”“Multi-unit activity”“噪声”“伪迹”或“待定”，填写置信度、检查清单和备注。程序保留全部候选与审核轨迹，不会因自动阈值静默删除 Unit。</p>
"""
    ).strip()
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
  <img class="product-shot" src="../assets/neuroflow-sorting.png" alt="NeuroEphys AI sorting workbench">
</section>
<section data-searchable>
  <h2>{'Kilosort4 settings exposed by NeuroEphys AI' if english else 'NeuroEphys AI 中的 Kilosort4 参数'}</h2>
  <table class="parameter-table"><thead><tr><th>{'Parameter' if english else '参数'}</th><th>{'Meaning' if english else '含义'}</th><th>{'Default' if english else '默认值'}</th><th>{'Recommendation' if english else '推荐设置'}</th><th>{'Consequence' if english else '改变后的影响'}</th></tr></thead>
  <tbody>{''.join(f"<tr><td><code>{e(row['name'])}</code></td><td>{e(row['meaning'])}</td><td>{e(row['default'])}</td><td>{e(row['recommended'])}</td><td>{e(row['effect'])}</td></tr>" for row in ks_params)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Unified results and comparison' if english else '统一结果与比较'}</h2>
  <p>{'Every backend keeps its native folder. NeuroEphys AI additionally records unit IDs, spike times in seconds, sampling rate, versions, parameters, logs, and optional channel/template fields in a common downstream schema. Sorter comparison reports matched, split, merged, unique, and consensus units. On real data this is agreement, not accuracy.' if english else '每个后端保留原生目录。NeuroEphys AI 额外把 unit ID、秒级 spike times、采样率、版本、参数、日志和可用通道/模板字段写入统一下游结构。sorter 比较报告匹配、拆分、合并、独有和共识 unit；真实数据上这叫一致度，不叫准确率。'}</p>
  {comparison_details}
</section>
"""
    return _layout(language, "sorting.html", title, lead, body)


def build_parameters(language: str) -> str:
    english = language == "en_US"
    title = "Parameter reference" if english else "参数参考"
    lead = (
        "Defaults are starting points, not universal truth. Change one setting at a time, preserve the reason, and compare evidence before and after."
        if english
        else "默认值仅作为起点。每次只改一个参数，记录原因，并比较修改前后的证据。"
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
  <img class="product-shot" src="../assets/neuroflow-figure-studio.png" alt="NeuroEphys AI Figure Studio">
</section>
"""
    return _layout(language, "figure-studio.html", title, lead, body)


def build_unit_curation(language: str) -> str:
    english = language == "en_US"
    title = "Manual unit curation" if english else "Unit 人工复核"
    lead = (
        "Every sorter produces candidate clusters. Manual review records the evidence "
        "used to retain, reject, or defer each candidate without erasing the native sorter output."
        if english
        else "每个sorter输出的cluster均先视为候选。人工复核记录保留、排除或暂缓决定所依据的证据，同时保留sorter原始输出。"
    )
    labels = (
        [
            ("Candidate single unit", "Waveform, refractory period, stability, and isolation support single-unit use; final scientific inclusion still follows the study protocol."),
            ("Multi-unit activity", "Biological spiking is present, while separation from nearby units remains insufficient."),
            ("Noise", "The cluster is dominated by artifacts, electrical noise, or invalid waveform structure."),
            ("Uncertain", "Evidence is incomplete or conflicting. The unit remains available for later review."),
        ]
        if english
        else [
            ("候选单神经元", "波形、不应期、稳定性与隔离证据支持单神经元使用；最终纳入仍应遵循研究方案。"),
            ("多单元活动", "存在生物放电，但与邻近神经元的分离证据不足。"),
            ("噪声", "cluster主要由伪迹、电噪声或无效波形结构构成。"),
            ("不确定", "证据不完整或相互冲突，保留该unit供后续继续检查。"),
        ]
    )
    checks = (
        [
            "Open Unit QC after activating the sorter result that will be reviewed.",
            "Select a unit. Inspect waveform, autocorrelogram, ISI violations, firing rate, SNR, amplitude over time, and available sorter diagnostics.",
            "Check waveform consistency across time and channels. Abrupt discontinuity or implausible shape requires closer review.",
            "Check the refractory-period evidence. A single threshold never settles identity by itself.",
            "Inspect amplitude and firing-rate stability across the whole recording; short fragments can hide drift or recording loss.",
            "Compare nearby or highly similar clusters for possible duplication, split, or merge errors.",
            "Choose a label, complete the evidence checklist, write an expert note, and save the decision.",
            "Repeat for every retained candidate. Export the decision table with reviewer, timestamp, metric snapshot, sorter, and source run.",
        ]
        if english
        else [
            "激活需要复核的sorter结果，然后进入“Unit质控”。",
            "选择一个unit，查看波形、自相关图、ISI违例、放电率、SNR、振幅随时间变化和可用的sorter诊断。",
            "检查波形在时间和通道上的一致性；突变、截断或不合理形状需要进一步核查。",
            "检查不应期证据；单一阈值无法独立决定unit身份。",
            "查看整段记录的振幅和放电率稳定性；短片段可能掩盖漂移或记录中断。",
            "比较邻近或高度相似cluster，检查重复、错误拆分和错误合并。",
            "选择标签，完成证据清单，填写专家备注并保存。",
            "逐个复核需要保留的候选；导出包含复核人、时间、指标快照、sorter和来源run的决定表。",
        ]
    )
    body = f"""
<section data-searchable>
  <h2>{'Why curation remains necessary' if english else '为什么需要人工复核'}</h2>
  <p>{'Kilosort4, MountainSort5, SpyKING CIRCUS 2, and other sorters use different detection and clustering strategies. Their unit counts can differ, and agreement measures reproducibility rather than biological truth. Curation applies an explicit laboratory decision rule to the evidence.' if english else 'Kilosort4、MountainSort5、SpyKING CIRCUS 2等工具采用不同检测与聚类策略，候选unit数量可能不同。算法一致度反映可复现性，无法直接等同于生物学真值；人工复核负责按实验室规则审查证据。'}</p>
</section>
<section data-searchable>
  <h2>{'Review procedure' if english else '复核步骤'}</h2>
  <ol class="steps">{''.join(f'<li>{e(item)}</li>' for item in checks)}</ol>
  <img class="product-shot" src="../assets/neuroephys-ai-unit-curation.png" alt="NeuroEphys AI manual unit curation workspace">
</section>
<section data-searchable>
  <h2>{'Available labels' if english else '可选标签'}</h2>
  <table><thead><tr><th>{'Label' if english else '标签'}</th><th>{'Use' if english else '使用条件'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><b>{e(name)}</b></td><td>{e(text)}</td></tr>' for name,text in labels)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Sorter-specific and shared evidence' if english else '通用证据与工具特有证据'}</h2>
  <p>{'The checklist and labels are sorter-independent. Native diagnostics remain attached to each result: Kilosort templates, amplitudes, depth-time plots, drift and contamination fields stay available; other sorters retain their own native files. Advanced split/merge work can continue in Phy or another dedicated curator and return through the sorting-result adapter.' if english else '标签与证据清单对sorter通用。每个结果仍保留原生诊断：Kilosort模板、振幅、深度-时间图、漂移和污染字段持续可见；其他sorter保留各自原生文件。复杂的拆分/合并可以在Phy等专用工具中完成，再通过sorting结果适配器导回。'}</p>
  <ul class="source-list">
    <li><a href="https://kilosort.readthedocs.io/en/stable/README.html">Kilosort4: manual curation with Phy</a></li>
    <li><a href="https://spikeinterface.readthedocs.io/en/stable/modules/metrics/quality_metrics.html">SpikeInterface quality metrics</a></li>
    <li><a href="https://phy.readthedocs.io/en/latest/quickstart/">Phy manual clustering guide</a></li>
  </ul>
</section>
"""
    return _layout(language, "unit-curation.html", title, lead, body)


def build_provenance(language: str) -> str:
    english = language == "en_US"
    title = "Intermediate artifacts and provenance" if english else "中间产物与溯源"
    lead = (
        "Each completed stage produces readable tables, figures, structured audit records, "
        "and machine-verifiable artifact links. These records also form the evidence available to AI."
        if english
        else "每个完成阶段都会生成可读表格、图、结构化审计记录和可校验的产物链接；这些记录同时构成AI能够使用的项目证据。"
    )
    rows = (
        [
            ("structured_runs.jsonl", "One record per run: stage, input, selected channels, segment, tool/version, parameters, start/end, status, warnings, error, recovery, and outputs."),
            ("artifact_manifest.json", "One record per artifact: ID, stage, source run, relative path, type, size, checksum, parameters, and input references."),
            ("workflow.json", "Current workflow nodes, state, selected tools, and saved parameters."),
            ("provenance.json", "Environment, project metadata, analysis settings, results summary, warnings, and output relationships."),
            ("CSV tables", "Unit metrics, event/trial tables, statistics, decoding, sorter comparisons, and plotted data."),
            ("PNG/SVG figures", "Review image plus editable vector output, linked to the same stage and parameters."),
            ("native sorter folders", "Unmodified sorter-native arrays, logs, templates, and diagnostics."),
        ]
        if english
        else [
            ("structured_runs.jsonl", "每次运行一条记录：阶段、输入、通道、片段、工具/版本、参数、起止时间、状态、警告、错误、恢复方式和输出。"),
            ("artifact_manifest.json", "每个产物一条记录：ID、阶段、来源run、相对路径、类型、大小、校验值、参数和输入引用。"),
            ("workflow.json", "当前工作流节点、状态、所选工具和已保存参数。"),
            ("provenance.json", "环境、项目元数据、分析设置、结果摘要、警告和输出关系。"),
            ("CSV表格", "Unit指标、事件/trial、统计、解码、sorter比较和绘图数据。"),
            ("PNG/SVG图", "用于快速检查的位图和可编辑矢量图，共享同一阶段与参数来源。"),
            ("sorter原生目录", "原样保留sorter数组、日志、模板和诊断文件。"),
        ]
    )
    body = f"""
<section data-searchable>
  <h2>{'Project evidence layers' if english else '项目证据层'}</h2>
  <table><thead><tr><th>{'Output' if english else '输出'}</th><th>{'Recorded content' if english else '记录内容'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><code>{e(name)}</code></td><td>{e(text)}</td></tr>' for name,text in rows)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'How AI uses intermediate data' if english else 'AI如何使用中间数据'}</h2>
  <ol class="steps">
    <li>{'Local analysis writes the scientific result and provenance first.' if english else '本地分析先写入科学结果与来源记录。'}</li>
    <li>{'The context builder selects compact fields such as metrics, status, warnings, parameters, and artifact IDs.' if english else '上下文构造器选取指标、状态、警告、参数和artifact ID等紧凑字段。'}</li>
    <li>{'Paths, identities, raw arrays, and large binary content are removed.' if english else '路径、身份信息、原始数组和大型二进制内容会被移除。'}</li>
    <li>{'The user reviews the exact online payload and can remove optional fields.' if english else '用户查看在线请求的完整内容，并可删除可选字段。'}</li>
    <li>{'An AI answer cites the run and artifact evidence available in the project.' if english else 'AI回答引用项目中已有的run和artifact证据。'}</li>
  </ol>
</section>
<section data-searchable>
  <h2>{'Recovery rule' if english else '恢复规则'}</h2>
  <p>{'Project files store links to every completed stage. Reopening restores the active page, source links, channel selection, sorter results, curation decisions, behavior mapping, statistics, figures, AI conversation, approved workflow, and audit history. Missing linked source data disables only the stages that need that source.' if english else '项目文件保存每个完成阶段的链接。重新打开后恢复当前页面、数据源、通道选择、sorter结果、人工决定、行为映射、统计、图表、AI对话、已批准工作流和审计历史。若外部数据源失效，只有依赖该数据源的阶段会被禁用。'}</p>
</section>
"""
    return _layout(language, "provenance.html", title, lead, body)


def build_real_data_validation(language: str) -> str:
    english = language == "en_US"
    title = "Real-data validation" if english else "真实数据验证"
    lead = (
        "A locally supplied 32-contact microwire recording was used to verify direct "
        "Open Ephys import, full-duration sorting recovery, behavior synchronization, "
        "downstream analysis, export, and project reload. The source data are not distributed."
        if english
        else "一批本地提供的32-contact微丝记录用于验证Open Ephys直接导入、全时长sorting恢复、行为同步、下游分析、导出和项目重载；原始数据不随软件分发。"
    )
    rows = (
        [
            ("Recording", "32 independent microwires, 30 kHz, 7,497.489 s, externally referenced during acquisition."),
            ("Acquisition preprocessing", "250–8,000 Hz online filtering. LFP, low-frequency spectra, and spike-field coupling are blocked."),
            ("Raw QC", "99.21875/100. No channels were removed from the configured 1–32 selection."),
            ("Kilosort4", "Version 4.1.7, nblocks=0, thresholds 9/8, 12 candidate units, 2,195,626 spikes. Internal runtime 1,870.35 s; wrapper runtime 2,096.54 s."),
            ("External offline sorting", "The official nex5file package read eight NEX5 candidate units from the same recording. Source files remained read-only; names, groups, waveform summaries, and alignment evidence were retained."),
            ("Behavior and synchronization", "4,654 MED-PC events; 744/744 synchronization anchors matched. Action-start analysis used event codes 17 and 19, 168 events total."),
            ("Statistics and decoding", "Outputs were generated as technical validation. The decoding result must not be interpreted as a biological claim."),
            ("Project recovery", "Saved project was reloaded, existing Kilosort and NEX5 arrays were reused, downstream outputs and artifact indexes were regenerated."),
            ("Manual review status", "Both result sets remain candidates until waveform, refractory, stability, duplication, and sorter evidence have been reviewed."),
        ]
        if english
        else [
            ("记录", "32根独立微丝，30 kHz，7,497.489秒；采集时使用外部参考。"),
            ("采集端处理", "在线250–8,000 Hz滤波；程序阻止LFP、低频频谱和spike-field coupling。"),
            ("原始质控", "99.21875/100；配置的1–32通道没有被自动剔除。"),
            ("Kilosort4", "版本4.1.7，nblocks=0，阈值9/8，12个候选unit，2,195,626个spike；内部用时1,870.35秒，含适配器总用时2,096.54秒。"),
            ("外部离线 sorting", "使用官方 nex5file 读取同一记录的8个 NEX5 候选 Unit；原始文件只读，名称、分组、波形摘要与时间对齐证据均保留。"),
            ("行为与同步", "MED-PC事件4,654条；744/744个同步锚点匹配。动作起始分析使用事件码17和19，共168个事件。"),
            ("统计与解码", "已生成技术验证输出；解码结果不得直接用于生物学结论。"),
            ("项目恢复", "保存后重新加载，复用已有Kilosort和 NEX5 数组，重新生成下游结果和产物索引。"),
            ("人工复核状态", "两份结果均保持候选状态，等待波形、不应期、稳定性、重复性和sorter证据的逐个检查。"),
        ]
    )
    body = f"""
<section data-searchable>
  <h2>{'Verified chain' if english else '已验证链路'}</h2>
  <table><thead><tr><th>{'Stage' if english else '阶段'}</th><th>{'Result' if english else '验证结果'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><b>{e(name)}</b></td><td>{e(text)}</td></tr>' for name,text in rows)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Sorter sensitivity and comparison' if english else 'Sorter敏感性与比较'}</h2>
  <p>{'The full Kilosort4 result contains 12 candidate units and the external NEX5 result contains eight. A bounded lag search and one-to-one timestamp matching found one strong pair. Several external units had high recall and low precision against one high-rate Kilosort cluster, which is compatible with merging, contamination, or different unit definitions. On the 30-minute segment, Kilosort4 produced four candidates while the clipped NEX5 result retained eight, again with one strong pair. Candidate counts and agreement prioritize manual review; they do not establish the neuron count.' if english else '整段 Kilosort4 结果含12个候选 Unit，外部 NEX5 结果含8个候选 Unit。经固定 lag 搜索和一对一时间戳匹配，只有1对达到强一致；部分外部 Unit 对一个高放电率 Kilosort cluster 具有高 recall、低 precision，提示合并、污染或单位定义差异。30分钟片段中，Kilosort4 含4个候选，裁剪后的 NEX5 仍含8个候选，其中1对达到强一致。候选数量和一致度均用于安排人工复核，不能直接确定真实神经元数量。'}</p>
  <p>{'The cross-unit duplicate screen also flagged several high-overlap pairs, including one above 80%. The program records the risk and keeps every unit. Final decisions require waveform, peak channel, ACG, refractory, amplitude-stability, and native-sorter evidence.' if english else '跨 Unit 重复筛查还发现若干时间戳高重合对，其中最高重合超过80%。程序只标记风险并保留原 Unit；最终判定需要同时查看波形、主通道、ACG、不应期、振幅稳定性和原 sorter 界面。'}</p>
</section>
<section data-searchable>
  <h2>{'Scientific limits' if english else '科学限制'}</h2>
  <ul class="checks">
    <li>{'The external NEX5 files contain eight candidate units. Their selection method and manual decisions have not been fully audited, so they cannot serve as ground truth.' if english else '外部 NEX5 确认保存了8个候选 Unit；其筛选方法和人工判断仍未完整审计，不能作为ground truth。'}</li>
    <li>{'The SW#1-to-subject mapping is a high-confidence inference from file order and owner notes, pending final owner confirmation.' if english else 'SW#1 与该动物的对应关系来自文件顺序和提供者说明，当前作为高可信推断保存，仍等待数据拥有者最终确认。'}</li>
    <li>{'Online high-pass filtering prevents recovery of true low-frequency activity.' if english else '在线高通滤波使真实低频活动无法恢复。'}</li>
    <li>{'Event codes 21 and 22 were coincident in this recording; codes 17 and 19 supplied the distinct action-start comparison.' if english else '该记录中事件码21和22时间完全重合；条件比较改用具有独立时间的17和19动作起始事件。'}</li>
    <li>{'Single-session decoding can reflect session structure and requires independent replication.' if english else '单session解码可能反映session结构，需要独立数据验证。'}</li>
  </ul>
</section>
"""
    return _layout(language, "real-data-validation.html", title, lead, body)


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
            ("A run shows another sorter's result", "The selected result was not activated or the run failed.", "Check active sorter, run log, native output folder, and result timestamp. NeuroEphys AI must show pending/failed rather than substitute."),
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
  <ul>{''.join(f'<li>{e(item)}</li>' for item in (["NeuroEphys AI version and operating system", "Project manifest with private paths redacted", "Current stage, selection, and parameters", "Exact first error line and audit-log tail", "Sorter name, backend version, GPU/CPU status", "Whether the issue reproduces on a teaching simulation"] if english else ["NeuroEphys AI 版本和操作系统", "隐去敏感路径后的项目清单", "当前阶段、具体选项和参数", "第一行真实错误与审计日志末尾", "sorter 名称、后端版本和 GPU/CPU 状态", "教学模拟项目能否复现"]))}</ul>
</section>
"""
    return _layout(language, "troubleshooting.html", title, lead, body)


def build_sources(language: str) -> str:
    english = language == "en_US"
    title = "Methods and sources" if english else "方法与来源"
    lead = (
        "NeuroEphys AI reuses established open-source computation and writes original interface, interoperability, tutorial, and audit layers. The summaries below are original paraphrases, not copied documentation."
        if english
        else "NeuroEphys AI 复用成熟开源计算能力，自主编写界面、兼容、教程和审计层。以下内容为原创概括，不复制原文。"
    )
    sources = [
        ("Kilosort4 documentation", "https://kilosort.readthedocs.io/en/latest/", "Documentation organization, GUI operating order, parameters, exported files, drift checks, sample-data tutorial."),
        ("Kilosort4 GUI guide", "https://kilosort.readthedocs.io/en/latest/gui_guide.html", "Data/probe selection, input preview, channel-count checks, run sequence."),
        ("Kilosort4 parameter guide", "https://kilosort.readthedocs.io/en/latest/parameters.html", "n_chan_bin, batch_size, nblocks, thresholds, time range, geometry, and duplicate-spike cautions."),
        ("SpikeInterface", "https://spikeinterface.readthedocs.io/en/stable/", "Extractors, preprocessing, sorter wrappers, postprocessing, quality metrics, and comparison interfaces."),
        ("SpikeInterface sorters", "https://spikeinterface.readthedocs.io/en/stable/modules/sorters.html", "Common sorter wrappers, native dependencies, and container execution."),
        ("SpikeInterface quality metrics", "https://spikeinterface.readthedocs.io/en/stable/modules/metrics/quality_metrics.html", "Definitions and implementation references for firing, refractory, amplitude, drift, and isolation-oriented metrics."),
        ("Elephant", "https://elephant.readthedocs.io/en/stable/modules.html", "Spike-train statistics, spectral analysis, correlation, phase, and signal-analysis APIs on Neo objects."),
        ("Neo", "https://neo.readthedocs.io/en/stable/read_and_analyze.html", "Unit-aware SpikeTrain, AnalogSignal, Event, Epoch, Segment, and Block objects."),
        ("Phy", "https://phy.readthedocs.io/en/latest/quickstart/", "Manual review of spike-sorting output."),
        ("NeuroExplorer nex5file", "https://neuroexplorer.com/docs/python_packages/nex5file.html", "Read-only parsing of .nex5 Neuron, Waveform, sampling-rate, and timestamp fields through the MIT-licensed public Python API. MATLAB readers and third-party interfaces were not copied."),
        ("MountainSort5", "https://pypi.org/project/mountainsort5/", "CPU-oriented sorting schemes and package interface."),
        ("Respiration/PFC study", "https://pmc.ncbi.nlm.nih.gov/articles/PMC10312056/", "Method structure for behavioral-state, respiration, spike, LFP, phase, and surrogate analyses."),
        ("GraphPad Prism graph controls", "https://www.graphpad.com/guides/prism/latest/user-guide/how_to_change_a_graph.htm", "Interaction expectations for editable graph objects, axes, grids, ticks, and exact size."),
        ("IBL Brain-Wide Map", "https://www.internationalbrainlab.com/brainwidemap", "Public neural and behavioral validation context."),
        ("DANDI Archive", "https://docs.dandiarchive.org/introduction/", "Versioned NWB public-data access and provenance."),
        ("DeepSeek chat completion API", "https://api-docs.deepseek.com/api/create-chat-completion", "Provider endpoint, streaming response, usage fields, and request structure."),
        ("DeepSeek function calling", "https://api-docs.deepseek.com/guides/function_calling/", "Structured function definitions and model-generated argument requests."),
        ("DeepSeek tool calls", "https://api-docs.deepseek.com/guides/tool_calls", "Tool-call response handling and multi-turn tool result flow."),
        ("OpenAI Responses API", "https://developers.openai.com/api/docs/guides/text", "Optional provider adapter and structured text generation."),
    ]
    body = f"""
<section data-searchable>
  <h2>{'Attribution table' if english else '来源与借鉴范围'}</h2>
  <table><thead><tr><th>{'Source' if english else '来源'}</th><th>{'How NeuroEphys AI uses it' if english else 'NeuroEphys AI 借鉴或调用的范围'}</th></tr></thead>
  <tbody>{''.join(f'<tr><td><a href="{e(url)}">{e(name)}</a></td><td>{e(scope if english else {"Documentation organization, GUI operating order, parameters, exported files, drift checks, sample-data tutorial.":"文档层级、GUI 操作顺序、参数、导出文件、漂移检查和示例教程结构。","Data/probe selection, input preview, channel-count checks, run sequence.":"数据/探针选择、输入预览、通道数检查和运行顺序。","n_chan_bin, batch_size, nblocks, thresholds, time range, geometry, and duplicate-spike cautions.":"n_chan_bin、batch_size、nblocks、阈值、时间范围、几何和重复 spike 注意事项。","Extractors, preprocessing, sorter wrappers, postprocessing, quality metrics, and comparison interfaces.":"数据读取、预处理、sorter 适配、后处理、质量指标和比较接口。","Common sorter wrappers, native dependencies, and container execution.":"统一sorter wrapper、原生依赖和容器执行机制。","Definitions and implementation references for firing, refractory, amplitude, drift, and isolation-oriented metrics.":"放电、不应期、振幅、漂移和隔离相关指标的定义与实现依据。","Spike-train statistics, spectral analysis, correlation, phase, and signal-analysis APIs on Neo objects.":"基于Neo对象的spike train统计、频谱、相关、相位和信号分析API。","Unit-aware SpikeTrain, AnalogSignal, Event, Epoch, Segment, and Block objects.":"带单位的SpikeTrain、AnalogSignal、Event、Epoch、Segment和Block对象。","Manual review of spike-sorting output.":"spike sorting输出的人工复核工作流。","Read-only parsing of .nex5 Neuron, Waveform, sampling-rate, and timestamp fields through the MIT-licensed public Python API. MATLAB readers and third-party interfaces were not copied.":"使用MIT许可Python包的公开API只读解析.nex5中的Neuron、Waveform、采样率和时间戳；未复制MATLAB读取器或第三方界面。","CPU-oriented sorting schemes and package interface.":"面向CPU的sorting scheme和包接口。","Method structure for behavioral-state, respiration, spike, LFP, phase, and surrogate analyses.":"行为状态、呼吸、spike、LFP、相位和surrogate分析的方法结构。","Interaction expectations for editable graph objects, axes, grids, ticks, and exact size.":"图元、坐标轴、网格、刻度和精确尺寸的可编辑交互预期。","Public neural and behavioral validation context.":"公开神经与行为数据的验证背景。","Versioned NWB public-data access and provenance.":"版本化NWB公开数据访问与来源记录。","Provider endpoint, streaming response, usage fields, and request structure.":"模型服务地址、流式返回、用量字段和请求结构。","Structured function definitions and model-generated argument requests.":"结构化函数定义和模型参数请求。","Tool-call response handling and multi-turn tool result flow.":"工具调用返回处理和多轮工具结果流程。","Optional provider adapter and structured text generation.":"可选模型适配器和结构化文本生成。"}[scope])}</td></tr>' for name,url,scope in sources)}</tbody></table>
</section>
<section data-searchable>
  <h2>{'Non-copying rule' if english else '不直接抄袭原则'}</h2>
  <div class="callout warning">{'NeuroEphys AI does not reproduce another product’s prose, screenshots, figures, numerical conclusions, or visual identity. It uses official method definitions and documentation patterns as references, then writes original product text, workflows, adapters, and interface behavior.' if english else 'NeuroEphys AI 不复制其他产品的原文、截图、论文图、数值结论或视觉识别；只把官方方法定义和文档组织方式作为参考，再自主编写产品文字、工作流、适配器和界面行为。'}</div>
</section>
<section data-searchable>
  <h2>{'Public source and deployment record' if english else '公开代码与部署记录'}</h2>
  <p>{'Source code, tests, public documentation, and de-identified demonstration assets are mirrored in two public repositories. Authorized workstations retain experimental data, validation projects containing local paths, and large analysis caches.' if english else '程序源代码、测试、公开教程和脱敏演示资源同步保存在两个公开仓库。真实实验数据、含本机路径的验证项目和大体积分析缓存保留在授权计算机中。'}</p>
  <ul>
    <li><a href="https://github.com/CarbonLack/neuroflow-ai">GitHub: CarbonLack/neuroflow-ai</a></li>
    <li><a href="https://gitlab.com/CarbonLack/neuroflow-ai">GitLab: CarbonLack/neuroflow-ai</a></li>
    <li><a href="https://github.com/CarbonLack/neuroflow-ai/blob/main/DEPLOYMENT_STATUS_ZH.md">{'Repository scope, Pages configuration, and deployment incident record' if english else '公开范围、Pages 配置和发布故障记录'}</a></li>
  </ul>
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
    "unit-curation.html": build_unit_curation,
    "ai-assistant.html": build_ai_assistant,
    "parameters.html": build_parameters,
    "figure-studio.html": build_figure_studio,
    "provenance.html": build_provenance,
    "real-data-validation.html": build_real_data_validation,
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
    <title>NeuroEphys AI Documentation</title>
    <link rel="stylesheet" href="styles.css?v=0.8.0">
  </head>
  <body class="language-gateway">
    <main class="gateway-panel">
      <p class="eyebrow">NeuroEphys AI Documentation</p>
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
