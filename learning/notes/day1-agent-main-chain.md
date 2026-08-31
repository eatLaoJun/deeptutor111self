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

## Agent 主调用链口述版

### 30秒版本

> 用户消息经过 `TurnRuntimeManager` 组装成 `UnifiedContext`，交给 `ChatOrchestrator` 路由到 `ChatCapability`，再由 `AgenticChatPipeline` 创建 `AgentLoop`。`AgentLoop` 在一个不断增长的 messages 列表上循环调用 LLM：有 `tool_calls` 就执行工具并回填 `role=tool` 结果继续下一轮，没有 `tool_calls` 就作为最终回答，所有事件通过 `StreamBus` 流式返回前端。

### 90秒版本

> 用户发起一次对话后，请求会先进入 `TurnRuntimeManager`。它负责创建回合，
> 收集历史消息、Memory、Skill 和附件等数据，并组装成 `UnifiedContext`。
> 数据准备完成后，由 `ChatOrchestrator.handle()` 统一调度。Orchestrator 根据
> `active_capability` 从 `CapabilityRegistry` 取得对应能力，没有指定时默认选择
> `chat`，同时管理本回合的 `StreamBus` 和流式事件生命周期。如果选中的是
> `chat`，就调用 `ChatCapability.run()`。`ChatCapability` 是一个很薄的 Chat
> 入口，它不负责路由和模型循环，只负责创建 `AgenticChatPipeline` 并继续下放。
> Pipeline 再组装工具、Prompt 和模型客户端，最后创建 `AgentLoop` 执行多轮
> LLM 与工具调用。

### 3分钟版本 

> 用户通过 WebSocket、CLI 或 SDK 发起对话后，请求先进入 `TurnRuntimeManager.start_turn()`。它在后台任务中收集历史消息、Memory 摘要、Skill Manifest、附件等数据，组装成统一的 `UnifiedContext`，这个 Context 包含了本回合所需的全部输入。
>
> 数据准备完成后交给 `ChatOrchestrator.handle()` 统一调度。Orchestrator 做三件事：从 `CapabilityRegistry` 根据 `active_capability` 选择能力（默认是 `chat`），创建并管理本回合的 `StreamBus` 用于流式事件输出，以及在回合结束时发送 `DONE` 并关闭 bus。
>
> 对于默认 Chat 场景，Orchestrator 调用 `ChatCapability.run()`。`ChatCapability` 是一个很薄的入口层，它不负责路由和模型循环，只负责创建 `AgenticChatPipeline` 并把 context 和 bus 传下去。
>
> `AgenticChatPipeline` 负责组装：从 context 提取可用工具并生成 Schema，构建 System Prompt（包含 Memory、Skill Manifest、工具列表），选择模型客户端，最后创建 `AgentLoop` 并传入这些配置。
>
> `AgentLoop.run()` 是真正的多轮执行引擎。它在一个不断增长的 messages 列表上循环调用 LLM：如果返回 `tool_calls`，就并行执行工具、将结果以 `role=tool` 回填到 messages，然后继续下一轮；如果没有 `tool_calls` 且有正文，就作为最终回答结束；如果既没有 `tool_calls` 又没有正文，追加纠正提示重试一次。所有 LLM 输出和工具执行事件都通过 `StreamBus` 流式返回调用方。
>
> 异常情况下，比如达到最大轮次或 LLM 中途失败，`AgentLoop` 会禁用工具 Schema 并强制调用一次 LLM 尝试收尾，保证回合有明确结果。

### 一句话区分

```text
ChatOrchestrator：选择谁处理，并管理回合事件流。
ChatCapability：接住 chat 请求，并把它交给 Chat Pipeline。
AgentLoop：在不断增长的 messages 上循环 LLM，直到没有 tool_calls。
```

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
