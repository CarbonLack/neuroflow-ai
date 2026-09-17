# NeuroEphys AI v1.2.6 — 下载与安装

首次使用请先阅读 GitHub 内的[安装与完整使用教程](https://github.com/CarbonLack/neuroflow-ai/blob/main/docs/GITHUB_USER_GUIDE_ZH.md)；
英文版见 [Installation and complete user guide](https://github.com/CarbonLack/neuroflow-ai/blob/main/docs/GITHUB_USER_GUIDE_EN.md)。

保留紫黑配色、原 Logo 及科学分析选择，重新整理首页、教程中心和工作区。

## 下载哪个文件

| 使用方式 | 下载文件 | 说明 |
| --- | --- | --- |
| Windows GPU Full 自选安装版（科研复现/比赛推荐） | `NeuroEphysAI-Setup-1.2.6-Full.exe` | 默认安装全部功能，包含 Kilosort 4、PyTorch/CUDA 与全部已适配 sorter；安装时也可取消 GPU 组件，仅装通用核心。安装包约2GB，Kilosort仍要求兼容NVIDIA硬件和驱动。 |
| Windows 标准安装版（日常推荐） | `NeuroEphysAI-Setup-1.2.6.exe` | 较小、安装最简单。包含 App 与核心科学分析，不包含数GB的GPU运行库；适合没有NVIDIA GPU或暂时不用Kilosort的用户。 |
| 免安装标准版 | `NeuroEphysAI-1.2.6-Windows-x64-portable.zip` | 完整解压后运行，不能只复制其中的exe；功能范围与标准安装版一致。 |
| Python 调用 | `neuroephys_ai-1.2.6-py3-none-any.whl` | 给使用Python 3.12的用户；通过pip安装并按需要配置可选依赖。 |

v1.2.6 增加官方 Harness SDK 路径和本机 MCP 查询：AI 可按需读取实际 Unit、
事件、结果表与本项目历史对话；密钥由 Harness 管理。分析运行仍须确认。AI 设置、上下文预览和完整
工作台均能在窄窗口自适应，不改变既有科学分析功能和紫黑配色。

App安装版自带Python运行环境；普通桌面用户不需要另装Python。需要完整复现能力时优先选 Full 并保留默认的 GPU 组件；只做 CPU 分析或电脑没有兼容 NVIDIA GPU 时选标准版。两版拥有相同界面和项目格式，只是随包提供的计算后端不同。标准版或取消 GPU 组件后，Kilosort 会明确显示不可用，并在 Sorter 管理页提供同版本 Full 下载入口，不会自动改用其他算法。

完整20分钟benchmark、公开数据缓存和实验记录都作为独立数据资产管理，不塞入安装包。下载App并不自动下载数十GB实验数据。

## 这次改了什么

- Harness SDK + MCP 项目查询，不再把机构 Harness 配置转换成直接模型 API 请求。
- 对话随项目自动归档；查询携带实际结果和快照证据；读取与执行权限分开。
- 空计划面板自动隐藏，窄窗聊天空间增加；失败与取消不冒充成功。
- Harness 是独立前提：安装包不捆绑机构账号、密钥或 dsh。请先按[官方说明](https://deepseek.com/harness/en/)配置 Harness，再在 App 设置中读取本机配置。

- 新增“读取本机 DeepSeek Harness 配置”，只读非敏感连接信息。
- 新增机构内网 HTTP 的显式安全开关、自定义密钥环境变量和 Provider 凭据隔离。
- Harness 返回的工具建议进入 App 本地白名单、Schema、风险和确认链路，不直接执行。
- AI 设置、云端数据预览和 AI 工作台在小窗口改为自动纵向布局。
- 教程中心改为 18 个可搜索任务：操作步骤、参数说明、问题排查分开；可调字号、记录已读、跳转到对应页面。
- 首页入口居中，保留 Logo 边框；紧凑导航、统一线条图标、折叠图表工具和窄栏换行。
- 三栏可同时使用，左侧可缩略，右侧 AI 可收放，中间分析区域宽度可拖动调整。
- Ctrl+K 查找操作与最近项目；Ctrl+Shift+H 打开教程；Ctrl+B / Ctrl+J 调整左、右栏。
- 切换项目检查未保存内容及正在运行的任务；修正单步任务进度。
- 中英文网页手册与 App 共用任务说明，更新首次操作、工作区说明与真实界面截图。

## 已验证与边界

137 项自动测试通过；Full、Full仅核心、标准安装版和标准便携版均经过独立安装或解压后的启动、离线 AI 确认保护及 SVG/PDF/PNG 导出检查。本机 Full 使用教学数据实际运行 Kilosort 4、MountainSort5、SpyKING CIRCUS 2、Tridesclous 2、Simple、Lupin，并保存比较结果。

本轮不修改科学算法默认值，也不作任意电脑兼容性保证。两套 20 分钟模拟 benchmark 和五个已确认真实动物组已完成三-sorter、行为同步、事件分析、导出和英文排版链路；但真实记录上不同 sorter 的一致度不是准确率，候选 Unit 仍必须人工复核。预处理桌面页仍是预览，Unit 复核不提供通用合并/拆分工具。

[中文操作手册](https://carbonlack.github.io/neuroflow-ai/zh/) · [English manual](https://carbonlack.github.io/neuroflow-ai/en/) · [完整验证记录](https://github.com/CarbonLack/neuroflow-ai/blob/main/RELEASE_VALIDATION_1.2.md) · [改动与验收说明](https://github.com/CarbonLack/neuroflow-ai/blob/main/docs/RELEASE_ACCEPTANCE_1.2_ZH.md)
