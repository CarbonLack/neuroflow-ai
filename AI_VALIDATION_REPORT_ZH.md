# NeuroEphys AI 受控AI集成验证

## 验证对象

- 项目：`<LOCAL_VALIDATION_PROJECT>`
- 记录时长：1800.000秒
- 当前Kilosort4候选unit：4
- 外部口头报告：8个细胞，状态为`unverified`
- 行为事件：4654
- 已定义trial：0

## 验证结果

1. 项目摘要不含原始数据路径和项目路径。
2. 在线请求载荷不含API密钥、原始数据路径和项目路径。
3. DeepSeek兼容`chat/completions`请求包含白名单工具Schema。
4. 模型提出`compute_unit_qc`后，本地规则完成参数与前置条件检查，并要求确认。
5. 250 Hz在线高通信息进入摘要，LFP请求被明确阻止。
6. 4个候选unit与口头8个细胞报告的差异被保留为待验证问题；当前证据无法判断哪个数量正确。
7. AI对话与已接受工作流写入项目，保存并重新打开后恢复成功。
8. 本轮使用本地模拟Provider验证协议和安全边界，没有调用外部模型服务。

## 产物

- JSON证据：`<LOCAL_VALIDATION_PROJECT>\exports\ai_validation\ai_integration_validation.json`
- 项目清单：`<LOCAL_VALIDATION_PROJECT>\neuroflow_project.json`

## 待验证

- 使用用户自己的DeepSeek API密钥进行一次真实在线服务连通测试。
- 在GUI中人工确认并执行一次AI提出的本地工具调用。
- 对12个全时长候选unit逐个完成人工复核。
