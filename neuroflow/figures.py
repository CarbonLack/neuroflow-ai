from __future__ import annotations

import re
from itertools import pairwise
from pathlib import Path

import numpy as np
from matplotlib import rcParams
from matplotlib.figure import Figure
from scipy import signal as scipy_signal

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


def _base_figure(
    rows: int = 1, columns: int = 1, height: float = 5.4
) -> tuple[Figure, object]:
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


def pending_step_figure(
    state: ProjectState,
    step_title: str,
    purpose: str,
    inputs: list[str],
    action: str,
) -> Figure:
    fig, axes = _base_figure(1, 1, 5.6)
    axis = axes[0, 0]
    axis.axis("off")
    english = state.metadata.get("language") == "en_US"
    heading = (
        f"{step_title} has not been run"
        if english
        else f"{step_title}尚未运行"
    )
    input_heading = "Current inputs" if english else "当前可用输入"
    action_heading = "Run consequence" if english else "运行后将得到"
    lines = "\n".join(f"• {item}" for item in inputs)
    axis.text(
        0.04,
        0.90,
        heading,
        transform=axis.transAxes,
        va="top",
        fontsize=17,
        fontweight="bold",
        color=INK,
    )
    axis.text(
        0.04,
        0.76,
        purpose,
        transform=axis.transAxes,
        va="top",
        fontsize=11,
        color=INK,
        wrap=True,
    )
    axis.text(
        0.04,
        0.58,
        f"{input_heading}\n{lines}",
        transform=axis.transAxes,
        va="top",
        fontsize=10,
        color=MUTED,
        linespacing=1.5,
    )
    axis.text(
        0.04,
        0.25,
        f"{action_heading}\n{action}",
        transform=axis.transAxes,
        va="top",
        fontsize=10,
        color=GREEN,
        linespacing=1.5,
    )
    return fig


def synchronization_figure(state: ProjectState) -> Figure:
    result = state.metadata.get("synchronization", {})
    if not result:
        events = state.events
        behavior_count = len(events)
        ttl_count = sum(
            "ttl_time_seconds" in event or "ephys_time_seconds" in event
            for event in events
        )
        return pending_step_figure(
            state,
            _text(state, "事件同步", "Synchronization"),
            _text(
                state,
                "把行为设备时间映射到电生理时间，确认事件发生顺序并量化时钟漂移。",
                "Map behavior-device time to electrophysiology time and quantify clock drift.",
            ),
            [
                _text(
                    state,
                    f"行为事件：{behavior_count}",
                    f"Behavior events: {behavior_count}",
                ),
                _text(
                    state,
                    f"带 TTL 时间的事件：{ttl_count}",
                    f"Events with TTL times: {ttl_count}",
                ),
                _text(
                    state,
                    "可在上方导入 behavior CSV 与 TTL CSV",
                    "Import behavior and TTL CSV files above",
                ),
            ],
            _text(
                state,
                "统一 trial 表、线性时钟映射、偏移/漂移、匹配残差和漏配计数。",
                "A unified trial table, linear clock map, offset/drift, residuals, and missing-pulse counts.",
            ),
        )

    fig, axes = _base_figure(2, 2, 6.4)
    behavior = np.asarray(
        [
            float(event.get("behavior_time_seconds", event["time_seconds"]))
            for event in state.events
        ],
        dtype=float,
    )
    ttl = np.asarray(
        [
            float(event.get("ttl_time_seconds", event["time_seconds"]))
            for event in state.events
        ],
        dtype=float,
    )
    predicted = (
        float(result.get("intercept_seconds", 0.0))
        + float(result.get("slope", 1.0)) * behavior
    )
    axes[0, 0].scatter(behavior, ttl, color=GREEN, s=28, label="Paired event")
    if behavior.size:
        order = np.argsort(behavior)
        axes[0, 0].plot(
            behavior[order],
            predicted[order],
            color=CORAL,
            linewidth=1.5,
            label="Linear clock map",
        )
    axes[0, 0].set_title(
        _text(state, "行为时钟 → 电生理时钟", "Behavior clock → ephys clock"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 0].set_xlabel(
        _text(state, "行为时间 (s)", "Behavior time (s)"), color=MUTED
    )
    axes[0, 0].set_ylabel(
        _text(state, "TTL / 电生理时间 (s)", "TTL / ephys time (s)"), color=MUTED
    )
    axes[0, 0].legend(frameon=False, fontsize=8)

    residual = np.asarray(result.get("residual_ms", []), dtype=float)
    axes[0, 1].plot(
        np.arange(1, len(residual) + 1),
        residual,
        "o-",
        color=CORAL,
        linewidth=1.2,
        markersize=4,
    )
    axes[0, 1].axhline(0, color=INK, linewidth=0.8)
    axes[0, 1].set_title(
        _text(state, "逐事件匹配残差", "Per-event matching residual"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 1].set_xlabel("Trial", color=MUTED)
    axes[0, 1].set_ylabel("Residual (ms)", color=MUTED)

    counts = [
        int(result.get("behavior_event_count", 0)),
        int(result.get("ttl_event_count", 0)),
        int(result.get("matched_count", 0)),
    ]
    axes[1, 0].bar(
        ["Behavior", "TTL", "Matched"],
        counts,
        color=[GOLD, CORAL, GREEN],
    )
    axes[1, 0].set_title(
        _text(state, "事件清点与配对", "Event inventory and pairing"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[1, 0].set_ylabel(_text(state, "事件数", "Event count"), color=MUTED)

    axes[1, 1].axis("off")
    summary = [
        f"Status: {result.get('status', 'unknown')}",
        f"Matched: {result.get('matched_count', 0)}",
        f"Missing TTL: {result.get('missing_ttl_events', 0)}",
        f"Missing behavior: {result.get('missing_behavior_events', 0)}",
        f"Offset: {float(result.get('intercept_seconds', 0.0)) * 1000:.3f} ms",
        f"Drift: {float(result.get('drift_ppm', 0.0)):.2f} ppm",
        f"Mean |residual|: {float(result.get('mean_abs_residual_ms', 0.0)):.3f} ms",
        f"Max |residual|: {float(result.get('max_abs_residual_ms', 0.0)):.3f} ms",
    ]
    axes[1, 1].text(
        0.03,
        0.96,
        "\n".join(summary),
        va="top",
        fontsize=10,
        family="monospace",
        color=INK,
    )
    axes[1, 1].set_title(
        _text(state, "同步质量摘要", "Synchronization quality summary"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    return fig


def raw_overview_figure(
    state: ProjectState,
    *,
    start_seconds: float = 2.0,
    window_ms: int = 60,
    first_channel: int = 0,
    visible_channels: int = 8,
    gain: float = 1.0,
    show_ground_truth: bool = True,
) -> Figure:
    fig, axes = _base_figure(2, 1, 6.2)
    if not state.ready:
        unit_ids = sorted(state.sorted_spikes)
        counts = [len(state.sorted_spikes[unit]) for unit in unit_ids]
        axes[0, 0].bar(np.arange(len(unit_ids)), counts, color=GREEN, width=0.75)
        axes[0, 0].set_title(
            _text(
                state, "已导入的 Unit 与 spike 数", "Imported units and spike counts"
            ),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel("Unit", color=MUTED)
        axes[0, 0].set_ylabel(_text(state, "Spike 数", "Spike count"), color=MUTED)
        event_times = [float(event["time_seconds"]) for event in state.events]
        axes[1, 0].eventplot(event_times, colors=CORAL, lineoffsets=1, linelengths=0.6)
        axes[1, 0].set_title(
            _text(state, "可用事件时间轴", "Available event timeline"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[1, 0].set_xlabel(
            _text(state, "记录时间 (s)", "Recording time (s)"), color=MUTED
        )
        axes[1, 0].set_yticks([])
        return fig
    raw = load_recording(state)
    start = int(np.clip(start_seconds, 0, state.duration_seconds) * state.sampling_rate)
    count = max(int(window_ms / 1000.0 * state.sampling_rate), 1)
    stop = min(start + count, raw.shape[0])
    first_channel = int(np.clip(first_channel, 0, state.channel_count - 1))
    last_channel = min(first_channel + max(visible_channels, 1), state.channel_count)
    traces = np.asarray(raw[start:stop, first_channel:last_channel], dtype=np.float32)
    traces *= state.scale_uv_per_bit
    traces -= np.median(traces, axis=0, keepdims=True)
    sample_step = max(int(np.ceil(max(len(traces), 1) / 8000)), 1)
    traces = traces[::sample_step]
    time_ms = (
        np.arange(start, stop, sample_step)[: len(traces)] / state.sampling_rate * 1000
    )
    robust_amplitude = float(np.nanpercentile(np.abs(traces), 99))
    spacing = max(robust_amplitude * 2.6, 25.0)
    offsets = np.arange(traces.shape[1]) * spacing
    for local_index, channel_index in enumerate(range(first_channel, last_channel)):
        line = axes[0, 0].plot(
            time_ms,
            traces[:, local_index] * gain + offsets[local_index],
            linewidth=0.7,
            color=INK,
            picker=3,
            label=f"Ch {channel_index}",
        )[0]
        line.set_gid(
            f"neuroflow-trace:{channel_index}:{offsets[local_index]:.12g}:{gain:.12g}"
        )
    axes[0, 0].set_title(
        _text(
            state,
            f"原始多通道波形 · Ch {first_channel}–{last_channel - 1} · 显示增益 {gain:.1f}x",
            f"Raw multichannel traces · Ch {first_channel}–{last_channel - 1} · display gain {gain:.1f}x",
        ),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 0].set_xlabel(
        _text(state, "记录时间 (ms)", "Recording time (ms)"), color=MUTED
    )
    axes[0, 0].set_yticks(offsets)
    axes[0, 0].set_yticklabels(
        [f"Ch {index}" for index in range(first_channel, last_channel)]
    )
    axes[0, 0].grid(axis="x", color=GRID, linewidth=0.7, alpha=0.65)
    axes[0, 0].grid(axis="y", visible=False)

    counts = [len(spikes) for spikes in state.ground_truth.values()]
    if counts and show_ground_truth:
        axes[1, 0].bar(np.arange(len(counts)), counts, color=GREEN, width=0.68)
        axes[1, 0].set_title(
            _text(
                state,
                "模拟 ground truth（仅用于验证 sorter，不是分析结果）",
                "Simulation ground truth (sorter validation only; not an analysis result)",
            ),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[1, 0].set_xlabel("Ground-truth unit", color=MUTED)
        axes[1, 0].set_ylabel(_text(state, "Spike 数", "Spike count"), color=MUTED)
    else:
        channel_rms = (
            np.sqrt(np.mean(traces**2, axis=0)) if traces.size else np.array([])
        )
        axes[1, 0].bar(
            np.arange(first_channel, last_channel),
            channel_rms,
            color=GREEN,
            width=0.75,
        )
        axes[1, 0].set_title(
            _text(state, "当前窗口的通道 RMS", "Channel RMS in the visible window"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[1, 0].set_xlabel(_text(state, "通道", "Channel"), color=MUTED)
        axes[1, 0].set_ylabel("RMS (µV)", color=MUTED)
    return fig


def behavior_figure(state: ProjectState) -> Figure:
    fig, axes = _base_figure(1, 2, 4.8)
    trials = state.trials
    if trials and any(
        "contrastLeft" in trial or "contrastRight" in trial for trial in trials
    ):
        signed_contrast = []
        choices = []
        reaction_times = []
        for trial in trials:
            left = trial.get("contrastLeft", np.nan)
            right = trial.get("contrastRight", np.nan)
            left = float(left) if left is not None else np.nan
            right = float(right) if right is not None else np.nan
            contrast = (
                -left if np.isfinite(left) else right if np.isfinite(right) else np.nan
            )
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
        axes[0, 0].set_title(
            _text(state, "IBL 风格心理测量曲线", "IBL-style psychometric curve"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel("Signed contrast (%)", color=MUTED)
        axes[0, 0].set_ylabel("P(choice > 0)", color=MUTED)
        reaction_by_level = [
            np.nanmedian(reaction[signed == level]) for level in levels
        ]
        axes[0, 1].plot(
            levels * 100, reaction_by_level, "o-", color=CORAL, linewidth=1.8
        )
        axes[0, 1].set_title(
            _text(state, "反应时与刺激强度", "Reaction time by stimulus strength"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel("Signed contrast (%)", color=MUTED)
        axes[0, 1].set_ylabel("Median reaction time (s)", color=MUTED)
    else:
        conditions = [str(event.get("condition", "all")) for event in state.events]
        names, counts = np.unique(conditions, return_counts=True)
        axes[0, 0].bar(names, counts, color=[GREEN, CORAL, GOLD][: len(names)])
        axes[0, 0].set_title(
            _text(state, "Trial 条件分布", "Trial condition counts"),
            loc="left",
            fontsize=11,
            color=INK,
        )
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
            axes[0, 1].set_title(
                _text(state, "Trial 反应时", "Trial reaction times"),
                loc="left",
                fontsize=11,
                color=INK,
            )
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
            axes[0, 1].set_title(
                _text(state, "事件时间与顺序", "Event time and order"),
                loc="left",
                fontsize=11,
                color=INK,
            )
            axes[0, 1].set_ylabel(
                _text(state, "记录时间 (s)", "Recording time (s)"), color=MUTED
            )
        axes[0, 1].set_xlabel("Trial", color=MUTED)
    return fig


def qc_figure(state: ProjectState) -> Figure:
    fig, axes = _base_figure(1, 2, 4.7)
    rms = np.asarray(state.qc.get("channel_rms", []), dtype=float)
    if rms.size:
        colors = [
            CORAL if index in state.qc.get("bad_channels", []) else GREEN
            for index in range(len(rms))
        ]
        axes[0, 0].bar(np.arange(len(rms)), rms, color=colors, width=0.82)
        axes[0, 0].axhline(
            np.median(rms) * 2.6, color=CORAL, linestyle="--", linewidth=1
        )
    axes[0, 0].set_title(
        _text(state, "各通道 RMS 噪声", "Per-channel RMS noise"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 0].set_xlabel(_text(state, "通道", "Channel"), color=MUTED)
    axes[0, 0].set_ylabel("ADC RMS", color=MUTED)

    labels = (
        ["50 Hz 比值", "坏通道", "饱和样本"]
        if state.metadata.get("language") != "en_US"
        else ["50 Hz ratio", "Bad channels", "Saturated samples"]
    )
    values = [
        state.qc.get("line_noise_ratio", 0),
        len(state.qc.get("bad_channels", [])),
        state.qc.get("saturated_samples", 0),
    ]
    axes[0, 1].barh(labels, values, color=[GOLD, CORAL, GREEN])
    axes[0, 1].set_title(
        _text(state, "主要质控指标", "Primary QC indicators"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    return fig


def qc_diagnostics_figure(state: ProjectState, view: str = "summary") -> Figure:
    if view == "summary":
        return qc_figure(state)
    if view == "psd":
        fig, axes = _base_figure(1, 2, 5.0)
        frequencies = np.asarray(state.qc.get("psd_frequencies_hz", []), dtype=float)
        channel_psd = np.asarray(state.qc.get("channel_psd", []), dtype=float)
        if channel_psd.size:
            image = axes[0, 0].imshow(
                10 * np.log10(np.maximum(channel_psd, 1e-12)),
                aspect="auto",
                interpolation="nearest",
                extent=[frequencies[0], frequencies[-1], len(channel_psd), 0],
                cmap="magma",
            )
            fig.colorbar(image, ax=axes[0, 0], label="Power (dB)", shrink=0.78)
            axes[0, 1].plot(
                frequencies,
                10 * np.log10(np.maximum(np.median(channel_psd, axis=0), 1e-12)),
                color=GREEN,
                linewidth=1.5,
                label="Median across channels",
            )
            axes[0, 1].axvline(50, color=CORAL, linestyle="--", label="50 Hz")
            axes[0, 1].legend(frameon=False, fontsize=8)
        axes[0, 0].set_title(
            _text(state, "通道 × 频率功率图", "Channel-by-frequency power map"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel(_text(state, "频率 (Hz)", "Frequency (Hz)"), color=MUTED)
        axes[0, 0].set_ylabel(_text(state, "通道", "Channel"), color=MUTED)
        axes[0, 1].set_title(
            _text(state, "全通道中位功率谱", "Median power spectrum"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel(_text(state, "频率 (Hz)", "Frequency (Hz)"), color=MUTED)
        axes[0, 1].set_ylabel("Power (dB)", color=MUTED)
        return fig
    fig, axes = _base_figure(1, 2, 5.0)
    timeline = np.asarray(state.qc.get("rms_timeline", []), dtype=float)
    times = np.asarray(state.qc.get("timeline_seconds", []), dtype=float)
    if timeline.size:
        normalized = timeline / np.maximum(np.median(timeline, axis=0), 1e-9)
        image = axes[0, 0].imshow(
            normalized.T,
            aspect="auto",
            interpolation="nearest",
            extent=[times[0], times[-1] + 1, len(normalized.T), 0],
            cmap="viridis",
            vmin=0.5,
            vmax=min(3.0, float(np.nanpercentile(normalized, 98))),
        )
        fig.colorbar(image, ax=axes[0, 0], label="RMS / channel median", shrink=0.78)
    axes[0, 0].set_title(
        _text(state, "记录期间的通道质量", "Channel quality over the recording"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 0].set_xlabel(_text(state, "记录时间 (s)", "Recording time (s)"), color=MUTED)
    axes[0, 0].set_ylabel(_text(state, "通道", "Channel"), color=MUTED)
    labels, counts = np.unique(
        np.asarray(state.qc.get("channel_labels", []), dtype=str), return_counts=True
    )
    axes[0, 1].barh(labels, counts, color=[GREEN, GOLD, CORAL, MUTED][: len(labels)])
    score = float(state.qc.get("quality_score", 0.0))
    axes[0, 1].set_title(
        _text(
            state,
            f"数据健康评分 {score:.1f}/100",
            f"Data health score {score:.1f}/100",
        ),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 1].set_xlabel(_text(state, "通道数", "Channel count"), color=MUTED)
    return fig


def preprocessing_figure(
    preview: dict[str, np.ndarray], language: str = "zh_CN"
) -> Figure:
    fig, axes = _base_figure(2, 1, 5.8)
    time_ms = preview["time_ms"]
    raw = preview["raw"]
    processed = preview["processed"]
    offsets = np.arange(raw.shape[1]) * 650
    axes[0, 0].plot(time_ms, raw + offsets, color=MUTED, linewidth=0.55)
    english = language == "en_US"
    axes[0, 0].set_title(
        "Before preprocessing" if english else "处理前",
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[1, 0].plot(time_ms, processed + offsets, color=GREEN, linewidth=0.55)
    axes[1, 0].set_title(
        "300–6000 Hz + common median reference preview"
        if english
        else "300–6000 Hz + common median reference 预览",
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[1, 0].set_xlabel("Time (ms)" if english else "时间 (ms)", color=MUTED)
    for axis in axes.flat:
        axis.set_yticks(offsets)
        axis.set_yticklabels([f"Ch {index}" for index in range(raw.shape[1])])
    return fig


def preprocessing_diagnostics_figure(
    preview: dict[str, np.ndarray],
    state: ProjectState,
    view: str = "ap",
) -> Figure:
    if view == "ap":
        fig, axes = _base_figure(2, 1, 5.8)
        time_ms = np.asarray(preview["time_ms"], dtype=float)
        visible = time_ms <= time_ms[0] + 80.0
        raw = np.asarray(preview["raw"])[visible]
        processed = np.asarray(preview["processed"])[visible]
        shown_time = time_ms[visible]
        offsets = np.arange(raw.shape[1]) * 650
        axes[0, 0].plot(shown_time, raw + offsets, color=MUTED, linewidth=0.55)
        axes[1, 0].plot(shown_time, processed + offsets, color=GREEN, linewidth=0.55)
        axes[0, 0].set_title(
            _text(state, "AP 分支：处理前", "AP branch: before preprocessing"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[1, 0].set_title(
            _text(
                state,
                "AP 分支：300-6000 Hz + common median reference",
                "AP branch: 300-6000 Hz + common median reference",
            ),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[1, 0].set_xlabel(_text(state, "时间 (ms)", "Time (ms)"), color=MUTED)
        for axis in axes.flat:
            axis.set_yticks(offsets)
            axis.set_yticklabels([f"Ch {index}" for index in range(raw.shape[1])])
        return fig
    if view == "lfp":
        fig, axes = _base_figure(1, 2, 5.0)
        lfp = np.asarray(preview["lfp"], dtype=float)
        times = np.asarray(preview["lfp_time_s"], dtype=float)
        channels = min(4, lfp.shape[1])
        scale = max(float(np.nanpercentile(np.abs(lfp[:, :channels]), 98)) * 2.5, 10)
        offsets = np.arange(channels) * scale
        axes[0, 0].plot(
            times,
            lfp[:, :channels] + offsets,
            color=GREEN,
            linewidth=0.6,
        )
        frequencies, power = np.array([]), np.empty((0, 0))
        if len(lfp):
            frequencies, power = scipy_signal.welch(
                lfp[:, :channels],
                fs=float(preview["lfp_sampling_rate_hz"]),
                nperseg=min(1024, len(lfp)),
                axis=0,
            )
        if power.size:
            axes[0, 1].plot(
                frequencies,
                10 * np.log10(np.maximum(power, 1e-12)),
                linewidth=1.0,
            )
            axes[0, 1].set_xlim(0, min(150, frequencies[-1]))
        axes[0, 0].set_title(
            _text(state, "LFP 分支波形预览", "LFP branch trace preview"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel(_text(state, "时间 (s)", "Time (s)"), color=MUTED)
        axes[0, 0].set_yticks(offsets)
        axes[0, 0].set_yticklabels([f"Ch {index}" for index in range(channels)])
        axes[0, 1].set_title(
            _text(state, "LFP 分支功率谱", "LFP branch power spectrum"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel(_text(state, "频率 (Hz)", "Frequency (Hz)"), color=MUTED)
        axes[0, 1].set_ylabel("Power (dB)", color=MUTED)
        return fig
    fig, axes = _base_figure(1, 2, 5.2)
    axes[0, 0].axis("off")
    pipeline = preview.get("pipeline", [])
    y = 0.92
    for index, step in enumerate(pipeline, start=1):
        text = (
            f"{index:02d}  {step['branch']}\n"
            f"{step['step']}\n"
            + " · ".join(
                f"{key}={value}" for key, value in step["parameters"].items()
            )
        )
        axes[0, 0].text(
            0.03,
            y,
            text,
            va="top",
            fontsize=9,
            color=INK,
            bbox={
                "boxstyle": "round,pad=0.45,rounding_size=0.15",
                "facecolor": "#eef5f2",
                "edgecolor": "#b9cdc4",
            },
        )
        y -= 0.28
    axes[0, 0].set_title(
        _text(state, "可审计预处理链", "Auditable preprocessing chain"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 1].axis("off")
    guardrails = preview.get("guardrails", [])
    axes[0, 1].text(
        0.02,
        0.95,
        _text(state, "运行前安全检查", "Pre-run safeguards")
        + "\n\n"
        + "\n\n".join(f"{index}. {item}" for index, item in enumerate(guardrails, 1)),
        va="top",
        fontsize=9,
        color=INK,
        wrap=True,
    )
    return fig


def sorting_figure(matches: list[dict], state: ProjectState) -> Figure:
    fig, axes = _base_figure(1, 2, 4.8)
    sorter_name = state.metadata.get("sorting", {}).get("sorter", "Sorter")
    unit_ids = [item["sorted_unit"] for item in matches]
    f1 = [item["f1"] for item in matches]
    colors = [
        GREEN if score >= 0.7 else GOLD if score >= 0.4 else CORAL for score in f1
    ]
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
    axes[0, 1].set_title(
        _text(
            state, "每个 Unit 的 spike 数量分布", "Spike-count distribution per unit"
        ),
        loc="left",
        fontsize=11,
        color=INK,
    )
    return fig


def sorting_comparison_figure(state: ProjectState) -> Figure:
    comparison = state.sorting_comparison
    fig, axes = _base_figure(1, 3, 3.2)
    if not comparison or not comparison.get("sorters"):
        for axis in axes.flat:
            axis.axis("off")
        axes[0, 0].text(
            0.02,
            0.9,
            _text(
                state,
                "尚无可比较的统一 sorting 结果",
                "No normalized sorting results are available for comparison",
            ),
            va="top",
            fontsize=15,
            color=INK,
        )
        axes[0, 0].text(
            0.02,
            0.7,
            _text(
                state,
                "运行一个 sorter 可与模拟真值比较；运行两个或更多 sorter "
                "可查看算法间匹配、独有 Unit 与共识 Unit。",
                "Run one sorter for simulated ground-truth validation, or two or "
                "more sorters for matched, unique, and consensus units.",
            ),
            va="top",
            fontsize=10,
            color=MUTED,
            wrap=True,
        )
        return fig

    sorters = comparison["sorters"]
    keys = list(sorters)
    units = [sorters[key]["unit_count"] for key in keys]
    spikes = [sorters[key]["spike_count"] for key in keys]
    x = np.arange(len(keys))
    ground_truth = comparison.get("ground_truth", {})
    if ground_truth:
        metric_names = ("mean_precision", "mean_recall", "mean_f1")
        labels = ("Precision", "Recall", "F1")
        width = 0.22
        for index, (metric, label) in enumerate(zip(metric_names, labels, strict=True)):
            axes[0, 0].bar(
                x + (index - 1) * width,
                [ground_truth[key][metric] for key in keys],
                width=width,
                label=label,
                color=(GREEN, GOLD, CORAL)[index],
            )
        axes[0, 0].set_ylim(0, 1.05)
        axes[0, 0].set_ylabel("Score", color=MUTED)
        axes[0, 0].set_title(
            _text(
                state,
                "仅模拟真值：准确性指标",
                "Ground truth only: performance",
            ),
            loc="left",
            fontsize=10,
            color=INK,
        )
        axes[0, 0].legend(frameon=False, fontsize=7, ncols=3)
    else:
        axes[0, 0].bar(x - 0.18, units, width=0.36, color=GREEN, label="Units")
        spike_scale = max(max(spikes, default=1) / max(max(units, default=1), 1), 1)
        axes[0, 0].bar(
            x + 0.18,
            np.asarray(spikes) / spike_scale,
            width=0.36,
            color=GOLD,
            label=f"Spikes / {spike_scale:.0f}",
        )
        axes[0, 0].set_ylabel(
            _text(state, "归一化数量", "Normalized count"), color=MUTED
        )
        axes[0, 0].set_title(
            _text(state, "统一结果规模", "Normalized result size"),
            loc="left",
            fontsize=10,
            color=INK,
        )
        axes[0, 0].legend(frameon=False, fontsize=7)
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(keys, rotation=18, ha="right", fontsize=8)

    agreement = np.eye(len(keys), dtype=float)
    for row in comparison.get("pairwise", []):
        i = keys.index(row["sorter_a"])
        j = keys.index(row["sorter_b"])
        agreement[i, j] = agreement[j, i] = row["mean_matched_agreement"]
    axes[0, 1].imshow(
        agreement,
        cmap="viridis",
        vmin=0,
        vmax=1,
        interpolation="nearest",
    )
    for i in range(len(keys)):
        for j in range(len(keys)):
            axes[0, 1].text(
                j,
                i,
                f"{agreement[i, j]:.2f}",
                ha="center",
                va="center",
                color="white" if agreement[i, j] < 0.65 else INK,
                fontsize=8,
            )
    axes[0, 1].set_xticks(np.arange(len(keys)), keys, rotation=25, ha="right")
    axes[0, 1].set_yticks(np.arange(len(keys)), keys)
    axes[0, 1].set_title(
        _text(state, "匹配 Unit 的平均一致度", "Mean agreement of matched units"),
        loc="left",
        fontsize=10,
        color=INK,
    )

    axes[0, 2].axis("off")
    consensus = comparison.get("consensus", {})
    result_lines = [
        f"{key}: {sorters[key]['unit_count']} U / {sorters[key]['spike_count']} spikes"
        for key in keys
    ]
    pair_lines = [
        (
            f"{row['sorter_a']} / {row['sorter_b']}: "
            f"{row['matched_unit_count']} match | "
            f"{row['unique_units_a']}/{row['unique_units_b']} unique"
        )
        for row in comparison.get("pairwise", [])
    ]
    consensus_line = (
        f"Consensus ≥{consensus.get('minimum_agreement_count', 2)}: "
        f"{consensus.get('unit_count', 0)} U / "
        f"{consensus.get('spike_count', 0)} spikes"
        if consensus
        else _text(state, "至少需要两个结果计算共识", "At least two results are required")
    )
    axes[0, 2].text(
        0.02,
        0.95,
        _text(state, "匹配摘要", "Matching summary"),
        va="top",
        fontsize=10,
        fontweight="bold",
        color=INK,
    )
    axes[0, 2].text(
        0.02,
        0.82,
        "\n".join(result_lines),
        va="top",
        fontsize=7.8,
        color=INK,
        wrap=True,
    )
    axes[0, 2].text(
        0.02,
        0.54,
        consensus_line,
        va="top",
        fontsize=7.8,
        color=INK,
        wrap=True,
    )
    axes[0, 2].text(
        0.02,
        0.38,
        "\n".join(pair_lines[:4]),
        va="top",
        fontsize=7.2,
        color=INK,
    )
    axes[0, 2].text(
        0.02,
        0.04,
        _text(
            state,
            "一致度不是生物学真值；仍需波形、ISI、漂移与人工复核。",
            "Agreement is not ground truth.\nReview waveform, ISI, drift, and units manually.",
        ),
        va="bottom",
        fontsize=7.2,
        color=CORAL,
    )
    return fig


def _sorting_result_dir(state: ProjectState) -> Path | None:
    value = state.metadata.get("sorting", {}).get("result_directory")
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None


def _load_npy(root: Path, name: str) -> np.ndarray | None:
    candidates = [root / name, *root.rglob(name)]
    for path in candidates:
        if path.exists():
            try:
                return np.load(path, allow_pickle=True)
            except (OSError, ValueError):
                return None
    return None


def sorting_diagnostics_figure(state: ProjectState, view: str = "pipeline") -> Figure:
    if view == "comparison":
        return sorting_comparison_figure(state)
    root = _sorting_result_dir(state)
    if root is None:
        fig, axes = _base_figure(1, 1, 5.6)
        axis = axes[0, 0]
        axis.axis("off")
        axis.text(
            0.5,
            0.56,
            _text(
                state,
                "尚无 sorting 输出",
                "No sorting output is available",
            ),
            ha="center",
            va="center",
            fontsize=15,
            color=INK,
        )
        axis.text(
            0.5,
            0.43,
            _text(
                state,
                "先在上方选择 sorter、核对参数，再点击“运行当前节点”。",
                "Select a sorter, verify parameters, then run the current stage.",
            ),
            ha="center",
            va="center",
            fontsize=10,
            color=MUTED,
        )
        return fig

    if view == "drift":
        fig, axes = _base_figure(1, 2, 5.4)
        spike_times = _load_npy(root, "spike_times.npy")
        positions = _load_npy(root, "spike_positions.npy")
        amplitudes = _load_npy(root, "amplitudes.npy")
        clusters = _load_npy(root, "spike_clusters.npy")
        if spike_times is None:
            return sorting_diagnostics_figure(state, "pipeline")
        times = np.asarray(spike_times).reshape(-1) / state.sampling_rate
        if positions is not None and np.asarray(positions).ndim == 2:
            depth = np.asarray(positions)[:, 1]
        elif clusters is not None:
            depth = np.asarray(clusters).reshape(-1).astype(float)
        else:
            depth = np.zeros_like(times)
        amp = (
            np.asarray(amplitudes).reshape(-1)
            if amplitudes is not None
            else np.ones_like(times)
        )
        usable = min(len(times), len(depth), len(amp))
        times, depth, amp = times[:usable], depth[:usable], amp[:usable]
        step = max(int(np.ceil(max(usable, 1) / 30_000)), 1)
        points = axes[0, 0].scatter(
            times[::step],
            depth[::step],
            c=amp[::step],
            s=4,
            alpha=0.45,
            cmap="viridis",
            linewidths=0,
        )
        fig.colorbar(
            points,
            ax=axes[0, 0],
            label=_text(state, "Spike 振幅", "Spike amplitude"),
            shrink=0.78,
        )
        axes[0, 0].set_title(
            _text(state, "Spike 深度-时间图", "Spike depth-time map"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel(_text(state, "时间 (s)", "Time (s)"), color=MUTED)
        axes[0, 0].set_ylabel(
            _text(state, "探针深度 (µm)", "Probe depth (µm)"), color=MUTED
        )
        if usable:
            edges = np.linspace(0, max(float(times.max()), 1e-6), 31)
            centers = (edges[:-1] + edges[1:]) / 2
            medians = np.array(
                [
                    np.nanmedian(depth[(times >= left) & (times < right)])
                    for left, right in pairwise(edges)
                ]
            )
            axes[0, 1].plot(centers, medians, "o-", color=CORAL, linewidth=1.5)
        axes[0, 1].set_title(
            _text(state, "分箱中位深度（漂移线索）", "Binned median depth (drift cue)"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel(_text(state, "时间 (s)", "Time (s)"), color=MUTED)
        axes[0, 1].set_ylabel(
            _text(state, "中位深度 (µm)", "Median depth (µm)"), color=MUTED
        )
        return fig

    if view == "amplitudes":
        fig, axes = _base_figure(1, 2, 5.4)
        spike_times = _load_npy(root, "spike_times.npy")
        amplitudes = _load_npy(root, "amplitudes.npy")
        clusters = _load_npy(root, "spike_clusters.npy")
        if spike_times is None or amplitudes is None:
            return sorting_diagnostics_figure(state, "pipeline")
        times = np.asarray(spike_times).reshape(-1) / state.sampling_rate
        amp = np.asarray(amplitudes).reshape(-1)
        clu = (
            np.asarray(clusters).reshape(-1)
            if clusters is not None
            else np.zeros_like(times)
        )
        usable = min(len(times), len(amp), len(clu))
        times, amp, clu = times[:usable], amp[:usable], clu[:usable]
        step = max(int(np.ceil(max(usable, 1) / 30_000)), 1)
        axes[0, 0].scatter(
            times[::step],
            amp[::step],
            c=clu[::step],
            s=4,
            alpha=0.4,
            cmap="turbo",
            linewidths=0,
        )
        axes[0, 0].set_title(
            _text(state, "Spike 振幅随时间", "Spike amplitude over time"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel(_text(state, "时间 (s)", "Time (s)"), color=MUTED)
        axes[0, 0].set_ylabel(_text(state, "振幅", "Amplitude"), color=MUTED)
        unit_ids = np.unique(clu)
        cv = np.asarray(
            [
                np.nanstd(amp[clu == unit]) / max(np.nanmean(amp[clu == unit]), 1e-9)
                for unit in unit_ids
            ]
        )
        axes[0, 1].bar(np.arange(len(unit_ids)), cv, color=GREEN)
        axes[0, 1].set_title(
            _text(
                state, "Unit 振幅变异系数", "Unit amplitude coefficient of variation"
            ),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel("Unit", color=MUTED)
        axes[0, 1].set_ylabel("CV", color=MUTED)
        return fig

    if view == "templates":
        fig, axes = _base_figure(1, 2, 5.4)
        templates = _load_npy(root, "templates.npy")
        channel_positions = _load_npy(root, "channel_positions.npy")
        if templates is None or np.asarray(templates).ndim != 3:
            return sorting_diagnostics_figure(state, "pipeline")
        templates = np.asarray(templates)
        count = min(12, templates.shape[0])
        time_ms = (
            (np.arange(templates.shape[1]) - templates.shape[1] // 2)
            / state.sampling_rate
            * 1000
        )
        peaks = np.max(np.abs(templates), axis=1)
        best_channels = np.argmax(peaks, axis=1)
        for unit in range(count):
            axes[0, 0].plot(
                time_ms,
                templates[unit, :, best_channels[unit]],
                linewidth=1.0,
                alpha=0.8,
                label=f"U{unit}",
            )
        axes[0, 0].set_title(
            _text(state, "峰值通道模板波形", "Template waveform on peak channel"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel(_text(state, "时间 (ms)", "Time (ms)"), color=MUTED)
        axes[0, 0].set_ylabel(
            _text(state, "白化模板幅值", "Whitened template amplitude"), color=MUTED
        )
        if count <= 8:
            axes[0, 0].legend(frameon=False, fontsize=7, ncols=2)
        mean_peak = peaks[:count].max(axis=0)
        if channel_positions is not None and np.asarray(channel_positions).shape[
            0
        ] == len(mean_peak):
            positions = np.asarray(channel_positions)
            points = axes[0, 1].scatter(
                positions[:, 0],
                positions[:, 1],
                c=mean_peak,
                s=70,
                cmap="magma",
                edgecolor="white",
            )
            fig.colorbar(points, ax=axes[0, 1], label="Peak |template|", shrink=0.78)
            axes[0, 1].set_xlabel("x (µm)", color=MUTED)
            axes[0, 1].set_ylabel(_text(state, "深度 (µm)", "Depth (µm)"), color=MUTED)
        else:
            axes[0, 1].plot(np.arange(len(mean_peak)), mean_peak, color=CORAL)
            axes[0, 1].set_xlabel(_text(state, "通道", "Channel"), color=MUTED)
        axes[0, 1].set_title(
            _text(state, "模板空间足迹", "Template spatial footprint"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        return fig

    if view == "similarity":
        fig, axes = _base_figure(1, 2, 5.4)
        similarity = _load_npy(root, "similar_templates.npy")
        if similarity is not None and np.asarray(similarity).ndim == 2:
            image = axes[0, 0].imshow(
                similarity,
                aspect="auto",
                interpolation="nearest",
                cmap="viridis",
                vmin=0,
                vmax=1,
            )
            fig.colorbar(
                image, ax=axes[0, 0], label="Template correlation", shrink=0.78
            )
        axes[0, 0].set_title(
            _text(state, "模板相似度矩阵", "Template similarity matrix"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel("Unit", color=MUTED)
        axes[0, 0].set_ylabel("Unit", color=MUTED)
        contamination_file = next(iter(root.rglob("cluster_ContamPct.tsv")), None)
        if contamination_file:
            try:
                table = np.genfromtxt(
                    contamination_file,
                    delimiter="\t",
                    names=True,
                    dtype=None,
                    encoding="utf-8",
                )
                values = np.atleast_1d(table[table.dtype.names[-1]]).astype(float)
                axes[0, 1].bar(np.arange(len(values)), values, color=CORAL)
            except (OSError, ValueError, IndexError):
                pass
        axes[0, 1].set_title(
            _text(state, "Kilosort 估计污染率", "Kilosort estimated contamination"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel("Unit", color=MUTED)
        axes[0, 1].set_ylabel(
            _text(state, "污染率 (%)", "Contamination (%)"), color=MUTED
        )
        return fig

    if view == "files":
        fig, axes = _base_figure(1, 1, 6.0)
        axis = axes[0, 0]
        axis.axis("off")
        meanings = {
            "spike_times.npy": "waveform peak sample for every spike",
            "spike_clusters.npy": "cluster assignment for every spike",
            "spike_positions.npy": "estimated x/y probe position per spike",
            "amplitudes.npy": "L2 PC-feature amplitude per spike",
            "templates.npy": "mean whitened waveform per cluster",
            "similar_templates.npy": "pairwise template correlation",
            "ops.npy": "settings and algorithm state",
            "cluster_ContamPct.tsv": "estimated refractory contamination",
            "cluster_KSLabel.tsv": "Kilosort good/mua label",
            "params.py": "Phy dataset configuration",
            "kilosort4.log": "full algorithm and resource log",
        }
        lines = []
        for path in sorted(root.iterdir()):
            if not path.is_file():
                continue
            size = path.stat().st_size / 1024
            meaning = meanings.get(path.name, "supporting output")
            lines.append(f"{path.name:<28} {size:>9.1f} KB   {meaning}")
        axis.text(
            0.01,
            0.98,
            _text(
                state,
                "真实输出目录与文件含义",
                "Real output directory and file meanings",
            ),
            va="top",
            fontsize=13,
            fontweight="bold",
            color=INK,
        )
        axis.text(
            0.01,
            0.91,
            f"{root}\n\n" + "\n".join(lines[:24]),
            va="top",
            family="monospace",
            fontsize=8.5,
            color=INK,
        )
        return fig

    sorting = state.metadata.get("sorting", {})
    sorter_name = str(
        sorting.get("sorter")
        or sorting.get("sorter_key")
        or state.active_sorter_key
        or "unknown"
    )
    is_kilosort = "kilosort" in sorter_name.lower()
    if view == "pipeline" and not is_kilosort:
        fig, axes = _base_figure(1, 2, 5.4)
        unit_ids = sorted(state.sorted_spikes)
        spike_counts = np.asarray(
            [len(state.sorted_spikes[unit]) for unit in unit_ids], dtype=float
        )
        rates = spike_counts / max(state.duration_seconds, 1e-9)
        axes[0, 0].bar(np.arange(len(unit_ids)), rates, color=GREEN)
        axes[0, 0].set_title(
            _text(
                state,
                f"{sorter_name} 统一结果",
                f"{sorter_name} normalized result",
            ),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel("Unit", color=MUTED)
        axes[0, 0].set_ylabel(
            _text(state, "放电率 (Hz)", "Firing rate (Hz)"), color=MUTED
        )
        axes[0, 1].axis("off")
        provenance = state.sorting_provenance.get(
            str(state.active_sorter_key), sorting
        )
        settings = provenance.get("settings", {})
        lines = [
            f"Sorter: {sorter_name}",
            f"Key: {state.active_sorter_key or provenance.get('sorter_key', 'unknown')}",
            f"Backend: {provenance.get('backend', 'unknown')}",
            f"Version: {provenance.get('version', 'unknown')}",
            f"Units: {len(unit_ids)}",
            f"Spikes: {int(spike_counts.sum())}",
            f"Time unit: {provenance.get('time_unit', 'seconds')}",
            "",
            "Parameters:",
            *[f"{key}: {value}" for key, value in settings.items()],
        ]
        axes[0, 1].text(
            0.02,
            0.98,
            "\n".join(lines),
            va="top",
            fontsize=9,
            family="monospace",
            color=INK,
        )
        axes[0, 1].set_title(
            _text(
                state,
                "实际运行来源、参数与统一接口",
                "Actual run provenance, parameters, and normalized interface",
            ),
            loc="left",
            fontsize=11,
            color=INK,
        )
        return fig

    fig, axes = _base_figure(1, 2, 5.4)
    log_file = next(iter(root.rglob("kilosort4.log")), None)
    stages: list[str] = []
    durations: list[float] = []
    log_tail = ""
    if log_file:
        text = log_file.read_text(encoding="utf-8", errors="replace")
        summary_pattern = re.compile(
            r"INFO\s+(?P<stage>preprocessing|drift corr|spike det\. \(univ\)|"
            r"cluster \(temp\)|spike det\. \(learn\)|cluster \(final\)|"
            r"cluster merge|postprocessing):\s+(?P<seconds>[0-9.]+)s"
        )
        for match in summary_pattern.finditer(text):
            stages.append(match.group("stage"))
            durations.append(float(match.group("seconds")))
        pattern = re.compile(
            r"(?P<stage>[A-Za-z][A-Za-z -]+?) (?:computed|extracted|completed) "
            r"in (?P<seconds>[0-9.]+)s"
        )
        if not stages:
            for match in pattern.finditer(text):
                stages.append(match.group("stage").strip())
                durations.append(float(match.group("seconds")))
        log_tail = "\n".join(text.splitlines()[-14:])
    if stages:
        axes[0, 0].barh(stages[-10:], durations[-10:], color=GREEN)
        axes[0, 0].set_xlabel(
            _text(state, "阶段耗时 (s)", "Stage time (s)"), color=MUTED
        )
    axes[0, 0].set_title(
        _text(
            state,
            f"{sorter_name} 运行阶段",
            f"{sorter_name} pipeline stages",
        ),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 1].axis("off")
    settings = sorting.get("settings", {})
    summary = sorting.get("runtime_summary", {})
    header = [
        f"Sorter: {sorting.get('sorter', 'unknown')}",
        f"Version: {sorting.get('version', 'unknown')}",
        f"Device: {sorting.get('device', sorting.get('backend', 'unknown'))}",
        f"Units: {len(state.sorted_spikes)}",
        f"Spikes: {sum(len(value) for value in state.sorted_spikes.values())}",
        f"batch_size: {settings.get('batch_size', 'default')}",
        f"nblocks: {settings.get('nblocks', 'default')}",
        (
            f"Th_universal / learned: {settings.get('Th_universal', 'default')} / "
            f"{settings.get('Th_learned', 'default')}"
        ),
    ]
    if summary:
        header.extend(
            [
                f"Refractory clusters: {summary.get('refractory_cluster_count', 'n/a')}",
                f"Median contamination: {summary.get('median_contamination', float('nan')):.3f}",
                f"Kept spike fraction: {summary.get('kept_spike_fraction', float('nan')):.3f}",
            ]
        )
    axes[0, 1].text(
        0.01,
        0.98,
        "\n".join(header) + ("\n\nLog tail:\n" + log_tail if log_tail else ""),
        va="top",
        fontsize=8.5,
        color=INK,
        family="monospace",
    )
    axes[0, 1].set_title(
        _text(state, "参数、结果与日志尾部", "Parameters, results, and log tail"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    return fig


def unit_metrics_figure(state: ProjectState, view: str = "overview") -> Figure:
    if view.startswith("unit:"):
        unit_id = int(view.split(":", 1)[1])
        diagnostic = state.unit_diagnostics.get(unit_id, {})
        if diagnostic:
            fig, axes = _base_figure(2, 2, 6.4)
            waveform = np.asarray(diagnostic["waveform"], dtype=float)
            waveform_time = np.asarray(diagnostic["waveform_time_ms"], dtype=float)
            for index, channel in enumerate(diagnostic["waveform_channels"]):
                axes[0, 0].plot(
                    waveform_time,
                    waveform[:, index],
                    linewidth=1.2,
                    label=f"Ch {channel}",
                )
            axes[0, 0].legend(frameon=False, fontsize=7, ncols=2)
            axes[0, 0].set_title(
                _text(
                    state,
                    f"Unit {unit_id} 平均波形",
                    f"Unit {unit_id} mean waveform",
                ),
                loc="left",
                fontsize=11,
                color=INK,
            )
            axes[0, 0].set_xlabel("Time (ms)", color=MUTED)
            axes[0, 0].set_ylabel("ADC", color=MUTED)
            axes[0, 1].bar(
                diagnostic["acg_lags_ms"],
                diagnostic["acg_counts"],
                width=0.9,
                color=GREEN,
            )
            axes[0, 1].axvspan(0, 1.5, color=CORAL, alpha=0.18)
            axes[0, 1].set_title(
                _text(state, "自相关与不应期", "Autocorrelation and refractory period"),
                loc="left",
                fontsize=11,
                color=INK,
            )
            axes[0, 1].set_xlabel("Lag (ms)", color=MUTED)
            isi_values = np.asarray(diagnostic["isi_ms"], dtype=float)
            axes[1, 0].hist(
                isi_values[(isi_values > 0) & (isi_values <= 100)],
                bins=np.arange(0, 102, 2),
                color=GOLD,
            )
            axes[1, 0].axvline(1.5, color=CORAL, linestyle="--")
            axes[1, 0].set_title(
                _text(state, "ISI 分布", "ISI distribution"),
                loc="left",
                fontsize=11,
                color=INK,
            )
            axes[1, 0].set_xlabel("ISI (ms)", color=MUTED)
            axes[1, 1].plot(
                diagnostic["stability_time_s"],
                diagnostic["stability_rate_hz"],
                color=GREEN,
                linewidth=1.4,
                label="Firing rate",
            )
            if diagnostic["amplitude_time_s"]:
                secondary = axes[1, 1].twinx()
                secondary.scatter(
                    diagnostic["amplitude_time_s"],
                    diagnostic["amplitude_adc"],
                    s=8,
                    alpha=0.35,
                    color=CORAL,
                    label="Spike amplitude",
                )
                secondary.set_ylabel("Amplitude (ADC)", color=CORAL)
            axes[1, 1].set_title(
                _text(state, "时间稳定性", "Stability over time"),
                loc="left",
                fontsize=11,
                color=INK,
            )
            axes[1, 1].set_xlabel(_text(state, "时间 (s)", "Time (s)"), color=MUTED)
            axes[1, 1].set_ylabel("Rate (Hz)", color=MUTED)
            return fig
    fig, axes = _base_figure(1, 2, 4.8)
    metrics = state.unit_metrics
    if metrics:
        rates = np.asarray([row["firing_rate_hz"] for row in metrics])
        snr = np.asarray([row["snr"] for row in metrics])
        violations = np.asarray([row["isi_violation_rate"] for row in metrics])
        colors = [GREEN if row["label"] == "候选单神经元" else CORAL for row in metrics]
        axes[0, 0].scatter(rates, snr, c=colors, s=42, edgecolor="white", linewidth=0.7)
        axes[0, 1].bar(np.arange(len(metrics)), violations * 100, color=colors)
    axes[0, 0].set_title(
        _text(state, "放电率与 SNR", "Firing rate and SNR"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 0].set_xlabel(_text(state, "放电率 (Hz)", "Firing rate (Hz)"), color=MUTED)
    axes[0, 0].set_ylabel("SNR", color=MUTED)
    axes[0, 1].set_title(
        _text(state, "不应期违例", "Refractory-period violations"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 1].set_xlabel("Unit", color=MUTED)
    axes[0, 1].set_ylabel("ISI violation (%)", color=MUTED)
    return fig


def neural_toolkit_figure(state: ProjectState, view: str) -> Figure:
    if view.startswith("event:"):
        return event_analysis_figure(state, int(view.split(":", 1)[1]))
    if view == "spike:statistics":
        fig, axes = _base_figure(2, 2, 6.4)
        rows = state.spike_train_analysis.get("rows", [])
        if rows:
            rates = np.asarray([row["rate_hz"] for row in rows], dtype=float)
            cv2_values = np.asarray([row["cv2"] for row in rows], dtype=float)
            fano = np.asarray([row["fano_trials"] for row in rows], dtype=float)
            lv_values = np.asarray([row["lv"] for row in rows], dtype=float)
            ids = np.asarray([row["unit_id"] for row in rows], dtype=int)
            axes[0, 0].scatter(rates, cv2_values, c=ids, cmap="viridis", s=48)
            axes[0, 1].bar(ids, fano, color=GOLD)
            axes[1, 0].scatter(lv_values, cv2_values, c=rates, cmap="magma", s=48)
            cch = state.spike_train_analysis.get("cch", {})
            axes[1, 1].bar(
                cch.get("lags_ms", []),
                cch.get("counts", []),
                width=4.2,
                color=GREEN,
            )
        axes[0, 0].set_title("Rate vs CV2", loc="left", fontsize=11, color=INK)
        axes[0, 0].set_xlabel("Rate (Hz)", color=MUTED)
        axes[0, 0].set_ylabel("CV2", color=MUTED)
        axes[0, 1].set_title(
            _text(state, "Trial Fano factor", "Trial Fano factor"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel("Unit", color=MUTED)
        axes[0, 1].set_ylabel("Fano factor", color=MUTED)
        axes[1, 0].set_title("Lv vs CV2", loc="left", fontsize=11, color=INK)
        axes[1, 0].set_xlabel("Lv", color=MUTED)
        axes[1, 0].set_ylabel("CV2", color=MUTED)
        axes[1, 1].set_title(
            _text(state, "前两个 Unit 的 CCH", "CCH for the first two units"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[1, 1].set_xlabel("Lag (ms)", color=MUTED)
        return fig
    if view == "spike:relationships":
        fig, axes = _base_figure(2, 2, 6.4)
        matrices = (
            ("correlation", "Binned correlation", "viridis"),
            ("sttc", "Spike time tiling coefficient", "RdYlGn"),
            ("victor_purpura", "Victor-Purpura distance", "magma"),
            ("van_rossum", "van Rossum distance", "magma"),
        )
        for axis, (key, title, cmap) in zip(axes.flat, matrices):
            values = np.asarray(state.spike_train_analysis.get(key, []), dtype=float)
            if values.size:
                image = axis.imshow(values, cmap=cmap, aspect="auto")
                fig.colorbar(image, ax=axis, shrink=0.68)
            axis.set_title(title, loc="left", fontsize=10, color=INK)
            axis.set_xlabel("Unit", color=MUTED)
            axis.set_ylabel("Unit", color=MUTED)
        return fig
    if view in {"lfp:psd", "lfp:coherence", "lfp:spectrogram"}:
        result = state.lfp_analysis
        fig, axes = _base_figure(1, 2, 5.2)
        if view == "lfp:psd":
            frequencies = np.asarray(result.get("frequencies_hz", []), dtype=float)
            psd = np.asarray(result.get("psd", []), dtype=float)
            for index, channel in enumerate(result.get("channel_ids", [])):
                axes[0, 0].plot(
                    frequencies,
                    10 * np.log10(np.maximum(psd[index], 1e-12)),
                    label=f"Ch {channel}",
                )
            axes[0, 0].set_xlim(0, min(150, frequencies[-1] if frequencies.size else 150))
            axes[0, 0].legend(frameon=False, fontsize=8)
            bands = list(result.get("band_power", {}))
            values = np.asarray(list(result.get("band_power", {}).values()), dtype=float)
            if values.size:
                width = 0.8 / values.shape[1]
                for channel_index in range(values.shape[1]):
                    axes[0, 1].bar(
                        np.arange(len(bands)) + channel_index * width,
                        values[:, channel_index],
                        width=width,
                        label=f"Ch {result['channel_ids'][channel_index]}",
                    )
                axes[0, 1].set_xticks(
                    np.arange(len(bands)) + width * (values.shape[1] - 1) / 2,
                    bands,
                    rotation=25,
                )
                axes[0, 1].legend(frameon=False, fontsize=8)
            axes[0, 0].set_title("Welch PSD", loc="left", fontsize=11, color=INK)
            axes[0, 0].set_xlabel("Frequency (Hz)", color=MUTED)
            axes[0, 1].set_title("Band power", loc="left", fontsize=11, color=INK)
            axes[0, 1].set_ylabel("Integrated power", color=MUTED)
            return fig
        if view == "lfp:coherence":
            frequencies = np.asarray(
                result.get("coherence_frequencies_hz", []), dtype=float
            )
            axes[0, 0].plot(
                frequencies, result.get("coherence", []), color=GREEN, linewidth=1.5
            )
            axes[0, 0].set_ylim(0, 1.02)
            axes[0, 1].plot(
                frequencies,
                result.get("phase_lag_rad", []),
                color=CORAL,
                linewidth=1.3,
            )
            axes[0, 0].set_title("Magnitude-squared coherence", loc="left")
            axes[0, 1].set_title("Cross-spectral phase lag", loc="left")
            for axis in axes.flat:
                axis.set_xlim(0, min(100, frequencies[-1] if frequencies.size else 100))
                axis.set_xlabel("Frequency (Hz)", color=MUTED)
            axes[0, 0].set_ylabel("Coherence", color=MUTED)
            axes[0, 1].set_ylabel("Phase lag (rad)", color=MUTED)
            return fig
        spectrogram_f = np.asarray(
            result.get("spectrogram_frequencies_hz", []), dtype=float
        )
        spectrogram_t = np.asarray(result.get("spectrogram_times_s", []), dtype=float)
        spectrogram_power = np.asarray(result.get("spectrogram_power", []), dtype=float)
        if spectrogram_power.size:
            mask = spectrogram_f <= 150
            image = axes[0, 0].pcolormesh(
                spectrogram_t,
                spectrogram_f[mask],
                10 * np.log10(np.maximum(spectrogram_power[mask], 1e-12)),
                shading="auto",
                cmap="magma",
            )
            fig.colorbar(image, ax=axes[0, 0], label="Power (dB)", shrink=0.78)
            median_power = np.median(spectrogram_power[mask], axis=1)
            axes[0, 1].plot(spectrogram_f[mask], median_power, color=GREEN)
        axes[0, 0].set_title("LFP spectrogram", loc="left")
        axes[0, 0].set_xlabel("Time (s)", color=MUTED)
        axes[0, 0].set_ylabel("Frequency (Hz)", color=MUTED)
        axes[0, 1].set_title("Median time-frequency power", loc="left")
        axes[0, 1].set_xlabel("Frequency (Hz)", color=MUTED)
        return fig
    if view == "coupling:phase":
        fig, axes = _base_figure(1, 2, 5.2)
        rows = state.spike_field_analysis.get("rows", [])
        if rows:
            ids = [row["unit_id"] for row in rows]
            strengths = [row["vector_strength"] for row in rows]
            p_values = [row["surrogate_p"] for row in rows]
            colors = [GREEN if value < 0.05 else MUTED for value in p_values]
            axes[0, 0].bar(ids, strengths, color=colors)
            first_id = ids[0]
            histogram = state.spike_field_analysis["phase_histograms"][first_id]
            axes[0, 1].bar(
                histogram["centers"],
                histogram["counts"],
                width=2 * np.pi / 18 * 0.9,
                color=GOLD,
            )
        axes[0, 0].set_title(
            _text(state, "相位锁定强度与 surrogate 检验", "Phase locking and surrogate test"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel("Unit", color=MUTED)
        axes[0, 0].set_ylabel("Mean vector length", color=MUTED)
        axes[0, 1].set_title(
            _text(state, "Unit 0 spike 相位分布", "Unit 0 spike-phase distribution"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel("Phase (rad)", color=MUTED)
        return fig
    case = state.case_studies.get("respiration", {})
    rows = case.get("rows", [])
    fig, axes = _base_figure(1, 2, 5.2)
    if view == "case:pac":
        for name, values in case.get("state_curves", {}).items():
            pac = values["pac"]
            axes[0, 0].plot(
                pac["phase_centers"],
                pac["normalized_amplitude"],
                linewidth=1.5,
                label=name,
            )
        axes[0, 0].legend(frameon=False, fontsize=8)
        axes[0, 0].set_title(
            _text(state, "呼吸相位 × gamma 振幅", "Respiration phase x gamma amplitude"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel("Respiration phase (rad)", color=MUTED)
        if rows:
            axes[0, 1].bar(
                [row["state"] for row in rows],
                [row["pac_kld"] for row in rows],
                color=[GREEN, CORAL, GOLD],
            )
        axes[0, 1].set_title("PAC modulation index (KLD)", loc="left")
        axes[0, 1].tick_params(axis="x", rotation=20)
        return fig
    for name, values in case.get("state_curves", {}).items():
        axes[0, 0].plot(
            values["respiration_psd_frequencies_hz"],
            values["respiration_psd"],
            linewidth=1.4,
            label=name,
        )
        axes[0, 1].plot(
            values["coherence_frequencies_hz"],
            values["coherence"],
            linewidth=1.4,
            label=name,
        )
    axes[0, 0].set_xlim(0, 12)
    axes[0, 1].set_xlim(0, 12)
    axes[0, 1].set_ylim(0, 1.02)
    axes[0, 0].legend(frameon=False, fontsize=8)
    axes[0, 1].legend(frameon=False, fontsize=8)
    axes[0, 0].set_title("Respiration PSD by simulated state", loc="left")
    axes[0, 1].set_title("Respiration-LFP coherence", loc="left")
    for axis in axes.flat:
        axis.set_xlabel("Frequency (Hz)", color=MUTED)
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
        raster.vlines(
            relative, trial_index + 0.6, trial_index + 1.4, color=INK, linewidth=0.65
        )
    raster.axvline(0, color=CORAL, linewidth=1.2)
    raster.set_title(f"Unit {unit_id} Raster", loc="left", fontsize=11, color=INK)
    raster.set_xlabel(
        _text(state, "相对事件时间 (s)", "Time from event (s)"), color=MUTED
    )
    raster.set_ylabel("Trial", color=MUTED)

    psth = axes[0, 1]
    labels = analysis.get(
        "condition_labels",
        ["Condition A", "Condition B"]
        if state.metadata.get("language") == "en_US"
        else ["条件 A", "条件 B"],
    )
    psth.plot(centers, unit["condition_a"], color=GREEN, linewidth=1.8, label=labels[0])
    psth.plot(centers, unit["condition_b"], color=CORAL, linewidth=1.8, label=labels[1])
    psth.axvline(0, color=INK, linewidth=1)
    psth.legend(frameon=False, fontsize=8)
    psth.set_title(
        _text(state, "条件 PSTH", "Condition PSTH"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    psth.set_xlabel(
        _text(state, "相对事件时间 (s)", "Time from event (s)"), color=MUTED
    )
    psth.set_ylabel(_text(state, "放电率 (Hz)", "Firing rate (Hz)"), color=MUTED)

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
    heatmap.set_title(
        _text(state, "群体响应热图", "Population response heatmap"),
        loc="left",
        fontsize=11,
        color=INK,
    )
    heatmap.set_xlabel(
        _text(state, "相对事件时间 (s)", "Time from event (s)"), color=MUTED
    )
    heatmap.set_ylabel("Unit", color=MUTED)

    summary = axes[1, 1]
    effects = [value["effect_hz"] for value in analysis["units"].values()]
    q_values = [value["q_value"] for value in analysis["units"].values()]
    colors = [GREEN if q < 0.05 else "#b7c2bd" for q in q_values]
    summary.bar(np.arange(len(effects)), effects, color=colors)
    summary.axhline(0, color=INK, linewidth=0.8)
    summary.set_title(
        _text(
            state,
            f"刺激后效应：{analysis['responsive_units']} 个 Unit 通过 FDR",
            f"Post-event effect: {analysis['responsive_units']} units pass FDR",
        ),
        loc="left",
        fontsize=11,
        color=INK,
    )
    summary.set_xlabel("Unit", color=MUTED)
    summary.set_ylabel(
        _text(state, "放电率变化 (Hz)", "Firing-rate change (Hz)"), color=MUTED
    )
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
    if view == "circular":
        coupling_rows = state.spike_field_analysis.get("rows", [])
        if coupling_rows:
            ids = np.asarray([row["unit_id"] for row in coupling_rows], dtype=int)
            preferred = np.asarray(
                [row["preferred_phase_rad"] for row in coupling_rows], dtype=float
            )
            strengths = np.asarray(
                [row["vector_strength"] for row in coupling_rows], dtype=float
            )
            surrogate_p = np.asarray(
                [row["surrogate_p"] for row in coupling_rows], dtype=float
            )
            colors = np.where(surrogate_p < 0.05, GREEN, MUTED)
            axes[0, 0].scatter(preferred, strengths, c=colors, s=46)
            for unit_id, x, y in zip(ids, preferred, strengths):
                axes[0, 0].annotate(
                    str(unit_id), (x, y), xytext=(3, 3), textcoords="offset points"
                )
            axes[0, 1].scatter(
                -np.log10(
                    np.maximum(
                        [row["rayleigh_p"] for row in coupling_rows], 1e-12
                    )
                ),
                -np.log10(np.maximum(surrogate_p, 1e-12)),
                c=colors,
                s=46,
            )
            threshold = -np.log10(0.05)
            axes[0, 1].axhline(threshold, color=CORAL, linestyle="--")
            axes[0, 1].axvline(threshold, color=CORAL, linestyle="--")
        axes[0, 0].set_title(
            _text(state, "偏好相位与锁定强度", "Preferred phase and locking strength"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 0].set_xlabel("Preferred phase (rad)", color=MUTED)
        axes[0, 0].set_ylabel("Mean vector length", color=MUTED)
        axes[0, 1].set_title(
            _text(
                state,
                "Rayleigh 近似与 circular-shift surrogate",
                "Rayleigh approximation vs circular-shift surrogate",
            ),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_xlabel("-log10(Rayleigh p)", color=MUTED)
        axes[0, 1].set_ylabel("-log10(surrogate p)", color=MUTED)
        return fig
    if view == "design":
        axes[0, 0].axis("off")
        axes[0, 1].axis("off")
        hierarchy = (
            f"Trials: {len(state.events)}\n"
            f"Units: {len(state.sorted_spikes)}\n"
            f"Sessions represented: 1 (demo)\n"
            f"Animals represented: not encoded (demo)\n\n"
            "Current primary contrast:\n"
            "within-trial baseline vs response\n\n"
            "Current multiplicity:\n"
            "units controlled with BH-FDR"
        )
        axes[0, 0].text(
            0.02,
            0.97,
            hierarchy,
            va="top",
            fontsize=10,
            color=INK,
        )
        design_notes = (
            "Decision checks\n\n"
            "1. Define the biological sampling unit.\n"
            "2. Mark paired or independent observations.\n"
            "3. Encode animal and session identifiers.\n"
            "4. Inspect distribution and variance assumptions.\n"
            "5. Use circular or surrogate statistics for phase data.\n"
            "6. Report effect sizes and uncertainty with p values."
        )
        axes[0, 1].text(
            0.02,
            0.97,
            design_notes,
            va="top",
            fontsize=10,
            color=INK,
        )
        axes[0, 0].set_title(
            _text(state, "当前样本层级", "Current sampling hierarchy"),
            loc="left",
            fontsize=11,
            color=INK,
        )
        axes[0, 1].set_title(
            _text(state, "检验前决策", "Pre-test decisions"),
            loc="left",
            fontsize=11,
            color=INK,
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
                "混合效应模型不可用\n\n"
                if state.metadata.get("language") != "en_US"
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
    axes[0, 0].scatter(x, effects, c=colors, s=35, label="Effect and bootstrap CI")
    axes[0, 0].axhline(0, color=INK, linewidth=0.8)
    axes[0, 0].set_title(
        _text(
            state,
            "效应量与 bootstrap 95% CI",
            "Effect size and bootstrap 95% CI",
        ),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[0, 0].set_xlabel("Unit", color=MUTED)
    axes[0, 0].set_ylabel(
        _text(state, "刺激后变化 (Hz)", "Post-stimulus change (Hz)"),
        color=MUTED,
    )
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
    axes[0, 1].set_title(
        _text(
            state,
            "置换检验与 FDR 校正",
            "Permutation test and FDR correction",
        ),
        loc="left",
        fontsize=11,
        color=INK,
    )
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
    axes[0, 0].set_title(
        _text(
            state,
            "交叉验证混淆矩阵",
            "Cross-validated confusion matrix",
        ),
        loc="left",
        fontsize=11,
        color=INK,
    )
    fig.colorbar(image, ax=axes[0, 0], shrink=0.65)
    null = np.asarray(result["null_scores"])
    axes[0, 1].hist(null, bins=22, color="#bac7c1", edgecolor="white")
    axes[0, 1].axvline(result["balanced_accuracy"], color=CORAL, linewidth=2)
    axes[0, 1].set_title(
        _text(
            state,
            f"置换检验 p={result['permutation_p']:.4f}",
            f"Permutation test p={result['permutation_p']:.4f}",
        ),
        loc="left",
        fontsize=11,
        color=INK,
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
    axes[1, 0].set_title(
        _text(
            state,
            "时间分辨神经解码",
            "Time-resolved neural decoding",
        ),
        loc="left",
        fontsize=11,
        color=INK,
    )
    axes[1, 0].set_xlabel(
        _text(state, "相对事件时间 (s)", "Time from event (s)"),
        color=MUTED,
    )
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
        _text(
            state,
            f"群体 PCA 轨迹 · 最大距离 {peak_distance:.2f}",
            f"Population PCA trajectories · maximum distance {peak_distance:.2f}",
        ),
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
