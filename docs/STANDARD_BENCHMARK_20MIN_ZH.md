# NeuroEphys AI 20 分钟标准模拟 benchmark

这套数据用于验证 NeuroEphys AI 的完整分析链，而不是用于展示一条“预先知道答案”的演示流程。正常项目只能看到宽带原始电压、行为事件、通道几何和一份故意不完美的候选 sorting；独立 `ground_truth` 目录仅供最终验证脚本读取。

## 两种记录体系

| 数据集 | 正式会话 | 时长 | 采样率 | 通道 | 原始数据量 |
|---|---:|---:|---:|---:|---:|
| Neuropixels-style（M1 + mPFC） | 7 | 20 min/会话 | 30 kHz | 128 | 64.512 GB |
| Tetrode（M1 + mPFC） | 7 | 20 min/会话 | 30 kHz | 32（8×4） | 16.128 GB |

轻量验收集另含两类电极各 2 个 3–4 分钟会话。它覆盖高噪声、近死通道、50/100/150 Hz 工频、瞬态、电极跳变、共模、轻度削顶和慢漂移，用于在生成约 80.64 GB 正式原始数据前快速确认代码与存储链路。

## 数据内容

- 每个正式会话含 50–70 个 Lever Press→Reward Delivery 行为 trial；奖励延迟服从截断分布，均值约 3 秒、标准差约 0.5 秒、范围 2–4 秒。
- 行为时间同时保存秒和 30 kHz 样本号，两者由同一时钟生成并逐项校验。
- M1 与 mPFC 分别包含 lever、reward anticipation、reward delivery、mixed、nonresponsive 五类神经元，含兴奋和抑制响应。
- Unit 具有不同基线放电率、regular/bursting/low/high/fast-spiking-like 表型、trial 抖动、慢放电漂移、振幅/空间漂移和排序难度。
- 宽带电压由空间波形、结构化 LFP、背景噪声、工频及稀疏 QC 异常叠加后，以 time-major `int16` 交错二进制写入；不会把整段原始电压同时放进内存。
- Neuropixels 波形跨相邻位点衰减；tetrode Unit 在同一四根 wire 上呈不同振幅组合。
- Spike 不再由单一光滑曲线重复粘贴：每个 Unit 从 somatic biphasic、triphasic、broad somatic、axonal-like 四类形态中生成，并具有接触点延迟、空间权重不规则性、亚采样相位、逐次振幅变化、burst 衰减和慢漂移。
- 背景加入低振幅远端神经元活动与局部相关噪声，使 100 ms 原始浏览窗口保持真实记录常见的不规则底噪；这些低于可分选阈值的活动不冒充可评分 Unit。
- 每个项目含一份 Kilosort/Phy 兼容的盲测 sorting，故意加入合并、拆分、漏检、误检和时间抖动，用于 Unit QC 与 sorter 横向比较。

## Spike 真实性标定

模拟波形参数不是凭截图主观调节。项目提供 `scripts/validate_waveform_realism.py`，可将生成的 ground-truth 模板与本地真实 Kilosort 逐次 Unit 波形作只读对照。当前标定使用 87 个负峰主导的真实 Unit，比较负峰半高宽、负峰到正回弹的时间、前置正相、回弹比例与逐次振幅变异系数；真实文件不会复制到仓库或用于训练。

当前固定 seed 的短预览结果（中位数）为：

| 指标 | 真实 | 模拟 |
|---|---:|---:|
| 负峰半高宽 | 0.200 ms | 0.200 ms |
| 负峰至正回弹 | 0.533 ms | 0.500 ms |
| 正回弹/负峰 | 0.230 | 0.223 |
| 逐次振幅变异系数 | 0.098 | 0.104 |

设计依据来自可公开复核的方法：MEArec 使用生物物理细胞模型、电极前向模型、振幅调制、重叠、漂移与远端神经元噪声生成可控 ground truth；真实 extracellular waveform 允许 negative、positive、biphasic/triphasic 等形态，而不是只有一种模板。参考：[MEArec 方法论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC7782412/)、[MEArec 官方说明](https://mearec.readthedocs.io/en/latest/overview.html)、[extracellular waveform 形态研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC10507124/)。

## 生成与复现

先估算空间：

```powershell
python scripts/generate_standard_benchmark.py --output "D:\benchmark" --config benchmark\dataset_config.yaml --tier estimate
```

生成轻量验收集：

```powershell
python scripts/generate_standard_benchmark.py --output "D:\benchmark" --config benchmark\dataset_config.yaml --tier lightweight
```

如需先做 65 秒生理形态预览，使用：

```powershell
python scripts/generate_standard_benchmark.py --output "D:\benchmark_preview" --config benchmark\physiological_preview_config.yaml --tier lightweight
python scripts/validate_waveform_realism.py --real-root "E:\真实数据" --sim-root "D:\benchmark_preview\lightweight\ground_truth" --output "D:\benchmark_preview\validation\realism_calibration"
```

轻量报告为 PASS 后生成正式集：

```powershell
python scripts/generate_standard_benchmark.py --output "D:\benchmark" --config benchmark\dataset_config.yaml --tier full
```

固定总 seed 与分层派生 session seed 保证相同配置生成相同数据。完成的 session 有 `.benchmark_complete.json` 标记，再次运行会重新验证并跳过；不完整目录不会被静默覆盖。

## 在 App 中分析

1. 在首页选择“打开／导入项目”，打开任一会话的 `neuroflow_project.json`。
2. 按常规路线完成原始 QC、预处理、sorting、Unit QC、行为对齐、事件分析、统计与作图。
3. 若要先练习 Unit QC，导入该会话 `benchmark_inputs/blinded_candidate_sorting` 下的 `spike_times.npy` 和 `spike_clusters.npy`。
4. 最后再阅读 `validation` 报告，或用独立 `ground_truth` 计算 precision、recall、F1；真实数据不应把不同 sorter 的一致度误称为准确率。

要对照自己导出的 Kilosort/Phy 结果，可运行：

```powershell
python scripts/evaluate_benchmark_sorting.py --truth "...\true_spike_times.npz" --candidate "...\my_sorting" --output "...\my_validation"
```

每个会话均保存原始数据、行为表、事件表、通道几何、盲测输入、项目清单和人类可读项目记录；根目录保存配置、生成日志、索引、验证报告以及低饱和紫/绿配色的示例图。

本数据还用于反向检验 App 的原始 QC：20 分钟正式项目暴露了近死通道漏报与 50 Hz 分辨率不足的问题。当前实现已增加近死通道分类，并使用更高频率分辨率和相对全通道基线区分正常背景工频与异常工频通道。
