from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


PURPLE = "#B59BC8"
GREEN = "#A7D39E"
INK = "#25222A"


def _metrics(mean_waveform: np.ndarray, sampling_rate: float, amplitude_cv: float) -> dict:
    waveform = np.asarray(mean_waveform, dtype=float).reshape(-1)
    edge = max(3, min(8, len(waveform) // 6))
    baseline = np.r_[waveform[:edge], waveform[-edge:]].mean()
    waveform = waveform - baseline
    trough_index = int(np.argmin(waveform))
    trough = float(-waveform[trough_index])
    positive_before = float(max(np.max(waveform[:trough_index], initial=0.0), 0.0))
    positive_after = float(max(np.max(waveform[trough_index + 1 :], initial=0.0), 0.0))
    peak_after_index = trough_index + 1 + int(np.argmax(waveform[trough_index + 1 :])) if trough_index + 1 < len(waveform) else trough_index
    threshold = -0.5 * trough
    left = trough_index
    right = trough_index
    while left > 0 and waveform[left - 1] <= threshold:
        left -= 1
    while right + 1 < len(waveform) and waveform[right + 1] <= threshold:
        right += 1
    return {
        "negative_peak": trough,
        "half_width_ms": (right - left + 1) / sampling_rate * 1000.0,
        "trough_to_peak_ms": max(peak_after_index - trough_index, 0) / sampling_rate * 1000.0,
        "pre_positive_ratio": positive_before / max(trough, 1e-9),
        "rebound_ratio": positive_after / max(trough, 1e-9),
        "amplitude_cv": float(amplitude_cv),
        "waveform": waveform,
        "trough_index": trough_index,
    }


def load_real_units(root: Path, sampling_rate: float) -> list[dict]:
    records: list[dict] = []
    for path in sorted(root.rglob("unit_*_waveforms.npy")):
        waveforms = np.load(path, mmap_mode="r")
        if waveforms.ndim == 3:
            waveforms = waveforms[:, :, 0]
        if waveforms.ndim != 2 or len(waveforms) < 20:
            continue
        # The median is resistant to occasional threshold crossings and artifacts.
        mean_waveform = np.median(np.asarray(waveforms, dtype=np.float32), axis=0)
        per_spike_amplitude = np.ptp(np.asarray(waveforms, dtype=np.float32), axis=1)
        central = per_spike_amplitude[
            (per_spike_amplitude >= np.percentile(per_spike_amplitude, 5))
            & (per_spike_amplitude <= np.percentile(per_spike_amplitude, 95))
        ]
        cv = float(np.std(central) / max(np.mean(central), 1e-9))
        row = _metrics(mean_waveform, sampling_rate, cv)
        row.update({"source": "real", "unit": path.stem, "path": str(path)})
        # Exclude positive-dominant/noisy snippets from the somatic negative-spike reference.
        if row["negative_peak"] >= 20 and np.max(row["waveform"]) <= 0.8 * row["negative_peak"]:
            records.append(row)
    return records


def load_simulated_units(root: Path, sampling_rate: float) -> list[dict]:
    records: list[dict] = []
    for path in sorted(root.rglob("waveform_templates.npz")):
        units_path = path.with_name("units.csv")
        units = pd.read_csv(units_path).set_index("unit_id") if units_path.exists() else pd.DataFrame()
        with np.load(path) as archive:
            for key in archive.files:
                if not key.endswith("_waveform_uv"):
                    continue
                unit_id = int(key.split("_")[1])
                template = archive[key]
                peak_channel = int(np.argmax(np.ptp(template, axis=0)))
                cv = float(units.loc[unit_id, "waveform_amplitude_cv"]) if not units.empty and "waveform_amplitude_cv" in units else np.nan
                row = _metrics(template[:, peak_channel], sampling_rate, cv)
                row.update(
                    {
                        "source": "simulated",
                        "unit": f"unit_{unit_id}",
                        "path": str(path),
                        "family": str(units.loc[unit_id, "waveform_family"]) if not units.empty and "waveform_family" in units else "unknown",
                    }
                )
                records.append(row)
    return records


def _percentile_summary(records: list[dict], key: str) -> dict:
    values = np.asarray([row[key] for row in records if np.isfinite(row[key])], dtype=float)
    return {
        "n": int(len(values)),
        "p10": float(np.percentile(values, 10)),
        "median": float(np.median(values)),
        "p90": float(np.percentile(values, 90)),
    }


def render_comparison(real: list[dict], simulated: list[dict], output: Path) -> None:
    rng = np.random.default_rng(20260915)
    fig = plt.figure(figsize=(12.0, 7.2), constrained_layout=True)
    grid = fig.add_gridspec(2, 3, height_ratios=[1.25, 1.0])
    ax_real = fig.add_subplot(grid[0, 0])
    ax_sim = fig.add_subplot(grid[0, 1])
    ax_overlay = fig.add_subplot(grid[0, 2])
    metric_axes = [fig.add_subplot(grid[1, index]) for index in range(3)]

    for ax, records, title, color in (
        (ax_real, real, "真实 Unit：逐次波形中位数", GREEN),
        (ax_sim, simulated, "模拟 Unit：ground truth 模板", PURPLE),
    ):
        chosen = rng.choice(len(records), size=min(18, len(records)), replace=False)
        for index in chosen:
            row = records[int(index)]
            waveform = row["waveform"] / max(row["negative_peak"], 1e-9)
            x = (np.arange(len(waveform)) - row["trough_index"]) / 30.0
            ax.plot(x, waveform, color=color, alpha=0.45, linewidth=0.9)
        ax.axhline(0, color="#C8C3CC", linewidth=0.7)
        ax.set(title=title, xlabel="相对负峰时间 (ms)", ylabel="归一化振幅")

    def normalized_interpolated(rows: list[dict]) -> np.ndarray:
        target = np.linspace(-0.8, 1.2, 201)
        curves = []
        for row in rows:
            waveform = row["waveform"] / max(row["negative_peak"], 1e-9)
            x = (np.arange(len(waveform)) - row["trough_index"]) / 30.0
            curves.append(np.interp(target, x, waveform))
        return target, np.asarray(curves)

    for rows, label, color in ((real, "真实", GREEN), (simulated, "模拟", PURPLE)):
        x, curves = normalized_interpolated(rows)
        median = np.median(curves, axis=0)
        low, high = np.percentile(curves, [10, 90], axis=0)
        ax_overlay.fill_between(x, low, high, color=color, alpha=0.20)
        ax_overlay.plot(x, median, color=color, linewidth=2.0, label=label)
    ax_overlay.axhline(0, color="#C8C3CC", linewidth=0.7)
    ax_overlay.set(title="总体形态范围（10%–90%）", xlabel="相对负峰时间 (ms)", ylabel="归一化振幅")
    ax_overlay.legend(frameon=False)

    metrics = [
        ("half_width_ms", "负峰半高宽 (ms)"),
        ("trough_to_peak_ms", "负峰至正回弹 (ms)"),
        ("rebound_ratio", "正回弹 / 负峰"),
    ]
    for ax, (key, label) in zip(metric_axes, metrics):
        values = [[row[key] for row in real], [row[key] for row in simulated]]
        parts = ax.violinplot(values, showmedians=True, showextrema=False)
        for body, color in zip(parts["bodies"], (GREEN, PURPLE)):
            body.set_facecolor(color)
            body.set_edgecolor(INK)
            body.set_alpha(0.75)
        parts["cmedians"].set_color(INK)
        ax.set_xticks([1, 2], ["真实", "模拟"])
        ax.set_ylabel(label)
        ax.spines[["top", "right"]].set_visible(False)

    for ax in fig.axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(False)
    fig.suptitle("NeuroEphys AI 波形真实性对照", fontsize=16, fontweight="bold", color=INK)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare simulated extracellular spikes with real exported unit waveforms.")
    parser.add_argument("--real-root", type=Path, required=True)
    parser.add_argument("--sim-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sampling-rate", type=float, default=30000.0)
    args = parser.parse_args()

    real = load_real_units(args.real_root, args.sampling_rate)
    simulated = load_simulated_units(args.sim_root, args.sampling_rate)
    if not real or not simulated:
        raise SystemExit(f"Insufficient waveforms: real={len(real)}, simulated={len(simulated)}")
    keys = ["half_width_ms", "trough_to_peak_ms", "pre_positive_ratio", "rebound_ratio", "amplitude_cv"]
    report = {
        "purpose": "只读真实数据校准；不把真实数据复制进项目，也不用于训练",
        "real_unit_count": len(real),
        "simulated_unit_count": len(simulated),
        "metrics": {
            key: {"real": _percentile_summary(real, key), "simulated": _percentile_summary(simulated, key)}
            for key in keys
        },
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "waveform_realism_metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Spike 波形真实性校准报告",
        "",
        f"- 真实 Unit：{len(real)} 个（E 盘 Kilosort 导出的逐次波形，只读分析）",
        f"- 模拟 Unit：{len(simulated)} 个",
        "- 表内范围为第 10–90 百分位，中间值为中位数。",
        "",
        "| 指标 | 真实数据 | 模拟数据 |",
        "|---|---:|---:|",
    ]
    labels = {
        "half_width_ms": "负峰半高宽 (ms)",
        "trough_to_peak_ms": "负峰到正回弹 (ms)",
        "pre_positive_ratio": "前置正峰/负峰",
        "rebound_ratio": "正回弹/负峰",
        "amplitude_cv": "逐次振幅变异系数",
    }
    for key in keys:
        real_summary = report["metrics"][key]["real"]
        sim_summary = report["metrics"][key]["simulated"]
        fmt = lambda value: f"{value['median']:.3f}（{value['p10']:.3f}–{value['p90']:.3f}）"
        lines.append(f"| {labels[key]} | {fmt(real_summary)} | {fmt(sim_summary)} |")
    lines.extend(
        [
            "",
            "说明：这里比较的是 extracellular spike 的形态分布，不要求每个模拟 Unit 复制某个真实 Unit；目标是让模拟总体落入真实数据的合理范围，并保留可控 ground truth。",
        ]
    )
    (args.output / "波形真实性校准报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    render_comparison(real, simulated, args.output / "waveform_realism_comparison.png")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
