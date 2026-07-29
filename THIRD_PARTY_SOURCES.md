# 第三方软件、方法与资料来源

NeuroEphys AI 采用“复用成熟计算能力、保留原生输出、自主实现适配与交互层”的工程原则。
仓库不复制第三方界面、教程原文、论文图片或论文数值结果。每个集成组件继续适用其原始许可证。

## 运行时科学组件

| 组件 | 用途 | 官方来源 |
|---|---|---|
| SpikeInterface | 数据读取、预处理、sorter适配、质量指标与结果比较 | https://spikeinterface.readthedocs.io/en/stable/ |
| Kilosort4 | 高密度及多通道spike sorting | https://kilosort.readthedocs.io/en/stable/ |
| MountainSort5 | CPU-oriented spike sorting | https://pypi.org/project/mountainsort5/ |
| SpyKING CIRCUS 2 | 多通道spike sorting | https://spikeinterface.readthedocs.io/en/stable/modules/sorters.html |
| Tridesclous 2 | CPU spike sorting | https://spikeinterface.readthedocs.io/en/stable/modules/sorters.html |
| Elephant | Spike train统计与相关分析 | https://elephant.readthedocs.io/en/stable/ |
| Neo | 带单位的神经生理数据对象 | https://neo.readthedocs.io/en/stable/ |
| SciPy / statsmodels | 统计检验与多重比较 | https://docs.scipy.org/doc/scipy/ ; https://www.statsmodels.org/ |
| scikit-learn | 分类、回归、聚类、降维与交叉验证 | https://scikit-learn.org/stable/ |
| Matplotlib | 交互图形与PNG/SVG/PDF导出 | https://matplotlib.org/stable/ |
| PySide6 | 桌面界面 | https://doc.qt.io/qtforpython-6/ |
| nex5file | NeuroExplorer `.nex5` 文件读取；保留原始候选 unit、spike 时间与波形摘要 | https://neuroexplorer.com/docs/python_packages/nex5file.html |

完整依赖版本由项目导出的环境记录提供。发布可执行包前应再次核对实际打包组件的许可证与再分发要求。

`nex5file` 采用 MIT 许可证。NeuroEphys AI 调用该软件包公开 API，
没有复制 NeuroExplorer 示例脚本、第三方 MATLAB 读取器、软件界面或教程文字。

## 方法与教程来源

- Kilosort4参数、导出与人工复核：
  https://kilosort.readthedocs.io/en/stable/README.html
  和 https://kilosort.readthedocs.io/en/stable/export_files.html
- SpikeInterface质量指标：
  https://spikeinterface.readthedocs.io/en/stable/modules/metrics/quality_metrics.html
- Elephant STTC：
  https://elephant.readthedocs.io/en/latest/reference/_toctree/spike_train_correlation/elephant.spike_train_correlation.spike_time_tiling_coefficient.html
- Phy人工复核：
  https://phy.readthedocs.io/en/latest/quickstart/
- DeepSeek API、函数调用与工具调用：
  https://api-docs.deepseek.com/api/create-chat-completion
  和 https://api-docs.deepseek.com/guides/function_calling/
- DeepSeek 当前模型标识、兼容地址与能力：
  https://api-docs.deepseek.com/api/list-models
  和 https://api-docs.deepseek.com/quick_start/pricing

网站“方法与来源”页逐项描述借鉴范围。全部解释文字由项目团队重新撰写。
