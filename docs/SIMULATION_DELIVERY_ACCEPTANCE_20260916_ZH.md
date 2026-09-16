# 两套 20 分钟模拟数据验收摘要

完整本地证据位于 `D:\PhD\AI大赛\NeuroEphysAI_Workspace\Delivery_Validation_20260915`。
本文件只同步可公开的方法与结论，不上传大型二进制记录和重复导出图件。

|数据|时长|通道|事件 / trial|Kilosort4|MountainSort5|SpyKING CIRCUS 2|
|---|---:|---:|---:|---:|---:|---:|
|Tetrode|1200 s|32|134 / 134|26 units|24 units|25 units|
|Neuropixels（修正几何）|1200 s|128|120 / 120|345 units|216 units|211 units|

两套数据均从只读宽带二进制记录、采样/探针信息和独立行为事件建立项目；ground truth
不进入 sorter，完成分选后才由独立评估读取。每个 sorter 均保存原生输出、标准化 spike
time、参数、日志、Unit 指标、事件分析、统计、图表和可恢复项目。

Tetrode 的平均 ground-truth recall：Kilosort4 约 0.964、MountainSort5 约 0.871、
SpyKING CIRCUS 2 约 0.952。修正几何的 Neuropixels 中，三者的候选簇 / F1 中位数 /
平均 GT recall / F1≥0.8 匹配数分别为 345/0.653/0.502/20、216/0.500/0.405/12、
211/0.601/0.496/17。候选簇多或 sorter 一致不等于真实准确率高。

本地交付树的 407 个 SVG 通过英文文本、物理坐标框和配对 PNG 的机械检查（0 个标记项）。
所有图件已生成 `publication/storyboard.json`：按测量与质量、事件相关神经证据、效应量与
不确定性、支持性诊断组织主图与附图，并为每个 panel 分配字母与英文图注草稿；完整文件
仍列在 `artifact_inventory.json`。这不是人工视觉审稿或科学有效性认证。

已修正的问题包括：双探针 `probe_id` 遗漏造成的坐标重叠、MountainSort5 高密度内存
策略、低频片段无 spike 时的不可估计状态、热图 Unit ID 显示，以及原论文输出缺少主/附图
故事板和 panel 字母。旧错误结果保留为诊断证据，不作为最终验收结果。
