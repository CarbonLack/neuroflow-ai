from __future__ import annotations

from pathlib import Path

from .models import ProjectState


def _event_label(state: ProjectState, code: int) -> str:
    dictionary = state.metadata.get("medpc", {}).get(
        "confirmed_event_dictionary",
        {},
    )
    item = dictionary.get(str(code), dictionary.get(code, {}))
    return str(item.get("zh_label", item.get("label", f"事件 {code}")))


def build_real_data_validation_report(
    state: ProjectState,
    export_dir: Path,
    restored: ProjectState,
    *,
    behavior_file: Path,
    ttl_channel: int,
    permutations: int,
) -> str:
    """Build an auditable Chinese report from project metadata and real outputs."""
    sync = state.metadata["synchronization"]
    validation = state.metadata.get("validation_case", {})
    probe = state.metadata.get("probe", {})
    sorting = state.sorting_provenance.get(state.active_sorter_key or "", {})
    event_codes = state.analysis.get("selected_event_codes", [])
    event_labels = "、".join(
        f"{code} = {_event_label(state, int(code))}" for code in event_codes
    )
    qc = state.qc
    decoding = state.decoding
    lfp_reason = state.metadata.get("acquisition_preprocessing", {}).get(
        "lfp_unavailable_reason",
        "未记录原因",
    )
    files = sorted(
        str(path.relative_to(state.root))
        for path in export_dir.rglob("*")
        if path.is_file()
    )
    file_list = "\n".join(f"- `{value}`" for value in files)
    transient = [channel + 1 for channel in qc.get("transient_channels", [])]
    bad = [channel + 1 for channel in qc.get("bad_channels", [])]
    restored_ok = (
        restored.active_sorter_key == state.active_sorter_key
        and len(restored.sorted_spikes) == len(state.sorted_spikes)
    )
    dataset = validation.get("dataset", state.name)
    selected_channels = validation.get(
        "selected_channels",
        f"{state.channel_count} channels",
    )
    brain_region = probe.get("brain_region", "未提供")
    electrode = validation.get(
        "electrode_construction",
        state.electrode_type,
    )
    reference = probe.get("reference_configuration", "未提供")
    known_bad = probe.get("known_hardware_bad_channels", [])

    return f"""# NeuroFlow 真实数据验证报告

## 验证对象

- 数据集：{dataset}
- 电极：{electrode}
- 记录脑区：{brain_region}
- 选择通道：{selected_channels}
- 参考与地：{reference}
- 预先已知坏道：{known_bad or "无"}
- 电生理输入：`{state.recording_path}`
- 行为输入：`{behavior_file}`
- 验证长度：{state.duration_seconds:.1f} 秒（{state.duration_seconds / 60:.1f} 分钟）
- 可恢复项目：`{state.root / "neuroflow_project.json"}`

## 实际执行步骤

1. NeuroFlow 以只读链接方式打开原始记录文件夹，按项目配置选择通道。原始文件不复制、不重命名、不覆盖。
2. 读取采集元数据并审计在线处理。本记录已经进行 250-8000 Hz 在线带通和分组 common-average reference，因此 AP 分支不重复滤波或重参考。
3. 因 250 Hz 以下频率已在采集阶段移除，NeuroFlow 阻止 LFP、低频频谱及 spike-field coupling。原因：{lfp_reason}
4. 原始质控跨整段记录抽取多个时间窗，检查 RMS、50 Hz 比值、饱和、持续异常和瞬时伪迹。
5. Kilosort4 读取 NeuroFlow 为所选通道生成的交错二进制缓存。独立微丝按独立 contact 处理，不构造虚假的相邻空间几何。
6. Kilosort 标准输出被转换成 NeuroFlow 的统一 sorting 接口：spike 时间统一为秒，同时保留原始 Kilosort 文件、参数、版本和日志。
7. MED-PC `C` 数组作为事件码，`D` 数组作为行为秒时间。事件码 11 与 Open Ephys digital input {ttl_channel} 上升沿匹配，再用分段线性 TTL 锚点映射全部行为事件。
8. 同步码 11/12 不进入神经响应比较。本次分析纳入当前记录范围内的 {event_labels}。
9. 对每个候选 unit 计算放电率、ISI violation、波形、SNR、ACG、振幅和时间稳定性。
10. 生成事件对齐 Raster、PSTH 和群体热图，并执行参数/非参数检验、效应量、置换检验和 FDR 校正。
11. 使用 Logistic regression、分层交叉验证及 {permutations} 次标签置换，验证事件分类的机器学习接口。
12. 使用 Elephant/Neo 计算 spike-train 指标。STTC 使用线性内存实现；Victor-Purpura 与 van Rossum 距离仅在审计记录注明的短窗内计算，避免长记录产生二次方内存增长。
13. 导出图、表、Methods、环境版本和工作流，保存项目后从磁盘重新加载，验证可以从上次位置继续。

## 关键结果

- 原始质控得分：{qc.get("quality_score", float("nan")):.1f}/100
- 持续高噪声候选通道（数据判据）：{bad or "无"}
- 瞬时异常候选通道（数据判据）：{transient or "无"}
- 50 Hz 比值：{qc.get("line_noise_ratio", float("nan")):.3f}
- MED-PC 行为事件：{sync["behavior_event_count"]}
- 同步锚点匹配：{sync["matched_count"]}/{sync["behavior_anchor_count"]}
- 全局时钟漂移：{sync["drift_ppm"]:.3f} ppm
- 全局拟合平均绝对残差：{sync["mean_abs_residual_ms"]:.3f} ms
- Sorter：{sorting.get("sorter", state.active_sorter_key)}
- Sorter 版本：{sorting.get("version", "unknown")}
- 候选 unit：{len(state.sorted_spikes)}
- Spike 总数：{sum(len(value) for value in state.sorted_spikes.values())}
- 当前事件分析纳入：{state.analysis["selected_event_count"]} 个事件
- FDR 后响应 unit：{state.analysis["responsive_units"]}/{len(state.sorted_spikes)}
- 分类平衡准确率：{decoding.get("balanced_accuracy", float("nan")):.3f}
- ROC AUC：{decoding.get("roc_auc", float("nan")):.3f}
- 标签置换 p 值：{decoding.get("permutation_p", float("nan")):.4f}
- 保存后恢复验证：{"通过" if restored_ok else "失败"}

## 科学边界

- 这是软件工程与分析链路验证，不是该实验的最终生物学结论。
- Kilosort 输出是候选 unit，仍需依据波形、ISI、稳定性和实验标准人工复核。
- 采集文件已在线高通至 250 Hz，无法恢复真实 LFP；NeuroFlow 不会用 AP 数据伪造 LFP 结果。
- 外部参考与地线未保存为通道，软件只能审计在线参考设置，不能离线重建参考电极信号。
- 当前事件分类只用于验证机器学习接口。正式结论需要按动物和 session 分层，并预先确定 trial、排除规则和统计单位。

## 输出位置

导出根目录：`{export_dir}`

{file_list}
"""
