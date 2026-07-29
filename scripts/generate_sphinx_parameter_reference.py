from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from neuroflow.tutorial_details import TUTORIAL_DETAILS  # noqa: E402
from neuroflow.tutorials import TUTORIALS  # noqa: E402


def _value(mapping: dict, key: str, language: str, default: str = "") -> str:
    if language == "en":
        return str(mapping.get(f"{key}_en", mapping.get(key, default)))
    return str(mapping.get(key, default))


def _clean(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text.replace("`", "``")


def _display_width(value: str) -> int:
    return sum(2 if "\u2e80" <= character <= "\uffff" else 1 for character in value)


def _heading(title: str, marker: str) -> list[str]:
    return [title, marker * _display_width(title), ""]


def _bullet_lines(values: list[str]) -> list[str]:
    lines: list[str] = []
    for value in values:
        lines.append(f"* {_clean(value)}")
    return lines + [""]


def build(language: str) -> str:
    english = language == "en"
    title = (
        "Detailed controls and parameter reference"
        if english
        else "逐项操作与参数参考"
    )
    lines = _heading(title, "=")
    lines.extend(
        [
            (
                "This reference follows the 11-stage workbench. It explains what each "
                "operation does, why it is available, what output changes, how the "
                "default is chosen, and which checks must precede interpretation."
                if english
                else (
                    "本参考按工作台的 11 个阶段组织，逐项说明操作会做什么、为什么提供、"
                    "输出如何变化、默认值从哪里来，以及解释结果前必须检查什么。"
                )
            ),
            "",
            (
                "Defaults are starting points, not universal recipes. Acquisition "
                "metadata and study design take precedence."
                if english
                else (
                    "默认值用于建立可检查的起点，不代表所有实验的固定配方。采集元数据和"
                    "实验设计始终具有更高优先级。"
                )
            ),
            "",
        ]
    )
    for chapter in TUTORIALS:
        key = str(chapter["key"])
        detail = TUTORIAL_DETAILS[key]
        chapter_title = _value(chapter, "title", language)
        stage_tag = chapter_title[:2]
        lines.extend(_heading(chapter_title, "-"))
        lines.append(_clean(_value(detail, "narrative", language)))
        lines.append("")
        lines.extend(
            _heading(
                (
                    f"{stage_tag} · Before you start"
                    if english
                    else f"{stage_tag} · 开始前准备"
                ),
                "~",
            )
        )
        lines.append(_clean(_value(detail, "before", language)))
        lines.append("")

        lines.extend(
            _heading(
                "Page controls and visible consequences"
                if english
                else "页面操作与可见后果",
                "~",
            )
        )
        lines[-3] = f"{stage_tag} · {lines[-3]}"
        lines[-2] = "~" * _display_width(lines[-3])
        for operation in detail.get("operations", []):
            operation_name = _value(operation, "name", language)
            lines.extend(_heading(f"{stage_tag} · {operation_name}", "^"))
            labels = (
                ("Action", "Purpose", "Visible result")
                if english
                else ("操作", "目的", "可见结果")
            )
            values = (
                _value(operation, "action", language),
                _value(operation, "purpose", language),
                _value(operation, "result", language),
            )
            for label, value in zip(labels, values, strict=True):
                lines.append(f"**{label}：** {_clean(value)}")
                lines.append("")

        lines.extend(
            _heading(
                "Parameter-by-parameter explanation"
                if english
                else "参数逐项说明",
                "~",
            )
        )
        lines[-3] = f"{stage_tag} · {lines[-3]}"
        lines[-2] = "~" * _display_width(lines[-3])
        for parameter in detail.get("parameters", []):
            parameter_name = _value(parameter, "name", language)
            lines.extend(_heading(f"{stage_tag} · {parameter_name}", "^"))
            labels = (
                (
                    "Meaning",
                    "Default",
                    "Recommended setting",
                    "Effect of changing it",
                )
                if english
                else ("含义", "默认值", "推荐设置", "调整后的影响")
            )
            values = (
                _value(parameter, "meaning", language),
                _value(parameter, "default", language),
                _value(parameter, "recommended", language),
                _value(parameter, "effect", language),
            )
            for label, value in zip(labels, values, strict=True):
                lines.append(f"**{label}：** {_clean(value)}")
                lines.append("")

        lines.extend(
            _heading(
                "Recommended operating order"
                if english
                else "推荐操作顺序",
                "~",
            )
        )
        lines[-3] = f"{stage_tag} · {lines[-3]}"
        lines[-2] = "~" * _display_width(lines[-3])
        recommended_key = "recommended_en" if english else "recommended"
        lines.extend(_bullet_lines(list(detail.get(recommended_key, []))))

        lines.extend(
            _heading(
                "Frequent mistakes" if english else "常见错误",
                "~",
            )
        )
        lines[-3] = f"{stage_tag} · {lines[-3]}"
        lines[-2] = "~" * _display_width(lines[-3])
        pitfalls_key = "pitfalls_en" if english else "pitfalls"
        lines.extend(_bullet_lines(list(detail.get(pitfalls_key, []))))

        lines.extend(
            _heading(
                (
                    f"{stage_tag} · Next step"
                    if english
                    else f"{stage_tag} · 下一步"
                ),
                "~",
            )
        )
        lines.append(_clean(_value(detail, "next", language)))
        lines.append("")
        reference_label = "Method source" if english else "方法来源"
        lines.append(
            f"**{reference_label}：** {_clean(_value(chapter, 'reference', language))}"
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    targets = {
        "en": ROOT / "docs" / "sphinx" / "en" / "parameter-reference.rst",
        "zh": ROOT / "docs" / "sphinx" / "zh" / "parameter-reference.rst",
    }
    for language, target in targets.items():
        target.write_text(build(language), encoding="utf-8", newline="\n")
        print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
