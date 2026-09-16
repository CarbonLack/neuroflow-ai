# 三批数据交付验收清单

状态：**三批端到端链路已完成；真实 Unit 人工科学复核尚未完成。**  
最后刷新：2026-09-17。

## 数据范围

1. **20 分钟 Neuropixels-like benchmark**：从原始 `recording.bin` 和行为/事件文件创建项目；几何修正版 session_01 完成 Kilosort4、MountainSort5、SpyKING CIRCUS2、ground-truth 评估、事件分析、图表和英文 publication 导出。
2. **20 分钟 tetrode benchmark**：从原始电压和行为文件导入；session_01 完成相同的三-sorter、ground-truth、行为、统计、图表和 publication 链路。
3. **王淑霏单日真实数据**：101、102、104、105、108 五个已确认动物组全部完成三 sorter、MED–电生理同步、事件分析、sorter 比较、英文图表和主/附图报告。12:58:41 记录的 33–64 通道无对应动物，不进入动物汇总和行为结论。采集时已滤除 300 Hz 以下信号，因此不做不受数据支持的 LFP/频谱耦合分析。

两个 benchmark 的“完成”指最终选定的两个 session_01，不扩大为整个 14-session 数据族均已跑完。

## 模拟数据结果摘要

### Tetrode

| Sorter | 候选 Unit | 全体真值平均召回 |
|---|---:|---:|
| Kilosort4 | 26 | 0.964 |
| MountainSort5 | 24 | 0.871 |
| SpyKING CIRCUS2 | 25 | 0.952 |

### 几何修正版 Neuropixels-like

| Sorter | 候选 Unit | 已配对中位 F1 | 全体真值平均召回 |
|---|---:|---:|---:|
| Kilosort4 | 345 | 0.653 | 0.502 |
| MountainSort5 | 216 | 0.500 | 0.405 |
| SpyKING CIRCUS2 | 211 | 0.601 | 0.496 |

候选之间的高一致度不能掩盖真值召回不足；必须同时报告未恢复的 ground-truth Unit，不只展示成功配对中位数。早期双探针几何重叠输出作为诊断证据保留，正式结果使用保留 `probe_id` 的修正版。

## 真实数据结果摘要

| Sorter | 五动物候选簇合计 | 保守自动筛选暂留 |
|---|---:|---:|
| Kilosort4 | 60 | 18 |
| MountainSort5 | 282 | 136 |
| SpyKING CIRCUS2 | 20 | 0 |

候选簇不是已确认 single unit；自动暂留只是人工复核队列。MountainSort5 与其他工具的数量差异必须通过波形、ISI、漂移、存在性、重复和合并/拆分复核解释。SpyKING CIRCUS2 的候选没有通过当前保守自动筛选，软件因此不生成筛选后推断图，而不是伪造结果。

同步锚点为 603–744 个；全局平均绝对残差约 7.99–15.21 ms。事件×候选 Unit 的显著组合不是显著细胞数，单动物事件结果也不能扩大为跨动物结论。

## 图件、排版与解释

- 模拟数据最终范围 407 张 SVG 机械审计为 0 个标记。
- 真实数据刷新 216 份英文 publication 报告；1057 张 SVG 机械审计为 0 个标记。
- 英文主图/附图、panel 字母、图注草稿、Methods、文件清单和校验值已生成。没有进主图的图和表保留在补充证据索引中。
- 机械审计仅检查文件结构、物理尺寸、英文文本和配对导出，不代替统计、人工视觉、生物学解释或期刊终审。

## 交付入口

- 模拟数据：`D:\PhD\AI大赛\NeuroEphysAI_Workspace\Delivery_Validation_20260915`
- 模拟详解：`模拟数据完整验收与结果解释.md`
- 真实数据：`E:\NeuroEphysValidation`
- 真实详解：`真实数据完整验收与结果解释.md`
- 两个目录均以 `实验结果导航.html` 为人工审阅入口。

## 仍需研究者完成

1. 真实 Unit 人工复核、重复检查和合并/拆分决策。
2. 数据提供者核对动物映射、代表波形与行为语义。
3. 跨动物正式统计、实验设计对照和目标期刊技术终审。
4. 如要宣称整个 14-session benchmark 完成，必须逐 session 重复当前验收，不得从两个 session_01 外推。
