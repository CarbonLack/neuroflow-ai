统计、机器学习与科学边界
========================

统计设计从生物学样本单位开始。Spike、Unit、session 和动物处于不同层级，未经论证
不能当作彼此独立的重复。

统计检验
--------

工作台提供配对与非配对检验、非参数替代、bootstrap 区间、置换检验、效应量、
多重比较校正、诊断和混合效应支持。混合模型只有在项目包含所需层级字段时才运行。

运行前定义：

* 观察单位；
* 配对或重复测量关系；
* 基线窗和响应窗；
* 多重比较所属检验族；
* 动物与 session 编号；
* 查看结果前确定的排除条件。

p 值需要与效应量和不确定性共同报告。未达到显著性的结果会如实保留，系统不会将其
改写成神经编码证据。

神经解码
--------

分类和回归使用事件/trial 级特征。输出包括交叉验证性能、混淆矩阵、适用时的
ROC/F1、标签置换证据、时间分辨结果、群体轨迹和特征重要性。

同一 session 或动物的样本可能同时进入训练集和测试集时，应使用分组划分。标准化、
特征筛选和降维应在每个训练折内部拟合。还需检查类别平衡和完整 null 分布。

阅读图表
--------

混淆矩阵同时显示计数和按行归一化比例。置换面板标出观察值与机会水平。缺少独立
验证的高训练分数不会作为科学结果展示。

机器学习性能说明指定验证设计下存在可预测信息。因果、机制和跨动物泛化仍需额外证据。

多 Session／多动物研究
----------------------

单个项目仍对应一个 recording session。完成各 Session 的事件对齐分析后，从
**文件 → 多 Session 研究…** 建立 Study，把多个 ``neuroflow_project.json`` 加入同一研究。
每行都必须填写真实的动物编号和唯一 Session 编号；电极、脑区或通道组不能冒充动物。

Study 工作区按以下层级处理数据：``trial → session → animal``。它提供：

* Session/动物整组留出的 Logistic、线性或 RBF SVM、收缩 LDA 和随机森林；
* 在每折训练集内部完成标准化，避免预处理信息泄漏；
* 分组 bootstrap 区间、组内标签置换和逐留出组性能；
* 每 Session 的条件效应汇总；动物数足够时才尝试动物随机截距、Session 方差分量的
  线性混合模型；
* 固定维度的群体分布特征，因此不会错误地把不同 Session 的 ``Unit 7`` 当作同一个细胞；
* 描述性的潜在动力学：PCA 后拟合正则化线性状态转移，并报告轨迹、解释方差和转移
  拟合度。

LDA（linear discriminant analysis）是监督分类方法；界面中的潜在动力学不是 LDA，
也不是深度生成模型。它只能概括当前数据中的低维轨迹与近似线性演化，不能证明动力学
机制或因果关系。

推荐顺序
~~~~~~~~

1. 每个 Session 单独完成导入、Unit 质控、TTL/行为同步和同一时间窗的事件分析；
2. 检查所有 Session 的条件名称、基线窗、响应窗和 bin 是否一致；
3. 建立 Study，核对动物与 Session 身份，明确排除项；
4. 先看 Session 级效应和数据覆盖，再运行按动物留出的线性基线模型；
5. 比较非线性模型时保留相同划分，并用置换分布判断性能是否超过该设计下的机会水平；
6. 最后查看低维轨迹，作为群体状态描述，而不是替代分层统计或独立验证。

只有一只动物时，软件自动退回 Session 留出，并明确标记结果不能作为跨动物推断。
不同 Session 的 Unit 身份只有在另行提供细胞追踪证据时才能匹配；当前安全默认是“不匹配”。

Python 与命令行
~~~~~~~~~~~~~~~~~~~~~~~~

Python 包提供 ``StudyState``、``add_project``、``run_multi_session_analysis`` 和
``run_latent_dynamics``。命令行可建立、检查和运行 Study：

.. code-block:: powershell

   neuroephys study-create D:\Study01 --name "Learning cohort"
   neuroephys study-add D:\Study01 D:\Projects\S01\neuroflow_project.json --animal A01 --session S01
   neuroephys study-inspect D:\Study01
   neuroephys study-run D:\Study01 --model "Linear SVM" --group-by animal --conditions correct error

输出保存为英文 SVG/PNG、trial 特征、留出组指标、预测表、Session 条件汇总和完整 JSON，
位于 Study 的 ``results/multi_session``。

.. raw:: html

   <img class="product-shot" src="../assets/neuroephys-decoding-zh.png"
        alt="NeuroEphys AI 中文交叉验证、置换检验与 ROC 页面">

向下滚动后，时间分辨解码、群体 PCA 轨迹和 Unit 特征重要性分别作为独立可编辑子图
显示。

.. raw:: html

   <img class="product-shot" src="../assets/neuroephys-decoding-detail-zh.png"
        alt="NeuroEphys AI 中文时间分辨解码和群体分析明细">
