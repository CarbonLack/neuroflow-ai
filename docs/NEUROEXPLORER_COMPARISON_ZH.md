# NeuroExplorer 对标与电极分选说明（2026-09-22）

## 科学上首先要区分什么

Spike train 是一串时间戳；waveform 才包含每次 spike 周围的电压采样。把 sorter 给出的一个时间戳绘在横坐标 0 ms，只表示**相对于 sorter 时间戳**，不表示生物学动作电位恰在 0 ms 起始。Kilosort 的 `spike_times.npy` 文档把该时间戳定义为峰值样本，但其他 sorter 的定义需查其来源；本软件不擅自重新对齐波形。图上的 0 ms 现已明确标注。

数字相邻的通道未必物理相邻。微丝阵列缺少空间几何时，Unit 复核默认只显示峰值接点；只有项目提供经核实的 `metadata.probe.contact_groups`，或同 shank 的 `metadata.contact_positions_um` 近邻几何，才会联显接点波形。多接点联显用于判断空间分布、重复检出和聚类边界，**不表示这些曲线是几个不同 Unit**。同接点波形 PCA 是质控辅助，不是单细胞真值或自动接受证据。

## 不同电极的 sorting 输入与空间假设

| 电极 | 可可靠使用的空间信息 | 分选与复核重点 |
| --- | --- | --- |
| Neuropixels | 密集探针接点位置、shank、深度和漂移轨迹（前提是元数据确实存在） | 多接点模板匹配、漂移校正、重复模板、跨深度污染；可在真实几何上看空间模板。 |
| Tetrode | 同一四接点组内的波形幅度比例与形态；不同 tetrode 不能凭编号合并 | 每组联合特征聚类；检查四接点形态、ACG、不应期、振幅随时间和组间重复。 |
| 单根／微丝阵列 | 单接点波形；若没有实测空间坐标，通道序号不是距离 | 每根或已确认组分选；核对噪声、伪迹、同时间重复事件，不能伪造几何邻域。 |

一只动物的 32 根微丝不等于一个四接点 tetrode。王淑霏数据已确认动物与通道映射，但未提供每根微丝的物理坐标；因此默认 `independent_contacts`，不会把 28–31 等编号相邻通道描绘成同一个 tetrode。

## 与 NeuroExplorer 的对照

NeuroExplorer 的官方分析目录覆盖放电率、ISI、ACG、burst、PSTH、交叉相关、连续信号频谱、波形比较和 Python 自定义分析。其波形比较提供 PCA 投影、峰谷特征与分时段平均波形；这是传统使用者熟悉的复核路径。NeuroEphys AI 目前已覆盖放电与事件响应、时序关系、部分 LFP/群体分析、可复现英文图文导出，并增加多 sorter 记录、项目审计、行为同步和受约束 AI；但不能声称全面覆盖 NeuroExplorer 的 place/head-direction、joint PSTH、所有波形编辑和丰富交互式人工拆分／合并。

本轮按熟悉的习惯增加“同接点 cluster 特征空间”视图（波形 PCA + 振幅时间图），并把第 11 步报告入口显式放到界面。仍需后续评估：真正的交互式 cluster split/merge、时间分段波形分布、place/head-direction 模块；这些不能在没有探针几何或行为位置数据的项目中强行启用。

## 官方资料

- NeuroExplorer [分析类型](https://neuroexplorer.com/docs/reference/analysis/types/index.html)与[波形比较](https://neuroexplorer.com/docs/reference/analysis/types/waves/WaveformComparison.html)
- NeuroExplorer [数据类型](https://www.neuroexplorer.com/docs/reference/analysis/datatypes/index.html)
- Kilosort [导出文件与 spike 时间戳](https://kilosort.readthedocs.io/en/stable/export_files.html)
- Phy [GUI 复核视图](https://phy.readthedocs.io/en/latest/visualization/)
- SpikeInterface [质量指标](https://spikeinterface.readthedocs.io/en/stable/modules/metrics/quality_metrics.html)
