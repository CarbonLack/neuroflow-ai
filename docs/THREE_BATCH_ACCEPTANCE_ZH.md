# 三批数据交付验收清单

状态：实施中，尚未完成三批端到端验收。

## 数据范围

1. Standard_Benchmark_20min_v2 Neuropixels：从原始 recording.bin 新建导入，单独导入 events.csv。
2. Standard_Benchmark_20min_v2 tetrode：同上。优先完成两类 session_01 全长20分钟，然后扩展其他会话；不得把单会话结果称为全部14会话分析完成。
3. 电生理数据+行为-王淑霏：Open Ephys 多动物会话、Subject行为文件、已有NEX5结果。必须确认动物—通道—行为—TTL映射后分动物运行。采集已滤除300 Hz以下信号，跳过不受数据支持的LFP/频谱耦合分析并显示原因。

## 每批必须交付

- 独立新建项目的导入记录、输入元数据、行为时钟检查和来源清单。
- 至少三个实际执行的sorter：优先Kilosort4、MountainSort5、SpyKING CIRCUS 2；失败时记录原因与替代，不把内置教学算法冒称正式sorter。
- 每个sorter独立保存原生结果、Unit QC、下游分析与评估；真实数据一致度不得叫准确率。模拟数据仅在最后评估时读取ground truth。
- 每个阶段的参数、有效样本量、数值检查、图像检查、中文解释和英文图注。
- 每个图表均进入主图、附图或源数据表清单；记录归属理由与文件路径。失败和不适用项目列入说明，不画伪结果。
- 主图按数据质量→行为与时序→单元事件响应→群体结果→稳健性组织；选择不按显著性筛选，不能隐藏反例。
- 单会话结论不得扩大为跨动物结论；同一动物的Unit不等于独立动物样本。

## 产品修改

- 工作区顶部显示紧凑语言切换入口，维持现有配色。
- 每项分析说明输入、计算、坐标轴、解释边界、下一步及常见错误。
- 论文模块导出英文图板、逐panel图注、主图/附图索引和完整图表清单。
- 期刊分别提供预设，不声称C/N/S具有一个共同的强制标准。

## 已核对

- Kilosort4 4.1.7、MountainSort5 0.5.9、SpikeInterface 0.104.8可用；CUDA GPU可用。安装可用不等于三个sorter端到端成功。
- Nature最终制图指南：https://www.nature.com/nature/for-authors/final-submission
- Nature图板指南：https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/
- 真实数据尚需确认：动物编号到通道映射、行为事件码、TTL通道与脉冲含义。
