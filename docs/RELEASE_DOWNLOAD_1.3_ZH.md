# NeuroEphys AI v1.3.1 — 下载与安装

v1.3.1 在多 Session／多动物 Study 工作区、整组交叉验证、层级汇总、潜在动力学基础上，
新增低负担 AI 阅读模式：默认只展示结论、关键证据状态和下一步，完整科学说明与限制可按需打开；
并继续提供 Python/CLI 接口和受控 AI Study 调用，同时保留 v1.2 的单 Session 正式工作流。

## 选择哪个版本

| 版本 | 文件 | 适用场景 |
|---|---|---|
| Windows GPU Full 自选安装版（科研复现/比赛推荐） | `NeuroEphysAI-Setup-1.3.1-Full.exe` | 默认包含 App、核心分析、Kilosort 4、PyTorch/CUDA 与全部已适配 sorter；安装时可取消 GPU 组件。Kilosort 仍需兼容的 NVIDIA GPU 和驱动。 |
| Windows 标准安装版（日常 CPU 推荐） | `NeuroEphysAI-Setup-1.3.1.exe` | 包含 App、Study、统计、机器学习、作图和 CPU 分析；不携带数 GB GPU 运行库。 |
| Windows 标准便携版 | `NeuroEphysAI-1.3.1-Windows-x64-portable.zip` | 不安装；必须完整解压后运行，不能只复制单独 EXE。 |
| Python 包 | `neuroephys_ai-1.3.1-py3-none-any.whl` | Python 3.12 用户用于脚本、CLI 和可重复批处理。 |

不知道选哪个时：有 NVIDIA GPU、需要 Kilosort 或比赛现场离线演示，选 Full；普通 CPU
电脑选标准安装版；没有安装权限选便携版；需要代码调用再加装 wheel。

## 多 Session 使用入口

1. 在每个 Session 项目中完成 Unit 复核、行为/TTL 同步和相同参数的事件对齐分析；
2. 选择 **文件 → 多 Session 研究…**；
3. 新建 Study，加入各项目清单并核对真实动物和 Session 编号；
4. 选择两个共有条件、留出层级、模型和置换次数；
5. 运行后在 Study 的 `results/multi_session` 查看英文图、CSV 和 JSON。

方法与限制见 [多 Session 分析路径](https://github.com/CarbonLack/neuroflow-ai/blob/main/docs/MULTI_SESSION_ANALYSIS_ZH.md)。
GitHub 和 App 内教程同时说明安装、单 Session 流程、Study、AI、图形和排错。

## 安全说明

候选 Unit、统计结果、模型性能和 AI 解释都需要研究者结合实验设计复核。AI 只读取用户
可预览的脱敏结构化摘要；原始电压和本地路径不上传，任何分析操作仍需本地验证与确认。
