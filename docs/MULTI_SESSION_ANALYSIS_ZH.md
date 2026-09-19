# NeuroEphys AI 多 Session／多动物分析路径

## 1. 为什么单独建立 Study 层

一个 NeuroEphys AI 项目对应一次记录 Session；Study 是若干已完成项目的索引和汇总结果，
不复制原始电压，也不改写各 Session 的结果。这样既能保留单 Session 的可追溯性，又能在
Study 中正确表达 `trial → session → animal` 的嵌套关系。

跨 Session 分析中，trial 数多不等于动物数多。不能把同一动物的几百个 trial 当成几百个
独立生物学重复，也不能因为两个项目里都出现 `Unit 7`，就假设它们是同一个神经元。
NeuroEphys AI 默认执行以下保护：

1. 整只动物或整个 Session 留出，禁止同组样本同时进入训练和测试；
2. 不跨 Session 匹配 Unit 编号；
3. 用固定维度的群体分布特征汇总不同数量的 Unit；
4. 动物数不足时不报告动物层级的确认性推断；
5. 数据标准化放进每个训练折，避免用测试集均值和方差训练模型。

## 2. 标准电生理分析路径

### A. 每个 Session 内

1. **数据与元数据核对**：采样率、通道、探针/脑区、动物、Session、事件来源。
2. **原始质量控制**：噪声、坏通道、饱和、工频；只有高通数据时明确跳过 LFP。
3. **sorting 与 Unit 复核**：保留 sorter 原生结果，结合波形、ISI、SNR、稳定性和重复 Unit 风险人工复核。
4. **时间同步**：用 TTL 将行为时钟映射到电生理时钟，检查 offset、slope、残差和事件顺序。
5. **事件对齐**：预先定义基线窗、响应窗、bin、平滑和条件；输出 Raster、PSTH、单 trial 和群体图。
6. **Session 内统计**：效应量、区间、置换/参数或非参数检验；Unit 或 trial 的观察层级必须写清楚。

### B. Study 层

1. **覆盖检查**：所有纳入 Session 必须有相同命名的两个待比较条件，且事件分析时间轴一致。
2. **描述性汇总**：先看每个 Session 的条件效应、trial 数、Unit 数和缺失情况。
3. **层级统计**：动物足够时，用动物随机截距和 Session 方差分量处理嵌套相关性；否则只报告描述结果。
4. **跨组解码**：优先按动物留出；只有一只动物时退回按 Session 留出，并明确不能外推到新动物。
5. **置换与不确定性**：标签只在相应组内置换；性能区间按留出组 bootstrap，而不是按 trial 随机抽样。
6. **随时间与时间泛化解码**：使用同一整组划分查看信息何时出现，并用 train-time × test-time 矩阵判断读出规则是短暂还是稳定。
7. **跨 Session 转移**：从一个完整 Session 训练、到另一个完整 Session 测试；对角线改用 Session 内交叉验证，避免显示乐观的训练分数。
8. **表征与子空间稳定性**：在不匹配单细胞的前提下，比较条件差异轨迹相关和低维群体矩子空间。
9. **群体动力学**：最后查看低维轨迹与近似线性转移，作为群体状态描述，不替代层级统计。

## 3. 当前模型分别回答什么

| 方法 | 回答的问题 | 主要优点 | 不能说明 |
|---|---|---|---|
| Logistic regression | 条件能否由群体特征线性预测 | 可解释的基线 | 非线性结构、因果 |
| Linear SVM | 是否存在稳定的线性最大间隔分离 | 适合特征数相对高的场景 | 概率并非天然机制量 |
| RBF SVM | 是否存在非线性可分信息 | 灵活的非线性对照 | 小样本易过拟合，解释性低 |
| Shrinkage LDA | 类别均值与收缩协方差能否形成线性分离 | 小样本线性基线 | 不是 latent dynamics model |
| Random forest | 非线性交互能否改善预测 | 可捕捉非线性和交互 | 特征重要性不等于因果贡献 |
| PCA + linear dynamics | 群体状态如何在低维空间随时间演化 | 轨迹直观、模型透明 | 不是深度生成模型，不证明真实动力学方程 |
| Linear mixed model | 条件效应在动物/Session 相关性后是否仍有证据 | 尊重层级结构 | 极少动物下的随机效应不可靠 |

用户曾提到“LDM”。这个缩写可能被不同领域用于不同模型，本软件不把它与 LDA 混为一谈：
当前明确实现并显示全称的是 **PCA + ridge-regularized linear state-transition model**。
未来若增加 GPFA、LFADS、dPCA、jPCA 或跨 Session manifold alignment，必须分别写清输入、
训练目标、验证方式和适用边界，不能统一标成“高级分析”。

## 4. 当前跨 Session 特征

每个 trial 先对每个 Unit 计算“响应窗放电率 − 基线窗放电率”，再跨 Unit 提取：

- 均值、中位数、标准差；
- 25% 和 75% 分位数；
- 响应增加 Unit 的比例；
- 响应窗放电率的均值和标准差。

这些特征不会依赖 Unit 数量或 Unit 编号，因此适合“不同 Session 没有可靠细胞追踪”的默认情况。
代价是它们会丢失单神经元身份和精细群体几何。若实验确有慢性细胞追踪、共享电极几何或经过验证的
跨天配准证据，应在未来增加显式的 matched-cell 模式，而不能偷偷复用当前 Unit ID。

## 5. 在 App 中操作

1. 分别打开每个 Session 项目，完成 Unit 质控、事件同步和事件对齐分析并保存。
2. 选择 **文件 → 多 Session 研究…**，点击“新建研究”。
3. 点击“添加 Session 项目…”，选择各项目的 `neuroflow_project.json`。
4. 为每个项目填写真实动物编号和唯一 Session 编号；取消勾选即可排除但保留记录。
5. 选择两个所有 Session 共有的条件、整组留出层级、模型和置换次数。
6. 点击“运行期刊级多 Session 综合分析”。计算在后台进行，一次完成主分析和控制分析。
7. 先查看主图的覆盖/QC、条件效应、留出组性能、混淆矩阵、随时间解码和低维轨迹；再用附图核对时间泛化、跨 Session 转移、表征稳定性、置换空分布和采样平衡。
8. 结果位于 Study 的 `results/multi_session`：
   - `trial_features.csv`
   - `session_condition_summary.csv`
   - `held_out_group_metrics.csv`
   - `held_out_group_scores.csv`
   - `grouped_decoding_predictions.csv`
   - `multi_session_results.json`
   - `main_figure_multi_session.svg/png`
   - `supplementary_figure_controls.svg/png`
   - `time_resolved_decoding.csv`
   - `temporal_generalization_matrix.csv`
   - `cross_session_transfer_matrix.csv`
   - `representation_similarity_matrix.csv`
   - `subspace_similarity_matrix.csv`
   - `INTERPRETATION.md`

## 6. AI 可以做什么

Study 保存后，会以安全摘要注册到当前项目的 AI 上下文。AI 可以读取研究 ID、动物/Session 数、
所选条件、既有结果和解释边界，并在协作模式中提出 `run_multi_session_analysis`。本地仍会验证研究是否
存在、参数是否合法，并要求用户确认；原始电压、完整数组和本地路径不会作为对话上下文上传。

AI 适合：解释图、比较模型、发现身份或覆盖问题、建议下一项检查。AI 不能：替代动物/Session 元数据核对、
自动宣布显著性、把预测解释成因果、或在没有细胞追踪证据时匹配神经元。

## 7. 方法与实现依据

- scikit-learn grouped cross-validation：<https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data>
- scikit-learn LDA：<https://scikit-learn.org/stable/modules/lda_qda.html>
- statsmodels MixedLM：<https://www.statsmodels.org/stable/mixed_linear.html>
- Yu et al., GPFA：<https://doi.org/10.1152/jn.90941.2008>
- Cunningham & Yu, dimensionality reduction review：<https://doi.org/10.1038/nn.3776>

这些来源用于核对方法定义与软件接口；NeuroEphys AI 的 Study 数据模型、保护规则、界面、导出和教程为
本项目独立实现。
