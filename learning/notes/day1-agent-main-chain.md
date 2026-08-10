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

## WebSocket、SSE 和 `done`

- HTTPS 是加密的 HTTP；WebSocket 的加密版本是 `wss://`，所以 HTTPS 和
  WebSocket 不是互斥选项。
- SSE 是服务端到客户端的单向 HTTP 事件流；WebSocket 是客户端与服务端双向通信。
- DeepTutor 的 `done` 只表示当前 turn 完成，不是 WebSocket 协议的关闭帧。
- 后端发送 `done` 后仍可继续接收消息；当前 Web 前端为了接收尾随的
  `session_meta`，会等待 15 秒后主动 `disconnect()`。

记忆句：**WebSocket 是通话线路，turn 是一次发言，`done` 是“这次发言说完了”，
不等于线路在协议层自动挂断。**

当前 Web 前端是按需连接：发送消息等动作调用 `sendThroughRunner()` 时才连接；打开
普通历史会话不会自动保持 WebSocket，只有发现 active turn 时才连接并订阅恢复。主动
取消、组件卸载、流超时和 `done` 后 15 秒清理会断开；意外掉线最多自动重连 5 次。

不要混淆三个生命周期：

```text
WebSocket     = 浏览器和后端之间的双向线路
turn          = 在线路上执行的一次问答任务
subscribe_turn = 把某个 turn 的事件转发到线路的订阅
```

后端的 WebSocket 主循环负责继续接收 `cancel_turn`、`submit_user_reply` 等消息；另一个
`_forward()` 后台任务负责向浏览器发送当前 turn 的事件。`done` 让 turn 和订阅收尾，
不直接终止主接收循环。

## 为什么 Runtime 固定调用 `ChatOrchestrator`

`ChatOrchestrator` 的名字有历史误导性，它实际是所有 Capability 的统一路由器：

```text
context.active_capability = chat       -> ChatCapability
context.active_capability = deep_solve -> DeepSolveCapability
context.active_capability = visualize  -> VisualizeCapability
```

`TurnRuntimeManager` 负责准备和管理 turn，`ChatOrchestrator` 负责根据名称从
`CapabilityRegistry` 选择能力；项目不是“一种 Capability 配一个 Orchestrator”。
