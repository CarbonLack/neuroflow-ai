# NeuroEphys AI 安装与完整使用教程

> 本页面是 GitHub 用户入口。不需要先阅读开发文档。所有原始数据默认留在本机；候选 Unit、自动筛选、统计显著和 AI 建议都需要研究者复核。

## 1. 我应该下载哪个版本？

在 [GitHub Releases](https://github.com/CarbonLack/neuroflow-ai/releases/latest) 中选择：

| 版本 | 适合谁 | 怎么用 | 注意 |
|---|---|---|---|
| **Full 离线安装版（推荐）** `NeuroEphysAI-Setup-1.2.3-Full.exe` | 比赛演示、科研工作站、需要 Kilosort/GPU 的用户 | 双击安装，按组件页选择 | 体积最大；GPU 还取决于 NVIDIA 驱动和硬件 |
| **标准安装版** `NeuroEphysAI-Setup-1.2.3.exe` | 普通 Windows 用户、教学、CPU 分析 | 双击安装 | 后续可在 Sorter 管理器补齐组件 |
| **标准便携版** `NeuroEphysAI-1.2.3-Windows-x64-portable.zip` | 无安装权限或移动硬盘用户 | 完整解压后运行 `NeuroEphysAI\NeuroEphysAI.exe` | 不能只复制单个 EXE |
| **Python 包** `neuroephys_ai-1.2.3-py3-none-any.whl` | 需要脚本、批处理和 API 的用户 | `python -m pip install <wheel>` | 建议 Python 3.12 |

完整 Full 便携 ZIP 大于 GitHub 2 GiB 单文件限制，因此 GitHub 主要提供 Full 安装包。本地构建可另行生成 Full 便携版。

## 2. Windows 安装

1. 从 Release 页下载安装包。
2. 可选：将下载文件与 `SHA256SUMS.txt` 对照，确认文件完整。
3. 双击安装包。Full 版在“组件”页可选桌面应用、科学分析和 GPU/Kilosort 组件。
4. 安装结束后双击 **NeuroEphys AI** 快捷方式。
5. 第一次启动后打开 **帮助 → 环境检测**，查看计算环境、可用 sorter 和磁盘空间。

默认工作区位于 `Documents\NeuroEphysAI`。原始数据保持只读，分析结果保存到独立项目目录。

## 3. 三分钟快速体验

1. 首页选择 **示例项目**。
2. 选择一个教学模拟数据。
3. 在左侧打开 **02 原始质控**，点击“运行此节点”。
4. 查看中间图表和“怎么看”说明；双击坐标轴可进入 Figure Studio。
5. 按 `Ctrl+S` 保存；关闭后在首页选择 **打开/导入项目**，选择 `neuroflow_project.json` 恢复。

按 `Ctrl+Shift+H` 打开可搜索的教程中心，按 `Ctrl+K` 搜索功能。

## 4. 导入自己的数据

在首页选择 **新建项目**，再选择实际入口：

- **通用二进制**：`.bin/.dat/.raw`；填写采样率、通道数、dtype、μV/bit 和交错方式。
- **记录系统**：Intan、Open Ephys、SpikeGLX/Neuropixels、Blackrock、Plexon、TDT、NWB。
- **已有 sorting**：Kilosort/Phy、IBL ALF、含 Units 的 NWB 或 `.nex5`。

创建项目后先在 **01 数据与项目** 核对：来源、采样率、通道数、时长、增益/单位、探针几何和行为事件。任何一项不确定时，不要盲目开始 sorting。

## 5. 行为数据和 TTL 导入

进入 **06 事件同步**，点击 **导入/替换行为与 TTL**。

行为 CSV 通常至少包含：

- `trial`：trial 编号；
- `condition`：条件；
- `event_type` 或事件编号；
- `behavior_time`：行为设备时钟中的时间。

TTL CSV 提供同一同步脉冲在电生理时钟中的时间。平台按顺序配对后拟合 `ephys_time = offset + slope × behavior_time`，并保存脉冲数、漂移和残差。不要在没有 TTL 证据时假定两台设备共用同一时钟。

## 6. 完整分析流程

| 阶段 | 作用 | 运行前核对 | 主要输出 |
|---|---|---|---|
| 01 数据与项目 | 确认来源和流程起点 | 采样率、通道、单位、时长 | 项目清单和来源索引 |
| 02 原始质控 | 检查 RMS、坏道、饱和、工频 | 原始电压是否可用 | QC 图与通道表 |
| 03 预处理 | 高通/带通、参考和预览 | 滤波范围与数据含义 | 可重建缓存和参数 |
| 04 Spike sorting | 使用选定 sorter 生成候选簇 | 环境、几何、时窗、通道 | sorter 原生结果和统一 spike times |
| 05 Unit 质控 | 波形、ISI、SNR、漂移和人工标签 | 候选不等于细胞 | 筛选决定与复核记录 |
| 06 事件同步 | 把行为钟映射到电生理钟 | 脉冲数、顺序、残差 | 对齐事件和同步 QC |
| 07 行为分析 | trial、选择、正确率、反应时 | 事件定义 | 行为图与表 |
| 08 神经活动 | Raster、PSTH、群体动态等 | 对齐点、时窗、bin | 神经响应图 |
| 09 统计检验 | 效应量、置换、bootstrap、多重校正 | 实验单位与假设 | 统计表和方法说明 |
| 10 机器学习 | 分类、回归、解码和聚类 | 防止 trial/时间泄漏 | 交叉验证、置换基线和特征结果 |
| 11 论文与复现 | 英文主图/附图、图注草稿、Methods 和清单 | 所有分析已审阅 | publication 报告和 provenance |

每个节点都可单独运行；不需要一条线走到底。有已完成 sorting 的用户可以直接从 05 开始。

## 7. 三 sorter 对比

在 **04 Spike sorting** 分别运行 Kilosort4、MountainSort5 和 SpyKING CIRCUS2，然后打开“Sorter 统一结果与比较”。确认三次运行使用同一原始记录、通道、时间区间和采样率。

真实数据没有 ground truth，因此工具间 precision/recall/F1 只描述输出一致性，不是真实准确率。任何候选 Unit 都应在 **05 Unit 质控** 中人工复核。

## 8. 图、表和论文导出

- 单击图中元素查看数值；双击坐标轴或点击“编辑子图”进入 Figure Studio。
- **当前对象** 只改一张图的一个对象；**统一样式** 对项目图使用相同字体、线宽、网格和配色。
- “论文与复现”使用英文标签生成主图、附图、子图字母、图注草稿、Methods、完整文件清单和校验值。
- 自动排版不代替研究者对生物学故事、统计、图注和目标期刊规格的终审。

## 9. AI 助手与机构 harness

在 **帮助 → AI 设置** 中选择手动、助手或协作模式。机构提供 OpenAI-compatible harness 时，填写实际 `base URL`、model 和 key，先点击“检测服务状态”。

App 自动生成受控的结构化项目上下文：当前步骤、已有结果、导出件、约束和允许的工具。默认不发送原始电压、大数组、本地路径和身份信息。协作模式中的本地操作仍需要白名单检查和用户确认。

## 10. 项目文件放在哪里？

| 路径 | 内容 |
|---|---|
| `neuroflow_project.json` | App 项目入口 |
| `inputs/` | 原始数据索引和导入信息 |
| `config/` | 参数和版本 |
| `cache/`, `derived/` | 可重建中间产物 |
| `results/` | sorter 原生输出和对比 |
| `exports/` | 图、表、报告和 publication |
| `logs/` | 运行日志、中文实验记录和人工笔记 |

备份时至少保留整个项目目录和原始数据。只复制一张图无法恢复分析。

## 11. Python 安装与最小例子

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install neuroephys_ai-1.2.3-py3-none-any.whl
neuroephys info --json
```

```python
from pathlib import Path
import neuroephys as ne

project = ne.create_simulated_project(Path("example_project"))
quality = ne.run_raw_qc(project)
print(quality["quality_score"])
```

可选依赖和更多 API 见 [README](../README.md) 与[Python 包手册](https://carbonlack.github.io/neuroflow-ai/zh/python-package.html)。

## 12. 常见问题

- **启动时缺 DLL：** 不要单独拷贝 EXE；重新完整安装或完整解压便携版。
- **Kilosort 不可用：** 检查是否使用 Full 版、NVIDIA 驱动、CUDA/PyTorch 探测和显存。也可选择 CPU sorter。
- **项目打不开：** 选择项目根目录中的 `neuroflow_project.json`；不要只选结果图。
- **行为事件数量不对：** 检查事件码、单位、重复行、同步脉冲和时钟映射。
- **小窗内容看不全：** 折叠左右侧栏，拖动分隔条；对话框和教程页支持滚动。
- **AI 无法连接：** 先使用状态检测，核对 base URL 是否含 `/v1`、model 名和 key；AI 不可用不影响确定性分析。

更详细的图文教程：[中文手册](https://carbonlack.github.io/neuroflow-ai/zh/) · [英文手册](https://carbonlack.github.io/neuroflow-ai/en/) · [GitHub Issues](https://github.com/CarbonLack/neuroflow-ai/issues)
