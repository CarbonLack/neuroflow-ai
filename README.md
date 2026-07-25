# NeuroFlow v0.4

NeuroFlow 是本地优先、模块化、可解释的在体细胞外多通道电生理分析工作台。
它不重新实现成熟 sorter，而是把数据导入、质量控制、Kilosort4、Unit 质控、
行为对齐、统计、机器学习、论文图和复现记录组织成一条可以逐步检查的链路。

## 这不是界面原型

首页只有两个主要数据入口：固定示例数据和用户自己的数据。示例数据保存在
`Documents/NeuroFlow/DemoData/NeuroFlow_demo`，包含二进制原始电压、事件表、
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
10. 项目、参数、Methods、统计表与 provenance 导出。

## 交互与语言

- 图中数据元素可点击，显示图层、横纵坐标含义和精确值；
- 原始波形可以选择起始时间、时间窗、首通道、可见通道数和显示增益；
- 双击任意坐标轴可修改标题、轴标签、范围与网格；
- 内置缩放、平移、复位和图片保存工具栏；
- 可切换突出数据点、阶梯线、灰度和高对比呈现；
- 系统级中文/English 切换，语言选择写入项目；
- 11 个工作流节点各自拥有“为什么做、输入、输出、必须检查、逐控件后果、方法来源”教程。

## 数据入口

- 固定模拟多通道示例，可作为 Neuropixels-like、tetrode 或线性探针教学数据；
- 自己的交错通道二进制记录，可附带事件 CSV；
- Intan、Open Ephys、SpikeGLX/Neuropixels、Blackrock、Plexon、TDT、NWB，
  通过 SpikeInterface extractor 转成项目缓存；
- IBL ALF 的 trials、spikes 和 clusters；
- 已有 Kilosort/Phy sorting 结果。

原始文件保持只读。只有明确选择复制时才复制通用二进制；记录系统适配器生成
项目级标准缓存。缺少原始电压时，原始质控与 sorting 会明确显示为跳过，不会伪造。

## Sorter

- **Kilosort4**：原生 NeuroFlow 适配器，完整 Demo 的默认 sorter；
- **SpyKING CIRCUS 2、Tridesclous2、Simple、Lupin**：SpikeInterface 原生
  sorter，均已接入并完成可用性探测；本轮另外实跑验证了 Tridesclous2 和 Simple；
- **MountainSort5**：适配器和安装清单已集成。其 `isosplit6` 在
  Windows/Python 3.12 下需要 Microsoft C++ Build Tools，未满足时会明确显示
  “不可用”，不会误报或阻止程序启动。

NeuroFlow 只逐项探测上述白名单 sorter，不再调用会枚举 HDSort、MATLAB 等所有
后端的全局检测，因此无关后端的编码或编译错误不会导致主程序启动崩溃。
Kilosort4 运行后可检查流程耗时、完整日志、深度-时间图、振幅稳定性、模板波形、
模板相似度、污染率、输出文件清单和模拟 ground truth 验证。

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

结果位于 `dist\NeuroFlow\NeuroFlow.exe`。选择 one-folder 是为了让大型科研依赖
保持可检查，并避免每次启动都重新解压。

## IBL 公开数据

下载一个处理后的 Brain-Wide Map session（不会下载巨大的原始 AP 文件）：

```powershell
python scripts\download_ibl_example.py --cache ibl_cache
```

然后在首页选择 **导入我的数据 > IBL ALF**。分析与论文 panel 的对应关系见
[`docs/IBL_REPRODUCTION.md`](docs/IBL_REPRODUCTION.md)。

## 测试

```powershell
python -m pytest -q
```

测试覆盖模拟原始记录、质控、通用二进制、Kilosort 输出、IBL ALF、项目恢复、
多统计视图、双语帮助、sorter 容错检测与机器学习解码。Kilosort4 GPU、
Tridesclous2 和 Simple 的真实运行属于单独的集成验证。

## 数据与仓库原则

仓库只保存源码、测试、文档和小型配置，不提交原始记录、IBL 缓存、项目输出、
虚拟环境、密钥或 Kilosort 中间文件。每个稳定里程碑在测试和窗口检查后再同步
GitHub 与 GitLab。
