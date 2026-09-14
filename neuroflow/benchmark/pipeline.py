from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np

from neuroflow.models import ProjectState
from neuroflow.project import save_project

from .behavior_generator import generate_behavior
from .candidate_sorting import export_blinded_candidate_sorting, write_private_recipe
from .config import load_config, save_config
from .ground_truth_exporter import export_ground_truth
from .lfp_generator import generate_lfp
from .neuron_generator import generate_units
from .neuropixels_forward_model import channel_geometry as neuropixels_geometry
from .qc_anomaly_generator import generate_qc_plan
from .raw_exporter import export_raw_recording
from .benchmark_report import generate_session_figures
from .sorting_evaluator import evaluate_candidate_sorting, write_sorting_evaluation
from .spike_train_generator import generate_spike_trains
from .tetrode_forward_model import channel_geometry as tetrode_geometry
from .validator import validate_session, write_validation_report
from .waveform_generator import generate_templates


def _jsonable(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: _jsonable(row.get(key)) for key in fields} for row in rows])


def estimate_storage(config: dict | None = None) -> dict:
    cfg = config or load_config()
    fs = int(cfg["sampling_rate_hz"])
    scale = {}
    total = 0
    for tier in ("lightweight", "full"):
        durations = cfg[tier]["duration_seconds"]
        if not isinstance(durations, list):
            durations = [durations] * int(cfg[tier]["sessions"])
        for electrode in ("neuropixels", "tetrode"):
            channels = int(cfg[electrode]["lightweight_channels"] if tier == "lightweight" else cfg[electrode]["channels"])
            raw_bytes = int(sum(float(value) for value in durations) * fs * channels * 2)
            scale[f"{tier}_{electrode}_raw_bytes"] = raw_bytes
            total += raw_bytes
    scale["all_raw_bytes"] = total
    scale["recommended_free_bytes"] = int(total * 1.22)
    scale["note"] = "Includes a 22% safety margin for LFP, ground truth, figures, temporary files, and reports."
    return scale


def _duration(cfg: dict, tier: str, session_index: int) -> float:
    value = cfg[tier]["duration_seconds"]
    return float(value[session_index] if isinstance(value, list) else value)


def _config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def _session_seed(base: int, tier: str, electrode: str, session_index: int) -> int:
    digest = hashlib.sha256(f"{base}:{tier}:{electrode}:{session_index}".encode()).digest()
    return int.from_bytes(digest[:8], "little")


def _make_project(
    root: Path,
    name: str,
    raw_path: Path,
    electrode: str,
    channels: int,
    duration: float,
    cfg: dict,
    events: list[dict],
    trials: list[dict],
    metadata: dict,
) -> Path:
    state = ProjectState(
        root=root,
        name=name,
        source_type="benchmark_binary",
        source_path=raw_path,
        recording_path=raw_path,
        sampling_rate=float(cfg["sampling_rate_hz"]),
        channel_count=channels,
        duration_seconds=duration,
        dtype="int16",
        scale_uv_per_bit=float(cfg["scale_uv_per_bit"]),
        electrode_type=electrode,
        events=[{"label": row["event_type"], "time_seconds": row["time_seconds"], "sample_index": row["sample_index"], "trial": row["trial"]} for row in events],
        trials=trials,
        ground_truth={},
        metadata=metadata,
        workflow_status={"import": "completed"},
        run_log=[
            "20-minute benchmark project generated from a deterministic seed.",
            "Ground truth is intentionally external and is not referenced by this project.",
            "Raw broadband data, behavior, geometry, and a blinded candidate sorting are ready for analysis.",
        ],
    )
    return save_project(state)


def generate_session(
    output_root: Path,
    cfg: dict,
    tier: str,
    electrode: str,
    session_index: int,
    progress: Callable[[str], None] | None = None,
) -> tuple[Path, Path, dict]:
    session_id = f"session_{session_index + 1:02d}"
    electrode_root = output_root / tier / electrode
    project_root = electrode_root / session_id
    truth_root = output_root / tier / "ground_truth" / electrode / session_id
    marker = project_root / ".benchmark_complete.json"
    if marker.is_file() and truth_root.is_dir():
        completed = json.loads(marker.read_text(encoding="utf-8"))
        if completed.get("config_hash") != _config_hash(cfg):
            raise RuntimeError(
                f"Existing session was generated with a different configuration: {project_root}"
            )
        return project_root, truth_root, validate_session(project_root, truth_root)
    if project_root.exists():
        raise FileExistsError(f"Refusing to overwrite incomplete benchmark session: {project_root}")

    seed = _session_seed(int(cfg["seed"]), tier, electrode, session_index)
    rng = np.random.default_rng(seed)
    duration = _duration(cfg, tier, session_index)
    channels = int(cfg[electrode]["lightweight_channels"] if tier == "lightweight" else cfg[electrode]["channels"])
    trial_range = tuple(int(v) for v in cfg[tier]["trial_range"])
    units_key = "lightweight_units_per_region" if tier == "lightweight" else "units_per_region"
    build_root = electrode_root / f".{session_id}.building-{seed:x}"
    build_truth = output_root / tier / "ground_truth" / electrode / f".{session_id}.building-{seed:x}"
    if build_root.exists() or build_truth.exists():
        raise FileExistsError(f"A previous build is preserved for inspection: {build_root}")
    raw_dir = build_root / "raw"
    raw_dir.mkdir(parents=True)
    if progress:
        progress(f"{tier}/{electrode}/{session_id}: behavior and neurons")
    trials, events = generate_behavior(rng, session_id, duration, trial_range, float(cfg["sampling_rate_hz"]), cfg["reward_latency"])
    geometry = (neuropixels_geometry if electrode == "neuropixels" else tetrode_geometry)(channels)
    units = generate_units(rng, electrode, channels, cfg[electrode][units_key], cfg["neuron_class_proportions"])
    spikes = generate_spike_trains(rng, units, trials, duration)
    templates = generate_templates(rng, units, electrode, channels, float(cfg["sampling_rate_hz"]))
    qc_plan, qc_rows = generate_qc_plan(rng, session_id, electrode, channels, duration, cfg["qc"], tier == "lightweight")
    lfp = generate_lfp(rng, duration, float(cfg["lfp_sampling_rate_hz"]), trials)
    np.save(raw_dir / "lfp_ground_signal_1khz.npy", lfp)
    raw_path = raw_dir / "recording.bin"
    raw_summary = export_raw_recording(
        raw_path, rng, duration, float(cfg["sampling_rate_hz"]), float(cfg["lfp_sampling_rate_hz"]),
        channels, float(cfg["scale_uv_per_bit"]), lfp, geometry, units, spikes, templates,
        qc_plan, cfg["noise"], float(cfg["chunk_seconds"]),
        (lambda text: progress(f"{tier}/{electrode}/{session_id}: {text}")) if progress else None,
    )
    profile = cfg[electrode]["acquisition_profiles"][session_index % len(cfg[electrode]["acquisition_profiles"])]
    metadata = {
        "benchmark_schema_version": cfg["schema_version"], "benchmark_tier": tier, "session_id": session_id,
        "electrode_type": electrode, "acquisition_profile": profile, "sampling_rate_hz": cfg["sampling_rate_hz"],
        "lfp_sampling_rate_hz": cfg["lfp_sampling_rate_hz"], "channel_count": channels,
        "duration_seconds": duration, "dtype": "int16", "scale_uv_per_bit": cfg["scale_uv_per_bit"],
        "interleaving": "time-major: sample x channel", "seed": seed, "raw_bytes": raw_summary["bytes"],
        "ground_truth_access": "external_only", "ground_truth_in_project": False,
        "recording_adapter": {"format": "generic_binary", "time_axis": 0, "channel_axis": 1},
    }
    (raw_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(raw_dir / "channel_geometry.csv", geometry)
    _write_csv(raw_dir / "behavior_trials.csv", trials)
    _write_csv(raw_dir / "events.csv", events)
    challenge = export_blinded_candidate_sorting(build_root / "benchmark_inputs" / "blinded_candidate_sorting", rng, spikes, float(cfg["sampling_rate_hz"]), duration)
    session_summary = {**metadata, **raw_summary, "unit_count": len(units), "trial_count": len(trials), "total_true_spikes": int(sum(len(v) for v in spikes.values()))}
    export_ground_truth(build_truth, session_summary, units, spikes, templates, qc_rows, qc_plan)
    write_private_recipe(build_truth, challenge)
    manifest = _make_project(build_root, f"Benchmark {electrode} {session_id} ({duration / 60:g} min)", raw_path, electrode, channels, duration, cfg, events, trials, {
        **metadata,
        "channel_geometry_path": str(raw_dir / "channel_geometry.csv"),
        "behavior_events_path": str(raw_dir / "events.csv"),
        "blinded_candidate_sorting_path": str(build_root / "benchmark_inputs" / "blinded_candidate_sorting"),
    })
    # The project is moved only after every file is complete; rewrite absolute paths after the move.
    build_root.rename(project_root)
    build_truth.rename(truth_root)
    payload = json.loads((project_root / manifest.name).read_text(encoding="utf-8"))
    old, new = str(build_root), str(project_root)
    # Rewrite paths recorded before the atomic directory move.
    def replace_paths(value):
        if isinstance(value, str):
            return value.replace(old, new)
        if isinstance(value, dict):
            return {key: replace_paths(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace_paths(item) for item in value]
        return value
    payload = replace_paths(payload)
    (project_root / manifest.name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    marker.write_text(json.dumps({"config_hash": _config_hash(cfg), "completed_at": datetime.now().isoformat(), **session_summary}, ensure_ascii=False, indent=2), encoding="utf-8")
    result = validate_session(project_root, truth_root)
    return project_root, truth_root, result


def _root_readme(root: Path, cfg: dict) -> None:
    estimate = estimate_storage(cfg)
    text = f"""# NeuroEphys AI 20-minute standard benchmark

这是可重复的在体电生理+行为学 benchmark，包含 Neuropixels-style 和 tetrode 两条独立数据路线。

## 怎么开始

1. 先打开 `OPEN_FIRST_PROJECT.txt` 中指向的 `neuroflow_project.json`。
2. 在 App 中先做原始信号 QC、预处理和 sorting。
3. `benchmark_inputs/blinded_candidate_sorting` 是可选的故意不完美 sorting，用来检验 Unit QC 和横向比较。
4. `ground_truth` 是独立答案区，正常项目不引用它；只在最终验证时使用。

## 目录

- `lightweight/`：2 个短会话/电极类型，用于快速试跑。
- `full/`：7 个 20 分钟会话/电极类型。
- `validation/`：机器可读 JSON 和人可读 Markdown 验证报告。
- `generation_log.txt`：生成进度和异常。

原始宽带数据估算：{estimate['all_raw_bytes'] / 1e9:.2f} GB；推荐生成前空间：{estimate['recommended_free_bytes'] / 1e9:.2f} GB。
"""
    (root / "README.md").write_text(text, encoding="utf-8")


def generate_benchmark(
    output_root: Path,
    config_path: Path | None = None,
    tiers: tuple[str, ...] = ("lightweight",),
    progress: Callable[[str], None] | None = None,
) -> dict:
    cfg = load_config(config_path)
    output_root.mkdir(parents=True, exist_ok=True)
    save_config(cfg, output_root / "dataset_config.yaml")
    estimate = estimate_storage(cfg)
    (output_root / "storage_estimate.json").write_text(json.dumps(estimate, ensure_ascii=False, indent=2), encoding="utf-8")
    _root_readme(output_root, cfg)
    results: list[dict] = []
    sessions: list[dict] = []
    for tier in tiers:
        if tier not in {"lightweight", "full"}:
            raise ValueError(f"Unknown benchmark tier: {tier}")
        for electrode in ("neuropixels", "tetrode"):
            for index in range(int(cfg[tier]["sessions"])):
                project, truth, result = generate_session(output_root, cfg, tier, electrode, index, progress)
                results.append(result)
                session_validation = output_root / "validation" / tier / electrode / f"session_{index + 1:02d}"
                comparison = evaluate_candidate_sorting(
                    truth / "true_spike_times.npz",
                    project / "benchmark_inputs" / "blinded_candidate_sorting",
                    float(cfg["sampling_rate_hz"]),
                )
                write_sorting_evaluation(comparison, session_validation)
                figure_paths: list[str] = []
                if index == 0:
                    figures = generate_session_figures(project, truth, session_validation / "example_figures")
                    figure_paths = [str(session_validation / "example_figures" / f"{name}.png") for name in figures]
                completed = json.loads((project / ".benchmark_complete.json").read_text(encoding="utf-8"))
                sessions.append({
                    "tier": tier, "electrode": electrode, "session": index + 1,
                    "project": str(project / "neuroflow_project.json"), "truth": str(truth),
                    "validation_passed": result["passed"], "sorting_comparison": str(session_validation / "sorting_ground_truth_comparison.json"),
                    "example_figures": figure_paths,
                    "duration_seconds": completed["duration_seconds"], "channel_count": completed["channel_count"],
                    "trial_count": completed["trial_count"], "unit_count": completed["unit_count"],
                    "true_spike_count": completed["total_true_spikes"], "raw_bytes": completed["bytes"],
                })
    validation_path = write_validation_report(results, output_root / "validation")
    index_payload = {"config_hash": _config_hash(cfg), "generated_at": datetime.now().isoformat(), "sessions": sessions, "validation_report": str(validation_path)}
    (output_root / "benchmark_index.json").write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(output_root / "生成汇总.csv", [{
        "层级": row["tier"], "电极类型": row["electrode"], "会话": row["session"],
        "时长_秒": row["duration_seconds"], "通道数": row["channel_count"], "trial数": row["trial_count"],
        "Unit数": row["unit_count"], "真实spike数": row["true_spike_count"],
        "原始数据_GB": round(row["raw_bytes"] / 1e9, 3), "验证": "PASS" if row["validation_passed"] else "FAIL",
        "项目文件": row["project"],
    } for row in sessions])
    total_bytes = sum(row["raw_bytes"] for row in sessions)
    report_lines = [
        "# 生成与验收汇总", "",
        f"- 会话数：{len(sessions)}", f"- 原始数据：{total_bytes / 1e9:.3f} GB",
        f"- 行为 trial：{sum(row['trial_count'] for row in sessions)}",
        f"- 真实 Unit：{sum(row['unit_count'] for row in sessions)}",
        f"- ground-truth spikes：{sum(row['true_spike_count'] for row in sessions):,}",
        f"- 自动验收：{'PASS' if all(row['validation_passed'] for row in sessions) else 'FAIL'}", "",
        "每个会话的项目路径、数量和状态见 `生成汇总.csv`；逐项科学校验见 `validation/validation_report.md`。", "",
        "正常 App 项目不包含 ground truth，而 `ground_truth/` 仅用于最后盲测对照。",
    ]
    (output_root / "生成与验收汇总.md").write_text("\n".join(report_lines), encoding="utf-8")
    first = next((row for row in sessions if row["tier"] == "full"), sessions[0] if sessions else None)
    if first:
        (output_root / "OPEN_FIRST_PROJECT.txt").write_text(f"在 NeuroEphys AI 首页选择‘导入项目’，打开：\n{first['project']}\n", encoding="utf-8")
    return index_payload
