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


def _text(state: ProjectState, chinese: str, english: str) -> str:
    return english if state.metadata.get("language") == "en_US" else chinese


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
    if not state.ready:
        unit_ids = sorted(state.sorted_spikes)
        counts = [len(state.sorted_spikes[unit]) for unit in unit_ids]
        axes[0, 0].bar(np.arange(len(unit_ids)), counts, color=GREEN, width=0.75)
        axes[0, 0].set_title("已导入的 Unit 与 spike 数", loc="left", fontsize=11, color=INK)
        axes[0, 0].set_xlabel("Unit", color=MUTED)
        axes[0, 0].set_ylabel("Spike 数", color=MUTED)
        event_times = [float(event["time_seconds"]) for event in state.events]
        axes[1, 0].eventplot(event_times, colors=CORAL, lineoffsets=1, linelengths=0.6)
        axes[1, 0].set_title("可用事件时间轴", loc="left", fontsize=11, color=INK)
        axes[1, 0].set_xlabel("记录时间 (s)", color=MUTED)
        axes[1, 0].set_yticks([])
        return fig
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


def behavior_figure(state: ProjectState) -> Figure:
    fig, axes = _base_figure(1, 2, 4.8)
    trials = state.trials
    if trials and any("contrastLeft" in trial or "contrastRight" in trial for trial in trials):
        signed_contrast = []
        choices = []
        reaction_times = []
        for trial in trials:
            left = trial.get("contrastLeft", np.nan)
            right = trial.get("contrastRight", np.nan)
            left = float(left) if left is not None else np.nan
            right = float(right) if right is not None else np.nan
            contrast = -left if np.isfinite(left) else right if np.isfinite(right) else np.nan
            signed_contrast.append(contrast)
            choices.append(float(trial.get("choice", np.nan)))
            stim = float(trial.get("stimOn_times", np.nan))
            move = float(trial.get("firstMovement_times", np.nan))
            reaction_times.append(move - stim)
        signed = np.asarray(signed_contrast)
        choices_arr = np.asarray(choices)
        reaction = np.asarray(reaction_times)
        levels = np.unique(signed[np.isfinite(signed)])
        choice_fraction = [
            np.nanmean(choices_arr[signed == level] > 0) for level in levels
        ]
        axes[0, 0].plot(levels * 100, choice_fraction, "o-", color=GREEN, linewidth=1.8)
        axes[0, 0].axvline(0, color=INK, linewidth=0.8)
        axes[0, 0].set_title("IBL 风格 psychometric curve", loc="left", fontsize=11, color=INK)
        axes[0, 0].set_xlabel("Signed contrast (%)", color=MUTED)
        axes[0, 0].set_ylabel("P(choice > 0)", color=MUTED)
        reaction_by_level = [
            np.nanmedian(reaction[signed == level]) for level in levels
        ]
        axes[0, 1].plot(levels * 100, reaction_by_level, "o-", color=CORAL, linewidth=1.8)
        axes[0, 1].set_title("反应时与刺激强度", loc="left", fontsize=11, color=INK)
        axes[0, 1].set_xlabel("Signed contrast (%)", color=MUTED)
        axes[0, 1].set_ylabel("Median reaction time (s)", color=MUTED)
    else:
        conditions = [str(event.get("condition", "all")) for event in state.events]
        names, counts = np.unique(conditions, return_counts=True)
        axes[0, 0].bar(names, counts, color=[GREEN, CORAL, GOLD][: len(names)])
        axes[0, 0].set_title("Trial 条件分布", loc="left", fontsize=11, color=INK)
        reaction_times = np.asarray(
            [float(event.get("reaction_time", np.nan)) for event in state.events]
        )
        if np.isfinite(reaction_times).any():
            for color, condition in zip((GREEN, CORAL, GOLD), names):
                mask = np.asarray(conditions) == condition
                axes[0, 1].scatter(
                    np.flatnonzero(mask),
                    reaction_times[mask],
                    color=color,
                    label=condition,
                )
            axes[0, 1].legend(frameon=False, fontsize=8)
            axes[0, 1].set_title("Trial 反应时", loc="left", fontsize=11, color=INK)
            axes[0, 1].set_ylabel("Reaction time (s)", color=MUTED)
        else:
            event_times = np.asarray(
                [float(event["time_seconds"]) for event in state.events]
            )
            axes[0, 1].plot(
                np.arange(len(event_times)),
                event_times,
                "o-",
                color=GREEN,
                label="Event time",
            )
            axes[0, 1].set_title("事件时间与顺序", loc="left", fontsize=11, color=INK)
            axes[0, 1].set_ylabel("记录时间 (s)", color=MUTED)
        axes[0, 1].set_xlabel("Trial", color=MUTED)
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
    sorter_name = state.metadata.get("sorting", {}).get("sorter", "Sorter")
    unit_ids = [item["sorted_unit"] for item in matches]
    f1 = [item["f1"] for item in matches]
    colors = [GREEN if score >= 0.7 else GOLD if score >= 0.4 else CORAL for score in f1]
    axes[0, 0].bar(np.arange(len(f1)), f1, color=colors)
    axes[0, 0].set_ylim(0, 1.05)
    axes[0, 0].set_xticks(np.arange(len(unit_ids)))
    axes[0, 0].set_xticklabels(unit_ids, rotation=60)
    axes[0, 0].set_title(
        f"{sorter_name} vs ground truth · best F1",
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 0].set_xlabel(f"{sorter_name} Unit", color=MUTED)
    axes[0, 0].set_ylabel("F1", color=MUTED)

    truth_counts = [len(spikes) for spikes in state.ground_truth.values()]
    sorted_counts = [len(spikes) for spikes in state.sorted_spikes.values()]
    axes[0, 1].boxplot(
        [truth_counts, sorted_counts],
        tick_labels=["Ground truth", sorter_name],
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
    labels = analysis.get("condition_labels", ["条件A", "条件B"])
    psth.plot(centers, unit["condition_a"], color=GREEN, linewidth=1.8, label=labels[0])
    psth.plot(centers, unit["condition_b"], color=CORAL, linewidth=1.8, label=labels[1])
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


def statistics_figure(state: ProjectState, view: str = "effects") -> Figure:
    fig, axes = _base_figure(1, 2, 4.8)
    rows = state.statistics.get("rows", [])
    if not rows:
        axes[0, 0].text(
            0.5,
            0.5,
            _text(state, "尚未运行统计套件", "Statistical suite has not run"),
            ha="center",
            va="center",
        )
        return fig
    if view == "conditions":
        welch = np.asarray([row["condition_welch_p"] for row in rows], dtype=float)
        mannwhitney = np.asarray(
            [row["condition_mannwhitney_p"] for row in rows], dtype=float
        )
        hedges = np.asarray([row["condition_hedges_g"] for row in rows], dtype=float)
        valid = np.isfinite(welch) & np.isfinite(mannwhitney)
        axes[0, 0].scatter(
            -np.log10(np.maximum(welch[valid], 1e-12)),
            -np.log10(np.maximum(mannwhitney[valid], 1e-12)),
            c=GREEN,
            s=38,
            label="Unit condition tests",
        )
        threshold = -np.log10(0.05)
        axes[0, 0].axvline(threshold, color=CORAL, linestyle="--")
        axes[0, 0].axhline(threshold, color=CORAL, linestyle="--")
        axes[0, 0].set_title(
            _text(state, "Welch t 与 Mann–Whitney U", "Welch t vs Mann–Whitney U"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel("-log10(Welch p)", color=MUTED)
        axes[0, 0].set_ylabel("-log10(Mann–Whitney p)", color=MUTED)
        valid_effect = np.isfinite(hedges)
        axes[0, 1].bar(
            np.arange(np.count_nonzero(valid_effect)),
            hedges[valid_effect],
            color=np.where(hedges[valid_effect] >= 0, GREEN, CORAL),
            label="Hedges g",
        )
        axes[0, 1].axhline(0, color=INK, linewidth=0.8)
        axes[0, 1].set_title(
            _text(state, "条件差异 Hedges g", "Condition effect: Hedges g"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel("Unit", color=MUTED)
        axes[0, 1].set_ylabel("Hedges g", color=MUTED)
        return fig
    if view == "diagnostics":
        shapiro = np.asarray([row["shapiro_p"] for row in rows], dtype=float)
        spearman = np.asarray([row["spearman_trial_r"] for row in rows], dtype=float)
        axes[0, 0].scatter(
            spearman,
            shapiro,
            c=np.where(shapiro < 0.05, CORAL, GREEN),
            s=38,
            label="Unit diagnostic",
        )
        axes[0, 0].axhline(0.05, color=CORAL, linestyle="--")
        axes[0, 0].set_title(
            _text(
                state,
                "正态性与 trial 顺序相关",
                "Normality and trial-order correlation",
            ),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel("Spearman r", color=MUTED)
        axes[0, 0].set_ylabel("Shapiro–Wilk p", color=MUTED)
        mixed = state.statistics.get("mixed_effects", {})
        axes[0, 1].axis("off")
        if mixed.get("available"):
            mixed_text = (
                f"Mixed-effects model\n\n"
                f"{mixed['formula']}\n\n"
                f"coefficient = {mixed['coefficient']:.4g}\n"
                f"p = {mixed['p_value']:.4g}\n"
                f"observations = {mixed['n_observations']}\n"
                f"units/groups = {mixed['groups']}\n"
                f"converged = {mixed['converged']}"
            )
        else:
            mixed_text = (
                "混合效应模型不可用\n\n" if state.metadata.get("language") != "en_US"
                else "Mixed-effects model unavailable\n\n"
            ) + mixed.get("error", "Two usable conditions are required.")
        axes[0, 1].text(
            0.03,
            0.95,
            mixed_text,
            ha="left",
            va="top",
            color=INK,
            fontsize=9,
        )
        return fig
    effects = np.asarray([row["effect_hz"] for row in rows])
    lows = np.asarray([row["ci95_low_hz"] for row in rows])
    highs = np.asarray([row["ci95_high_hz"] for row in rows])
    significant = np.asarray([row["significant_fdr"] for row in rows])
    colors = np.where(significant, GREEN, "#b8c2be")
    x = np.arange(len(rows))
    axes[0, 0].errorbar(
        x,
        effects,
        yerr=np.vstack([effects - lows, highs - effects]),
        fmt="none",
        ecolor="#89958f",
        capsize=2,
        linewidth=0.8,
    )
    axes[0, 0].scatter(
        x, effects, c=colors, s=35, label="Effect and bootstrap CI"
    )
    axes[0, 0].axhline(0, color=INK, linewidth=0.8)
    axes[0, 0].set_title("效应量与 bootstrap 95% CI", loc="left", fontsize=11, color=INK)
    axes[0, 0].set_xlabel("Unit", color=MUTED)
    axes[0, 0].set_ylabel("刺激后变化 (Hz)", color=MUTED)
    p = np.asarray([max(row["permutation_p"], 1e-12) for row in rows])
    q = np.asarray([max(row["fdr_q"], 1e-12) for row in rows])
    axes[0, 1].scatter(
        -np.log10(p),
        -np.log10(q),
        c=colors,
        s=35,
        label="Raw p and FDR q",
    )
    axes[0, 1].axhline(-np.log10(0.05), color=CORAL, linestyle="--")
    axes[0, 1].set_title("置换检验与 FDR 校正", loc="left", fontsize=11, color=INK)
    axes[0, 1].set_xlabel("-log10(raw p)", color=MUTED)
    axes[0, 1].set_ylabel("-log10(FDR q)", color=MUTED)
    return fig


def decoding_figure(state: ProjectState) -> Figure:
    fig, axes = _base_figure(2, 3, 6.8)
    result = state.decoding
    if not result:
        axes[0, 0].text(
            0.5,
            0.5,
            _text(state, "尚未运行解码", "Decoding has not run"),
            ha="center",
            va="center",
        )
        return fig
    matrix = np.asarray(result["confusion_matrix"])
    image = axes[0, 0].imshow(matrix, cmap="Greens")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axes[0, 0].text(column, row, matrix[row, column], ha="center", va="center")
    axes[0, 0].set_xticks(range(len(result["classes"])), result["classes"])
    axes[0, 0].set_yticks(range(len(result["classes"])), result["classes"])
    axes[0, 0].set_title("交叉验证混淆矩阵", loc="left", fontsize=11, color=INK)
    fig.colorbar(image, ax=axes[0, 0], shrink=0.65)
    null = np.asarray(result["null_scores"])
    axes[0, 1].hist(null, bins=22, color="#bac7c1", edgecolor="white")
    axes[0, 1].axvline(result["balanced_accuracy"], color=CORAL, linewidth=2)
    axes[0, 1].set_title(
        f"置换检验 p={result['permutation_p']:.4f}", loc="left", fontsize=11, color=INK
    )
    axes[0, 1].set_xlabel("Balanced accuracy", color=MUTED)
    roc = result["roc_curve"]
    axes[0, 2].plot(
        roc["fpr"],
        roc["tpr"],
        color=GREEN,
        linewidth=1.8,
        label=f"ROC AUC={result['roc_auc']:.3f}",
    )
    axes[0, 2].plot([0, 1], [0, 1], linestyle="--", color=MUTED)
    axes[0, 2].legend(frameon=False, fontsize=8)
    axes[0, 2].set_title(
        f"ROC · F1={result['f1']:.3f}",
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 2].set_xlabel("False positive rate", color=MUTED)
    axes[0, 2].set_ylabel("True positive rate", color=MUTED)
    centers = np.asarray(result["bin_centers"])
    scores = np.asarray(result["time_resolved_accuracy"])
    axes[1, 0].plot(
        centers,
        scores,
        color=GREEN,
        linewidth=1.8,
        label="Time-resolved balanced accuracy",
    )
    axes[1, 0].axhline(0.5, color=MUTED, linestyle="--", linewidth=1)
    axes[1, 0].axvline(0, color=CORAL, linewidth=1)
    axes[1, 0].set_ylim(0.25, 1.02)
    axes[1, 0].set_title("IBL 风格时间分辨解码", loc="left", fontsize=11, color=INK)
    axes[1, 0].set_xlabel("相对事件时间 (s)", color=MUTED)
    axes[1, 0].set_ylabel("Balanced accuracy", color=MUTED)
    trajectories = np.asarray(result["population_trajectories"])
    colors = [GREEN, CORAL]
    for index, label in enumerate(result["classes"]):
        axes[1, 1].plot(
            trajectories[index, :, 0],
            trajectories[index, :, 1]
            if trajectories.shape[2] > 1
            else np.zeros(trajectories.shape[1]),
            color=colors[index],
            label=label,
            linewidth=1.8,
        )
        axes[1, 1].scatter(
            trajectories[index, 0, 0],
            trajectories[index, 0, 1] if trajectories.shape[2] > 1 else 0,
            color=colors[index],
            marker="o",
            s=28,
        )
    axes[1, 1].legend(frameon=False)
    peak_distance = float(np.max(result["trajectory_distance"]))
    axes[1, 1].set_title(
        f"群体 PCA 轨迹 · 最大距离 {peak_distance:.2f}",
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[1, 1].set_xlabel("PC1", color=MUTED)
    axes[1, 1].set_ylabel("PC2", color=MUTED)
    importance = np.asarray(result["feature_importance"])
    order = np.argsort(importance)[::-1][: min(15, len(importance))]
    axes[1, 2].bar(
        np.arange(len(order)),
        importance[order],
        color=GOLD,
        label="Feature importance",
    )
    axes[1, 2].set_xticks(
        np.arange(len(order)),
        [str(result["unit_ids"][index]) for index in order],
        rotation=60,
    )
    cluster = result["cluster_results"]
    axes[1, 2].set_title(
        "Feature importance\n"
        f"K-means ARI={cluster['kmeans_adjusted_rand']:.2f} · "
        f"GMM ARI={cluster['gmm_adjusted_rand']:.2f}",
        loc="left",
        fontsize=10,
        color=INK,
    )
    axes[1, 2].set_xlabel("Unit", color=MUTED)
    axes[1, 2].set_ylabel("Importance", color=MUTED)
    return fig


def regression_figure(state: ProjectState) -> Figure:
    fig, axes = _base_figure(1, 3, 4.8)
    result = state.regression
    if not result:
        axes[0, 0].text(
            0.5,
            0.5,
            _text(state, "尚未运行回归", "Regression has not run"),
            ha="center",
            va="center",
        )
        return fig
    observed = np.asarray(result["observed"])
    predicted = np.asarray(result["predicted"])
    residuals = np.asarray(result["residuals"])
    lower = float(min(observed.min(), predicted.min()))
    upper = float(max(observed.max(), predicted.max()))
    axes[0, 0].scatter(
        observed,
        predicted,
        color=GREEN,
        s=38,
        label="Observed vs predicted",
    )
    axes[0, 0].plot([lower, upper], [lower, upper], "--", color=MUTED)
    axes[0, 0].set_title(
        f"{result['model']} · CV R²={result['r2']:.3f}",
        loc="left",
        fontsize=10,
        color=INK,
    )
    axes[0, 0].set_xlabel("Observed reaction time (s)", color=MUTED)
    axes[0, 0].set_ylabel("Predicted reaction time (s)", color=MUTED)
    axes[0, 1].scatter(
        predicted,
        residuals,
        color=CORAL,
        s=38,
        label="Regression residual",
    )
    axes[0, 1].axhline(0, color=INK, linewidth=0.8)
    axes[0, 1].set_title(
        f"Residuals · MAE={result['mae_seconds']:.3f}s · "
        f"RMSE={result['rmse_seconds']:.3f}s",
        loc="left",
        fontsize=10,
        color=INK,
    )
    axes[0, 1].set_xlabel("Predicted reaction time (s)", color=MUTED)
    axes[0, 1].set_ylabel("Residual (s)", color=MUTED)
    importance = np.asarray(result["feature_importance"])
    order = np.argsort(importance)[::-1][: min(15, len(importance))]
    axes[0, 2].bar(
        np.arange(len(order)),
        importance[order],
        color=GOLD,
        label="Regression feature importance",
    )
    axes[0, 2].set_xticks(
        np.arange(len(order)),
        [str(result["unit_ids"][index]) for index in order],
        rotation=60,
    )
    axes[0, 2].set_title(
        _text(state, "连续变量特征重要性", "Continuous-target feature importance"),
        loc="left",
        fontsize=10,
        color=INK,
    )
    axes[0, 2].set_xlabel("Unit", color=MUTED)
    axes[0, 2].set_ylabel("Importance", color=MUTED)
    return fig
