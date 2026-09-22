# NeuroEphys AI 安装与完整使用教程

> 本页面是 GitHub 用户入口。不需要先阅读开发文档。所有原始数据默认留在本机；候选 Unit、自动筛选、统计显著和 AI 建议都需要研究者复核。

## 1. 我应该下载哪个版本？

在 [GitHub Releases](https://github.com/CarbonLack/neuroflow-ai/releases/latest) 中选择：

| 版本 | 适合谁 | 怎么用 | 注意 |
|---|---|---|---|
| **Full 离线安装版** `NeuroEphysAI-Setup-1.3.5-Full.exe` | 比赛演示、科研工作站、需要 Kilosort/GPU 的用户 | 双击安装，按组件页选择 | 包含 v1.3.5 全部功能与完整离线 GPU/CUDA/Kilosort 组件 |
| **标准安装版（推荐）** `NeuroEphysAI-Setup-1.3.5.exe` | 普通 Windows 用户、教学、CPU 分析 | 双击安装 | 包含最新 AI 对话与图像解读入口；后续可在 Sorter 管理器补齐组件 |
| **标准便携版** `NeuroEphysAI-1.3.5-Windows-x64-portable.zip` | 无安装权限或移动硬盘用户 | 完整解压后运行 `NeuroEphysAI\NeuroEphysAI.exe` | 不能只复制单个 EXE |
| **Python 包** `neuroephys_ai-1.3.5-py3-none-any.whl` | 需要脚本、批处理和 API 的用户 | `python -m pip install <wheel>` | 建议 Python 3.12 |

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
首次启动会询问是否从第 1 步开始分步学习；可选“不再提醒我”。之后仍可点工作区的“本步引导”、按 `F1`，或从 **帮助 → 当前步骤新手引导** 重开。**帮助 → 重置新手引导** 可恢复逐步自动提示。

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
| 07 行为分析 | 两种行为谱：动物分行、单动物行为分行；其他统计可选 | 事件时间与动物标识 | 可调时间尺度的行为图与表 |
| 08 神经活动 | Raster、PSTH、群体动态等 | 对齐点、时窗、bin | 神经响应图 |
| 09 统计检验 | 效应量、置换、bootstrap、多重校正 | 实验单位与假设 | 统计表和方法说明 |
| 10 机器学习 | 分类、回归、解码和聚类 | 防止 trial/时间泄漏 | 交叉验证、置换基线和特征结果 |
| 11 论文与复现 | 英文主图/附图、图注草稿、Methods 和清单 | 所有分析已审阅 | publication 报告和 provenance |

每个节点都可单独运行；不需要一条线走到底。有已完成 sorting 的用户可以直接从 05 开始。
行为谱中的细线表示瞬时记录事件，色块表示有明确开启/关闭配对的持续区间。可设起点与时间尺度。单动物项目不会自动汇总其他动物；运行第 07 步会保存两张 PNG/SVG 到 `results/behavior`。

## 7. 三 sorter 对比

在 **04 Spike sorting** 分别运行 Kilosort4、MountainSort5 和 SpyKING CIRCUS2，然后打开“Sorter 统一结果与比较”。确认三次运行使用同一原始记录、通道、时间区间和采样率。

真实数据没有 ground truth，因此工具间 precision/recall/F1 只描述输出一致性，不是真实准确率。任何候选 Unit 都应在 **05 Unit 质控** 中人工复核。

## 8. 图、表和论文导出

- 单击图中元素查看数值；双击坐标轴或点击“编辑子图”进入 Figure Studio。
- **当前对象** 只改一张图的一个对象；**统一样式** 对项目图使用相同字体、线宽、网格和配色。
- “论文与复现”生成真正组合到同一画布的英文主图与附图，每张图有 SVG/PDF 矢量版和 PNG 预览、a/b/c 面板编号、逐面板英文图注草稿、Methods、清单和校验值。App 内选择整张 Figure 查看；展开面板后可用箭头调顺序、编辑图注。重新运行本步骤会保留 `exports/publication/author_edits.json` 中的修改。
- `exports/panels/` 保存逐坐标轴原图，`exports/figure_data/` 保存作图数值和来源索引，`exports/provenance.json` 保存原始数据与流程来源。包括未显著结果在内的所有已导出图均进入主图或附图。
- 自动排版不代替研究者对生物学故事、统计、图注和目标期刊规格的终审。

## 9. 多 Session／多动物研究

单个项目对应一个 Session。先在每个项目内使用相同的事件定义、基线/响应窗和 bin 完成
Unit 复核、行为同步与事件对齐，然后选择 **文件 → 多 Session 研究…**：

1. 新建 Study 并加入各项目的 `neuroflow_project.json`；
2. 核对真实动物编号、唯一 Session 编号、纳入状态和共有条件；
3. 选择两个共有条件、按动物或 Session 整组留出、模型及置换次数；
4. 一次运行 Session QC、配对效应、整组解码、置换、随时间/时间泛化解码、跨 Session 转移和表征稳定性；
5. 在 Study 的 `results/multi_session` 取得英文主图与附图、CSV 矩阵、完整 JSON 和 `INTERPRETATION.md`。

不同 Session 的同号 Unit 默认不是同一细胞；只有一只动物时只能做 Session 留出，不能
宣称跨动物泛化。LDA 是分类器，潜在动力学是独立的 PCA + 正则化线性转移描述。详见
[完整方法与操作](MULTI_SESSION_ANALYSIS_ZH.md)；
[论文主图/附图调研与 App 对照](MULTI_SESSION_PAPER_METHODS_ZH.md)。

## 10. AI 助手与机构 harness

在 **帮助 → AI 设置** 中选择手动、助手或协作模式。本机已部署 DeepSeek Harness 时，点击“读取本机 DeepSeek Harness 配置”，再点击“检测服务状态”。软件只读取地址、模型和环境变量名，不读取 Harness 凭据文件。

AI 使用版本化的受控项目摘要，不依赖 Harness 网页。原始电压和本地路径不发送；协作模式下也只能提出白名单工具，实际操作由 App 在本地校验并按风险要求确认。

回复默认使用“简洁阅读”：先给结论，再显示不超过三个关键点、已读取的项目证据、下一步和重要警告。模型会先把内部字段翻译成科研含义，再按需说明“为什么”“你现在可以怎么做”和“需要注意”，不再用固定限字强行截短。完整科学解释、限制、证据编号与候选操作没有删除，点击“查看完整说明与依据”即可打开。需要逐项检查时，可将“回复显示”切换为“完整内容”。

项目内对话可分成多个会话：点击“新对话”开始新主题，软件用第一个问题自动命名；在展开窗口可重命名、选择“项目分析／图表解读／方法问答／通用问题”等分类，并搜索分类、标题及对话正文。用当前图发起的新会话自动归入图表解读。旧版平铺历史保留在“早期对话”。这些分类只属于本 App，不会改变 Harness 网页自身的“未分组”。右侧侧栏可切换会话；回车发送、Shift+回车换行。即使没有打开项目也可以提问一般科研知识与其他问题；涉及本软件的具体操作时，AI 可查询内置教程，涉及当前项目时再查询实际结果。

需要让模型看到图的像素时，点击“解读图”，检查 PNG 预览并确认。只有当前图通过 Harness SDK 图像消息发送，图像字节不存入对话档案；图中如含原始波形或标签，需在预览时自行判断是否发送。普通 API Provider 当前不支持图像入口，软件不会把只有图标题的上下文伪装成已看图。图像观察只用于解释可见现象，精确数字仍以项目结果为准。

App 自动生成受控的结构化项目上下文：当前步骤、已有结果、导出件、约束和允许的工具。默认不发送原始电压、大数组、本地路径和身份信息。协作模式中的本地操作仍需要白名单检查和用户确认。

保存 Study 后，AI 可读取脱敏的 Study ID、计数、条件、验证设计和结果摘要，并在协作模式
提出受控运行；路径、动物/Session 行明细、原始电压和大数组不发送。

## 11. 项目文件放在哪里？

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

## 12. Python 安装与最小例子

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install neuroephys_ai-1.3.5-py3-none-any.whl
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

## 13. 常见问题

- **启动时缺 DLL：** 不要单独拷贝 EXE；重新完整安装或完整解压便携版。
- **Kilosort 不可用：** 检查是否使用 Full 版、NVIDIA 驱动、CUDA/PyTorch 探测和显存。也可选择 CPU sorter。
- **项目打不开：** 选择项目根目录中的 `neuroflow_project.json`；不要只选结果图。
- **行为事件数量不对：** 检查事件码、单位、重复行、同步脉冲和时钟映射。
- **小窗内容看不全：** 折叠左右侧栏，拖动分隔条；对话框和教程页支持滚动。
- **AI 无法连接：** 先使用状态检测，核对 base URL 是否含 `/v1`、model 名和 key；AI 不可用不影响确定性分析。

更详细的图文教程：[中文手册](https://carbonlack.github.io/neuroflow-ai/zh/) · [英文手册](https://carbonlack.github.io/neuroflow-ai/en/) · [GitHub Issues](https://github.com/CarbonLack/neuroflow-ai/issues)
