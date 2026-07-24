from __future__ import annotations

import numpy as np
from matplotlib import rcParams
from matplotlib.figure import Figure

from .analysis import load_recording
from .models import ProjectState


INK = "#17221f"
MUTED = "#66716d"
GREEN = "#1f7a63"
CORAL = "#d86d4b"
GOLD = "#c9972b"
GRID = "#dfe5e2"
PAPER = "#ffffff"

def _configure_fonts() -> None:
    rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    rcParams["axes.unicode_minus"] = False


_configure_fonts()


def _base_figure(rows: int = 1, columns: int = 1, height: float = 5.4) -> tuple[Figure, object]:
    _configure_fonts()
    fig = Figure(figsize=(9.2, height), facecolor=PAPER, constrained_layout=True)
    axes = fig.subplots(rows, columns, squeeze=False)
    for axis in axes.flat:
        axis.set_facecolor(PAPER)
        axis.tick_params(colors=MUTED, labelsize=8)
        axis.grid(color=GRID, linewidth=0.7, alpha=0.65)
        for spine in axis.spines.values():
            spine.set_color("#cfd8d4")
    return fig, axes


def raw_overview_figure(state: ProjectState) -> Figure:
    fig, axes = _base_figure(2, 1, 6.2)
    raw = load_recording(state)
    start = int(2.0 * state.sampling_rate)
    count = int(0.06 * state.sampling_rate)
    traces = np.asarray(raw[start : start + count, :8], dtype=np.float32)
    time_ms = np.arange(count) / state.sampling_rate * 1000
    offsets = np.arange(8) * 700
    axes[0, 0].plot(time_ms, traces + offsets, linewidth=0.65, color=INK)
    axes[0, 0].set_title("原始多通道电压预览", loc="left", fontsize=11, color=INK)
    axes[0, 0].set_xlabel("时间 (ms)", color=MUTED)
    axes[0, 0].set_yticks(offsets)
    axes[0, 0].set_yticklabels([f"Ch {index}" for index in range(8)])

    counts = [len(spikes) for spikes in state.ground_truth.values()]
    axes[1, 0].bar(np.arange(len(counts)), counts, color=GREEN, width=0.68)
    axes[1, 0].set_title("模拟数据中的已知神经元放电数（仅用于验证）", loc="left", fontsize=11, color=INK)
    axes[1, 0].set_xlabel("Ground-truth unit", color=MUTED)
    axes[1, 0].set_ylabel("Spike 数", color=MUTED)
    return fig


def qc_figure(state: ProjectState) -> Figure:
    fig, axes = _base_figure(1, 2, 4.7)
    rms = np.asarray(state.qc.get("channel_rms", []), dtype=float)
    if rms.size:
        colors = [CORAL if index in state.qc.get("bad_channels", []) else GREEN for index in range(len(rms))]
        axes[0, 0].bar(np.arange(len(rms)), rms, color=colors, width=0.82)
        axes[0, 0].axhline(np.median(rms) * 2.6, color=CORAL, linestyle="--", linewidth=1)
    axes[0, 0].set_title("各通道RMS噪声", loc="left", fontsize=11, color=INK)
    axes[0, 0].set_xlabel("通道", color=MUTED)
    axes[0, 0].set_ylabel("ADC RMS", color=MUTED)

    labels = ["50 Hz比值", "坏通道", "饱和样本"]
    values = [
        state.qc.get("line_noise_ratio", 0),
        len(state.qc.get("bad_channels", [])),
        state.qc.get("saturated_samples", 0),
    ]
    axes[0, 1].barh(labels, values, color=[GOLD, CORAL, GREEN])
    axes[0, 1].set_title("主要质控指标", loc="left", fontsize=11, color=INK)
    return fig


def preprocessing_figure(preview: dict[str, np.ndarray]) -> Figure:
    fig, axes = _base_figure(2, 1, 5.8)
    time_ms = preview["time_ms"]
    raw = preview["raw"]
    processed = preview["processed"]
    offsets = np.arange(raw.shape[1]) * 650
    axes[0, 0].plot(time_ms, raw + offsets, color=MUTED, linewidth=0.55)
    axes[0, 0].set_title("处理前", loc="left", fontsize=11, color=INK)
    axes[1, 0].plot(time_ms, processed + offsets, color=GREEN, linewidth=0.55)
    axes[1, 0].set_title("300–6000 Hz + common median reference 预览", loc="left", fontsize=11, color=INK)
    axes[1, 0].set_xlabel("时间 (ms)", color=MUTED)
    for axis in axes.flat:
        axis.set_yticks(offsets)
        axis.set_yticklabels([f"Ch {index}" for index in range(raw.shape[1])])
    return fig


def sorting_figure(matches: list[dict], state: ProjectState) -> Figure:
    fig, axes = _base_figure(1, 2, 4.8)
    unit_ids = [item["sorted_unit"] for item in matches]
    f1 = [item["f1"] for item in matches]
    colors = [GREEN if score >= 0.7 else GOLD if score >= 0.4 else CORAL for score in f1]
    axes[0, 0].bar(np.arange(len(f1)), f1, color=colors)
    axes[0, 0].set_ylim(0, 1.05)
    axes[0, 0].set_xticks(np.arange(len(unit_ids)))
    axes[0, 0].set_xticklabels(unit_ids, rotation=60)
    axes[0, 0].set_title("Kilosort结果与ground truth最佳F1", loc="left", fontsize=11, color=INK)
    axes[0, 0].set_xlabel("Kilosort Unit", color=MUTED)
    axes[0, 0].set_ylabel("F1", color=MUTED)

    truth_counts = [len(spikes) for spikes in state.ground_truth.values()]
    sorted_counts = [len(spikes) for spikes in state.sorted_spikes.values()]
    axes[0, 1].boxplot(
        [truth_counts, sorted_counts],
        tick_labels=["Ground truth", "Kilosort4"],
        patch_artist=True,
        boxprops={"facecolor": "#dcece6", "edgecolor": GREEN},
        medianprops={"color": CORAL, "linewidth": 1.8},
    )
    axes[0, 1].set_title("每个Unit的Spike数量分布", loc="left", fontsize=11, color=INK)
    return fig


def unit_metrics_figure(state: ProjectState) -> Figure:
    fig, axes = _base_figure(1, 2, 4.8)
    metrics = state.unit_metrics
    if metrics:
        rates = np.asarray([row["firing_rate_hz"] for row in metrics])
        snr = np.asarray([row["snr"] for row in metrics])
        violations = np.asarray([row["isi_violation_rate"] for row in metrics])
        colors = [GREEN if row["label"] == "候选单神经元" else CORAL for row in metrics]
        axes[0, 0].scatter(rates, snr, c=colors, s=42, edgecolor="white", linewidth=0.7)
        axes[0, 1].bar(np.arange(len(metrics)), violations * 100, color=colors)
    axes[0, 0].set_title("放电率与SNR", loc="left", fontsize=11, color=INK)
    axes[0, 0].set_xlabel("放电率 (Hz)", color=MUTED)
    axes[0, 0].set_ylabel("SNR", color=MUTED)
    axes[0, 1].set_title("不应期违例", loc="left", fontsize=11, color=INK)
    axes[0, 1].set_xlabel("Unit", color=MUTED)
    axes[0, 1].set_ylabel("ISI violation (%)", color=MUTED)
    return fig


def event_analysis_figure(state: ProjectState, unit_id: int | None = None) -> Figure:
    analysis = state.analysis
    if not analysis:
        return raw_overview_figure(state)
    unit_ids = list(analysis["units"])
    if unit_id not in unit_ids:
        unit_id = unit_ids[0]
    unit = analysis["units"][unit_id]
    centers = analysis["bin_centers"]
    fig, axes = _base_figure(2, 2, 6.8)
    raster = axes[0, 0]
    for trial_index, relative in enumerate(unit["aligned_spikes"]):
        raster.vlines(relative, trial_index + 0.6, trial_index + 1.4, color=INK, linewidth=0.65)
    raster.axvline(0, color=CORAL, linewidth=1.2)
    raster.set_title(f"Unit {unit_id} Raster", loc="left", fontsize=11, color=INK)
    raster.set_xlabel("相对事件时间 (s)", color=MUTED)
    raster.set_ylabel("Trial", color=MUTED)

    psth = axes[0, 1]
    psth.plot(centers, unit["condition_a"], color=GREEN, linewidth=1.8, label="条件A")
    psth.plot(centers, unit["condition_b"], color=CORAL, linewidth=1.8, label="条件B")
    psth.axvline(0, color=INK, linewidth=1)
    psth.legend(frameon=False, fontsize=8)
    psth.set_title("条件PSTH", loc="left", fontsize=11, color=INK)
    psth.set_xlabel("相对事件时间 (s)", color=MUTED)
    psth.set_ylabel("放电率 (Hz)", color=MUTED)

    heatmap = axes[1, 0]
    population = np.asarray(analysis["population_z"])
    if population.size:
        order = np.argsort(np.argmax(population, axis=1))
        image = heatmap.imshow(
            population[order],
            aspect="auto",
            interpolation="nearest",
            extent=[centers[0], centers[-1], len(order), 0],
            cmap="RdYlGn",
            vmin=-3,
            vmax=3,
        )
        fig.colorbar(image, ax=heatmap, label="Baseline z-score", shrink=0.75)
    heatmap.axvline(0, color="white", linewidth=1)
    heatmap.set_title("群体响应热图", loc="left", fontsize=11, color=INK)
    heatmap.set_xlabel("相对事件时间 (s)", color=MUTED)
    heatmap.set_ylabel("Unit", color=MUTED)

    summary = axes[1, 1]
    effects = [value["effect_hz"] for value in analysis["units"].values()]
    q_values = [value["q_value"] for value in analysis["units"].values()]
    colors = [GREEN if q < 0.05 else "#b7c2bd" for q in q_values]
    summary.bar(np.arange(len(effects)), effects, color=colors)
    summary.axhline(0, color=INK, linewidth=0.8)
    summary.set_title(
        f"刺激后效应：{analysis['responsive_units']}个Unit通过FDR",
        loc="left",
        fontsize=11,
        color=INK,
    )
    summary.set_xlabel("Unit", color=MUTED)
    summary.set_ylabel("放电率变化 (Hz)", color=MUTED)
    return fig
