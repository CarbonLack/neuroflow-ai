NeuroEphys AI 操作手册
==================================================

.. raw:: html

   <p class="manual-kicker">本地电生理分析工作台 · v1.2.0</p>

从手头的数据出发，完成质控、sorting、Unit 复核、事件分析和结果导出。
这里按 App 中的实际操作组织教程；第一次使用，可以先用教学示例完成一次保存和重新打开。

.. raw:: html

   <nav class="task-links" aria-label="按当前任务开始">
     <a class="task-link" href="quick-start.html"><strong>第一次使用</strong><span>打开 8 通道教学示例，运行质控，保存一张图，再重新打开项目。</span></a>
     <a class="task-link" href="first-project.html"><strong>分析自己的数据</strong><span>按原始记录、已有 sorting 或 NeuroEphys 项目选择入口。</span></a>
     <a class="task-link" href="workspace.html"><strong>找到按钮与调整窗口</strong><span>三栏布局、当前分析、AI 助手、教程、快捷键。</span></a>
     <a class="task-link" href="troubleshooting.html"><strong>遇到问题</strong><span>从无法运行、数据不对、图没更新和项目路径丢失开始排查。</span></a>
   </nav>

.. raw:: html

   <a href="../assets/neuroephys-workspace-zh.png"><img class="product-shot" src="../assets/neuroephys-workspace-zh.png" alt="NeuroEphys AI 分析工作区：左侧步骤、中间图表、右侧助手"></a>
   <p class="figure-note">点击截图查看原尺寸。菜单和控件名称与 App 中文界面对应。</p>

先选分析路线
------------

**有原始电压：** 从导入和原始质控开始，再选择预处理和 sorter；完成 Unit 复核后做下游分析。

**有 Kilosort、Phy 或人工筛选结果：** 导入已有结果，检查 Unit 和时间单位，从 Unit 质控继续。
只有结果文件、没有原始电压时，不能重新 sorting，也不能补回缺少的原始波形。

**已有 NeuroEphys AI 项目：** 使用 **打开／导入项目**，选择 ``neuroflow_project.json``。
保存的项目目录与被链接的原始记录都应保留。

十一阶段是导航顺序。实际能运行哪些分析，取决于项目已有的输入；事件分析需要事件，
LFP 分析需要保留低频成分的数据。每次先看页面底部“当前”所选内容，再运行。

.. toctree::
   :maxdepth: 1
   :caption: 开始与日常操作

   quick-start
   requirements-install
   first-project
   workspace
   task-guide
   workflow
   provenance

.. toctree::
   :maxdepth: 1
   :caption: 按分析任务查阅

   sorting-curation
   events-analysis
   statistics-ml
   figures
   ai-assistant

.. toctree::
   :maxdepth: 1
   :caption: 参数、验证与排障

   parameter-reference
   real-data-validation
   troubleshooting
   sources

Windows App 与 Python 包共享分析能力，但并非每个脚本选项都有对应的界面控件。
各模块的已验证范围见 :doc:`real-data-validation`；候选 Unit 与统计解释需结合实验判断。

`English manual <../en/index.html>`_ · `下载发布版 <https://github.com/CarbonLack/neuroflow-ai/releases>`_
