from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import ProjectState


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "tolist"):
        try:
            return _jsonable(value.tolist())
        except (TypeError, ValueError):
            pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == normalized:
        return
    path.write_text(normalized, encoding="utf-8")


def _source_record(state: ProjectState) -> dict[str, Any]:
    source = state.source_path or state.recording_path
    record: dict[str, Any] = {
        "原始数据路径": str(source) if source else None,
        "原始数据只读": True,
        "项目内是否复制原始数据": bool(state.metadata.get("copy_source", False)),
        "读取方式": state.source_type,
        "采样率_Hz": state.sampling_rate,
        "通道数": state.channel_count,
        "时长_秒": state.duration_seconds,
        "数据类型": state.dtype,
        "每bit微伏": state.scale_uv_per_bit,
        "电极或探针": state.electrode_type,
        "记录适配器": state.metadata.get("recording_adapter", {}),
    }
    if source and source.exists():
        record["来源存在"] = True
        if source.is_file():
            record["来源文件字节数"] = source.stat().st_size
    else:
        record["来源存在"] = False
    return record


def _adaptation_markdown(state: ProjectState) -> str:
    items = state.metadata.get("adaptation_log", [])
    if not items:
        return "- 当前没有记录到需要新增适配的问题。"
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            lines.append(f"{index}. {item}")
            continue
        problem = str(item.get("问题", item.get("problem", "未说明")))
        fix = str(item.get("处理", item.get("fix", "未说明")))
        effect = str(item.get("结果", item.get("result", "待验证")))
        status = str(item.get("状态", item.get("status", "已记录")))
        lines.extend(
            [
                f"{index}. **{problem}**",
                f"   - 处理：{fix}",
                f"   - 结果：{effect}",
                f"   - 状态：{status}",
            ]
        )
    return "\n".join(lines)


def _chinese_run_message(message: str) -> str:
    replacements = (
        (r"^Open Ephys linked read-only: (\d+) selected channels, ([0-9.]+) seconds, (\d+) digital edges$", r"Open Ephys 只读链接完成：\1 通道，\2 秒，\3 个数字边沿"),
        (r"^Generic binary recording imported: (.+)$", r"通用二进制记录导入完成：\1"),
        (r"^Kilosort/Phy sidecar detected:.*$", "已识别 Kilosort/Phy 辅助文件：采样率、通道数、数据类型和可用探针几何已记录"),
        (r"^Raw QC completed: quality score ([0-9.]+)/100, (\d+) high-noise channels, 50 Hz ratio ([0-9.]+)$", r"原始质控完成：质量分 \1/100，高噪声通道 \2 个，50 Hz 比值 \3"),
        (r"^AP preprocessing skipped:.*$", "AP 预处理未重复执行：采集元数据表明在线滤波或参考已完成"),
        (r"^Sorter comparison updated: (\d+) result\(s\), (\d+) pair\(s\)$", r"Sorter 比较已更新：\1 份结果，\2 组两两比较"),
        (r"^Kilosort4 result loaded: (\d+) units, (\d+) spikes$", r"Kilosort4 结果导入完成：\1 个候选 Unit，\2 个 spike"),
        (r"^Kilosort4 completed: (\d+) units, (\d+) spikes$", r"Kilosort4 本机运行完成：\1 个候选 Unit，\2 个 spike"),
        (r"^Sorter progress: Kilosort4 ([^ ]+) on (.+) is running$", r"正在运行 Kilosort4 \1；计算设备：\2"),
        (r"^Sorter progress: Preparing an interleaved cache for the selected channels; the linked source remains read-only$", "正在为已选通道准备交错二进制缓存；原始数据继续保持只读"),
        (r"^Sorter progress: Interleaved cache: ([0-9.]+)/([0-9.]+) seconds written \((\d+)/(\d+) chunks\)$", r"Sorting 缓存进度：已写入 \1/\2 秒（第 \3/\4 块）"),
        (r"^Sorter progress: Reusing the verified interleaved sorting cache$", "复用已经核验的 Sorting 缓存"),
        (r"^Sorter progress: SpikeInterface (.+) is running through SpikeInterface$", r"正在通过 SpikeInterface 运行 \1"),
        (r"^Sorter progress: Sorting completed: (\d+) units$", r"Sorting 完成：\1 个候选 Unit"),
        (r"^SpikeInterface (.+) completed: (\d+) units$", r"SpikeInterface \1 完成：\2 个候选 Unit"),
        (r"^NeuroEphys AI project restored$", "NeuroEphys AI 项目已恢复并重新保存"),
    )
    for pattern, replacement in replacements:
        if re.match(pattern, message):
            return re.sub(pattern, replacement, message)
    return message


def _write_comparison_exports(state: ProjectState) -> None:
    comparison = state.sorting_comparison
    destination = state.root / "results" / "sorting_comparison"
    destination.mkdir(parents=True, exist_ok=True)
    if not comparison:
        _write_text(
            destination / "README_对比说明.md",
            "# Sorting 横向比较\n\n至少保存两个 sorting 结果后，这里会生成汇总表。"
            "真实数据上的算法一致度不是准确率；只有带 ground truth 的数据才报告准确率、召回率和 F1。",
        )
        return
    (destination / "comparison_summary.json").write_text(
        json.dumps(_jsonable(comparison), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (destination / "sorter_summary.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sorter", "unit_count", "spike_count", "backend", "version"],
        )
        writer.writeheader()
        for key, item in comparison.get("sorters", {}).items():
            provenance = item.get("provenance", {})
            writer.writerow(
                {
                    "sorter": key,
                    "unit_count": item.get("unit_count", 0),
                    "spike_count": item.get("spike_count", 0),
                    "backend": provenance.get("backend", ""),
                    "version": provenance.get("version", ""),
                }
            )
    with (destination / "pairwise_summary.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        fields = [
            "sorter_a",
            "sorter_b",
            "matched_unit_count",
            "mean_matched_agreement",
            "unique_units_a",
            "unique_units_b",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in comparison.get("pairwise", []):
            writer.writerow({key: item.get(key, "") for key in fields})
    _write_text(
        destination / "README_对比说明.md",
        "# Sorting 横向比较\n\n"
        "- `sorter_summary.csv`：每个 Sorter 的 Unit 与 spike 总数。\n"
        "- `pairwise_summary.csv`：两两匹配、独有 Unit 和匹配后平均一致度。\n"
        "- `comparison_summary.json`：完整矩阵和溯源信息，供软件恢复。\n\n"
        "算法一致度用于检查结果是否稳健，不等同于生物学真值或准确率。\n\n"
        "方法依据：SpikeInterface comparison 模块的 `compare_two_sorters` 与 "
        "`compare_multiple_sorters`：https://spikeinterface.readthedocs.io/en/latest/modules/comparison.html",
    )


def update_human_project_records(state: ProjectState) -> None:
    """Maintain a scientist-readable project tree alongside the machine manifest."""
    for folder in ("inputs", "config", "logs", "cache", "derived", "results", "exports"):
        (state.root / folder).mkdir(parents=True, exist_ok=True)
    (state.root / "exports" / "tables").mkdir(parents=True, exist_ok=True)
    (state.root / "exports" / "figures").mkdir(parents=True, exist_ok=True)

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    state.metadata["project_layout_version"] = "1.0"
    source_record = _source_record(state)
    (state.root / "inputs" / "source_index.json").write_text(
        json.dumps(_jsonable(source_record), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    parameters = {
        "项目名": state.name,
        "最后更新": now,
        "工作流状态": state.workflow_status,
        "当前激活Sorter": state.active_sorter_key,
        "Sorter来源与参数": state.sorting_provenance,
        "预处理": state.preprocessing,
        "项目元数据": state.metadata,
    }
    (state.root / "config" / "project_parameters.json").write_text(
        json.dumps(_jsonable(parameters), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_text(state.root / "logs" / "run_log.txt", "\n".join(state.run_log))
    run_lines = "\n".join(
        f"{index}. {_chinese_run_message(message)}"
        for index, message in enumerate(state.run_log, start=1)
    ) or "- 尚无运行记录。"
    _write_text(
        state.root / "logs" / "实验日志_中文.md",
        f"""# {state.name} · 实验日志

最后更新：{now}

## 数据与项目

- 项目位置：`{state.root}`
- 原始数据：`{source_record.get('原始数据路径')}`
- 原始数据策略：只读链接，不在原目录写入分析结果
- 记录：{state.channel_count} 通道，{state.sampling_rate:g} Hz，{state.duration_seconds:.3f} 秒，{state.dtype}
- 当前 Sorting：{state.active_sorter_key or '尚未选择'}

## 发现的问题、处理和结果

{_adaptation_markdown(state)}

## 软件操作记录

{run_lines}

## 解释边界

- Sorter 输出是候选 Unit，仍需质量控制和人工复核。
- 两个 Sorter 在真实数据上的匹配程度叫“一致度”，不能写成准确率。
- `inputs` 只保存来源索引；原始数据本身保持只读。
""",
    )
    manual_notes = state.root / "logs" / "人工实验笔记.md"
    if not manual_notes.exists():
        _write_text(
            manual_notes,
            "# 人工实验笔记\n\n此文件留给实验人员补充动物、脑区、任务、异常情况和人工复核决定；软件不会覆盖它。",
        )
    _write_text(
        state.root / "00_README_项目说明.md",
        f"""# {state.name}

这是一个可恢复的 NeuroEphys AI 实验项目。打开项目时选择根目录内的 `neuroflow_project.json`。

## 文件夹怎么读

- `inputs/`：原始数据位置和读取参数；原始数据保持只读。
- `config/`：本次采集、分析参数、版本和当前状态。
- `logs/`：中文实验日志、原始运行记录和人工笔记。
- `cache/`：为预览或 Sorter 准备的可重建缓存，可很大。
- `derived/`：统一格式的中间结果，例如每个 Sorter 的秒制 spike 时间。
- `results/`：各 Sorter 原生输出及 `sorting_comparison/` 横向对比表。
- `exports/`：最终表格、图和可复现导出。

## 保存原则

原始数据不改动；参数、问题、修正、中间结果、最终结果分别保存。若复制项目给别人，原始大文件未随项目复制时，需要重新定位 `inputs/source_index.json` 记录的数据源。

最后更新：{now}
""",
    )
    _write_comparison_exports(state)
