# NeuroEphys AI v1.2.0 — 操作体验与手册

保留紫黑配色、原 Logo 及科学分析选择，重新整理首页、教程中心和工作区。

## 下载哪个文件

| 使用方式 | 下载文件 | 说明 |
| --- | --- | --- |
| Windows 完整 App | `NeuroEphysAI-Setup-1.2.0-Full.exe` | 含 Kilosort 4、PyTorch/CUDA 运行库及本轮验证的六个 sorter；约 2.08 GB。GPU 分析仍需要兼容硬件和驱动。 |
| Windows 核心 App | `NeuroEphysAI-Setup-1.2.0.exe` | 约 237 MB，不含完整 GPU 运行库；可用 sorter 以环境探测为准。 |
| 免安装核心版 | `NeuroEphysAI-1.2.0-Windows-x64-portable.zip` | 完整解压后运行，不能只复制其中的 exe。依赖范围与核心版一致。 |
| Python 调用 | `neuroephys_ai-1.2.0-py3-none-any.whl` | 给使用 Python 3.12 的用户；通过 pip 安装并按需要配置可选依赖。 |

App 安装版自带 Python 运行环境；普通桌面用户不需要另装 Python。完整包与核心包是不同依赖配置，不是不同界面版本。

## 这次改了什么

- 教程中心改为 18 个可搜索任务：操作步骤、参数说明、问题排查分开；可调字号、记录已读、跳转到对应页面。
- 首页入口居中，保留 Logo 边框；紧凑导航、统一线条图标、折叠图表工具和窄栏换行。
- 三栏可同时使用，左侧可缩略，右侧 AI 可收放，中间分析区域宽度可拖动调整。
- Ctrl+K 查找操作与最近项目；Ctrl+Shift+H 打开教程；Ctrl+B / Ctrl+J 调整左、右栏。
- 切换项目检查未保存内容及正在运行的任务；修正单步任务进度。
- 中英文网页手册与 App 共用任务说明，更新首次操作、工作区说明与真实界面截图。

## 已验证与边界

107 项自动测试通过；打包程序启动、离线 AI 确认保护及 SVG/PDF/PNG 导出通过。本机完整包使用教学数据实际运行 Kilosort 4、MountainSort5、SpyKING CIRCUS 2、Tridesclous 2、Simple、Lupin，并保存比较结果。云端核心包构建已成功。

本轮不修改科学算法默认值，不声称新增真实实验数据验证或任意电脑兼容性保证。真实记录上不同 sorter 的一致度不是准确率；预处理桌面页仍是预览，Unit 复核不提供通用合并/拆分工具。

[中文操作手册](https://carbonlack.github.io/neuroflow-ai/zh/) · [English manual](https://carbonlack.github.io/neuroflow-ai/en/) · [完整验证记录](https://github.com/CarbonLack/neuroflow-ai/blob/main/RELEASE_VALIDATION_1.2.md) · [改动与验收说明](https://github.com/CarbonLack/neuroflow-ai/blob/main/docs/RELEASE_ACCEPTANCE_1.2_ZH.md)
