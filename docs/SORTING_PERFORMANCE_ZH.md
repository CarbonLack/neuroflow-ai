# Spike sorting 耗时检查（v1.3.3）

本页区分“处理大量数据需要时间”和“程序失败”。不以运行了几分钟作为故障判据；先看项目 `logs/run_log.txt`、各 sorter 原生日志、缓存状态和最终审计记录。

## 本机的一次真实测量

项目 `NeuroEphys_AI_project_20260921_191450`：32 通道、30 kHz、7,497.5 秒（约 125 分钟）的 Open Ephys 数据。交织排序缓存约 14.4 GB，只在首次需要创建；原始文件保持只读。

| 环节 | 实测 | 解释 |
|---|---:|---|
| 首次重排 Open Ephys 数据 | 约 136 秒 | 从每通道原文件读出并形成适合 sorter 的交织二进制；后续 sorter 复用通过大小检查的缓存。 |
| MountainSort5 完整节点 | 719.367 秒 | 包含上述首次缓存、独立触点分组运行、结果整理；单个触点通常约 16–27 秒。 |
| Kilosort4 完整节点 | 753.278 秒 | 复用缓存；使用 RTX 3080。其原生日志报告算法内部 726.7 秒。 |

Kilosort4 的内部 726.7 秒中，universal spike detection 435.3 秒、learned detection 109.0 秒、final clustering 119.7 秒。因此本例瓶颈不是“启动 App 慢”或“缓存反复写”，而是长记录上的检测与聚类。两种 sorter 都有完成记录；Unit 数量不一致还需要波形、ISI、污染率、稳定性等人工复核，真实数据没有 ground truth，不能据 Unit 数判定哪个更准确。

## 为什么 MountainSort5 不直接一次处理所有 32 通道？

该记录没有测量过的跨触点几何信息。软件将其保守地标记为独立接点，按接点运行并汇总结果，不凭空声称相邻电极是同一探针位置。当前 SpikeInterface 运行器使用 `engine="loop"` 串行执行；官方同时支持 `joblib` 多进程，但并行可能提高内存与磁盘压力。本机此前运行时内存已较高，故没有未经基准测试就把默认行为改成并行。若以后具备真实分组/几何信息，应先录入真实信息，再比较串行与有限并行的耗时、内存和 Unit 质量。

## 研究者现在怎么判断

1. 在排序页先看实际记录分钟数、通道数、约需读取的数据量和缓存状态。第 03 页只是预处理预览，不代表已经在 GPU 上做完 sorter 的完整检测与聚类。
2. 在项目 `logs/run_log.txt` 中看是否持续出现缓存进度、sorter 启动与完成；Kilosort 细节在 `results/kilosort4/kilosort4.log`，MountainSort5 每个组在 `results/mountainsort5/<group>/spikeinterface_log.json`。
3. 复跑同一项目应确认显示“复用缓存”；若每次都重建，检查是否换了项目目录/输入通道、缓存文件是否缺失，或磁盘容量不足。不要手工混用不同原始记录的缓存。
4. 需要快速试流程时，先选有代表性的短片段或教学 sorter；正式结论仍需完整记录、同样的参数、Unit 质控和跨 sorter 一致性检查，不能把短片段结果伪装成整段结果。
5. 优先将排序输入和结果放在本地 SSD，检查磁盘剩余空间、GPU 是否被 PyTorch 识别以及是否出现内存交换。关闭 App 窗口不等同于安全地取消底层 sorter；不要在运行中删除缓存/结果。

参考： [SpikeInterface 分组运行 API](https://spikeinterface.readthedocs.io/en/latest/api.html)、[MountainSort5 官方仓库及 schemes](https://github.com/flatironinstitute/mountainsort5)、[Kilosort4 硬件建议](https://kilosort.readthedocs.io/en/latest/hardware.html)。以上外部文档只说明机制；时间数据来自本项目本机日志，不是软件普遍速度保证。
