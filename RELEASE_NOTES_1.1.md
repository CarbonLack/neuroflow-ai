# NeuroEphys AI 1.1.0 发行说明

NeuroEphys AI 1.1 将公开发表数据作为外部压力测试，增强的仍然是通用的
细胞外电生理工作平台，而不是论文抓取或一键复现工具。

## 新增功能

- 单 trial/群体动态：按事件和脑区选择，可调 bin、Gaussian sigma、
  基线层级与峰值/PCA/可选 Rastermap 排序。
- 每 trial 有效时间窗：支持可变反应时任务，不把 trial 外时段误当作零放电。
- 群体图：排序热图、单 trial、条件比较和 PCA 轨迹可切换，并可导出
  SVG/PDF/PNG、CSV 和压缩数组。
- 连续行为回归：神经—行为时滞、完整 trial 留出、线性/岭回归和重复的
  神经元数量—性能扫描。
- 精细时序/功能关系：三种 CCG 归一化、固定窗/中心抖动、侧翼标准差/
  经验 P 值、FDR/Bonferroni、脑区/距离筛选和可审计的 pair cap。
- 三个正式入口：桌面 App、`neuroephys` Python API 和 `neuroephys population` /
  `neuroephys connectivity` 命令行。

## 公开数据验收

Trautmann et al. (2025) Fig. 7 公开 LIP/SC 数据（Zenodo 7946011）通过了来源校验和
定量对照。在作者披露的 trial 筛选、1 ms bin、Gaussian sigma=25 ms、单 trial 有效窗
和刺激/眼跳双对齐下，NeuroEphys AI 与作者 MATLAB 核的逐点一致性为：

- LIP：`r=0.998685`；
- SC：`r=0.998148`。

论文声明用于 Figs. 1--6/8 的 Zenodo DOI 在验证时未注册/返回 404，这些图不标记
为已复现。论文专用加载和 panel 布局仅位于独立验证工作区，不进入核心产品。

## 发行物

- `NeuroEphysAI-Setup-1.1.0.exe`；
- `NeuroEphysAI-1.1.0-Windows-x64-portable.zip`；
- `neuroephys_ai-1.1.0-py3-none-any.whl`；
- `neuroephys_ai-1.1.0.tar.gz`；
- `SHA256SUMS.txt`。
