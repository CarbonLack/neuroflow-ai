"""Assemble one indexed NeuroEphys AI delivery folder.

Public materials and private validation records are kept in separate
subdirectories. Raw electrophysiology and behavior files are never copied.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BRAND_FILES = (
    "neuroephys-ai-mark.svg",
    "neuroephys-ai-mark.png",
    "neuroephys-ai.ico",
    "cover-ink-magenta.png",
    "cover-ink-magenta.svg",
    "cover-ink-magenta-zh.png",
    "cover-ink-magenta-zh.svg",
)

SCREENSHOT_FILES = (
    "neuroflow-home.png",
    "neuroephys-ai-unit-curation.png",
    "neuroflow-sorting.png",
    "neuroflow-figure-studio.png",
    "neuroflow-figure-studio-axes.png",
    "neuroephys-event-analysis-en.png",
    "neuroephys-event-analysis-detail-en.png",
    "neuroephys-decoding-en.png",
    "neuroephys-decoding-detail-en.png",
    "neuroephys-event-analysis-zh.png",
    "neuroephys-event-analysis-detail-zh.png",
    "neuroephys-decoding-zh.png",
    "neuroephys-decoding-detail-zh.png",
    "neuroephys-ai-assistant-interface-preview-en.png",
)

PUBLIC_RECORDS = (
    "DEVELOPMENT_PREVIEW.md",
    "DEPLOYMENT_STATUS_ZH.md",
    "THIRD_PARTY_SOURCES.md",
    "PROJECT_RIGHTS_NOTICE_ZH.md",
    "AI_USER_GUIDE_ZH.md",
    "AI_DATA_SECURITY_ZH.md",
    "AI_VALIDATION_REPORT_ZH.md",
    "SUBMISSION_BRIEF_ZH.md",
    "SUBMISSION_BRIEF_EN.md",
)

PRIVATE_RECORDS = (
    "REAL_DATA_WORKFLOW_ZH.md",
    "WANGSHUFEI_SUBJECT101_RUNBOOK_ZH.md",
    "WANGSHUFEI_BATCH_VALIDATION_ZH.md",
    "BUG_FIX_LOG_ZH.md",
    "OUTPUT_INDEX_ZH.md",
    "INTERNAL_VALIDATION_SUMMARY_ZH.md",
)


def copy_existing(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)
    return True


def write_index(destination: Path, package_name: str | None) -> None:
    zh = f"""# NeuroEphys AI 开发预览交付索引

本目录汇总了当前可用于报名、演示、离线阅读和本机验证的材料。

## 从这里开始

1. `01_Brand`：中英文封面、图标和矢量标志。
2. `02_Screenshots`：软件界面、事件分析、统计与机器学习截图。
3. `03_Documentation_Offline`：完整双语离线手册；中文请打开 `zh/index.html`。
4. `04_Windows_Preview/{package_name or "待生成"}`：Windows 开发预览版。
5. `05_Public_Validation`：可公开的开发状态、来源、AI 安全和权利说明。
6. `06_Private_Local_Validation`：真实数据运行记录，仅供团队本机核验，禁止上传公开仓库。
7. `SHA256SUMS.txt`：交付文件的 SHA-256 校验值。

## 在线入口

- GitHub：https://github.com/CarbonLack/neuroflow-ai
- 中文手册：https://carbonlack.github.io/neuroflow-ai/zh/
- English manual：https://carbonlack.github.io/neuroflow-ai/en/
- 开发预览下载：https://github.com/CarbonLack/neuroflow-ai/releases

## 状态说明

当前版本属于开发预览。手册与验证报告分别标注真实数据验证、模拟数据验证和仅有接口的能力。原始电生理和行为数据没有复制到本目录。AI 界面预览只证明交互和安全控制；只有实际连接 Provider 并完成请求后生成的截图，才能标注为真实模型对话。
"""
    en = f"""# NeuroEphys AI development-preview delivery index

This folder collects material for submission, demonstration, offline reading,
and local verification.

## Start here

1. `01_Brand`: English and Chinese covers, icons, and vector mark.
2. `02_Screenshots`: application, event-analysis, statistics, and decoding views.
3. `03_Documentation_Offline`: complete bilingual manual; open `en/index.html`.
4. `04_Windows_Preview/{package_name or "pending"}`: Windows development preview.
5. `05_Public_Validation`: public development, attribution, AI safety, and rights records.
6. `06_Private_Local_Validation`: local-path validation records for the team only.
7. `SHA256SUMS.txt`: SHA-256 checksums.

## Online links

- GitHub: https://github.com/CarbonLack/neuroflow-ai
- English manual: https://carbonlack.github.io/neuroflow-ai/en/
- Chinese manual: https://carbonlack.github.io/neuroflow-ai/zh/
- Preview downloads: https://github.com/CarbonLack/neuroflow-ai/releases

## Status

This is a development preview. The manual distinguishes real-data validation,
simulation-only validation, and interface-only work. No raw electrophysiology
or behavior data is copied into this folder. An AI interface preview verifies
layout and safety controls only; it must not be presented as a real model
conversation unless a Provider request was actually completed.
"""
    (destination / "START_HERE_ZH.md").write_text(zh, encoding="utf-8")
    (destination / "START_HERE_EN.md").write_text(en, encoding="utf-8")


def write_checksums(destination: Path) -> None:
    rows: list[str] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS.txt":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.relative_to(destination).as_posix()}")
    (destination / "SHA256SUMS.txt").write_text(
        "\n".join(rows) + "\n",
        encoding="utf-8",
    )


def assemble(destination: Path, private_project: Path | None = None) -> None:
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(
            f"Destination already exists; choose a new delivery folder: {destination}"
        )
    destination.mkdir(parents=True)

    brand_dir = destination / "01_Brand"
    for name in BRAND_FILES:
        copy_existing(ROOT / "assets" / "brand" / name, brand_dir / name)

    screenshot_root = ROOT / "docs" / "site" / "assets"
    screenshot_dir = destination / "02_Screenshots"
    for name in SCREENSHOT_FILES:
        language = "ZH" if name.endswith("-zh.png") else "EN"
        copy_existing(screenshot_root / name, screenshot_dir / language / name)

    copy_existing(
        ROOT / "docs" / "site",
        destination / "03_Documentation_Offline",
    )

    package_name: str | None = None
    executable_dir = ROOT / "dist" / "NeuroEphysAI"
    if executable_dir.exists():
        preview_dir = destination / "04_Windows_Preview"
        preview_dir.mkdir(parents=True)
        archive_base = preview_dir / "NeuroEphysAI-0.10.0-dev-windows-x64"
        archive_path = Path(
            shutil.make_archive(
                str(archive_base),
                "zip",
                executable_dir.parent,
                executable_dir.name,
            )
        )
        package_name = archive_path.name

    public_dir = destination / "05_Public_Validation"
    for name in PUBLIC_RECORDS:
        copy_existing(ROOT / name, public_dir / name)
    copy_existing(
        ROOT / "docs" / "sphinx" / "en" / "real-data-validation.rst",
        public_dir / "REAL_DATA_VALIDATION_EN.rst",
    )
    copy_existing(
        ROOT / "docs" / "sphinx" / "zh" / "real-data-validation.rst",
        public_dir / "REAL_DATA_VALIDATION_ZH.rst",
    )

    private_dir = destination / "06_Private_Local_Validation"
    private_dir.mkdir(parents=True)
    (private_dir / "DO_NOT_UPLOAD_PUBLICLY.txt").write_text(
        "These records can contain local paths and experimental metadata. "
        "They are included for the research team only. Raw data are not copied.\n",
        encoding="utf-8",
    )
    for name in PRIVATE_RECORDS:
        copy_existing(ROOT / name, private_dir / name)
    if private_project is not None:
        private_project = private_project.resolve()
        selected = private_dir / "Selected_Derived_Outputs"
        for name in (
            "VALIDATION_REPORT_ZH.md",
            "validation_summary.json",
            "sorter_comparison_summary.json",
        ):
            copy_existing(private_project / name, selected / name)
        copy_existing(
            private_project / "results" / "sorting_comparison",
            selected / "sorting_comparison",
        )
        copy_existing(
            private_project / "exports" / "ai_validation",
            selected / "ai_validation",
        )

    write_index(destination, package_name)
    write_checksums(destination)
    print(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--private-project",
        type=Path,
        help="Optional local validation project; only selected derived records are copied.",
    )
    args = parser.parse_args()
    assemble(args.destination, private_project=args.private_project)


if __name__ == "__main__":
    main()
