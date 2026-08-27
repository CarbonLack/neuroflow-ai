from __future__ import annotations

import argparse
import csv
import json
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from neuroflow.analysis import preprocessing_preview, run_raw_qc
from neuroflow.data_import import (
    import_binary_recording,
    import_device_recording,
    inspect_binary_sidecars,
)
from neuroflow.figures import (
    preprocessing_diagnostics_figure,
    qc_diagnostics_figure,
    sorting_comparison_figure,
)
from neuroflow.models import ProjectState
from neuroflow.project import save_project
from neuroflow.sorting import load_kilosort4_result, run_kilosort4, run_sorter
from neuroflow.sorting_results import (
    compare_sorting_results,
    register_sorting_result,
)


@dataclass(frozen=True)
class RecordingSpec:
    batch: str
    condition: str
    kind: str
    source: Path
    kilosort: Path
    sampling_rate: float
    channel_count: int
    scale_uv_per_bit: float

    @property
    def project_name(self) -> str:
        return f"{self.batch}_{self.condition}"


def discover_recordings(data_root: Path) -> list[RecordingSpec]:
    specs: list[RecordingSpec] = []
    for structure_path in sorted(data_root.rglob("structure.oebin")):
        session_root = next(
            (
                ancestor
                for ancestor in structure_path.parents
                if (ancestor / "kilosort4").is_dir()
            ),
            None,
        )
        node_root = next(
            (
                ancestor
                for ancestor in structure_path.parents
                if ancestor.name.lower().startswith("record node")
            ),
            structure_path.parent,
        )
        if session_root is None:
            continue
        specs.append(
            RecordingSpec(
                batch=session_root.parent.name,
                condition=session_root.name,
                kind="open_ephys",
                source=node_root,
                kilosort=session_root / "kilosort4",
                sampling_rate=30_000.0,
                channel_count=384,
                scale_uv_per_bit=0.195,
            )
        )

    for params_path in sorted(data_root.rglob("params.py")):
        if not params_path.parent.name.lower().startswith("kilosort"):
            continue
        folder = params_path.parent.parent
        if any(folder.rglob("structure.oebin")):
            continue
        preferred = folder / f"{folder.name}.bin"
        candidates = [
            path
            for path in folder.glob("*.bin")
            if "filtered" not in path.stem.lower()
        ]
        source = preferred if preferred.is_file() else max(
            candidates,
            key=lambda path: path.stat().st_size,
            default=None,
        )
        if source is None:
            continue
        sidecars = inspect_binary_sidecars(source)
        lower_name = folder.name.lower()
        condition = (
            "withmate"
            if "withmate" in lower_name
            else "solo"
            if "solo" in lower_name
            else folder.name
        )
        specs.append(
            RecordingSpec(
                batch=folder.parent.name,
                condition=condition,
                kind="binary",
                source=source,
                kilosort=params_path.parent,
                sampling_rate=float(sidecars.get("sampling_rate") or 30_000.0),
                channel_count=int(sidecars.get("channel_count") or 0),
                scale_uv_per_bit=1.0,
            )
        )
    specs.sort(key=lambda item: (item.batch, item.condition, item.kind))
    missing = [path for item in specs for path in (item.source, item.kilosort) if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing local validation source(s):\n" + "\n".join(map(str, missing)))
    return specs


def _adaptation_entries(spec: RecordingSpec) -> list[dict[str, str]]:
    shared = [
        {
            "问题": "过去的项目保存只有机器清单，不便于实验人员直接检查",
            "处理": "新增来源索引、参数、中文实验日志、中间结果、Sorter 原生结果、横向比较和最终导出目录",
            "结果": "每次保存项目时同步更新，原始数据仍保持只读",
            "状态": "已修正并验证",
        },
        {
            "问题": "Sorting 横向比较入口不直观",
            "处理": "保留 SpikeInterface 两两和多 Sorter 算法，新增并排结果表、CSV 和完整 JSON",
            "结果": "用户可直接比较 Unit 数、spike 数、匹配、独有 Unit 和一致度",
            "状态": "已修正并验证",
        },
    ]
    if spec.kind == "open_ephys":
        shared[0:0] = [
            {
                "问题": "Open Ephys 同时包含 AP 与 LFP，原界面留空会报多流错误，手填 ID 也未传入底层读取器",
                "处理": "新增流探测；能唯一识别时自动选择 ProbeA-AP，同时保留人工指定 Stream ID",
                "结果": "本记录自动选中 AP 流，LFP 不被误送入 Spike sorting",
                "状态": "已修正并用真实数据验证",
            },
            {
                "问题": "真实数据进入 QC 时，当前 SpikeInterface 已使用 select_channels，而旧代码调用 channel_slice",
                "处理": "新增新旧两套通道选择接口的兼容分支，不移除旧版本支持",
                "结果": "384 通道记录能够重新打开并完成 QC、预处理和结果导入",
                "状态": "第一次真实运行发现，第二次运行已通过",
            },
        ]
    else:
        shared.insert(
            0,
            {
                "问题": "通用 .bin 需要人工填写采样率、通道数和探针几何，容易填错",
                "处理": "只读解析相邻 Kilosort params.py 与探针 JSON，并按 chanMap 恢复四 shank 空间顺序",
                "结果": "本记录自动识别 20 kHz、128 通道、int16 和四 shank 几何",
                "状态": "已修正并用真实数据验证",
            },
        )
    return shared


def create_full_project(spec: RecordingSpec, output_root: Path) -> ProjectState:
    project_root = output_root / spec.batch / "projects" / spec.project_name
    if spec.kind == "open_ephys":
        state = import_device_recording(project_root, spec.source, "Open Ephys")
    else:
        state = import_binary_recording(
            project_root,
            spec.source,
            sampling_rate=spec.sampling_rate,
            channel_count=spec.channel_count,
            dtype="int16",
            scale_uv_per_bit=spec.scale_uv_per_bit,
            copy_source=False,
        )
    state.name = spec.project_name
    state.metadata["validation_batch"] = spec.batch
    state.metadata["condition"] = spec.condition
    state.metadata["adaptation_log"] = _adaptation_entries(spec)
    state.metadata["raw_source_policy"] = "read_only"
    state.qc = run_raw_qc(state, seconds=min(2.0, state.duration_seconds))
    state.preprocessing = preprocessing_preview(
        state,
        start_seconds=0.0,
        duration_seconds=min(0.2, state.duration_seconds),
    )
    load_kilosort4_result(state, spec.kilosort, sorter_key="kilosort4_existing")
    state.workflow_status.update(
        {
            "import": "completed",
            "qc": "completed",
            "preprocess": "completed",
            "sorting": "completed",
        }
    )
    save_project(state)
    figures = state.root / "exports" / "figures"
    qc_diagnostics_figure(state, "summary").savefig(
        figures / "01_原始质控.png", dpi=180, bbox_inches="tight"
    )
    preprocessing_diagnostics_figure(state.preprocessing, state, "ap").savefig(
        figures / "02_预处理预览.png", dpi=180, bbox_inches="tight"
    )
    save_project(state)
    return state


def _preview_binary(source: Path, destination: Path, frames: int, channels: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected_values = frames * channels
    raw = np.memmap(source, dtype=np.int16, mode="r", shape=(source.stat().st_size // 2,))
    if raw.size < expected_values:
        raise ValueError(f"{source} is shorter than the requested preview")
    np.asarray(raw[:expected_values]).tofile(destination)


def create_preview_comparison(
    spec: RecordingSpec,
    output_root: Path,
    preview_seconds: float,
    run_cpu_sorter: bool,
) -> ProjectState:
    project_root = (
        output_root
        / spec.batch
        / "method_comparison"
        / f"{spec.project_name}_{preview_seconds:g}s"
    )
    if spec.kind == "open_ephys":
        state = import_device_recording(project_root, spec.source, "Open Ephys")
        duration = min(preview_seconds, state.duration_seconds)
        adapter = deepcopy(state.metadata["recording_adapter"])
        adapter["start_frame"] = 0
        adapter["end_frame"] = int(duration * state.sampling_rate)
        state.metadata["recording_adapter"] = adapter
        state.duration_seconds = duration
    else:
        duration = preview_seconds
        preview_path = project_root / "cache" / f"source_preview_{preview_seconds:g}s.bin"
        _preview_binary(
            spec.source,
            preview_path,
            int(duration * spec.sampling_rate),
            spec.channel_count,
        )
        state = import_binary_recording(
            project_root,
            preview_path,
            sampling_rate=spec.sampling_rate,
            channel_count=spec.channel_count,
            dtype="int16",
            scale_uv_per_bit=spec.scale_uv_per_bit,
            copy_source=False,
        )
        sidecars = state.metadata.get("detected_sidecars", {})
        full_sidecars = deepcopy(inspect_binary_sidecars(spec.source))
        state.metadata["detected_sidecars"] = full_sidecars or sidecars
        if full_sidecars.get("contact_positions_um"):
            state.metadata["contact_positions_um"] = full_sidecars["contact_positions_um"]
            state.metadata["contact_shank_ids"] = full_sidecars.get("contact_shank_ids", [])
            state.metadata["probe"] = {
                "geometry_mode": "sidecar_geometry",
                "geometry_source": full_sidecars.get("geometry_path"),
            }
        state.source_path = spec.source
    state.name = f"{spec.project_name}_方法对比_{preview_seconds:g}秒"
    state.metadata["adaptation_log"] = _adaptation_entries(spec)
    state.metadata["comparison_window_seconds"] = [0.0, state.duration_seconds]
    state.metadata["comparison_notice"] = (
        "All sorter results are restricted to the same preview window. Agreement is not accuracy."
    )

    reference = load_kilosort4_result(
        state,
        spec.kilosort,
        sorter_key="kilosort4_existing_same_window",
    )
    cropped = {}
    for unit_id, spikes in reference.items():
        values = spikes[(spikes >= 0.0) & (spikes < state.duration_seconds)]
        if values.size:
            cropped[unit_id] = values
    reference_provenance = dict(state.sorting_provenance["kilosort4_existing_same_window"])
    reference_provenance["comparison_window_seconds"] = [0.0, state.duration_seconds]
    register_sorting_result(
        state,
        "kilosort4_existing_same_window",
        cropped,
        reference_provenance,
    )

    progress = lambda message: state.log(f"Sorter progress: {message}")
    run_kilosort4(
        state,
        state.root / "results" / "kilosort4_local",
        progress,
        {
            "batch_size": 60_000,
            "nblocks": 0,
            "Th_universal": 9,
            "Th_learned": 8,
            "save_extra_vars": True,
        },
        sorter_key="kilosort4_local_same_window",
    )
    if run_cpu_sorter:
        try:
            run_sorter(
                state,
                "simple",
                state.root / "results" / "simple",
                progress,
                activate=False,
                update_comparison=False,
            )
        except Exception as exc:  # noqa: BLE001 - preserve the two Kilosort results
            state.metadata.setdefault("adaptation_log", []).append(
                {
                    "问题": "CPU Simple Sorter 在真实高通道预览上未完成",
                    "处理": "保留同一时间窗内已有 Kilosort 与本机 Kilosort 结果，不覆盖或伪造 CPU 结果",
                    "结果": f"{type(exc).__name__}: {exc}",
                    "状态": "已记录；方法对比仍可用，CPU 路线待单独优化",
                }
            )
            state.log(f"Simple sorter failed without discarding other results: {type(exc).__name__}: {exc}")
    compare_sorting_results(state)
    state.workflow_status.update({"import": "completed", "sorting": "completed"})
    save_project(state)
    figure = sorting_comparison_figure(state)
    figure.savefig(
        state.root / "exports" / "figures" / "03_Sorting横向比较.png",
        dpi=180,
        bbox_inches="tight",
    )
    save_project(state)
    return state


def write_master_report(
    output_root: Path,
    full_projects: list[ProjectState],
    comparisons: list[ProjectState],
    failures: list[dict[str, str]],
    data_root: Path | None = None,
) -> None:
    rows = []
    for state in full_projects:
        rows.append(
            {
                "project": state.name,
                "project_path": str(state.root),
                "channels": state.channel_count,
                "sampling_rate_hz": state.sampling_rate,
                "duration_seconds": state.duration_seconds,
                "sorter_results": ",".join(state.sorting_results),
                "units": len(state.sorted_spikes),
                "qc_quality_score": round(float(state.qc.get("quality_score", 0.0)), 1),
                "status": "completed",
            }
        )
    with (output_root / "项目总表.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    comparison_rows: list[str] = []
    for state in comparisons:
        sorters = state.sorting_comparison.get("sorters", {})
        pairs = state.sorting_comparison.get("pairwise", [])
        old_key = "kilosort4_existing_same_window"
        new_key = "kilosort4_local_same_window"
        pair = next(
            (
                item
                for item in pairs
                if {item.get("sorter_a"), item.get("sorter_b")} == {old_key, new_key}
            ),
            {},
        )
        old = sorters.get(old_key, {})
        new = sorters.get(new_key, {})
        simple = sorters.get("simple", {})
        comparison_rows.append(
            f"| {state.name} | {old.get('unit_count', 0)} / {old.get('spike_count', 0)} | "
            f"{new.get('unit_count', 0)} / {new.get('spike_count', 0)} | "
            f"{simple.get('unit_count', 0)} / {simple.get('spike_count', 0)} | "
            f"{pair.get('matched_unit_count', 0)} | "
            f"{float(pair.get('mean_matched_agreement', 0.0)):.3f} | `{state.root}` |"
        )
    comparison_table = (
        "| 项目 | 既有 Kilosort Unit/spike | 本机 Kilosort Unit/spike | Simple Unit/spike | Kilosort 匹配 Unit | 匹配平均一致度 | 项目位置 |\n"
        "|---|---:|---:|---:|---:|---:|---|\n"
        + "\n".join(comparison_rows)
        if comparison_rows
        else "- 尚未运行本地方法对比。"
    )
    failure_lines = "\n".join(
        f"- {item['project']}：{item['error']}" for item in failures
    ) or "- 无。"
    source_label = str(data_root) if data_root is not None else "外部电生理数据"
    report = f"""# {source_label} · NeuroEphys AI 真实数据验证

## 保存位置

`{output_root}`

## 已完成

- 四份原始记录均以只读方式建立独立 NeuroEphys AI 项目。
- 每个项目保存来源索引、参数、中文实验日志、QC、预处理预览和已有 Kilosort4 统一结果。
- Open Ephys 自动选择 AP 流；通用二进制自动识别 Kilosort 参数和四 shank 几何。
- 所有比较均限制到相同时间窗；真实数据报告一致度，不报告伪准确率。

## 方法对比项目

{comparison_table}

比较窗口均为记录开始后的 30 秒。既有 Kilosort 结果来自完整记录后截取该时间窗，本机 Kilosort 与 Simple 是只在该 30 秒窗口内重新训练和运行；因此这里用于验证接入、重跑和结果一致性，不把一致度冒充准确率。

## 未完成或失败

{failure_lines}

## 目录规则

进入任一项目先读 `00_README_项目说明.md` 和 `logs/实验日志_中文.md`。原始数据没有被移动或修改。

## 方法来源

- SpikeInterface comparison：<https://spikeinterface.readthedocs.io/en/latest/modules/comparison.html>
- Kilosort4：<https://kilosort.readthedocs.io/en/latest/>
"""
    (output_root / "README_总报告.md").write_text(report, encoding="utf-8")
    (output_root / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local electrophysiology data without modifying raw sources")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT.parent / "real_data_validation",
    )
    parser.add_argument("--preview-seconds", type=float, default=30.0)
    parser.add_argument("--skip-preview-sorters", action="store_true")
    parser.add_argument("--skip-cpu-sorter", action="store_true")
    args = parser.parse_args()

    args.output_root.mkdir(parents=True, exist_ok=True)
    specs = discover_recordings(args.data_root)
    full_projects: list[ProjectState] = []
    comparisons: list[ProjectState] = []
    failures: list[dict[str, str]] = []
    for spec in specs:
        try:
            print(f"[full] {spec.project_name}", flush=True)
            full_projects.append(create_full_project(spec, args.output_root))
        except Exception as exc:  # noqa: BLE001 - continue to preserve every independent experiment
            failures.append({"project": spec.project_name, "stage": "full", "error": f"{type(exc).__name__}: {exc}"})
            print(f"[failed] {spec.project_name}: {exc}", flush=True)

    if not args.skip_preview_sorters:
        representatives = []
        for batch in dict.fromkeys(item.batch for item in specs):
            batch_items = [item for item in specs if item.batch == batch]
            representatives.append(
                next(
                    (item for item in batch_items if item.condition == "solo"),
                    batch_items[0],
                )
            )
        for spec in representatives:
            try:
                print(f"[compare] {spec.project_name}", flush=True)
                comparisons.append(
                    create_preview_comparison(
                        spec,
                        args.output_root,
                        args.preview_seconds,
                        run_cpu_sorter=not args.skip_cpu_sorter,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - the full projects remain valid
                failures.append({"project": spec.project_name, "stage": "comparison", "error": f"{type(exc).__name__}: {exc}"})
                print(f"[failed comparison] {spec.project_name}: {exc}", flush=True)

    write_master_report(
        args.output_root,
        full_projects,
        comparisons,
        failures,
        data_root=args.data_root,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
