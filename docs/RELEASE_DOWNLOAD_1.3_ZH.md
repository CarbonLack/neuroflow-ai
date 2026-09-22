# NeuroEphys AI v1.3.5 — 下载与安装

v1.3.5 在多 Session／多动物 Study 工作区、整组交叉验证、层级汇总、潜在动力学基础上，
提供分步引导、按步骤保存的聊天、宽敞的阅读区、机构兼容接口图像提交、经核实几何的 Unit 复核和可直接打开的英文图文报告；
同时保留自适应 AI 回答、Python/CLI 接口、受控 Study 调用和单 Session 正式工作流。
真实看图依赖本机已配置且支持图像的模型服务，App 安装包本身不包含机构模型账号。

## 选择哪个版本

| 版本 | 文件 | 适用场景 |
|---|---|---|
| Windows GPU Full 自选安装版（完整功能推荐） | `NeuroEphysAI-Setup-1.3.5-Full.exe` | 包含本版全部功能与完整离线 GPU/CUDA/Kilosort 组件；安装时仍可取消 GPU 组件。比赛演示、离线使用和需要 Kilosort 时优先选它。 |
| Windows 标准安装版（轻量日常版） | `NeuroEphysAI-Setup-1.3.5.exe` | 包含最新 AI 对话与图像解读入口、App、Study、统计、机器学习、作图和 CPU 分析；不携带数 GB GPU 运行库。 |
| Windows 标准便携版 | `NeuroEphysAI-1.3.5-Windows-x64-portable.zip` | 不安装；必须完整解压后运行，不能只复制单独 EXE。 |
| Python 包 | `neuroephys_ai-1.3.5-py3-none-any.whl` | Python 3.12 用户用于脚本、CLI 和可重复批处理。 |

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
