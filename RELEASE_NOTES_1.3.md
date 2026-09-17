# NeuroEphys AI 1.3 release notes

## 1.3.0：多 Session／多动物 Study 层

本版在既有单 Session 十一阶段流程之上增加独立 Study 工作区。单个项目的导入、质控、
sorting、Unit 复核、行为同步和事件分析保持不变；完成后的项目可以被 Study 只读索引，
用于跨 Session／跨动物汇总。

### 新增能力

- 文件菜单、首页和 Ctrl+K 操作查找中增加“多 Session 研究”；
- Study 清单显式记录生物学动物编号、唯一 Session 编号、纳入状态、项目状态和共有条件；
- 用户可选择两个共有条件、Logistic、线性/RBF SVM、收缩 LDA 或随机森林；
- 按整只动物或整个 Session 留出，标准化仅在训练折拟合；
- 逐留出组性能、混淆矩阵、组内标签置换、分组 bootstrap 区间；
- Session 条件效应汇总；动物数足够时尝试带动物随机截距和 Session 方差分量的混合模型；
- 固定维度群体分布特征，不默认匹配跨 Session Unit ID；
- 描述性 PCA + 正则化线性状态转移轨迹；
- 英文 SVG/600 DPI PNG、CSV 与 JSON 完整导出；
- Windows App 后台计算、窄窗口纵向重排；
- Python API 与 `study-create`、`study-add`、`study-inspect`、`study-run` CLI；
- AI 上下文可读取脱敏 Study 摘要，并在协作模式提出受控运行；原始电压、本地路径和
  动物/Session 明细不会进入云端摘要。

### 科学边界

- 只有一只动物时自动退回 Session 留出，不宣称跨动物泛化；
- 相同 Unit 编号不是跨 Session 细胞身份；
- LDA 是监督分类器，潜在动力学是另一个描述模型；
- 解码性能只说明指定验证设计下存在可预测信息，不等于因果或神经机制；
- 极少动物时不提供随机效应确认性推断。

完整操作与方法说明见 `docs/MULTI_SESSION_ANALYSIS_ZH.md` 和双语网页手册的
“统计、机器学习与科学边界”。
