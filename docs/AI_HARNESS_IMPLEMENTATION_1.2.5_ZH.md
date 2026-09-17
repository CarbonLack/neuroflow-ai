# v1.2.5 AI 实现与验收记录

这是对早期接通测试的补充，不将 v1.2.4 描述为已具备完整研究助手。

## 实际架构

App → 已安装官方 dsh SDK stdio 协议 → 模型 → 本机 MCP 项目接口。
SDK 负责模型与认证；MCP 负责查询当前 app 快照和提出操作。没有把机构密钥转换成直接 API 调用。

五项工具：当前上下文、数据/操作目录、分页结果查询、本项目对话检索、受控分析提案。
查询返回实际值与证据编号；任意文件访问、shell 和代码执行被关闭。分析提案只加入待确认队列，实际运行仍由 App 原有白名单和任务执行器负责。完成或失败后可在对话中回读任务记录。

每次请求启动自己的短生命周期 runtime，结束/取消后清理；不是长期保活的 Harness 会话。连续对话由项目档案负责。MCP 仅监听 loopback，使用每次随机令牌；该令牌不进入提示词。结果快照与项目绑定，不在 MCP 线程访问 Qt。

## 已验收

- 完整回归：154 项通过。存在依赖库弃用警告以及 pytest 退出时临时目录权限提示；进程退出码为 0，未隐藏该环境提示。

- 实际 32 通道、1200 秒模拟 benchmark 已完成 kilosort4 的项目：GUI 请求查询第 26 条 Unit 指标，模型返回 unit_id=25、spike_count=3195、firing_rate_hz=2.6625、snr=6.4304947079408175，与项目原值一致。
- 下一轮调用历史检索并讨论上述 Unit。早期连续短语匹配找不到多关键词提问，已改为按明确关键词匹配程度排序，并补回归测试；重新真实调用通过。
- 对话归档后重载成功；输入实验项目不修改，验证数据写入独立目录。
- 数据分页、过滤、深层数组、不可变快照、项目隔离、敏感字段阻断、操作参数验证、MCP 实际协议及未认证访问拒绝均有自动测试。
- SDK 成功、服务身份异常、失败结束、取消与子进程清理由协议测试覆盖。
- 实际在线操作闭环通过：模型提议原始质控时没有执行；在 GUI 拒绝后仍未执行；确认后本地质控生成实际结果，自动下一轮查询审计和结果并解释，没有再次提议运行。使用独立 2 秒模拟测试项目，不触碰已有实验结果。证据在同级 `action_loop_v2/live_action_acceptance.json`。
- 标准版冻结 exe 的 MCP 服务启动、官方客户端协议、实际数值查询自检通过。

本地 GUI 验证证据位于 `D:\PhD\AI大赛\发布验证\v1.2.5_AI\source_gui_v2`。
脚本 `scripts/validate_harness_integration.py` 需显式指定已有项目和独立输出目录；它会发起真实在线请求。

## 仍须区分的边界

源代码测试不等于发布安装包验收；安装包必须另行通过内置 MCP 查询自检。实时账号失效、机构网络变化仍可能导致服务失败。当前查询针对结构化数据而非截图像素，不提供原始电压传输。不能凭 SNR 或 sorter 之间的一致性宣称单神经元真值。所有科研结论仍需研究人员审核。

## 上游与实现依据

- 官方 SDK 服务协议：https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/sdk
- 官方 MCP 客户端：https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/mcp/mcp-client
- MCP Python SDK（MIT）：https://github.com/modelcontextprotocol/python-sdk/tree/v1.x

本机已验证 dsh 0.1.5-rc.1；MCP Python 依赖固定为 1.30.0。采用官方已安装运行时及公开 JSON-RPC 协议的小型客户端，不声称已安装尚不可通过当前包索引获得的官方 Python SDK 包。
