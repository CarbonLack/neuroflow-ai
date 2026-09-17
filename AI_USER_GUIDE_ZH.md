# NeuroEphys AI 受控 AI 助手使用手册

## 1. AI 在工作流中的位置

NeuroEphys AI 的数据读取、质控、sorting、同步、统计、机器学习和绘图由本地确定性模块执行。AI 助手读取这些模块生成的结构化摘要，提供解释、候选工作流和受控工具建议。

AI 服务断开、未配置或关闭时，手动分析功能仍可运行。

## 2. 打开 AI 助手

1. 打开或创建项目。
2. 点击顶部“AI assistant”，或点击“Hide/show AI panel”展开右侧面板。
3. 面板顶部显示当前模式、Provider、模型和服务状态。
4. 点击“Preview cloud data”查看本次允许发送的内容。
5. 点击“AI manual”打开软件内说明。
6. 点击“AI settings”配置服务。

## 3. 三种模式

### 手动模式

- 不向模型发送请求；
- AI 按钮保持可见，便于随时重新启用；
- 全部工作流节点由用户选择和运行；
- 适合数据保密要求高、网络不可用或希望独立操作的场景。

### 助手模式

- AI 可以解释项目、页面、参数、结果和错误；
- AI 可以提出候选工作流；
- AI 返回的工具调用不会执行；
- 适合学习、流程复核和排错。

### 协作模式

- AI 可以提出白名单工具调用；
- NeuroEphys AI 在本地检查工具名、参数、依赖、输入和工作流顺序；
- 界面显示确认弹窗；
- 用户确认后，本地确定性模块执行；
- sorting、覆盖结果、在线发送、批量和长时间任务始终要求确认。

## 4. 配置 Provider

1. 打开“AI settings”。
2. 如果本机已部署 DeepSeek Harness，点击“读取本机 DeepSeek Harness 配置”。
3. 软件仅读取 Harness 中的 Provider、地址、模型和密钥环境变量名；不读取 Harness 密钥文件。
4. 如果是机构内网 HTTP 地址，只有勾选“仅对此机构内网 harness 允许 HTTP”后才能连接。公网地址必须使用 HTTPS。
5. 点击“检测服务状态”，确认模型列表与延迟。
6. 选择是否流式回复、推理强度、超时和重试次数。
7. 点击“应用设置”保存非敏感配置。

也可手动选择 DeepSeek、OpenAI-compatible、Ollama 或其他受支持的 Provider。Provider 适配器与分析代码分离；AI 无论来自哪个服务，都只能读取同一套受控项目摘要，并只能提出已注册的工具请求。

Provider 接口与分析代码分离。实验室私有服务、Ollama 和其他兼容端点可以复用 OpenAI-compatible 配置。

## 5. API 密钥

- 默认仅保留在当前进程内存；
- 可选择写入操作系统凭据区；
- 可使用 Provider 对应的环境变量；
- 项目文件不保存密钥；
- 结构化日志不保存密钥；
- 导出报告不保存密钥；
- Git 仓库不包含密钥。

切换 Provider 后，各 Provider 使用各自的凭据项。

## 6. 查看 AI 上下文

点击“Preview cloud data”。预览窗口列出即将发送的 JSON 字段。典型内容包括：

- 记录格式、采样率、通道数、时长和单位；
- 电极类型、脑区、参考方式和已知坏道；
- 采集滤波和参考设置；
- QC 指标；
- 当前预处理；
- sorter、版本、参数、候选 cluster 和 spike 数；
- Unit QC 与人工复核摘要；
- TTL、行为事件、正式 trial 数和同步残差；
- 统计和机器学习摘要；
- 已完成、失败、跳过和待运行节点；
- 当前页面、图表和 unit；
- 可选的匿名化最新日志。

用户可以取消本次请求，也可以移除无需发送的可选字段。

以下内容不会进入在线请求：

- 原始电压数组；
- 视频和完整行为文件；
- 本机绝对路径；
- API 密钥；
- 未经选择的完整日志；
- 原始数据文件夹。

## 7. 常用任务

### Explain this stage

解释当前节点的目的、输入、输出、参数和质量检查。

### Review project

概括已经识别的数据、已完成节点、缺失信息、风险和建议下一步。

### Propose workflow

把研究问题转换成可编辑候选工作流。右侧表格显示：

- 是否使用该节点；
- 节点名称；
- 选择理由；
- 前置条件；
- 推荐参数及理由。

用户可以取消节点、替换节点或修改参数。点击“Apply plan to project”只保存计划并移动到建议节点，不会自动执行。

### Explain latest error

读取匿名化错误摘要，区分数据问题、环境问题、参数问题和第三方工具错误，并给出恢复建议。

## 8. 工具调用确认

协作模式下，AI 可提出：

```text
inspect_project
summarize_recording
run_raw_qc
preview_preprocessing
run_sorter
load_sorting_result
compute_unit_qc
import_behavior
align_events
generate_psth
run_statistics
run_decoding
edit_figure
export_project
```

确认弹窗显示：

- 工具；
- 参数；
- 输入；
- 风险等级；
- 是否属于高成本操作；
- 是否修改项目；
- 用户确认要求。

模型不能创建未注册工具。原始数据删除、覆盖和未经授权的传输没有白名单入口。

## 9. 科学解释

AI 解释结果时分成六部分：

1. 已观察到的结果；
2. 支持结果的统计证据；
3. 可以考虑的生物学解释；
4. 当前结果不能推出的结论；
5. 数据和方法限制；
6. 建议增加的验证。

候选 cluster 统一称为 candidate unit 或 candidate cluster。完成专家复核后可记录为 candidate single unit、multi-unit activity、noise 或 uncertain。

## 10. 项目记忆

- 对话记录保存在当前项目；
- 已批准候选工作流保存在当前项目；
- 不同项目默认隔离；
- 保存项目后关闭软件；
- 重新打开 `neuroflow_project.json` 后恢复对话和工作流。

## 11. AI 如何“读懂” App

- 应用使用有版本号的 `neuroephys.cloud-project-summary.v2` 上下文协议；
- 每次请求自动加入当前项目、当前节点、已完成/失败/跳过的步骤、结果摘要和界面位置；
- 新分析模块只要把结构化结果注册到项目摘要，AI 即可使用；
- 新本地操作必须单独加入工具白名单和参数 Schema，因此“能理解新功能”不等于“可任意执行”。

这是 App 内置的 Provider 适配，不需要用界面自动化去操作 Harness 网页，也不依赖某个特定聊天窗口。

## 12. 当前实机验证

当前 Windows 开发机已验证：

- 自动识别已安装 DeepSeek Harness 的非敏感配置；
- 机构内网 Provider 健康检查通过，并能返回模型列表；
- `deepseek-v4.1-flash` 最小真实请求成功；
- Harness 返回的紧凑工具建议可转换为本地受控工具请求；
- `inspect_project` 已通过本地白名单和参数验证，但测试中没有执行任何 AI 建议的操作；
- 原始电压、本地路径和密钥没有进入请求。
