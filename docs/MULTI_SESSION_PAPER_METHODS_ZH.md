# 多 Session 电生理分析：论文证据、问题链与 NeuroEphys AI 实现

## 1. 不是“把 Session 拼在一起”

多 Session 分析首先要确定推断单位。trial 嵌套在 Session 中，Session 可能继续嵌套在动物中；同一
Session 的 trial 不能随机拆到训练集和测试集两侧。不同 Session 中相同 Unit ID 默认也不是同一个
神经元。NeuroEphys AI 因而使用整组留出、Session 内置换和以 Session 为单位的 bootstrap。

当前 20 分钟 benchmark 没有动物编号，所以只允许“留出整个 Session 后仍可解码”的结论；界面和
报告会明确禁止把它写成跨动物泛化或生物学重复。

## 2. 论文主图和附图通常分别回答什么

| 论文做法 | 主图承担的问题 | 附图/扩展数据承担的问题 | App 中的对应实现 |
|---|---|---|---|
| IBL brain-wide map：单细胞条件敏感性、正则化解码、跨 Session 汇总的群体轨迹、编码模型 | 哪些任务变量能被神经元和群体表示，何时出现 | 纳入阈值、空模型、FDR、不同区域/细胞标准、二维切片和完整时间轨迹 | Session QC、配对群体效应、分组解码、随时间解码、轨迹与明确的纳入边界 |
| Steinmetz 等：刺激、选择、动作和投入度的分布式编码 | 单细胞与群体信号如何贯穿任务时间线 | 区域、样本量、模型和行为混杂控制 | 不只画 PSTH；同时输出逐 Session 效应、混淆矩阵、留出组结果和置换空分布 |
| Gallego 等：跨日潜在动力学、CCA 对齐、跨日解码 | 行为稳定时，群体动力学是否保留 | 未对齐对照、维数敏感性、静态簇对照、不同脑区和 sorted-unit 对照 | 不追踪 Unit ID；比较固定群体矩空间中的条件轨迹相关、子空间相似和跨 Session 转移矩阵 |
| 时间泛化研究：在一个时间窗训练、在所有时间窗测试 | 信息何时出现，神经代码是短暂变化还是稳定维持 | 时间窗、平滑、chance/null 与不同亚群控制 | 同一整组交叉验证划分下输出 train-time × test-time 时间泛化矩阵 |
| Tetrode/海马研究：逐 Session place field、群体位置解码、跨日稳定性 | 空间表征和解码是否稳定 | field 匹配、波形/ISI、行为采样和不同 bin 的控制 | 只有存在真实 x/y、速度和轨迹时才启用空间分析；本 benchmark 无位置变量，因此绝不生成伪 place field |

主要核对来源：

- [IBL, A brain-wide map of neural activity during complex behaviour](https://www.nature.com/articles/s41586-025-09235-0)
- [Steinmetz et al., Distributed coding of choice, action and engagement across the mouse brain](https://www.nature.com/articles/s41586-019-1787-x)
- [Gallego et al., Long-term stability of cortical population dynamics underlying consistent behavior](https://www.nature.com/articles/s41593-019-0555-4)
- [Trautmann et al., Large-scale high-density brain-wide neural recording in nonhuman primates](https://www.nature.com/articles/s41593-025-01976-5)
- [Flexible neural population dynamics govern the speed and stability of sensory encoding](https://www.nature.com/articles/s41467-024-50563-y)
- [Distinct timescales of population coding across cortex](https://www.nature.com/articles/nature23020)

## 3. 一次运行生成的完整问题链

1. **数据是否可比？** 输出每个 Session 的 Unit 数、对齐事件数、条件计数、平均发放率和零计数比例。
2. **平均反应是否一致？** 输出每个 Session 的 `response − baseline` 条件效应，以及 Session 配对
   bootstrap 区间；有至少三只真实动物时才尝试层级混合模型。
3. **信息能否推广？** 整个动物或整个 Session 留出；所有标准化仅在训练折拟合；输出 balanced
   accuracy、ROC AUC、混淆矩阵、逐留出组结果和 Session 内标签置换。
4. **信息何时出现？** 对每个时间 bin 重复同一整组验证，输出随时间的 balanced accuracy 和整组
   bootstrap 区间。
5. **神经代码是否随时间稳定？** 输出 train-time × test-time 时间泛化矩阵。对角线是瞬时可解码性，
   离对角线的高值说明读出规则可以跨时间复用。
6. **能否从一个 Session 转移到另一个？** 行为/事件条件不变时，输出完整 train-session ×
   test-session 矩阵；对角线采用 Session 内交叉验证，不显示乐观的训练准确率。
7. **群体表征是否相似？** 在不匹配细胞的前提下，比较群体分布矩的条件差异轨迹相关和低维子空间
   相似度。这是表征稳定性的描述，不是“同一细胞被连续追踪”。
8. **动力学如何演化？** PCA 只用于可视化固定群体矩轨迹；ridge 状态转移仅提供描述性 R² 和时间尺度，
   不作因果或深度生成模型声明。

## 4. 主图与附图分工

- **英文主图**：研究覆盖/QC、留出 Session 解码、混淆矩阵、逐 Session 条件效应、随时间解码、
  群体潜在轨迹。顺序是“数据可信 → 平均效应 → 可推广信息 → 时间过程 → 动力学”。
- **英文附图**：跨 Session 转移、时间泛化、条件轨迹相似、子空间相似、置换空分布、Unit 数与发放率
  敏感性。它们检验主结论是否依赖某个 Session、某一时刻或样本量失衡。
- **完整表格**：所有图均有 CSV；另有完整 JSON 和 `INTERPRETATION.md`，不让“只剩一张图、无法审计”。

## 5. 不能从当前 benchmark 得出的结论

- 没有真实动物 ID，不能声称跨动物泛化或计算动物层随机效应。
- 使用外部模拟 ground truth 是验证工作流，不是 sorter 在真实数据上的准确率。
- 没有 x/y、速度和轨迹，不能生成 place field、空间信息量或 Bayesian position decoding。
- 不同 Session 的 Unit ID 不表示同一细胞；若未来提供 waveform/geometry/cell-tracking 证据，应作为
  独立的可选模块加入，而不能静默假设。
