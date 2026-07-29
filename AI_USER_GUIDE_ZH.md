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
2. Provider 选择 DeepSeek，或选择 OpenAI-compatible。
3. 填写 Base URL。
4. 填写模型名称。
5. 填写 API 密钥。
6. 选择是否使用流式回复。
7. 设置超时和重试次数。
8. 点击“Check service”检测状态。
9. 点击“Save”保存非敏感配置。

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

## 11. 授权真实项目验证

30分钟项目的 AI 回归检查包含：

- 识别1,800秒、32通道、30 kHz；
- 识别保存信号已在线高通至250 Hz；
- 阻止 LFP 建议；
- 概括 Kilosort4 的4个候选 cluster；
- 把外部“8个细胞”记录为未验证观察；
- 明确无法据此判定4或8哪个正确；
- 提出 `compute_unit_qc` 工具调用；
- 本地规则将该调用标记为需要用户确认；
- 保存并重开项目后恢复2条对话和候选计划。

协议测试使用本机 DeepSeek-compatible HTTP 服务完成，没有发送原始数据和本机路径。真实外部 DeepSeek API 需要用户提供密钥后继续验证。
