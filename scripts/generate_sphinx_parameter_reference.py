from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neuroflow.tutorial_details import TUTORIAL_DETAILS
from neuroflow.tutorials import TUTORIALS
from neuroflow.tutorial_catalog import TUTORIAL_CATALOG, catalog_text
from generate_task_manual import rst_text


def build(language: str) -> str:
    english = language == "en"
    locale = "en_US" if english else "zh_CN"
    title = "Controls and method parameters" if english else "操作与方法参数参考"
    lines = [title, "=" * 80, "",
             ("The operating steps below share the App's task catalogue. Method parameters explain "
              "the underlying tools; not every parameter is adjustable in the desktop interface. "
              "Reference values are not a guarantee of the current App or sorter default. "
              "Use the settings and saved run record for your selected analysis."
              if english else
              "下方操作步骤与 App 教程共用内容。方法参数用于理解底层工具，并非全部可在桌面界面调节；"
              "参考值也不等于当前 App 或所选 sorter 的实际默认值。请以所选分析的设置和运行记录为准。"),
             "", ":doc:`task-guide`", ""]
    for chapter in TUTORIALS:
        key = chapter["key"]
        item = next(item for item in TUTORIAL_CATALOG if item["id"] == key)
        text = lambda field: rst_text(catalog_text(item, field, locale))
        lines += [text("title"), "-" * 100, "", text("summary"), "",
                  "**" + ("Have ready" if english else "先准备好") + "**", "", text("prerequisites"), ""]
        for index, step in enumerate(item["steps"], 1):
            lines += [f'{index}. **{rst_text(catalog_text(step, "title", locale))}**', "",
                      "   " + rst_text(catalog_text(step, "body", locale)), ""]
        lines += ["**" + ("Check the result" if english else "完成检查") + "**", "", text("check"), "",
                  "**" + ("Saved output" if english else "保存位置") + "**", "", text("output"), ""]
        for parameter in TUTORIAL_DETAILS[key].get("parameters", []):
            get = lambda field: rst_text(str(parameter.get(field + "_en", parameter.get(field, "")) if english else parameter.get(field, "")))
            name = chapter["title"][:2] + " · " + get("name")
            lines += [name, "~" * 100, ""]
            for field, label in (
                ("meaning", "Meaning" if english else "含义"),
                ("default", "Reference value" if english else "参考值"),
                ("recommended", "Method considerations" if english else "方法考虑"),
                ("effect", "Effect" if english else "影响"),
            ):
                lines += [f"**{label}:** {get(field)}", ""]
        if item["reference"]:
            label = "Method documentation" if english else "方法文档"
            lines += [f'`{label} <{item["reference"]}>`__', ""]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    for language in ("en", "zh"):
        target = ROOT / "docs/sphinx" / language / "parameter-reference.rst"
        target.write_text(build(language), encoding="utf-8", newline="\n")
        print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
