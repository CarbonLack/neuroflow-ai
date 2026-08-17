方法、软件与来源
================

NeuroEphys AI 通过公开接口调用成熟库，并自主开发项目、适配器、工作流、解释、图表
和审计层。本站方法说明均使用原创表述。

核心来源
--------

* `SpikeInterface 官方文档 <https://spikeinterface.readthedocs.io/en/stable/>`_
  ——记录读取、预处理、sorter 接口、后处理和质量指标。
* `Kilosort4 官方文档 <https://kilosort.readthedocs.io/en/latest/>`_
  ——安装、参数、运行、导出文件和 Phy 衔接。
* `Elephant 官方文档 <https://elephant.readthedocs.io/en/latest/>`_
  ——基于 Neo 的 spike train 与电生理分析。
* `Neo 官方文档 <https://neo.readthedocs.io/en/stable/>`_
  ——通用电生理数据对象。
* `NWB 官方文档 <https://nwb-overview.readthedocs.io/>`_
  ——神经生理数据标准组织。
* `IBL ONE 官方文档 <https://int-brain-lab.github.io/ONE/>`_
  ——IBL 公开数据和 ALF 对象访问。
* `DANDI Archive 文档 <https://docs.dandiarchive.org/>`_
  ——公开 NWB 数据查找与下载。
* `Trautmann et al. 2025 <https://doi.org/10.1038/s41593-025-01976-5>`_ 与
  `Fig. 7 公开数据/代码 <https://zenodo.org/records/7946011>`_
  ——NHP 高密度记录的外部验收和单 trial/精细时序方法定义。
* `Rastermap 论文与官方代码 <https://github.com/MouseLand/rastermap>`_
  ——可选群体活动排序后端；未捆绑时使用内置峰值时间或 PCA 排序。
* `DeepSeek API 文档 <https://api-docs.deepseek.com/>`_
  ——可选在线结构化生成和工具调用传输。
* `Ollama OpenAI 兼容接口 <https://docs.ollama.com/api/openai-compatibility>`_
  ——可选本机模型服务。

来源标注与数据
--------------

每个公开验证项目记录数据编号、版本、来源网址和本地转换。私人记录不进入公开仓库和
发布压缩包。第三方许可证归各项目所有，本仓库不重新发布其源代码或文档原文。
