# NeuroEphys AI Unit 人工复核手册

## 1. 为什么要人工复核

Sorter 输出的是候选 cluster。阈值、漂移、模板相似、噪声、合并和拆分都会改变候选数量。自动 `good`、`mua` 或质量分数只能提供筛查证据。

人工复核适用于 Kilosort、MountainSort、SpyKING CIRCUS、Tridesclous 和其他统一接入的 sorter。各 sorter 提供的原生证据不同，最终复核界面使用统一字段并保留原生文件。

## 2. 打开复核页

1. 打开项目。
2. 进入“04 Spike sorting”，确认当前活动 sorter。
3. 进入“05 Unit QC”并运行自动指标。
4. 点击“人工复核 Units”。
5. 左侧选择一个候选 cluster。

## 3. 中间诊断图

### 平均波形

检查：

- 波形是否有清晰、短暂的动作电位形状；
- 峰谷是否平滑；
- 是否存在异常振铃或饱和；
- 主要通道与相邻通道是否符合电极结构；
- 不同时间段波形是否稳定。

独立微丝没有可靠空间邻接时，通道轮廓主要用于识别峰值通道和串扰，不能解释为连续空间位置。

### ACG 与不应期

检查0附近的计数和1–2 ms区域。明显不应期违例可能提示：

- 多个神经元合并；
- 检测噪声；
- 重复 spike；
- 阈值或模板问题。

低放电率cluster的ACG证据较弱，应结合波形和稳定性。

### ISI 分布

检查短ISI比例、分布形状和长尾。图中的虚线标记项目使用的不应期阈值。当前默认筛查阈值为1.5 ms。

### 放电与振幅稳定性

检查：

- 记录前后是否持续存在；
- 放电率是否突然消失或激增；
- 振幅是否单调漂移；
- 是否存在短时高噪声爆发；
- 长记录中的抽样是否覆盖完整时段。

## 4. 证据清单

逐项勾选已经人工查看的内容：

- waveform shape；
- refractory period and ACG；
- amplitude stability；
- recording stability；
- channel or spatial profile；
- duplicate or split-cluster risk。

勾选表示“已检查”，不表示“通过”。

## 5. 决策标签

### Candidate single unit

证据支持相对隔离且稳定的候选单单元。保留“candidate”表述，因为缺少真实ground truth。

### Multi-unit activity

波形或不应期提示多个神经元混合，但活动仍可能适合MUA分析。

### Noise

证据更符合噪声、伪迹、重复检测或不可解释信号。

### Uncertain

证据不足、相互冲突或需要回到Phy/Kilosort原生诊断进一步检查。

## 6. 保存与恢复

填写决策、置信度、复核者和备注后点击“保存决定”。记录写入：

```text
neuroflow_project.json
metadata.unit_curation.<sorter>.<unit_id>
```

保存项目后关闭软件。重新打开项目时，当前 sorter 的复核进度、标签、证据清单和备注会恢复。

## 7. 授权真实项目当前状态

- 30分钟Kilosort4默认参数得到4个候选cluster；
- 30分钟较低阈值运行得到5个候选cluster；
- 全时长Kilosort4得到12个候选cluster；
- 数据提供者口头提到8个细胞，暂时没有对应的Phy、NEX、MAT或人工标签文件；
- 这些数字不能直接比较召回率；
- 当前需要逐个复核全时长12个候选cluster，并与30分钟、其他sorter和后续人工结果交叉检查。
