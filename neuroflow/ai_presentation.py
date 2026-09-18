from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from typing import Any


_HEADING_PREFIX = re.compile(r"^#{1,6}\s*")
_BULLET_PREFIX = re.compile(r"^(?:[-*•]|\d+[.)])\s*")
_MARKDOWN_EMPHASIS = re.compile(r"[*_`]+")
_SPACE = re.compile(r"[ \t]+")
_SENTENCE = re.compile(r"(?<=[。！？!?])\s*|(?<=[.!?])\s+")
_STAGE_LABELS = {
    "zh_CN": {
        "import": "数据与项目",
        "qc": "原始质控",
        "preprocess": "预处理",
        "sorting": "Spike sorting",
        "unit_qc": "Unit 质控",
        "sync": "事件同步",
        "behavior": "行为分析",
        "analysis": "神经活动分析",
        "statistics": "统计检验",
        "decoding": "机器学习与神经解码",
        "export": "论文与复现",
    },
    "en_US": {
        "import": "Data and project",
        "qc": "Raw QC",
        "preprocess": "Preprocessing",
        "sorting": "Spike sorting",
        "unit_qc": "Unit QC",
        "sync": "Event synchronization",
        "behavior": "Behavior analysis",
        "analysis": "Neural analysis",
        "statistics": "Statistical testing",
        "decoding": "Machine learning and decoding",
        "export": "Publication and reproducibility",
    },
}


@dataclass(frozen=True, slots=True)
class AIReadableView:
    conclusion: str
    highlights: tuple[str, ...]
    activity: str
    next_step: str
    warning: str
    has_details: bool


def _clean_line(value: str) -> str:
    text = _HEADING_PREFIX.sub("", str(value).strip())
    text = _BULLET_PREFIX.sub("", text)
    text = _MARKDOWN_EMPHASIS.sub("", text)
    return _SPACE.sub(" ", text).strip()


def _shorten(value: str, limit: int) -> str:
    text = _SPACE.sub(" ", value.replace("\n", " ")).strip()
    if len(text) <= limit:
        return text
    sentences = [item.strip() for item in _SENTENCE.split(text) if item.strip()]
    selected = ""
    for sentence in sentences:
        candidate = sentence if not selected else f"{selected} {sentence}"
        if len(candidate) > limit:
            break
        selected = candidate
    if selected:
        return selected
    return text[: max(1, limit - 1)].rstrip("，,；;：:。.!！?") + "…"


def _answer_lines(answer: str) -> list[str]:
    return [
        cleaned
        for raw in str(answer).replace("```", "").splitlines()
        if (cleaned := _clean_line(raw))
    ]


def _is_label_only(line: str, english: bool) -> bool:
    normalized = line.strip(" ：:。.!！?").lower()
    labels = (
        {
            "conclusion", "summary", "answer", "result", "key points",
            "why", "what to do now", "important limitation", "next step",
        }
        if english
        else {
            "结论", "摘要", "回答", "结果", "重点", "关键点", "为什么",
            "你现在可以怎么做", "现在怎么做", "需要注意", "下一步",
        }
    )
    return normalized in labels


def build_readable_ai_view(
    answer: str,
    *,
    warnings: list[str] | tuple[str, ...] | None = None,
    suggested_next_stage: str = "",
    tool_calls: list[dict[str, Any]] | None = None,
    query_evidence: list[dict[str, Any]] | None = None,
    language: str = "zh_CN",
) -> AIReadableView:
    """Create a deterministic, low-burden view without discarding the full reply."""
    english = language == "en_US"
    lines = _answer_lines(answer)
    substantive_lines = [line for line in lines if not _is_label_only(line, english)]
    if not substantive_lines:
        conclusion = "No readable answer was returned." if english else "模型没有返回可读的回答。"
    else:
        conclusion = _shorten(substantive_lines[0], 260 if english else 170)

    next_candidates = [
        line
        for line in substantive_lines
        if (
            any(token in line.lower() for token in ("next", "what to do now"))
            if english
            else any(token in line for token in ("下一步", "你现在可以怎么做", "现在怎么做"))
        )
    ]

    priority_tokens = (
        ("next", "recommend", "result", "conclusion", "because", "cannot", "risk")
        if english
        else (
            "下一步", "建议", "结果", "结论", "为什么", "因为", "原因",
            "不能", "风险", "需要", "说明", "意味着",
        )
    )
    highlights: list[str] = []
    for line in substantive_lines[1:]:
        if line == conclusion or len(line) < 4:
            continue
        if line in next_candidates:
            continue
        if any(token in line.lower() for token in priority_tokens):
            highlights.append(_shorten(line, 210 if english else 135))
        if len(highlights) >= 3:
            break
    if not highlights:
        for line in substantive_lines[1:4]:
            if line != conclusion and len(line) >= 4:
                if line in next_candidates:
                    continue
                highlights.append(_shorten(line, 210 if english else 135))

    evidence_count = len(query_evidence or [])
    proposal_count = len(tool_calls or [])
    activity_parts: list[str] = []
    if evidence_count:
        activity_parts.append(
            f"Read {evidence_count} current-project evidence item(s)"
            if english
            else f"已读取当前项目的 {evidence_count} 项证据"
        )
    if proposal_count:
        activity_parts.append(
            f"Proposed {proposal_count} local action(s), awaiting confirmation"
            if english
            else f"提出 {proposal_count} 个本地操作，等待你确认"
        )
    activity = " · ".join(activity_parts)

    next_step = _shorten(next_candidates[0], 180 if english else 120) if next_candidates else ""
    if not next_step and suggested_next_stage:
        stage_label = _STAGE_LABELS.get(language, {}).get(
            suggested_next_stage, suggested_next_stage
        )
        next_step = (
            f"Suggested stage: {stage_label}"
            if english
            else f"建议进入：{stage_label}"
        )

    warning_items = [str(item).strip() for item in (warnings or []) if str(item).strip()]
    warning = _shorten(warning_items[0], 190 if english else 125) if warning_items else ""
    compact_material = "\n".join([conclusion, *highlights, activity, next_step, warning])
    has_details = (
        len(str(answer).strip()) > len(compact_material) + 80
        or len(lines) > len(highlights) + 1
        or len(warning_items) > 1
        or bool(query_evidence)
        or bool(tool_calls)
    )
    return AIReadableView(
        conclusion=conclusion,
        highlights=tuple(highlights[:3]),
        activity=activity,
        next_step=next_step,
        warning=warning,
        has_details=has_details,
    )


def readable_view_html(
    view: AIReadableView,
    *,
    detail_url: str = "",
    language: str = "zh_CN",
) -> str:
    english = language == "en_US"
    parts = [f'<div class="answer-lead">{escape(view.conclusion)}</div>']
    if view.highlights:
        parts.append('<ul class="answer-points">')
        parts.extend(f"<li>{escape(item)}</li>" for item in view.highlights)
        parts.append("</ul>")
    if view.activity:
        label = "Checked" if english else "已检查"
        parts.append(
            f'<div class="activity"><b>{label}</b> · {escape(view.activity)}</div>'
        )
    if view.next_step:
        label = "Next" if english else "下一步"
        parts.append(
            f'<div class="next"><b>{label}</b> · {escape(view.next_step)}</div>'
        )
    if view.warning:
        label = "Attention" if english else "请注意"
        parts.append(
            f'<div class="warning"><b>{label}</b> · {escape(view.warning)}</div>'
        )
    if detail_url and view.has_details:
        label = "View full answer and evidence" if english else "查看完整说明与依据"
        parts.append(f'<div class="detail-link"><a href="{escape(detail_url)}">{label}</a></div>')
    return "".join(parts)


def full_response_html(record: dict[str, Any], language: str = "zh_CN") -> str:
    english = language == "en_US"
    sections: list[str] = []

    def add_section(title: str, values: Any) -> None:
        if not values:
            return
        if isinstance(values, str):
            body = "<p>" + escape(values).replace("\n", "<br>") + "</p>"
        elif isinstance(values, list):
            body = "<ul>" + "".join(
                f"<li>{escape(str(item))}</li>" for item in values if str(item).strip()
            ) + "</ul>"
        else:
            body = f"<pre>{escape(str(values))}</pre>"
        sections.append(f"<h3>{escape(title)}</h3>{body}")

    add_section("Full answer" if english else "完整回答", record.get("answer", ""))
    add_section("Warnings" if english else "警告与限制", record.get("warnings", []))
    interpretation = record.get("scientific_interpretation", {})
    labels = {
        "observed_results": ("Observed results", "已观察到的结果"),
        "statistical_evidence": ("Statistical evidence", "统计证据"),
        "possible_interpretations": ("Possible interpretations", "可能的解释"),
        "unsupported_conclusions": ("Unsupported conclusions", "不能据此推出的结论"),
        "limitations": ("Limitations", "局限"),
        "suggested_validation": ("Suggested validation", "建议验证"),
    }
    if isinstance(interpretation, dict):
        for key, values in interpretation.items():
            label = labels.get(key, (str(key), str(key)))[0 if english else 1]
            add_section(label, values)
    calls = record.get("tool_calls", [])
    if calls:
        call_lines = []
        for call in calls:
            name = str(call.get("name", "local action"))
            reason = str(call.get("reason", "")).strip()
            call_lines.append(f"{name}: {reason}" if reason else name)
        add_section(
            "Proposed actions (not yet run)" if english else "候选操作（尚未运行）",
            call_lines,
        )
    evidence = record.get("query_evidence", [])
    if evidence:
        add_section(
            "Project evidence read" if english else "本次读取的项目证据",
            [
                str(item.get("evidence_id") or item.get("section") or item.get("query") or item)
                for item in evidence
            ],
        )
    return (
        "<style>body{font-family:'Segoe UI';line-height:1.55;color:#f6f2fa;}"
        "h3{color:#d58be8;margin-top:18px;}li{margin:5px 0;}"
        "pre{white-space:pre-wrap;}</style>" + "".join(sections)
    )
