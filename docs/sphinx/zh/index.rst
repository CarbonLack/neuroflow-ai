NeuroEphys AI
==============

**开发预览版 · v0.10.0-dev**

NeuroEphys AI 是面向在体细胞外多通道电生理的本地工作台。一个项目可以连续保存
原始数据导入、质量控制、预处理、spike sorting、Unit 人工复核、行为同步、神经
分析、统计、解码、图表编辑和溯源记录。

当前版本用于展示产品雏形、验证工具互操作性和收集可复现的测试反馈。候选 Unit、
统计结果和生物学解释仍需研究者审核。

.. raw:: html

   <img class="product-shot" src="../assets/neuroflow-analysis.png"
        alt="NeuroEphys AI 神经分析工作区">

当前可用内容
------------

* Neuropixels 类探针、tetrode 和独立微丝教学模拟，包含行为、TTL 和已知 spike 时间。
* 通用二进制和已支持记录系统的直接导入入口。
* 多种 sorter 的原生结果可转换为“Unit 编号 + 秒制 spike 时间 + 来源记录”的公共接口。
* 波形、不应期、振幅和稳定性证据支持的 Unit 人工复核。
* Raster、PSTH、群体热图、统计、解码和可编辑矢量图导出。
* 可选的受控 AI 助手。模型服务关闭时，手动分析仍可运行。

语言
----

中文手册 · `English documentation <../en/index.html>`_

.. toctree::
   :maxdepth: 2
   :caption: 开始使用

   requirements-install
   first-project
   workflow

.. toctree::
   :maxdepth: 2
   :caption: 科学分析流程

   sorting-curation
   events-analysis
   statistics-ml

.. toctree::
   :maxdepth: 2
   :caption: 产品手册

   ai-assistant
   figures
   parameter-reference
   provenance
   real-data-validation
   troubleshooting
   sources
