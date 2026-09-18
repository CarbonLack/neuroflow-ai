# 神经电生理编码/解码分析流程

## 1. 先区分“编码”与“解码”

- **编码分析**问：刺激、选择、运动或奖励发生时，单个 Unit 或神经群体的活动如何变化。常见输出是 raster、PSTH、调谐/条件效应、群体热图与潜在轨迹。
- **解码分析**问：只看留出的神经活动，模型能否预测一个预先定义的离散标签或连续变量。它是可预测信息的检验，不自动证明因果关系，也不等同于“脑区专门编码某抽象概念”。

NeuroEphys AI 因此把流程分成“先验证事件与响应，再做交叉验证模型”，同时在项目中保留两者的共同 trial、时间窗和标签来源。

## 2. 推荐的完整路径

1. **确认数据与时钟**：核对 Unit、事件/行为时间、同步、trial 定义和排除规则。
2. **标签可用性检查**：显示标签来自 `condition`、`label` 还是 `event_type`，列出每类 trial 数；少于两个有效类别时停止，不用含糊的模型错误代替数据诊断。
3. **单 Unit 编码图**：每个 Unit 的 raster、条件 PSTH/SEM、baseline 与 response window、trial 级响应，以及效应方向和不确定性。
4. **总体/群体图**：Unit × time 排序热图、条件平均群体响应、单 trial 群体活动、PCA 轨迹与解释方差。总体图补充而不替代单 Unit 证据。
5. **构建特征**：以 trial 为样本；从预先定义的因果时间窗提取每个 Unit 的计数或放电率。预测行为时不能使用行为发生后的信息。
6. **交叉验证**：二分类默认分层折叠；多 session/动物时按 session 或动物分组留出。缩放、PCA、特征选择和超参数搜索必须只在训练折拟合。
7. **主要性能图**：交叉验证混淆矩阵、balanced accuracy、ROC/AUC、precision/recall/F1，并明确机会水平、每类样本数和折数。
8. **置换基线**：在保持合法分组的前提下打乱标签，比较观察分数与零分布，并报告置换次数和经验 p 值。
9. **时间分辨解码**：在事件对齐时间 bin 内重复完整验证，绘制性能随时间曲线；正式时间段推断应使用 cluster/permutation 或其他多重比较控制。
10. **可解释性与稳健性**：报告 Unit 重要性或线性权重、neuron-count 曲线、不同模型/时间窗的敏感性；权重不是因果贡献。
11. **群体几何**：PCA/LDA/dPCA 或条件轨迹用于描述表示结构；可视化分离不替代交叉验证和置换检验。
12. **可复现导出**：保存 trial 特征、真实/预测标签、折分配、随机种子、模型版本、全部图表和 Methods。

## 3. App 中的对应输出

“08 神经活动 → 完整神经活动分析包”一次生成所有当前数据可支持的神经图，并写入：

`results/neural_activity_complete/`

- `figures/`：PNG 与可编辑 SVG；
- `tables/`：Unit、群体、LFP、耦合与统计表；
- `arrays/`：完整群体数组；
- `methods.md`、`workflow.json`、`provenance.json`：参数、流程与软件版本。

“10 机器学习”在运行前显示标签来源、类别计数、trial 数和 Unit 数。分类成功后同一张总览包含混淆矩阵、置换零分布、ROC/AUC、时间分辨性能、群体 PCA 轨迹和 Unit 重要性。

完整包中的精细时序是快速筛查：默认固定随机种子，最多 30 个 Unit 对、每对 20 次 jitter surrogate。正式全量 CCG/连接推断应进入专家入口，扩大 Unit 对范围并通常使用至少 1,000 次 surrogate；软件会保存实际配置和是否截断。

## 4. 本次 Session 7 故障的解释

旧版只从事件记录的 `condition` 字段取分类标签；这批 benchmark 把有效信息保存在 `label` 字段。因此 132 个事件虽然实际由 66 次 `lever_press` 与 66 次 `reward_delivery` 构成，却在事件分析结果里全部变成 `unknown`，解码器只看到一个类别并停止。

v1.3.2 按 `condition → label → event_type → event/event_code` 的优先级解析标签，记录实际来源，并把类别计数、失败原因与修复建议同时提供给界面和 AI。它不会凭空创造标签；真实数据没有可靠条件字段时仍会明确停止。

## 5. 方法依据

- scikit-learn：交叉验证、分层拆分、混淆矩阵和置换检验。<https://scikit-learn.org/stable/modules/cross_validation.html>、<https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.permutation_test_score.html>、<https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html>
- Elephant：放电率、ISI、Fano factor、CCH 与群体 spike-train 统计。<https://elephant.readthedocs.io/en/stable/reference/statistics.html>、<https://elephant.readthedocs.io/en/stable/reference/_spike_train_processing.html>
- 近期神经群体研究的常见做法包括无重叠的交叉验证、标签置换、时间分辨解码和 cluster permutation；具体设计必须服从实验的 session/动物层级与因果时间关系。

