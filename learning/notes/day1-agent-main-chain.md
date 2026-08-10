# Day 1：Agent 主调用链

## 2026-08-10 闭卷摸底

### 已经掌握

- 知道默认 Chat 由 `AgentLoop` 驱动多轮 LLM 调用。
- 知道有 `tool_calls` 时需要执行工具并继续下一轮。
- 知道 `ask_user` 会暂停当前回合，收到用户回答后继续。
- 知道工具执行后可能触发 Context Checkpoint。

### 当前混淆点

1. 把“无 `tool_calls` 的正常结束”和“无正文的空回答重试”混在了一起。
2. `ChatOrchestrator`、`ChatCapability` 和 `AgenticChatPipeline` 的边界不清楚。
3. 把 `StreamBus` 理解成了事件过滤器；它实际是单回合异步事件通道。
4. 忘记了 `terminate` 表示工具产物直接成为本回合最终结果。
5. 主链中缺少 `CapabilityRegistry` 和 `AgenticChatPipeline`。

### 本轮纠正后的主链

```text
CLI / WebSocket / SDK
  -> UnifiedContext
  -> ChatOrchestrator.handle()
  -> CapabilityRegistry 选择 Capability（默认 chat）
  -> ChatCapability.run()
  -> AgenticChatPipeline.run()
  -> AgentLoop.run()
  -> LLM
       无 tool_calls + 有正文 -> 正常结束
       无 tool_calls + 无正文 -> 只追加一次纠正提示并重试
       有 tool_calls -> 执行工具 -> role=tool 回填 -> 下一轮 LLM
  -> StreamBus
  -> 调用方
```

### 下一步

- 闭卷解释五个核心对象的职责。
- 闭卷重画主链，不混入空回答和工具调用的内部细节。

## `ChatOrchestrator` 是什么时候被调用的

标准入口先进入 `TurnRuntimeManager`，不是前端直接调用 `ChatOrchestrator`：

```text
WebSocket 收到 start_turn
  -> TurnRuntimeManager.start_turn()
  -> 创建后台任务 _run_turn()
  -> 收集历史、Memory、Skill、附件等数据
  -> 构造 UnifiedContext
  -> ChatOrchestrator().handle(context)
  -> 选择并运行具体 Capability
```

CLI 和 Python SDK 先经过 `DeepTutorApp.start_turn()`，之后也进入同一个
`TurnRuntimeManager.start_turn()`。
