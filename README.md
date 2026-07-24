# NeuroFlow v0.2

NeuroFlow 是本地优先、模块化、可解释的在体细胞外多通道电生理分析工作台。
它不重新实现成熟 sorter，而是把数据导入、质量控制、Kilosort4、Unit 质控、
行为对齐、统计、机器学习、论文图和复现记录组织成一条可以逐步检查的链路。

## 这不是界面原型

完整模拟 Demo 会生成真实的交错 `int16` 多通道电压，然后实际执行：

1. 原始信号 RMS、坏通道、饱和与 50 Hz 检查；
2. 300–6000 Hz 与 common median reference 预览；
3. Kilosort4 spike sorting（检测到 CUDA 时使用 GPU）；
4. 与模拟 ground truth 的 spike 匹配和 F1 验证；
5. Unit 放电率、ISI violation、波形、SNR；
6. 事件对齐、Raster、PSTH 和群体热图；
7. 配对 t、Wilcoxon、置换检验、bootstrap CI、效应量、FDR/Bonferroni；
8. Logistic regression、linear SVM、random forest、交叉验证和置换零分布；
9. IBL 风格时间分辨解码、心理测量曲线、反应时和群体 PCA 轨迹；
10. 项目、参数、Methods、统计表与 provenance 导出。

## 数据入口

- 模拟 Neuropixels-like、四电极阵列或线性探针；
- 自己的交错通道二进制记录，可附带事件 CSV；
- Intan、Open Ephys、SpikeGLX/Neuropixels、Blackrock、Plexon、TDT、NWB，
  通过 SpikeInterface extractor 转成项目缓存；
- IBL ALF 的 trials、spikes 和 clusters；
- 已有 Kilosort/Phy sorting 结果。

原始文件保持只读。只有明确选择复制时才复制通用二进制；记录系统适配器生成
项目级标准缓存。缺少原始电压时，原始质控与 sorting 会明确显示为跳过，不会伪造。

## Sorter

- **Kilosort4**：原生 NeuroFlow 适配器，当前完整 Demo 的默认 sorter；
- **MountainSort5、SpyKING CIRCUS 2、Tridesclous 2**：通过 SpikeInterface
  注册，只有依赖实际安装后才显示为“可运行”。

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
统计套件与机器学习解码。Kilosort GPU 的完整运行属于单独的集成验证。

## 数据与仓库原则

仓库只保存源码、测试、文档和小型配置，不提交原始记录、IBL 缓存、项目输出、
虚拟环境、密钥或 Kilosort 中间文件。每个稳定里程碑在测试和窗口检查后再同步
GitHub 与 GitLab。
