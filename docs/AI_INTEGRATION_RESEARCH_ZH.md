# AI 接入调研与决策记录

日期：2026-09-17。状态：方案调研和原型验证；不是正式安装版验收报告。

## 目标

用户在 app 内自然讨论当前项目。AI 应知道当前页面、选项、图、数据字段、
已运行操作和实际结果；能继续以前的项目对话，按需进一步查询。
读取操作应顺畅，分析任务应可追踪，修改和重算保持用户控制。
研究所凭据仅通过其支持的 Harness 使用，不从 Harness 提取密钥再直连模型。

## 已查明的问题

1. v1.2.4 的 institute_harness 实际使用 chat/completions，读取 Harness 的连接
   配置不等于通过 Harness 运行。此前说明将二者混为一谈，应予纠正。
2. Chat 路径要求 JSON，但没有提供完整的回答字段协议。不同 JSON 字段或仅有
   工具建议可能导致 empty answer。截图没有原始响应，不能断言唯一根因。
3. 实测一次问候返回仅有 tool_calls 的 JSON。旧流程不会自动完成读取再回答。
4. 上下文已有大部分结果摘要，但嵌套数据截断到三层，列表最多二十项；不能
   用这个摘要替代逐表查询。UI 对话发送只取最近六条消息，即约三轮。
5. 当前界面上下文原来仅记录阶段、视图和 sorter，不包含图标题及坐标范围。
6. 项目检查工具原来显示本地弹窗，结果没有回传模型形成连续对话。

## 核对官方资料和本机版本

本机 @deepseek-ai/dsh/package.json 为 0.1.5-rc.1。
本机包含 dsh-sdk-app、dsh-sdk-protocol、dsh-sdk-jsonrpc-server、dsh-mcp-client。

- SDK 使用逐行 JSON-RPC，initialize 指定 provider/model，session/prompt 只返回
  入队回执；真正答案通过 session.event 回来。不能把入队当作回答完成。
- SDK 有会话事件和 running/idle 状态；当前协议没有单次请求取消方法，关闭
  对应 runtime 是取消路径。因此要有明确的进程所有权和项目会话隔离。
- 本机 MCP 仅桥接 tools，不支持 resources/prompts。官网 master 已增加资源
  能力，不能把最新文档中的能力当作本机已具备。
- SDK 默认是 coding-agent 工具组合，包含文件/命令行能力。必须采用应用专用
  配置，并验证实际暴露的工具，不能仅凭提示词要求模型不要使用 shell。

官方来源：

- https://github.com/deepseek-ai/deepseek-harness/tree/master/python
- https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/sdk/protocol/README.md
- https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/sdk/server/README.md
- https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md
- https://deepseek.com/harness/en/
- https://modelcontextprotocol.io/specification/2025-06-18/architecture

## 方案比较

| 方案 | 自然对话 | 按需读数据与执行 | 本研究所限制 | 维护代价 | 结论 |
|---|---|---|---|---|---|
| 直接模型 API / 通用 API SDK | 可以 | app 自建工具循环和记忆 | 不能据此认定满足仅限 Harness 的要求 | 初期低，后续 agent 逻辑高 | 保留给其他用户，不作为本研究所主方案 |
| 仅嵌入 Harness 网页 | 可以 | 仍需项目接口 | 由 Harness 调用 | 网页与 app 状态易脱节 | 不是完整集成 |
| 官方 Harness SDK + app 上下文 | 可以 | 只有主动传入摘要，仍需查询接口 | 模型和凭据由 Harness 管理 | 中等 | 适合作为会话基础 |
| 仅 MCP 插件连接 Harness | 在 Harness 里对话 | 可查询、执行、扩展 | 由 Harness 调用 | 中等 | 可用作外部入口，但不能单独完善 app 内对话 |
| 官方 SDK + NeuroEphys MCP 工具桥 | app 内自然对话 | 按需查询，执行结果回传 | 由 Harness 调用 | 中等，可复用现有分析模块 | 推荐主方案 |
| 大型多代理框架 | 可以 | 需额外编排 | 仍需适配 Harness | 高 | 当前无充分收益 |

SDK 与 MCP 并不互相替代：SDK 管会话和运行事件，MCP 提供 app 能力。

## 推荐的实现边界

app 对话窗 → 官方 Harness SDK → 模型 → NeuroEphys MCP 查询/任务接口 → app。

一、每个请求附上当前项目 ID、状态版本、当前页面、参数、图标题/范围、
已完成/失败/待运行步骤、结果目录索引。快照必须来自内存中最新状态。

二、增加按需工具：获取当前上下文；列数据集；查询事件和 trial；查询指定
sorter/Unit 的指标；分页读取结果表；查询图对应的数据和参数；读取日志；
检索本项目历史对话。完整数组通过范围、列和行数限制查询，避免把二十分钟
电压直接塞入模型。图像能力需检查实际模型支持，不能默认模型看得到截图。

三、读取工具自动执行。运行分析、改变参数和导出走现有任务接口；返回任务 ID，
随后查询进度和结果。不能仅返回“已安排”，便在对话里说“已完成”。

四、对话以项目保存，切换项目要切换会话。旧结果携带分析参数、版本、时间和
状态；重算后旧回答不再充当当前事实。更早对话提供检索，不声称无限记忆。

五、功能注册、UI 调用和 AI 工具适配复用同一分析定义；新功能需声明参数、
输入前提、输出、耗时及修改范围。MCP tools/list 更新后可被 Harness 发现。

六、保留现有深色紫色 UI。自然聊天无需强制展现大段 JSON；查询和任务用简洁
状态条，错误保留在对话中并允许重试。小窗可滚动，三栏可调宽。

## 研究阶段验证及当时未完成项（历史记录）

以下是原型阶段记录，不代表 v1.2.5 最新实现。已接入的查询桥、真实 GUI 读数、历史检索修正和当前限制见 [v1.2.5 实现记录](AI_HARNESS_IMPLEMENTATION_1.2.5_ZH.md)。

- 当前源码完整测试：145 passed；311 条依赖库警告。pytest 退出清理还存在
  Windows 临时目录权限提示，测试进程退出码为 0；不把它算成业务测试失败。
- 原 API 路径的回答协议修正后，一次真实对话能解释 32 通道、30 秒、20 事件、
  sorting pending、Unit 为 0 的含义。输入为明确标记的测试上下文，不是用户
  当前打开项目的全流程验收。
- 官方 SDK 原型通过已安装 dsh、已配置 provider/model 返回“SDK已连接”。
  app 不读取该调用的模型密钥。
- 原型位于 neuroflow/harness_sdk.py，配置位于 harness_sdk.patch.yml。
  尚未注册为 app provider，不会替换正式版的运行路径。
- 原型每次新建会话，尚未实现持久 runtime、MCP 查询桥、完整错误和取消测试；
  因此不能声称已经实现研究助手。需要优先使用官方 Python SDK 或验证协议客户端
  的行为，再决定最终客户端实现，避免维护不必要的自研传输。
- 原 API 修正、上下文和对话窗口扩展属于源码开发变更，既有 v1.2.4 exe 不会
  自动改变。新安装版应在下列验收通过后构建发布。

## 必须通过的验收

1. 真正从 app 当前状态回答通道、时长、阶段和选中图的含义。
2. 按指定 Unit、事件类型、结果表查询，并用查询数值回答；错误结果不得伪装成功。
3. 连续多轮追问引用正确；保存、关闭和重开项目后仍可继续。
4. 两个项目交替提问不串数据；运行分析后下一轮读到新结果和新状态版本。
5. 读取不打断对话，重算有明确范围和确认；取消、断线、超时能恢复。
6. 模型不支持图片时有明确说明，仍可读取图表的数据及绘制参数。
7. 新增分析定义后在工具目录可发现，不为每项功能单独硬编码提示词。
8. 安装后的 exe 在小窗和三栏布局通过上述测试；记录模型、版本、问题、查询、
   输出证据及失败原因后再发布。单次连通测试不算验收完成。
