# NeuroEphys AI v0.9.0

公开操作手册：[NeuroEphys AI Documentation](https://carbonlack.github.io/neuroephys-ai-docs/)

公开文档仓库：[CarbonLack/neuroephys-ai-docs](https://github.com/CarbonLack/neuroephys-ai-docs)

主仓库同步手册：[NeuroEphys AI Manual](https://carbonlack.github.io/neuroflow-ai/)

公开仓库与部署状态：[DEPLOYMENT_STATUS_ZH.md](DEPLOYMENT_STATUS_ZH.md)

NeuroEphys AI 是本地优先、模块化、可解释的在体细胞外多通道电生理分析工作台。
平台调用经过验证的 sorter 和分析库，将数据导入、质量控制、sorting、人工 Unit
复核、行为对齐、Neo/Elephant 神经分析、统计、机器学习、论文图和复现记录组织成
可逐步检查、替换和恢复的工作流。

## 受控AI助手

软件提供手动、助手和协作三种模式。DeepSeek兼容接口是第一阶段默认入口，同时
支持OpenAI兼容服务、实验室私有服务和未来本地服务。Provider层支持流式回复、
结构化输出、工具调用、超时、重试、取消和服务状态检测。

在线模型只接收用户预览并确认的结构化摘要。原始电压、大型数组、本地路径和身份
信息留在本机；API密钥保存在当前会话、环境变量或操作系统凭据区，不进入项目、
日志、Git仓库和报告。

助手模式只提供解释和建议。协作模式允许模型提出白名单工具调用，本地规则会检查
参数、依赖、输入完整性和工作流顺序，随后弹出确认窗口。Sorting、覆盖结果、批量
运行、在线发送信息和长时间任务始终需要用户确认。AI服务不可用时，全部确定性
分析功能继续运行。

详细操作见[受控AI助手](docs/site/zh/ai-assistant.html)，中间产物和上下文关系见
[中间产物与溯源](docs/site/zh/provenance.html)。

## 可执行工作流

首页把“新建空白项目”“导入自己的数据”“打开已验证公开项目”“教学模拟”和
“恢复项目”明确分开。空白项目不会生成模拟数据，进入 01 数据与项目页面后才由
用户选择通用二进制、记录系统文件或已有 sorting 结果。数据入口会确定流程起点、
sorting 可用性和后续必需的元数据。
示例数据保存在
`Documents/NeuroEphysAI/DemoData/NeuroFlow_demo`，包含二进制原始电压、事件表、
元数据、ground truth、精确导入配置和数据说明。完整 Demo 会实际执行：

1. 原始信号 RMS、坏通道、饱和与 50 Hz 检查；
2. 300–6000 Hz 与 common median reference 预览；
3. Kilosort4、SpyKING CIRCUS 2、Tridesclous2、Simple 或 Lupin 实际 sorting；
4. 与模拟 ground truth 的 spike 匹配和 F1 验证；
5. Unit 放电率、ISI violation、波形、SNR；
6. 事件对齐、Raster、PSTH 和群体热图；
7. 参数/非参数检验、置换、bootstrap、效应量、条件比较、混合模型与多重校正；
8. 11 种分类器、5 种连续变量回归、交叉验证、置换、ROC/F1、特征重要性、K-means 与 GMM；
9. IBL 风格时间分辨解码、心理测量曲线、反应时和群体 PCA 轨迹；
10. Elephant 放电统计、CCH、STTC、spike-train 距离与 LFP 频谱、相干性分析；
11. Spike-field 相位锁定、循环移位检验和呼吸相位-振幅耦合验证案例；
12. 项目、参数、Methods、统计表、完整图集与 provenance 导出。

## 原创性与来源

NeuroEphys AI 不复制其他软件或文章的界面、文案、截图、图表和实现代码。项目只调用
开源库公开 API，并依据官方文档和原始论文核对数据结构、方法定义与能力边界；
界面、适配器、规则、教程、示例数据和图形均由 NeuroEphys AI 独立设计。

- 官方方法与 API 来源见 [`docs/METHODS_AND_SOURCES.md`](docs/METHODS_AND_SOURCES.md)；
- 原创双语产品文档入口为 [`docs/site/index.html`](docs/site/index.html)；
- 呼吸案例使用 NeuroEphys AI 自己的模拟数据，只演示方法结构，不宣称复现论文结果；
- 微信推文仅用于发现主题和追溯原文，不复制其内容。

## 交互与语言

- 图中数据元素可点击，显示图层、横纵坐标含义和精确值；
- 原始波形可以选择起始时间、时间窗、首通道、可见通道数和显示增益；
- 双击坐标轴或点击“图形设置”可打开 Figure Studio；整图、坐标轴、线、散点、
  柱/填充区、热图、文字和图例均可逐对象编辑，并在内嵌预览中即时检查；
- 坐标轴支持 X/Y 实际长度和画布位置、四条轴线独立显示/颜色/线宽/偏移、
  主次刻度和间隔、数字格式、X/Y 独立主次网格、自定义参考线以及图例边框；
- 内置缩放、平移、复位和图片保存工具栏；
- 可切换突出数据点、阶梯线、灰度和高对比呈现；
- 系统级中文/English 切换，语言选择写入项目；
- 11 个工作流节点各自拥有“为什么做、输入、输出、必须检查、逐控件后果、方法来源”教程。

## 数据入口

- 三套可选择的完整模拟项目：Neuropixels-like 二选一任务、tetrode 空间探索与奖励、独立微丝感觉刺激；
- 每套项目均包含原始电压、真实探针接触位置、行为事件、TTL、条件/选择/结果/反应时以及 ground truth；
- “导入自己的数据”只显示用户文件入口，不再默认显示模拟数据；
- 自己的交错通道二进制记录，可附带事件 CSV；
- Intan、Open Ephys、SpikeGLX/Neuropixels、Blackrock、Plexon、TDT、NWB，
  通过 SpikeInterface extractor 转成项目缓存；
- IBL ALF 的 trials、spikes 和 clusters；
- 具有 Units、行为事件、位置、睡眠状态或 ripple 区间的 NWB，例如
  DANDI 上公开的 Buzsáki Lab 会话；
- 已有 Kilosort/Phy sorting 结果。
- NeuroExplorer/Offline Sorter `.nex5` 候选 Unit、spike 时间和波形摘要；可附加到
  含原始电压的项目，并与 Kilosort 等结果按统一秒时间接口比较。

公开验证入口锁定两套实际跑通的数据，用户可以直接建立或打开项目缓存：

- IBL Brain-Wide Map `EID 4ecb5d24-f5cc-402c-be28-9d0f7cb14b3a`；
- Buzsáki Lab DANDI `000552/0.230630.2304` 的固定 NWB asset。

数据已下载时，首页双击“已验证公开项目”即可查看本机状态并直接建立或打开项目缓存。

原始文件保持只读。只有明确选择复制时才复制通用二进制；记录系统适配器生成
项目级标准缓存。缺少原始电压时，原始质控与 sorting 会明确显示为跳过，不会伪造。

## Sorter

- **Kilosort4**：原生 NeuroEphys AI 适配器，完整 Demo 的默认 sorter；
- **SpyKING CIRCUS 2、Tridesclous2、Simple、Lupin**：SpikeInterface 原生
  sorter，均已接入并完成可用性探测；
- **MountainSort5**：通过 SpikeInterface 接入，Windows 发布环境会编译并封装
  `isosplit6`；适合 CPU、tetrode 和中低通道数流程；

授权的 30 分钟真实记录已分别实跑 Kilosort4、MountainSort5、SpyKING
CIRCUS 2 和 Tridesclous2。不同算法产生的候选 Unit 数量差异较大；平台保留各自
原生输出并转换成统一的秒级 spike 接口，结果需要结合质量指标和人工复核解释。

NeuroEphys AI 逐项探测白名单 sorter，避免枚举 HDSort、MATLAB 等未配置后端。
无关后端的编码或编译错误不会导致主程序启动崩溃。
Kilosort4 运行后可检查流程耗时、完整日志、深度-时间图、振幅稳定性、模板波形、
模板相似度、污染率、输出文件清单和模拟 ground truth 验证。

每个 sorter 的原生文件保留不变，同时转换为统一的 Unit→秒级 spike times
结构。多次运行不会覆盖其他 sorter：用户可切换当前结果，并在“Sorter 统一结果与
比较”视图查看 Unit 匹配、一致度、算法独有 Unit 和共识 Unit。模拟或配对
ground truth 数据可以把 precision、recall 与 F1 解释为检测性能；真实外部结果
只将这些数值用于描述两份输出的一致度。

外部 NEX5 结果以只读对照接入。真实数据比较使用 precision、recall、F1、
chance-corrected agreement 和受限 lag 描述两个输出的时间戳一致度；界面明确标记
两份结果均非 ground truth。Unit QC 额外筛查跨 Unit 的近同时 spike 重合，并把
可能重复、串扰或拆分风险交给人工复核，不自动删除候选。

## 启动

双击 `run_demo.bat`。开发环境也可以运行：

```powershell
..\.venv312\Scripts\python.exe app.py
```

在一台新 Windows 电脑上先运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

构建可携带的 Windows one-folder 应用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

结果位于 `dist\NeuroEphysAI\NeuroEphysAI.exe`。选择 one-folder 是为了让大型科研依赖
保持可检查，并避免每次启动都重新解压。

## 真实公开数据验证

NeuroEphys AI 已用两条互补的真实公开数据入口完成集成验证：

- IBL Brain-Wide Map 的 ALF session：
  `EID 4ecb5d24-f5cc-402c-be28-9d0f7cb14b3a`、`probe00`；
- Buzsáki Lab / DANDI `000552` 的 NWB session：
  `sub-e14-2m3_ses-e14-2m3-201121_behavior+ecephys.nwb`。

下载 IBL 处理后会话（不会下载巨大的原始 AP 文件）：

```powershell
python scripts\download_ibl_example.py --cache ibl_cache
```

下载固定的 Buzsáki/DANDI NWB 示例：

```powershell
python scripts\download_buzsaki_example.py
```

运行两套公开数据的可重复集成验证：

```powershell
python scripts\validate_public_datasets.py
```

完整数据 ID、实际导入数量、图、指标、运行限制和官方来源见
[`docs/site/zh/real-data-validation.html`](docs/site/zh/real-data-validation.html)。这些结果用于证明
导入、统一数据结构、事件分析、统计和解码链路能够运行，不等于复现原论文结论，
也不把 20 次置换的 smoke test 当作正式显著性证据。

## 运行反馈

右侧审计记录持续保存每个步骤的消息；同时：

- 运行前弹窗列出项目、节点、sorter 和模型并要求确认；
- 运行成功弹窗列出已完成节点、耗时和结果保存状态；
- 运行失败弹窗显示首要错误并说明已完成结果不会被删除。

## 测试

```powershell
python -m pytest -q
```

测试覆盖模拟原始记录、质控、通用二进制、Kilosort 输出、IBL ALF、NWB Units、
Figure Studio 对象目录、常量数据统计容错、项目恢复、多统计视图、双语帮助、
sorter 容错检测、机器学习解码、AI 隐私摘要、结构化云端协议、候选流程确认和
AI 审计历史恢复。Kilosort4、MountainSort5、SpyKING CIRCUS 2 和
Tridesclous2 的真实运行属于单独的集成验证。

## 数据与仓库原则

仓库只保存源码、测试、文档和小型配置，不提交原始记录、IBL 缓存、项目输出、
虚拟环境、密钥或 Kilosort 中间文件。每个稳定里程碑在测试和窗口检查后再同步
GitHub 与 GitLab。
