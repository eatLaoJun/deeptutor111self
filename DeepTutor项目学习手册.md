# DeepTutor 项目学习手册

> 本文档位于仓库根目录，是本项目学习过程的唯一主文档。

> 用途：持续记录对 DeepTutor 的技术栈、架构、调用链和具体实现的理解。
>
> 使用方式：既可以直接阅读，也可以把本文档交给 GPT，在语音通话中按章节讲解和提问。
>
> 当前基线：`main` 分支，提交 `d90ce8f8`，最后更新于 2026-08-09。

## 目录

- [1. 如何使用这份手册](#1-如何使用这份手册)
- [2. 项目是什么](#2-项目是什么)
- [3. 技术栈](#3-技术栈)
- [4. 总体架构](#4-总体架构)
- [5. 核心概念](#5-核心概念)
- [6. 一次对话的主调用链](#6-一次对话的主调用链)
- [7. 目录与关键文件](#7-目录与关键文件)
- [8. 本地启动](#8-本地启动)
- [9. 推荐学习路线](#9-推荐学习路线)
- [10. 待深入的问题](#10-待深入的问题)
- [11. 术语表](#11-术语表)
- [12. 后续记录模板](#12-后续记录模板)
- [13. 更新记录](#13-更新记录)

## 1. 如何使用这份手册

配套面试设计材料：[鼎校伴学：知识点学习闭环与面试学习指南](鼎校伴学-知识点学习闭环与面试学习指南.md)。
该文档覆盖业务故事、显式状态、暂停恢复、补救、异常和评测口径，属于设计学习材料，
不代表当前 checkout 已实现对应能力；本手册仍是项目实现事实的主文档。

### 1.1 阅读原则

本文档区分三类信息：

- **已验证**：已从当前代码、配置或实际运行结果中确认。
- **待验证**：从命名或局部代码推断，但还没有追完调用链。
- **背景知识**：用于帮助理解项目，不代表 DeepTutor 一定采用了该实现。

新增结论应尽量附带代码路径。实现发生变化时，修改原章节，不要在文档末尾重复堆叠互相冲突的描述。

### 1.2 给语音 GPT 的建议提示词

可以把本文档发给 GPT，然后这样说：

> 你是我的 DeepTutor 项目学习教练。请严格以文档中标记为“已验证”的内容为事实基础。每次只讲一个主题，先用通俗语言说明它解决什么问题，再讲核心对象和调用顺序，最后用三个问题检查我是否理解。如果文档证据不足，请明确说“文档中尚未验证”，不要自行补全项目实现。

### 1.3 持续维护规则

以下内容值得写入：

- 已追通的一条真实调用链。
- 某个核心类、协议、数据结构的职责。
- 配置读取顺序、状态存储位置和运行时覆盖规则。
- 排查问题时确认的根因、证据和验证方法。
- 重要的设计取舍，以及它和普通实现方式的区别。

以下内容通常不写入：

- 没有得到结论的随手搜索过程。
- 临时日志和一次性命令输出。
- 尚未验证的猜测。
- 与理解项目无关的机械性修改。

## 2. 项目是什么

**状态：已验证**

DeepTutor 是一个 agent-native 智能学习伴侣。它不是把所有学习功能都塞进一个固定流程，而是使用两层扩展模型：

1. **Tools**：由 LLM 在一次 agent 循环中按需调用的单次工具。
2. **Capabilities**：接管整个用户回合的多阶段能力流程。

项目提供三个主要入口：

- CLI：Typer 命令行。
- Web：Next.js 前端通过 HTTP/WebSocket 调用 FastAPI 后端。
- Python SDK：通过应用门面以代码方式调用。

三个入口最终共享运行时编排层，核心目标是让同一套 Tool、Capability、上下文和流式事件协议可以被不同入口复用。

主要证据：

- `AGENTS.md`
- `deeptutor/runtime/orchestrator.py`
- `deeptutor/core/context.py`
- `deeptutor/app/facade.py`
- `deeptutor/api/routers/unified_ws.py`
- `deeptutor_cli/main.py`

## 3. 技术栈

### 3.1 后端和运行时

**状态：已验证**

| 领域 | 技术 | 在项目中的作用 |
| --- | --- | --- |
| 语言 | Python 3.11+ | 后端、CLI、Agent 运行时和能力实现 |
| Web API | FastAPI | HTTP API 与 WebSocket 服务 |
| ASGI Server | Uvicorn | 运行 FastAPI 应用 |
| 数据模型 | Pydantic 2 | API、配置和结构化数据校验 |
| CLI | Typer、Rich、Prompt Toolkit | 命令、终端输出和交互式 REPL |
| 异步通信 | asyncio、WebSocket | Agent 执行、流式事件和实时交互 |
| LLM SDK | OpenAI、Anthropic、DashScope 等 | 对接不同模型提供商 |
| RAG | LlamaIndex、BM25、FAISS | 文档索引、检索和知识库问答 |
| 本地数据 | SQLite/aiosqlite、JSON/YAML 文件 | 本地状态、设置及部分业务数据 |
| HTTP 客户端 | HTTPX、aiohttp、Requests | 外部模型、搜索和集成调用 |

依赖真相源是 `pyproject.toml`。`requirements/` 下的文件用于镜像 Docker/CI 等安装分组，不应反过来覆盖 `pyproject.toml` 的定义。

### 3.2 前端

**状态：已验证**

| 领域 | 技术 |
| --- | --- |
| 框架 | Next.js 16 |
| UI | React 19 |
| 语言 | TypeScript |
| 样式 | Tailwind CSS 3 |
| 国际化 | i18next、react-i18next |
| 可视化 | Chart.js、Mermaid、Cytoscape |
| 测试 | Playwright、Node 测试脚本 |

前端依赖和命令定义在 `web/package.json`。源码位于 `web/app/`、`web/components/`、`web/features/`、`web/lib/` 等目录。

#### 前端 Hook 与状态管理的实际用法

**状态：已验证**

Hook 是 React 函数组件复用状态和副作用逻辑的机制，不只是“以 `use` 开头的工具函数”。
本项目前端没有额外引入 Redux 或 Zustand；主聊天状态集中在
`UnifiedChatProvider` 中：`useReducer` 管理消息、会话和流式状态的成组迁移，`useRef`
保存 runner、重连定时器及最新状态等不应触发渲染的可变对象，`useCallback` 稳定发送、取消、
重试等操作函数，`useMemo` 计算派生状态和稳定 Context value，`useEffect` 负责订阅、定时器和
卸载清理。这里的职责边界比背 API 名称更重要：展示状态用 state/reducer，外部系统同步用
effect，跨渲染但不驱动界面的对象用 ref，memo/callback 主要用于避免不必要的重新计算或
引用变化，不能把它们当作业务正确性的保障。

项目还把可复用交互抽成自定义 Hook。例如 `useSmoothStreamText` 用 state、ref、effect 和
`requestAnimationFrame` 平滑展示 WebSocket 增量，并在停止流或组件清理时取消动画；
`useChatAutoScroll` 用 ref 保存 DOM 和是否跟随底部，用 layout effect 在浏览器绘制前校正
滚动位置，并清理动画帧、MutationObserver、定时器和事件监听。Hook 必须稳定地在函数组件或
自定义 Hook 顶层调用，不能放进普通条件、循环和事件处理函数，否则 React 无法依靠调用顺序
正确关联各次渲染的 Hook 状态。

关键证据：`web/context/UnifiedChatContext.tsx:916-1885`、
`web/hooks/useSmoothStreamText.ts`、`web/hooks/useChatAutoScroll.ts`、`web/package.json`。

### 3.3 配置

**状态：已验证**

项目根目录的 `.env` 被有意忽略。运行时设置主要位于：

```text
data/user/settings/
```

也可以通过 `DEEPTUTOR_HOME` 或 `deeptutor start --home <path>` 指向其他运行时工作目录。

当前本地配置的默认端口：

- 后端：`8001`
- 前端：`3782`

## 4. 总体架构

**状态：已验证**

```text
CLI / Python SDK                 WebSocket API
        |                              |
        v                              v
DeepTutorApp.start_turn()   TurnRuntimeManager.start_turn()
        |                              |
        +--------------+---------------+
                       |
                       v
          TurnRuntimeManager._run_turn()
                       |
                       v
               UnifiedContext
              |
              v
      ChatOrchestrator
              |
      选择 Capability
       默认是 chat
              |
     +--------+--------+
     |                 |
     v                 v
ToolRegistry    CapabilityRegistry
     |                 |
     +--------+--------+
              |
              v
          StreamBus
              |
              v
       流式事件返回调用方
```

理解这张图时要抓住四点：

1. CLI 和 Python SDK 先经过 `DeepTutorApp.start_turn()`；WebSocket 直接调用
   `TurnRuntimeManager.start_turn()`，最终都由 `_run_turn()` 构造 `UnifiedContext`。
2. `ChatOrchestrator` 决定本回合交给哪个 Capability。
3. Registry 负责发现和获取 Tool/Capability，不让编排器硬编码所有实现。
4. `StreamBus` 统一输出进度、内容、错误和完成事件。

### 4.1 WebSocket、SSE 与 `done` 的边界

**状态：已验证**

HTTPS 表示“加密的 HTTP”，WebSocket 表示一种全双工通信协议，两者不是同一维度的
反义概念。浏览器访问 HTTPS 页面时，通常使用加密的 `wss://` WebSocket。普通 HTTP
请求即使复用了底层 TCP 连接，应用层仍主要按“一次请求、一次响应”工作；WebSocket
握手成功后，同一条逻辑连接上客户端和服务端都可以随时发送多条消息。

SSE 也是基于 HTTP 的长时间流式响应，但主要是服务端向客户端单向推送；客户端需要
向服务端提交新数据时，通常还要另发 HTTP 请求。WebSocket 则是双向的，所以本项目能
在同一入口上既接收 `start_turn`、`submit_user_reply`、`cancel_turn`，又持续向前端推送
模型事件。

`done` 是 DeepTutor 自定义的“当前 turn 已结束”业务事件，不是 WebSocket 协议的关闭
帧。后端 `/api/v1/ws` 在发送完某个 turn 的 `done` 后仍停留在
`while not closed: await ws.receive_text()`，连接真正结束的条件是断开、异常或显式关闭。
当前 Web 前端收到 `done` 后先把界面标为流结束，为等待标题等 `session_meta` 尾随事件，
再延迟 15 秒调用 `disconnect()`。所以准确说法是：**`done` 结束一次回合的事件流；当前
前端策略随后关闭连接，但不是 `done` 在协议层直接关掉连接。**

当前前端采用按需连接，而不是“进入对话页就永久连接”：`UnifiedChatProvider` 挂载时只
准备 runner 容器；发送消息、重新生成、提交 `ask_user` 回答等动作经过
`sendThroughRunner()`，才由 `ensureRunner()` 创建并连接 `UnifiedWSClient`。打开历史会话
主要先走 HTTP 加载；只有服务端报告该会话仍有 active turn 时，前端才建立 WebSocket 并
发送 `subscribe_turn` 恢复事件流。主动取消、页面 Provider 卸载、客户端流超时以及
`done` 后的延迟清理都会断开连接；非主动掉线则最多按指数退避重连 5 次，并通过
`resume_from` 续接原 turn。

理解运行时必须分开三种生命周期：WebSocket 是浏览器与后端之间的双向“线路”，turn 是
线路上传输的一次任务，`subscribe_turn` 是把该任务事件转发到这条线路的订阅。后端收到
`start_turn` 后，主协程仍在 `receive_text()` 等待取消或用户补充输入，同时另建
`_forward()` 后台任务，把 `runtime.subscribe_turn()` 产生的事件用 `send_text()` 推回
浏览器。turn 完成时订阅队列收到结束哨兵并停止 `_forward()`，但 WebSocket 主接收循环
仍可继续。因此 turn、订阅和连接可以先后结束，三者不是同一个对象。

关键证据：

- `deeptutor/api/routers/unified_ws.py:44-68,79-104,113-133,314-324`
- `web/lib/unified-ws.ts:157-250`
- `web/context/UnifiedChatContext.tsx:718,940-952,1045-1068,1129-1212,1214-1257,1482-1533,1538-1555`

## 5. 核心概念

### 5.1 UnifiedContext

**状态：已验证**

文件：`deeptutor/core/context.py`

`UnifiedContext` 是一次用户回合的统一输入对象，主要包含：

- 会话 ID 和用户消息。
- 历史消息。
- 用户显式启用的 Tools。
- 当前选择的 Capability。
- 知识库和附件。
- 单次请求配置覆盖。
- 语言、记忆、Persona、Skill 和 Source 上下文。
- Capability 自定义的 metadata。

关键设计点：入口层不应为不同 Capability 各造一套参数。所有入口先把数据整理成 `UnifiedContext`，后面的编排和扩展机制才能保持一致。

可以把它理解为一次回合的“请求包”：

```text
WebSocket / CLI / Python SDK
            ↓
把各自的输入整理为 UnifiedContext
            ↓
ChatOrchestrator.handle(context)
            ↓
Capability.run(context, stream)
            ↓
Pipeline 根据 context 组装 Prompt、工具和附件
```

它是一个 Python `dataclass`，通常只服务于当前回合。它不是：

- HTTP Request 对象；
- 数据库里的会话记录；
- 全局单例；
- Agent Loop 自己的循环状态。

重要字段：

| 字段 | 作用 |
| --- | --- |
| `session_id` | 当前会话标识；为空时 Orchestrator 会生成 |
| `user_message` | 当前这一轮的用户消息 |
| `conversation_history` | 之前的 user/assistant 消息 |
| `enabled_tools` | 用户显式开启的可选工具 |
| `allowed_builtin_tools` | 内置自动挂载工具的权限白名单 |
| `active_capability` | 本轮选择的能力；为空时默认 `chat` |
| `knowledge_bases` | 本轮挂载的知识库名称 |
| `attachments` | 图片、PDF 或其他文件 |
| `config_overrides` | 本轮临时配置覆盖 |
| `language` | Prompt 和输出语言 |
| `memory_context` | 注入系统提示词的记忆内容 |
| `persona_context` | 当前 Persona/Soul 指令 |
| `skills_manifest` | 当前用户可见的 Skill 清单 |
| `source_manifest` | 已附加来源的简要目录 |
| `metadata` | turn id、source index、用户等待器等扩展数据 |

一个最小例子：

```python
context = UnifiedContext(
    session_id="session-123",
    user_message="解释傅里叶变换",
    active_capability="chat",
    enabled_tools=["web_search"],
    language="zh",
)
```

`ChatOrchestrator` 不会解析这些业务字段，而是把完整 Context 路由给选中的
Capability。`AgenticChatPipeline` 才会读取其中的知识库、附件、工具、Memory、
Skill 和 metadata，生成本轮真正传给模型的 messages 和 tool schemas。

### 5.2 Tool

**状态：已验证到注册、装载、调用和结果回填**

Tool 是单次函数能力，由 LLM 在 agent 循环中按需选择。例如：

- `web_search`
- `paper_search`
- `reason`
- `rag`
- `read_source`
- `exec`
- `code_execution`

Tool 的基础协议位于 `deeptutor/core/tool_protocol.py`，注册表位于 `deeptutor/runtime/registry/tool_registry.py`。

并非所有 Tool 都永久暴露。部分工具根据知识库、附件、沙箱等上下文条件自动挂载，这可以减少无关工具对模型上下文的占用。

#### 工具存在哪里

需要区分四种不同的“存储”：

| 层次 | 存放位置 | 存放内容 |
| --- | --- | --- |
| 源代码 | `deeptutor/tools/`、`deeptutor/tools/builtin/__init__.py` | 工具类、参数定义和 `execute()` 实现 |
| 进程运行时 | 全局 `ToolRegistry._tools` 字典 | `工具名 -> BaseTool 实例` |
| 当前回合 | `AgentLoop.enabled_tools`、`AgentLoop.tool_schemas` | 本回合可用工具名和 function-calling schema |
| 对话循环 | `AgentLoop` 的 `messages` 列表 | assistant 的 tool call 和执行后的 `role=tool` 结果 |

`BUILTIN_TOOL_TYPES` 是内置工具类清单。首次调用 `get_tool_registry()` 时，
`ToolRegistry.load_builtins()` 会实例化这些类，并通过
`self._tools[tool.name] = tool` 保存到当前 Python 进程的内存中。

模型不会收到 Python 工具对象或 `execute()` 源代码。它只收到由
`ToolDefinition.to_openai_schema()` 生成的 JSON schema，例如工具名、说明、
参数类型和必填项。真正的工具实例始终留在服务端注册表中。

#### 工具怎样交给当前 AgentLoop

```text
BUILTIN_TOOL_TYPES
  -> ToolRegistry._tools：注册全部可用工具实例
  -> _compose_enabled_tools(context)：选出本回合允许使用的工具名
  -> _build_llm_tool_schemas(...)：生成本回合工具 schemas
  -> AgentLoop(enabled_tools=..., tool_schemas=...)
  -> _call_llm(): kwargs["tools"] = tool_schemas
  -> 模型返回 tool_calls
  -> dispatch_tool_calls()
  -> ToolRegistry.execute(name, **args)
  -> BaseTool.execute(**args)
  -> ToolResult
  -> 转为 role=tool 消息，进入下一轮 LLM
```

也就是说，传给 `AgentLoop` 的不是“全部工具代码”，而是：

1. `enabled_tools`：本回合启用的工具名称，主要用于 Prompt 和运行时控制。
2. `tool_schemas`：真正发给模型的工具调用协议。

模型根据 schema 产生工具名和 JSON 参数；服务端再按工具名回到
`ToolRegistry._tools` 查找实例并执行。

#### 真实案例：`brainstorm` 如何跑完一轮

`BrainstormTool` 是一个完整但链路较短的内置 Tool：

1. `BrainstormTool.get_definition()` 声明工具名 `brainstorm`，并定义必填
   `topic` 和可选 `context` 两个字符串参数。
2. `BrainstormTool` 被列在 `BUILTIN_TOOL_TYPES` 中；
   `ToolRegistry.load_builtins()` 实例化并注册它。
3. 当用户为当前回合启用 `brainstorm` 后，
   `_compose_enabled_tools()` 保留该名称，`build_openai_schemas()` 再把
   `ToolDefinition` 变成模型可见的 function schema。模型看到的是
   工具名、说明、参数类型和 `required=["topic"]`，而不是 Python 代码。
4. 如果外层 Chat LLM 返回
   `brainstorm({"topic": "Agent 学习路线", "context": "面试准备"})`，
   `AgentLoop` 会先保存 assistant 的 tool call，再交给
   `dispatch_tool_calls()`。
5. Dispatcher 解析 JSON 参数并调用
   `execute_tool_call() -> ToolRegistry.execute() -> BrainstormTool.execute()`。
6. `BrainstormTool.execute()` 继续调用
   `deeptutor.tools.brainstorm.brainstorm()`。该函数使用自己的头脑风暴
   system prompt 执行**一次独立 LLM 调用**，它不会再进入一个新的
   AgentLoop。
7. 内层 LLM 的文本被包装为 `ToolResult.content`；dispatcher 再将其转为
   包含原 `tool_call_id` 的 `role=tool` 消息，追加回外层 Chat
   `messages`，下一轮外层 LLM 读取该结果并组织最终答案。

因此这个案例中有两次职责不同的模型调用：**外层 Chat LLM
做工具决策和最终回答，内层 Brainstorm LLM 只做发散生成**。

关键证据：

- `deeptutor/core/tool_protocol.py:16-94,170-217`
- `deeptutor/tools/builtin/__init__.py:42-74,1442-1447`
- `deeptutor/runtime/registry/tool_registry.py:36-59,93-151`
- `deeptutor/agents/chat/agentic_pipeline.py:302-335,536-569,643-648`
- `deeptutor/agents/chat/agent_loop.py:269-363`
- `deeptutor/core/agentic/tool_dispatch.py:84-190,337-467,516-548`
- `deeptutor/tools/brainstorm.py:45-104`
- `tests/core/test_builtin_tools.py::test_brainstorm_tool_passes_llm_arguments`
- `tests/agents/chat/test_agent_loop.py::test_tool_round_then_finish`

Deferred MCP 工具还有一层会话级记录：
`deeptutor/services/mcp/session_state.py` 会把已经动态加载的**工具名称**
保存到当前 chat session 工作区的 `loaded_tools.json`。这里持久化的仍然只是
名称，不是 Python 工具实例，也不是完整工具源代码。

### 5.3 Capability

**状态：已验证到架构层，逐个流程待深入**

Capability 是接管整个回合的多阶段流程。当前架构描述中的主要能力包括：

- `chat`
- `mastery_path`
- `deep_solve`
- `deep_question`
- `deep_research`
- `visualize`
- `math_animator`

Capability 的基础协议位于 `deeptutor/core/capability_protocol.py`，注册表位于 `deeptutor/runtime/registry/capability_registry.py`，内置能力映射位于 `deeptutor/runtime/bootstrap/builtin_capabilities.py`。

### 5.4 StreamEvent 与 StreamBus

**状态：已验证到主流程与事件缓冲边界**

相关文件：

- `deeptutor/core/stream.py`
- `deeptutor/core/stream_bus.py`

Capability 不直接依赖某个 UI，而是向 `StreamBus` 发出统一事件。CLI、WebSocket 和 SDK 可以各自消费这些事件。

这是一种“执行逻辑和展示方式解耦”的设计：能力只描述发生了什么，入口决定如何显示。

StreamBus 的机制层可拆成三件套（已核对 `stream_bus.py` 的 `emit/subscribe/close`）：

- **异步队列**：`subscribe()` 为每个订阅者创建一个 `asyncio.Queue()`，空队列上的 `get()` 会挂起等待。当前未设置 `maxsize`，属于无界队列，不能说成“队列满了生产者自动等待”；`await q.put(event)` 本身不代表已经实现容量背压。
- **多订阅者**：`emit()` 先把事件追加到 `_history`，再向各订阅队列放入同一个事件对象的引用，而非深拷贝整份 payload。新订阅者先回放历史，再消费自己的实时队列。
- **显式收尾标记**：编排器在 `finally` 里发出 `DONE`，随后 `close()` 设置 `_closed` 并向各订阅队列放入 `None` 哨兵。消费者处理完前面的事件后退出，不是因为队列暂时为空；关闭后的新订阅者则回放历史后直接结束。

**本轮内存不只有 `messages`**

`StreamBus._history` 在本轮持续保留已发出的事件，当前没有按条数或字节数裁剪；
`close()` 也不清空它。取消订阅会移除对应队列，回合收尾会注销 bus，但对象仍需等其他
引用释放后才可回收，不能把“关闭 Stream”理解成“立即清空所有内存”。
证据：`deeptutor/core/stream_bus.py` 的 `__init__/emit/subscribe/close`，以及
`deeptutor/runtime/orchestrator.py` 的 `handle()` 收尾。

外层 `TurnRuntimeManager._run_turn()` 还会累积 `assistant_events` 和
`content_segments`，供事件持久化和最终答案组装使用；`turn_runtime.py:1019` 的实时
订阅队列同样未设置容量上限。因此容量评估还需计入事件对象、队列引用、序列化临时
缓冲及工具返回值，不能只用 Prompt Token 数估算一个用户的全部内存。
证据：`deeptutor/services/session/turn_runtime.py:1162`、`:1167`、`:1671`、`:1674`。

**评估建议，不是当前容量实测**：区分“在线连接数”和“同时执行的 Turn 数”，按基础
服务及所有 worker 常驻内存、空闲连接开销、活跃 Turn 增量和安全余量估算整机负载。
外部 LLM/OCR 推理不在本机加载对应模型，但上传缓冲和返回结果仍可能占用本机内存；
是否支持 200 人在线还应压测长会话、集中提问、大工具结果和慢消费者。上下文裁剪
只限制发给模型的内容，不自动限制上述事件历史或队列，不能据此承诺固定人数上限。

**关于 `_bus_registry`（模块级全局查找表，不是单例）**

`stream_bus.py` 末尾有一个模块级变量 `_bus_registry: dict[str, StreamBus] = {}`，外加 `register_bus / unregister_bus / get_bus` 三个函数。它和 `class StreamBus` 是**同一文件、同一模块层级的两个独立名称**——`_bus_registry` 不是 `StreamBus` 的类属性。

- **是全局变量**：定义在模块顶层，Python 模块只会被 import 一次，所有引用 `stream_bus` 的代码共享同一个 dict 对象。
- **不是单例模式**：单例指「某个类只能有一个实例」，而这里的 `StreamBus` 在每个回合都 `new` 一个，注册表里同时挂着**多个** StreamBus 实例（一个 turn_id 对应一个）。真正「全局唯一」的是那张 dict 容器本身，不是 StreamBus 实例。
- **准确定性**：这是 Service Locator / Registry 模式——用模块级全局变量做一张「按 key 找服务实例」的查找表，对象本身可多例注册进去。下划线前缀只是「模块内部用」的 Python 惯例。

它与 5.4 三件套的关系：三件套讲的是**单个 bus 实例内部**如何扇出事件；`_bus_registry` 讲的是**多个 bus 实例之间**如何被外部按 turn_id 找回（尤其 ask_user 暂停恢复要用，见 6.9）。证据 `stream_bus.py:308-325`。

### 5.5 Skill

**状态：已验证到存储、Manifest 组装和按需加载**

Skill 是供模型按任务需要查阅的流程包，不是可直接执行的
Tool。每个 Skill 以目录为单位，核心文件是 `SKILL.md`，还可携带
`references/` 等附属资源。

运行时有两层来源：

- 内置 Skill：`deeptutor/skills/builtin/`，运行时只读。
- 用户 Skill：当前用户 workspace 的 `skills/` 目录；同名时覆盖内置 Skill。

普通 Skill 不会把全文都塞进 System Prompt。`SkillService.summary_entries()`
先生成名称、说明和可用状态等 Manifest，`turn_runtime` 将它写入
`UnifiedContext.skills_manifest`。Chat 看到有 Skill 后自动挂载 `read_skill`
Tool；模型匹配到任务时，再调用 `read_skill` 读取完整 `SKILL.md`
或附属文件。只有标记 `always: true` 且当前可用的 Skill 会被提前
全文注入。

`read_skill_file()` 拒绝绝对路径和 `..` 路径穿越，并限制单次返回文本
长度；因此 Skill 的核心取舍是**先给目录，命中后再读全文**，以减少
无关上下文占用。

关键证据：

- `deeptutor/services/skill/service.py:1-46,215-254,408-520,993-1022`
- `deeptutor/services/session/turn_runtime.py:1375-1412,1625`
- `deeptutor/agents/chat/agentic_pipeline.py:536-569`
- `deeptutor/tools/builtin/__init__.py:1203-1276`

### 5.6 三层记忆

**状态：已验证到存储结构、归并入口和 Chat 注入**

Memory 模块是 Agent 的**长期记忆子系统**，负责把用户在不同业务场景中产生的
原始交互和行为数据，提炼成可追溯、可更新、可按需读取的用户记忆，并在后续回合
中提供给 Agent。它不是 LLM 本身，也不等同于当前回合的 conversation history 或
知识库 RAG：history 主要服务当前上下文窗口，RAG 提供外部资料，Memory 则沉淀
用户跨回合、跨场景的稳定事实、学习状态和显式偏好。

代码上，`MemoryStore` 是统一门面；Snapshot Adapter 负责从各业务存储读取实体，
Trace 负责追加原始事件，consolidator 负责 Snapshot Entity→L2→L3 的 LLM 归并、审计、去重和
结构合并，`read_memory` / `write_memory` 则是 Agent 可调用的记忆读写入口。

记忆模块以当前用户的 memory root 为隔离边界。这里的“三层”不是数据库冷热分层，
而是从业务原文到场景事实、再到跨场景长期认识的逐级提炼：

| 层级 | 主要存储 | 职责 |
| --- | --- | --- |
| L1 | `snapshot/<surface>/`、`trace/<surface>/<YYYY-MM-DD>.jsonl` | 保留各业务场景的当前原始实体、变更记录和事件 Trace |
| L2 | `L2/<surface>.md`、`L2/<surface>.meta.json` | 从单一场景增量提取带来源引用的短事实 |
| L3 | `L3/<recent\|profile\|scope\|preferences>.md` 及对应 meta | 跨场景聚合近期状态、稳定画像、知识范围和显式偏好 |

#### 持久化边界：记忆会保存，但不是统一写入关系型数据库

“L1/L2/L3 入库”需要区分**持久化**和**写入 MySQL/SQLite 表**：

- **L1 的业务原始数据**仍保存在各自业务存储中。以 Chat 和 Quiz 为例，消息、
  题目及作答记录来自会话 SQLite；Notebook、KB、Partner 等 surface 则由对应的
  JSON、JSONL 或 workspace 文件提供。L1 不是一张统一的 memory 表。
- **L1 的记忆侧索引与证据**保存在当前用户的 memory root：Snapshot 的
  `state.json` / `changes.jsonl` 记录实体指纹和变更，`trace/<surface>/` 下的
  JSONL 记录按场景追加的原始事件。Snapshot 刷新和 Trace 追加都是文件持久化。
- **L2 和 L3 的归并结果**直接持久化为 Markdown 文档及旁路的 `*.meta.json`，
  更新时通过临时文件加原子替换写盘；它们不是 MySQL 表，也不是向量数据库中的
  embedding。L2/L3 的文档 ID、引用关系和增量处理状态都在这些文件中维护。
- 当前实现中，业务原始数据会随业务流程持续写入；L2/L3 则由 Memory Workbench
  或 `run_update` 更新流程触发，并非每条消息都同步执行一次 LLM 归并。更新后可按
  配置自动执行 dedup / merge。

因此更准确的说法是：**三层记忆都做了持久化，L1 连接业务原始存储并保存文件型
证据索引，L2/L3 采用按用户隔离的 Markdown + JSON 文件存储，而不是统一“入库”到
MySQL。**

需要区分两个容易混淆的概念：

```text
业务原始数据（事实来源）
SQLite / JSON / JSONL / workspace 文件
              │ Snapshot Adapter 读取并统一包装
              ▼
L1（Memory 的原始证据视图）
Entity + fingerprint + snapshot state/change + Trace
              │ LLM 增量提取
              ▼
L2（场景事实） → L3（跨场景长期记忆）
```

因此，“原始数据层”通常指业务系统里的 source of truth；“L1”是记忆系统对这些
原始数据的逻辑层和证据入口。当前实现不会把所有业务原文再复制到 L1 目录：Chat
原文仍在会话 SQLite 中，Adapter 读取后临时构造 `Entity`；L1 目录主要保存
fingerprint、变更日志和 Trace。面试中可以简化说“L1 保留原始交互证据”，但不要
说成“L1 一定是一张保存全部 user/assistant/system 原文的表”。

#### L1：原始数据与证据层

L1 当前有两种互补来源。`snapshot.adapters` 从真实业务存储读取 `chat`、
`notebook`、`quiz`、`kb`、`book`、`partner`、`cowriter` 七类实体；每个
`Entity` 都有稳定 id、时间、完整正文、metadata 和 fingerprint。刷新时把
fingerprint 集合写入 `snapshot/<surface>/state.json`，并把 added / modified /
removed 变化追加到 `changes.jsonl`。此外，`MemoryStore.emit()` 会把偏好声明、
KB 查询等事件追加到按天分片的 Trace JSONL；该写入失败只记录日志，不反向打断业务。

L1 不是一个需要由 L2 “启动”的常驻任务。业务流程先独立写入各自的事实存储；
`snapshot.read_snapshot(surface)` 每次都通过 Adapter 现场读取这些数据。
`refresh_snapshot(surface)` 只是把当前 fingerprint 和差异日志落盘。当前
`run_update("L2", surface)` 直接调用 `read_snapshot()`，不会先调用
`refresh_snapshot()`。因此，更新 L2 会消费 L1 的实时证据视图，但不等于启动
或刷新 L1。

`Entity` 是本次调用期间的标准化 Python 对象，不是另一份持久化业务数据。
它用 `id` 建立 `<surface>:<id>` 证据引用，用 `label` 和 `ts` 在 L1 界面展示，
用 `content` 向 L2 Update/Audit 提供完整正文，用 `metadata` 保留业务语义，用
`fingerprint` 判断同 id 实体的内容是否变化。API 返回或归并调用结束后，这批
`Entity` 对象就释放；Snapshot 目录不保存其完整 `content`。

当前真正调用 `read_snapshot()` 的地方只有三类：打开 Memory 首页或 L1 页面时的
`GET /memory/snapshot/{surface}`（包括页面重新获得焦点时重读）、L2 Update，
以及 L2 Audit。点击 L1 页的 Refresh 才会调用 `refresh_snapshot()`，把当前
`{entity_id: fingerprint}`、label 和 `last_refresh` 原子写入 `state.json`，并把与上次
state 相比的 added / modified / removed 追加到 `changes.jsonl`。这个 Refresh 的用途是
让 L1 界面能显示“自上次确认后发生了什么变化”，它不会调用 LLM，也不会
自动触发 L2。

Trace 是 L1 的另一条独立写入路径。例如 RAG 查询完成时追加 `kb/query`，
`write_memory` 写显式偏好时追加 `chat/preference_stated`，直接按 UTC 日期写入
`trace/<surface>/<date>.jsonl`。根据当前 `run_update("L2", ...)` 实现，自动 L2 Update
只读 Snapshot Entity，并不读通用 Trace JSONL。Trace 目前可通过
`GET /memory/trace/{surface}` 读取；KB query 还会显示在 L1 Queries 页、计入 L2 overview
的 backlog，而 `preferences` 条目会保存 preference Trace id 作为来源 ref。

#### L1 到 L2：单场景事实抽取

L2 场景与上述七个 surface 一一对应。更新某个 L2 时，consolidator 通过
`snapshot.read_snapshot(surface)` 读取当前实体，再用 `<surface>:<entity_id>`
与 `<surface>.meta.json` 中的 `seen_entity_refs` 做集合差，只处理未归并的实体。
新实体按时间排列并按边界切块，LLM 只能输出指定 section 下、长度不超过 240 字符
且带本 chunk 合法 ref 的事实。Runtime 会再次校验引用池，然后通过统一 `AddOp`
追加到 Markdown 文档并原子写盘；可配置在更新后继续运行 LLM 去重和无 LLM 的
结构合并。由此 L2 保存的是“Chat 中反复出现的误解”“Quiz 中的错误模式”这类
场景事实，而不是整段原文副本。

这里的“反复出现”是归并提示词的语义目标，不是当前代码里的次数阈值。
`update_l2.yaml` 要求抽取“稳定事实”，各 surface 的 focus 也强调反复主题或错误模式；
但 Runtime 只硬性校验事实至少有 1 个本 chunk 的合法 ref，没有要求“至少出现
2 次”或“至少 2 个 ref”。所以它目前是 LLM 基于证据的语义归纳，不是可复现的
统计判定。

#### L2 到 L3：跨场景综合

更新 L3 时，consolidator 读取七份 L2 文档，通过各 L2 entry id 与 L3 meta 的
`seen_l2_entry_ids` 做增量判断，再让 LLM 按 slot 综合：`recent` 记录近期活动，
`profile` 记录有多处证据支撑的稳定画像，`scope` 记录熟悉、练习中或不确定的知识
范围。当前 L3 事实引用的是参与综合的裸 surface 名，因此追溯路径是
`L3 -> L2 surface 文档 -> L1 entity`。提示词要求结论保持客观、带场景限定，并由
Runtime 校验引用、长度和文档结构。`preferences` 不参与自动聚合，只在用户明确
表达偏好时由 `write_memory` Tool 写入；该 Tool 同时生成一条 L1 Trace 作为来源。

L3 也不能整体等同于“用户画像”：只有 `profile` slot 专门承载身份、学习风格和
知识水平；`recent`、`scope`、`preferences` 分别承载近期活动、知识边界和显式偏好。
`profile` 的 focus 要求多个 surface、多个 L2 条目支撑，但当前引用校验器只强制至少
1 个合法 surface ref，并未从代码上强制“跨多个 surface”；这同样属于提示词设计目标。

#### 广义用户画像与内部 slot 生命周期

对产品和简历表述，可以把 L3 中所有跨 Session 的用户长期信息统一称为**广义用户画像**，
其内部包含稳定特征、近期活动、知识状态和显式偏好。“统一叫用户画像”是对外概念收敛，
不代表内部所有信息采用同一种生命周期。当前 DeepTutor 没有名为 `learning_state` 的单独
slot：稳定身份、学习风格、知识水平进入 `profile`，最近 1～4 周活动进入 `recent`，已接触
概念及“熟悉/练习中/不确定”进入 `scope`，显式偏好进入 `preferences`。

需要注意术语范围：源码中的 `profile` 只表示广义用户画像里的稳定画像维度，并不等于整个
L3；对外说“用户画像”时则可以统称 `profile + recent + scope + preferences`。

| 维度 | 稳定画像维度（`profile`） | 动态学习维度（`recent + scope`） |
| --- | --- | --- |
| 典型内容 | 年级、长期学习风格、相对稳定的知识水平 | 当前章节、知识点掌握度、近期错题、任务进度 |
| 稳定性 | 较高，跨较长时间成立 | 较低，会随练习、测评和复习持续变化 |
| 推荐更新触发 | 明确信息变更，或多次/跨场景证据形成稳定结论 | 完成练习、测评、任务或一次有效学习 Session 后 |
| 推荐更新频率 | 低频、证据阈值高，通常按天/周或事件触发 | 高频、事件驱动，可按回合后或批次聚合 |
| 冲突处理 | 谨慎覆盖，需要新证据足够稳定 | 新结果可按时间和置信度快速替换旧状态 |
| 时效策略 | 长期有效，缓慢衰减或显式修改 | 必须带时间，过期、衰减或被更新状态覆盖 |
| Agent 用途 | 调整讲解风格、默认难度和交互方式 | 选择下一知识点、复习内容和练习难度 |

两类信息可以同时进入 `UnifiedContext`，但不应无条件把全部历史内容每轮完整注入。推荐让
画像保持短小并以较高优先级提供稳定约束，再按当前问题检索相关的最新学习状态；每条状态
保留 `updated_at`、来源证据和置信度，避免 Agent 使用已经过期的掌握结论。

这里的“区分”是逻辑生命周期隔离，不要求物理上拆成两个数据库。`profile`、`recent`、
`scope`、`preferences` 本身已经是类型标签，关系数据库中可以统一使用一张 L3 表，以
`(user_id, slot)` 作为唯一键分别保存内容和元数据，不需要再增加重复的 `memory_type`。
关键是每个 slot 独立维护版本、更新时间、证据、置信度和过期策略，并允许局部更新。
若把全部 slot 放进同一行 JSON 也能工作，但高频更新 `recent/scope` 时需要处理整行覆盖和
并发写冲突；“同表按 slot 分行”通常更直接。

`UnifiedContext` 是一次请求的组合视图，不是持久化数据模型：Context Builder 可以把同表
中的多个 slot 组装成一个 `memory_context`。当前 DeepTutor 把 L3 分别保存为多个 Markdown
文件，再由 `read_l3_concat()` 统一拼接；这是文件存储下的实现选择，而不是必须物理分离的
架构约束。整体仍可概括为“按 slot 独立更新，读取时组合消费”。

**当前实现边界：** `profile`、`recent`、`scope` 都由用户在 Memory Workbench 选择 slot
执行 Update，或直接调用对应 API 后，基于未处理的 L2 entry 增量生成；仓库当前没有为
画像和学习状态设置不同周期的自动调度。因此表中的更新频率属于推荐的 Runtime 策略，
不是已经存在的定时任务。

关键证据：

- `deeptutor/services/memory/consolidator/prompts/zh/_meta.yaml:26-35`
- `deeptutor/services/memory/consolidator/modes/update.py:357-706`
- `deeptutor/services/memory/store.py:103-151`

#### 回到 Agent 上下文

当请求显式携带 memory references 时，`turn_runtime` 调用
`MemoryStore.read_l3_concat()` 拼接四份 L3 文档，写入
`UnifiedContext.memory_context`，随后 `ChatPromptAssembler` 把它作为独立的
`memory` System Prompt block 注入本回合。没有显式预注入时，只要用户已有 L3
内容，Chat 仍可自动挂载 `read_memory` Tool，由模型在需要个性化回答时按需读取。
因此长期记忆既支持回合开始前的显式注入，也支持 Agent Loop 内的按需检索。

#### RAG 证据与 Tool Result：本轮上下文和持久化边界

**状态：已验证当前 Chat 主链路**

RAG 证据和 Tool Result 都会进入本轮模型消息上下文，但不是预先存进 `UnifiedContext` 的
同名字段。`UnifiedContext` 保存 `conversation_history`、`knowledge_bases`、
`memory_context` 等本轮输入；Agent Loop 再根据这些输入构造并持续扩展本轮 `messages`。

RAG 有两条进入模型输入的路径：

1. 有已选知识库时，Loop 开始前对最多 3 个 KB 并发检索，每个 KB 的证据正文最多保留
   4000 字符，并作为 KB Seed 拼到本轮末尾的 user message，因此第一次 LLM 调用就能看到。
2. 模型在 Loop 中主动调用 `rag` 时，检索正文作为 `ToolResult.content` 被转换为
   `role=tool` message；其他普通工具也使用相同协议，下一轮 LLM 读取结果后继续推理。

“入库”需要区分不同对象：

| 对象 | 是否持久化 | 后续模型是否自动复用 |
| --- | --- | --- |
| 知识库原文和索引 | 是，属于 KB 自身存储 | 后续重新检索后使用 |
| 自动 KB Seed 的证据正文 | 不作为对话正文或独立 Tool Result 保存 | 否；下一轮需要重新检索 |
| Agent 主动调用产生的 Tool Result | 作为 assistant 的 `events_json`、`turn_events` 和 workspace 事件轨迹保存 | 否；默认历史构造不读取事件正文 |
| 最终 assistant 回答 | 作为普通 assistant message 保存 | 是；可进入后续历史或会话摘要 |
| RAG Memory Trace | 只记录 query、KB 名称和结果字符数 | 可作为 L1 行为证据，但不包含检索 passage |

因此 `role=tool` 只在当前 Agent Loop 的内存消息列表中存在，不会作为 `messages` 表的一条
独立历史消息保存。`ContextBuilder` 重建下一轮上下文时只读取 user/assistant/system 的
正文，不读取 `events_json`；Chat L1 Snapshot 同样不吸收 Tool Result 事件。工具若自身具有
持久化副作用，例如 `write_memory`、`write_note` 或生成文件，则由对应 Service 保存业务结果，
不能据此推导所有 Tool Result 都会自动进入长期记忆。

#### Redis 能否存放 Agent Loop 的 `messages`

**当前事实**：可以在架构上接入，但当前主链路没有 Redis Session Store。跨回合的
user/assistant 消息由 `SessionStoreProtocol` 抽象，目前实现是 SQLite 或 PocketBase；
`ContextBuilder.build()` 从 Store 读取并压缩历史，`AgentLoop.run()` 再创建本轮局部
`messages`，后续 assistant tool calls 和 `role=tool` 结果直接追加到这份列表。
证据：`deeptutor/services/session/protocol.py`、`context_builder.py:352-461`、
`deeptutor/agents/chat/agent_loop.py:190-363`。

**推荐方案，不代表当前已实现**：Redis 更适合作为跨 worker 的活跃 Turn 缓存或恢复
checkpoint，而不是替代协程内的工作列表。建议执行路径为：

```text
持久化会话历史 -> 组装本地 messages -> Agent Loop 就地追加
                                  -> 稳定轮次边界写 Redis checkpoint
Turn 完成 -> 最终消息/事件写权威存储 -> 删除 Redis key 或等待 TTL
```

所谓“稳定边界”至少应保证一条 assistant tool-call 声明与它对应的全部 `role=tool`
结果已经配对，避免进程在中间失败后恢复出违反模型协议的半轮状态。checkpoint 还应保存
`turn_id`、轮次、版本号、状态和过期时间，并通过版本比较、事务或 Lua 保证并发更新不会
相互覆盖；大型 Tool Result 只保存摘要和对象存储引用，不把原始文件塞进 Redis。

这种设计的主要收益是 WebSocket 重连、worker 故障转移和多实例接续执行，而不是凭空
节省内存。Redis 本身也是内存系统；如果和应用部署在同一台 16 GB 服务器，只是把数据从
Python 堆移动到 Redis，并增加序列化副本。每次 append 都把整份 256K 上下文远程覆写，
还会放大网络和序列化开销，因此应按完成轮次或关键状态点 checkpoint，而非逐条消息写。

当前 Loop 接近上下文窗口的 90% 时，还会优先把早期 `role=tool` 正文替换为裁剪提示。这进一步
说明 Tool Result 是本轮工作记忆，而不是稳定长期记忆。准确概括是：**本轮原文回填、事件轨迹
持久化、跨轮不直接复用、长期记忆不自动吸收。**

**设计建议，不代表当前已实现：**生产系统不宜在“全部入库”和“完全不入库”之间二选一，
更合理的是按用途选择性持久化：

| 层次 | 推荐保存内容 | 推荐策略 |
| --- | --- | --- |
| Tool 运行审计 | tool/call id、脱敏参数、状态、耗时、错误、结果摘要或对象引用 | 短期或按合规周期保存；大结果不直接塞数据库 |
| Tool 业务副作用 | 写入的 Memory、Note、文件、任务等领域对象 | 由对应 Service 作为权威数据长期保存 |
| RAG 检索追踪 | query、KB、retriever/mode、index version、Top-K 的 chunk id/rank/score/content hash、耗时 | 独立 Retrieval Trace 保存，支持评测、回归和问题定位 |
| RAG 证据正文 | 通常不重复保存全文，只保存 Chunk 引用 | 语料可变且要求复现时，再保存快照或不可变版本引用 |
| 长期用户画像 | 从结果中验证出的稳定用户事实及来源引用 | 经过抽取、冲突检查和置信度门槛后选择性晋升，禁止原样灌入 |

对当前 DeepTutor，`RAGService` 的 L1 Trace 只有 query、KB 名称和结果字符数，不能独立复现
当时的 Top-K；主动 RAG Tool 的完整 metadata 虽在事件轨迹中，但自动 KB Seed 没有等价的
候选明细持久化。若要支撑线上 Recall 回放与检索回归，建议新增统一 `RetrievalTrace`，记录
稳定 Chunk 引用和索引/检索配置，而不是依赖聊天消息或复制 passage 全文。Tool Result 也应
采用“短结果内联、大结果对象存储加引用、敏感字段脱敏或不存”的策略。

一种可直接落地的关系模型是：

```text
tool_executions
  id, session_id, turn_id, tool_call_id, tool_name,
  redacted_args_json, status, latency_ms,
  result_preview, result_ref, error_code, created_at

rag_retrievals
  id, session_id, turn_id, query, kb_id,
  retriever_mode, index_version, top_k, latency_ms, created_at

rag_retrieval_items
  retrieval_id, rank, chunk_id, score, content_hash, source, page
```

一次 Tool 调用开始时可插入 `running` 记录，结束后更新状态、耗时和结果引用；RAG 则在一次
query 记录下保存多条候选 item。短小且安全的结果可内联 preview，较大的 JSON、网页正文或
执行产物写对象存储/文件存储，数据库只保存 `result_ref + hash + size + TTL`。知识库原文、
Chunk 和向量索引继续由 KB/Vector Store 管理，用户画像只接收经过验证后的抽取事实。

当前 DeepTutor 尚未采用上述专表：SQLite 把 Tool 相关 StreamEvent 同时保存在 assistant
message 的 `events_json` 与 `turn_events`，并镜像到 workspace 的 `events.jsonl`；KB 原文和
索引使用知识库目录/version 存储，Memory Trace 使用按日 JSONL。因此这是对现有事件存储的
结构化生产改造建议，而不是当前数据库 schema 的描述。

简历中不宜写成“UnifiedContext 内直接存放 RAG 和 Tool Result”，更准确的说法是：

> 基于 UnifiedContext 承载近期对话、用户画像与知识库选择，并在 Agent Loop 中按需注入
> RAG 证据和 Tool Result，通过历史摘要、结果裁剪与优先级控制治理模型上下文。

关键证据：

- `deeptutor/core/context.py:34-84`
- `deeptutor/agents/chat/agent_loop.py:163-205,346-400`
- `deeptutor/agents/chat/agentic_pipeline.py:360-401,1015-1085,1152-1188`
- `deeptutor/core/agentic/tool_dispatch.py:492-568`
- `deeptutor/services/session/turn_runtime.py:1579-1659,1661-1720,1987-2019`
- `deeptutor/services/session/sqlite_store.py:133-147,762-815,1211-1267`
- `deeptutor/services/rag/service.py:150-166`
- `deeptutor/services/memory/snapshot/adapters.py:395-442`

#### 跨 Session 原文回忆：三层记忆之外的按需检索

**状态：已验证当前能力缺口；以下工具方案属于设计建议，尚未接入普通 Chat**

当前 Chat 的 L1 粒度是一条 `Entity` 对应一个 Session，`content` 中包含该 Session 的
用户/助手消息，`metadata` 中保存 `session_id` 和消息数量。但当前 L2 并不是“每条 L1
固定生成一条 Session 摘要”：L2 Update 会把未处理的 L1 Entity 分块交给模型抽取事实，
随后进行去重和合并，最终保存为 `L2/chat.md`。因此，**现有 L2 是带来源引用的事实文档，
还不是可以按 Session 直接执行 SQL 查询的摘要表**。

当前 `read_memory` 是无参数工具，只调用 `MemoryStore.read_l3_concat()` 返回 recent、
profile、scope、preferences 四份 L3；它不会查询 L1/L2，也不会根据用户当前问题搜索
历史 Session。`ContextBuilder` 同样只压缩当前 Session 的摘要和近期消息。

产品已经支持用户显式选择旧会话：请求携带 `history_references` 后，`turn_runtime`
会通过 Session Store 读取该会话并将 transcript 作为 Source 注入。但这是“用户先选中
哪段历史”，不是 Agent 在听到“我上次提过的那件事”后自主定位历史。Partner 模块已有
`partner_search`，能够跨 Partner 的全部会话做关键词搜索并返回标题、角色、时间和片段，
但它被限制在 Partner 存储中，普通产品 Chat 不能直接调用。

如果目标设计中的 L2 确实是“每个 Session 的可检索摘要”，则不需要增加 L4，也不必
一开始就在 L1 原文上建立全文索引。更合适的是让 L2 承担轻量索引，让 L1 保留原始证据，
形成**情景记忆（episodic recall）访问路径**：

```text
稳定偏好、画像、知识状态
  -> read_memory / L3

“上次、之前、我说过的……”等具体历史指代
  -> recall_conversation
  -> 按用户、时间、主题、实体等条件查询 L2 摘要
  -> 根据 L2 的来源引用定位 L1 Session / 消息
  -> 读取命中消息前后的相邻对话作为证据
  -> 把小段原始证据回填 Agent
```

首版可以设计成一个工具：

```text
recall_conversation(
  query: string,
  time_hint: string | null = null,
  limit: int = 5,
  context_messages: int = 2
)
```

目标 L2 记录至少需要 `user_id`、`session_id`、摘要、主题/实体、发生时间，以及
`source_message_ids` 或起止消息 id。只有 `session_id` 时可以定位会话，但无法准确回到
“那一句”及其邻域；消息级来源引用是从摘要回溯原文的关键。`current_user_id` 与
`current_session_id` 必须由 Runtime 私下注入，并限制候选数和回填字符数，避免跨用户
读取和整段历史重新进入 Prompt。

在用户历史规模不大、L2 已有主题/实体/时间等结构化字段时，首版不需要 FTS5/BM25：
先用 SQL 条件筛选出少量候选，再按字段匹配度、新鲜度打分，或让模型只对前 20～30 条
L2 摘要重排即可。需要注意，“存进数据库”只解决持久化，不会自动解决相关性排序；
如果只有一列自然语言摘要并使用 `%LIKE%`，同义改写仍可能漏召回，数据量增大后也会产生
全表扫描。此时再把 FTS5/BM25 或 Embedding 作为候选召回增强，而不是首版硬依赖。

BM25 是一种基于关键词的相关性排序算法。它主要同时考虑：查询词在当前文档中出现的
次数、该词在全部文档中的稀有程度，以及文档长度；同一个词重复出现时收益会逐渐饱和，
长文档也会受到长度归一化，避免单纯因为字数多而排名靠前。可以口语化理解为：
“查询词在这条摘要里比较突出，并且在其他摘要里不常见，这条摘要就更值得排在前面。”
它不理解真正的语义，因此“考研”和“研究生入学考试”未必能够互相命中。FTS5 是
SQLite 提供的全文索引能力，BM25 是 FTS5 可用于结果排序的评分方式，两者不是同一个概念。

当前实现要走这条路线，需要先把 L2 从单个 Markdown 事实文档扩展为可查询的 Repository/
表，并在 L2 生成时保存 Session 和消息级来源引用；Tool 依赖 Repository 接口，而不直接
依赖 SQLite。命中后再通过现有 Session Store 回取 L1 原文。读取相邻消息时还需尊重
`parent_message_id` 分支，避免把 regenerate 产生的兄弟分支混入同一段上下文。

关键证据：

- `deeptutor/tools/builtin/__init__.py:633-660`
- `deeptutor/services/memory/store.py:72-84`
- `deeptutor/services/memory/snapshot/adapters.py:395-458`
- `deeptutor/services/memory/consolidator/modes/update.py`
- `deeptutor/services/memory/paths.py`
- `deeptutor/services/session/context_builder.py:104-178,341-446`
- `deeptutor/services/session/turn_runtime.py:1243-1248,1473-1534`
- `deeptutor/services/session/protocol.py:14-83`
- `deeptutor/services/session/sqlite_store.py:123-157,1159-1416`
- `deeptutor/tools/partner_memory.py:225-310`

#### 三层记忆分别在什么时候使用

三层不是每轮对话都同时发送给模型，而是分别服务于不同阶段：

| 层级 | 主要使用时机 | 当前作用 |
| --- | --- | --- |
| L1 | 业务数据采集、Snapshot 刷新、Trace 追加，以及 L2 更新或审计时 | 提供未经语义压缩的原始证据和可追溯来源，通常不直接注入 Chat Prompt |
| L2 | 从 L1 更新场景记忆、执行 L2 审计/去重/合并，以及生成 L3 时 | 提供某个 surface 的结构化事实，当前主要作为 L3 的输入和 Memory Workbench 的审计对象 |
| L3 | 回合开始前显式选择记忆，或 Agent 在对话中调用 `read_memory` 时 | 提供跨场景的近期状态、画像、知识范围和偏好，是当前 Chat Agent 主要直接消费的长期记忆 |

#### 从触发到消费的实际生命周期

当前没有将 L1→L2→L3 串成自动流水线，也没有 Memory 定时归并任务。每个动作
都有独立触发点：

| 动作 | 当前触发方式 | 运行时做什么 | 持久化结果 | 后续会不会自动继续 |
| --- | --- | --- | --- | --- |
| 构造 L1 Snapshot 视图 | 打开 Memory/L1、返回页面焦点、L2 Update、L2 Audit，或直接调 API | Adapter 读业务存储并构造 `list[Entity]` | 默认不保存 Entity 正文 | 不会 |
| 提交 L1 Snapshot 差异 | L1 页点 Refresh，或 POST refresh API | 用 fingerprint 比较上次 state | `state.json` + `changes.jsonl` | 不会触发 L2 |
| 追加 L1 Trace | 特定业务事件，如 KB 查询、明确偏好写入 | 标准化为 `TraceEvent` 并追加 | `trace/<surface>/<date>.jsonl` | 不会自动触发 L2 |
| 生成/增量更新 L2 | L2 Workbench 选中 surface 后点 Update，或调 Update API | 现场读 Entity，仅抽取未见 id，LLM 生成带证据 ref 的事实 | `L2/<surface>.md` + `.meta.json` | 可按设置自动 dedup/merge，不会生成 L3 |
| 生成/增量更新 L3 | L3 Workbench 选中 `recent/profile/scope` 后点 Update，或调 Update API | 读所有 L2，仅综合未见 L2 entry | `L3/<slot>.md` + `.meta.json` | 可按设置自动 dedup/merge |
| 写 L3 偏好 | 对话中用户明确表达偏好，Agent 调 `write_memory` | 直接增改 `preferences` 并生成 Trace 证据 | `L3/preferences.md` + L1 Trace | 立即可被后续对话读取 |
| 消费 L3 | 对话编辑器显式选择 Memory，或 Agent 调 `read_memory` | `read_l3_concat()` 拼接四份 L3 | 不产生新记忆 | 注入当前 Prompt 或返回 Tool 结果 |

L2/L3 的 Markdown 不是等全部 chunk 处理完才一次写入；每个 chunk 只要有合法新事实，
`write_doc_checkpoint()` 就会先序列化 Markdown，通过临时文件 + `os.replace()` 原子替换，
并注册本次 run 的 Undo checkpoint。所有 chunk 结束后，再写 `.meta.json` 记录已看过的
上游 ID。

当前还有一个需要明确的增量边界：Snapshot 的 fingerprint 可以把同 id 的内容变化
显示为 `modified`，但 L2 Update 的增量集合只比较 `<surface>:<entity_id>` 是否已在
`seen_entity_refs`，不比较 fingerprint。因此，已处理的 Chat session 后续增加消息时，
L1 Refresh 会显示 modified，但普通 L2 Update 不会因此重新抽取该 session。L2 Audit
会重读当前 Entity 来核验已有 L2 条目；若要让 Update 全量重做，Workbench 的 Reset
会删除该 L2 Markdown 和 meta，下一次 Update 才会重新摄取全部 Entity。

例如一次新对话完成后，原始消息先进入业务存储，相关事件可追加到 L1；执行
`run_update("L2", "chat")` 时，L1 被读取并提取为 Chat 场景事实；再执行
`run_update("L3", "profile")` 或其他 slot 更新时，L2 被跨场景综合。下一次
对话若需要个性化信息，`turn_runtime` 读取 L3 并注入 `UnifiedContext`，或者由
Agent 调用 `read_memory` 读取。也就是说，L1/L2 主要支撑“记忆生成、审计和追溯”，
L3 主要支撑“对话时使用”。

#### 与 LangChain / LangGraph 的边界：编排框架不等于记忆模型

**状态：已验证当前代码边界；选型结论属于设计判断**

截至当前代码，`pyproject.toml`、`requirements/` 和 `deeptutor/` 没有把
LangChain 或 LangGraph 作为运行时依赖。DeepTutor 已有自己的运行时边界：
`deeptutor/runtime/orchestrator.py` 通过 Capability Registry 路由回合，
`deeptutor/core/context.py` 的 `UnifiedContext` 是 CLI、WebSocket 和 SDK 共用的
请求上下文，`deeptutor/core/agentic/loop.py` 负责 Agent Loop；记忆侧则由
`MemoryStore`、Snapshot、Trace 和 `consolidator` 分工完成。

面试中不应回答“LangChain/LangGraph 不好”，而应说明**问题层次不同**：

| 组件 | 擅长解决的问题 | 在本项目中的边界 |
| --- | --- | --- |
| LangChain | Prompt、模型、Tool、Retriever 等通用组件组合 | 不能直接定义 L1 证据、L2 场景事实、L3 用户模型及来源关系 |
| LangGraph | 有状态图、分支、暂停恢复、checkpoint 和持久化执行 | checkpoint 是工作流执行状态，不等于跨回合语义记忆；仍需独立的记忆数据模型和读取策略 |
| DeepTutor Memory | Snapshot/Trace 证据、L2/L3 增量归并、引用校验、原子写入和按用户隔离 | 这是领域数据与生命周期，不是某个 Agent 框架的默认能力 |

因此当前选择是让记忆的 source of truth 保持在 DeepTutor 自己的存储和协议中，
避免把框架 checkpoint、对话 history 和长期记忆混为一层，也避免为了一个简单的
归并链路引入额外依赖和第二套状态模型。代价是重试、幂等、可观测性等基础设施需要
自己维护；这些约束已经体现在 `consolidator/modes/update.py` 的增量集合、
`consolidator/meta.py` 的 `seen_*` 元数据以及 `MemoryStore` 的原子写入路径中。

这不是永久排斥框架：若未来某个能力需要复杂分支、人工确认或长时间暂停恢复，可以
用 LangGraph 编排该能力的节点，并把 L1/L2/L3 当作自定义 `MemoryStore` 节点访问；
框架只负责 workflow，不能取代记忆的 schema、provenance、冲突策略和评测。若引入，
应先以适配器隔离，并用延迟、失败恢复、token 成本、记忆准确率和可追溯性做对比评测。

#### LangChain / LangGraph 的记忆实现模型

**状态：已根据 LangChain 官方 Python 文档核对（2026-08-23）；以下不是 DeepTutor 当前实现**

当前生态需要区分两代概念：旧版 LangChain 有 `ConversationBufferMemory`、
`ConversationSummaryMemory` 等 `BaseMemory` 类；它们通常在一次链调用前加载历史，
在调用后通过 `save_context` 写回消息或摘要。现在的 LangChain agent 主要建立在
LangGraph runtime 上，短期记忆推荐使用 checkpointer，而不是把旧版 Memory 类当成
长期用户画像。

**LangChain 的基础消息历史。** `BaseChatMessageHistory` 抽象负责保存消息，后端可以
是进程内列表，也可以接 Redis、SQL 等实现；`RunnableWithMessageHistory` 用调用配置中的
`session_id` 找到对应 history，把历史放入 `MessagesPlaceholder`，执行 Runnable 后再把
本轮输入和输出追加回 history。这条链路解决的是“同一会话继续对话”，不自动做事实抽取、
跨会话用户画像、来源引用或冲突消解。旧版 `Conversation*Memory` 的 buffer/window/
summary/vector 差别，本质也是“如何加载和压缩消息”，而不是完整的领域记忆模型。

**LangGraph 的短期记忆。** 图有一个可持久化的 State，通常包含 `messages` 等字段；
编译图时传入 checkpointer，调用时传 `configurable.thread_id`。每个 graph superstep
会生成 checkpoint，保存该 thread 的状态、元数据、版本和必要的 writes。下一次使用同一
`thread_id` 时，图从最近 checkpoint 恢复；换 thread 就是另一段会话。内存版
`InMemorySaver` 适合演示，生产环境可换 SQLite/Postgres 等 checkpointer。它同时支撑
中断恢复、故障重试、历史回放和 time travel，但保存的是**工作流状态**。

短期记忆不会自动无限增长。`messages` 若接近模型窗口，需要由应用或 middleware
显式 trim、删除旧消息，或先调用模型生成 summary 再把旧消息压缩；checkpointer 只负责
可靠保存状态，不替应用决定摘要内容。

**LangGraph 的长期记忆。** 跨 thread 的数据应放在独立的 Store 中，而不是塞进某个
thread checkpoint。应用使用 `(user_id, "memories")` 一类 namespace 和 key/value
保存 JSON 记忆，例如 `store.put(namespace, key, value)`；需要个性化时用
`store.get` 精确读取，或 `store.search` 做查询感知召回。Store 可以配置 embedding
建立语义索引，也可以只做精确 key 查询。何时写入、写什么、如何更新旧事实、是否失效，
通常由节点、middleware 或模型调用的 memory tool 决定，框架不会凭空完成 L1/L2/L3
式的证据归并。

可以把两者记成下面的边界：

```text
checkpointer + thread_id  -> 当前线程的 workflow state / 短期对话记忆
Store + user namespace    -> 跨线程长期数据 / 可选语义召回
应用逻辑或 memory tool    -> 抽取、去重、冲突、过期和写入策略
```

因此，LangGraph 的 `MemorySaver` 不是 DeepTutor L3 的替代品；它更接近“这次图运行到
哪一步、当前消息状态是什么”。若用 LangGraph 承载 DeepTutor，应让 graph 节点调用
`MemoryStore` 读写 L1/L2/L3，同时独立使用 checkpointer 保存 workflow 恢复状态。

官方参考：LangChain [Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)、
LangGraph [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) 和
[Memory](https://docs.langchain.com/oss/python/langgraph/add-memory)。

#### Mem0 OSS 对照：条目化存储与查询感知召回

为评估 Markdown 全量读取的替代方案，已对照 Mem0 官方仓库
`4fa483907704735ba0bec030e3c946ee1614b50e`（2026-08-20）的当前 OSS 实现。
下述结论是对该版本源码的阅读结果，不是 DeepTutor 已有功能。

Mem0 不使用 DeepTutor 这种 L1/L2/L3 Markdown 文档。它把长期记忆拆成
独立条目：默认主存储是 Qdrant，每条保存 UUID、embedding 和 payload；
payload 包含记忆文本 `data`、BM25 预处理文本 `text_lemmatized`、内容 hash、
`user_id` / `agent_id` / `run_id`、归属、时间和业务 metadata。SQLite
`history.db` 只负责记录变更历史，并为每个 session scope 保留最近 10 条
消息供后续抽取解析，它不是主记忆检索库。

`Memory.add(infer=True)` 当前的主链路是：

```text
新消息 + 该 scope 最近 10 条消息
        │
        ├─用新消息做向量查询，取 10 条相关旧记忆
        │
        └─单次 LLM 抽取自包含的新记忆条目
                 ↓
      批量 embedding → MD5 精确去重 → 向量库批量 ADD
                 ↓
      SQLite 写 ADD 审计记录 + 实体索引 + 最近消息
```

这条 v3 主链路已从旧版 `ADD/UPDATE/DELETE/NONE` 决策改为 ADD-only。
旧版 prompt 和 `_update_memory()` / `_delete_memory()` 公共操作仍保留在代码中，
但不应据此把当前自动抽取说成“LLM 会修改或删除旧记忆”。
`infer=False` 则跳过 LLM，把非 system 消息原文直接作为记忆条目。

`Memory.search()` 是 query-aware 召回，而不是把全部记忆拼入 Prompt：

1. 先用 `user_id` / `agent_id` / `run_id` 及 metadata 限定租户和业务范围。
2. 对 query 做 embedding、BM25 词形化和实体抽取。
3. 向量检索过取 `max(4 * top_k, 60)` 条，并在支持的向量库上单独做
   keyword/BM25 检索。独立实体 collection 把查询实体映射回关联的 memory id。
4. `threshold` 先对 semantic score 做硬门限，默认为 `0.1`；过期条目
   默认被过滤。通过门限后再计算
   `(semantic + normalized_bm25 + entity_boost) / max_possible`，实体加分上限为 `0.5`。
5. 按组合分数取 `top_k`；配置 reranker 且调用时传 `rerank=True`，才会再重排。
   `explain=True` 可返回各信号分数，便于调参。

当前 OSS 实现有三个不能忽略的边界。第一，最终候选集只由
semantic search 结果构成，BM25 和实体信号只能给已进入候选集的条目
加分，不能独立召回一条向量漏检的记忆。第二，`latest_only`、
`reference_date` 和 decay 等能力出现在 Platform 客户端或提示中；OSS
`Memory.search()` 没有 `latest_only`，并且会明确拒绝 `reference_date`。
第三，虽然 v3 prompt 要求 LLM 输出 `linked_memory_ids`，但该版本
`_add_to_vector_store()` 没有把这个字段映射并写入主 memory payload，
`uuid_mapping` 也未被后续使用。因此当前源码中可验证的
`linked_memory_ids` 主要是“实体索引→记忆条目”关联，不能把
Platform changelog 所述的完整版本链直接当成当前 OSS 已落地事实。

以用户偏好变化为例，实际语义是：

```text
用户：我喜欢川菜
→ LLM 可能抽取：“用户喜欢川菜”
→ 向量库新增一条 memory，并写 embedding、hash、user_id 和时间

用户：最近胃不舒服，暂时不能吃辣
→ 写入前召回“用户喜欢川菜”作为去重和关联上下文
→ LLM 可能新增：“用户因近期胃部不适，暂时不能吃辣”
→ ADD-only 意味着前后两条会共存，旧偏好不会被自动删除

用户：帮我推荐晚餐
→ 向量相似度可能把两条都召回，BM25/实体信号只负责加分
→ OSS search 本身不判定“暂时不能吃辣”应覆盖当前菜品选择
```

具体抽取文本和排名是模型与 embedding 相关的，上例是依照已验证
代码链路给出的结果示意，不是确定性输出。它说明了一个工程边界：
“相关召回”不等于“冲突解析”。如果推荐必须遵循当前健康约束，
业务层还需要有效期、事实状态、版本关系或召回后冲突判定。

对 DeepTutor 的可取之处不是去掉 L1/L2/L3，而是把它们保留为
内部语义分层，将运行时存储和召回改为条目化：L1 保留可追溯证据，
L2 保存带 source ref、scope、状态和 embedding 的场景事实，L3 保存
有多条 L2 证据支撑的跨场景结论。召回时可按用户和场景过滤，
取向量与 BM25 候选的并集，加上实体、时效、重要度和证据质量分数，
再在 token budget 内组装少量相关记忆。冲突事实宜采用“新增版本、
标记旧版失效并记录 `supersedes_id`”，而不是直接覆盖；这样同时保留
可追溯性与当前有效状态。这些是可选演进方向，尚未在当前代码中实现。

一句话区分两者：**DeepTutor 当前是分层文档式归并 + L3 整体读取；
Mem0 OSS 当前是 LLM 条目抽取 + 向量主存储 + 查询感知混合检索。**

为验证这条演进路径，`learning/demos/memory_hybrid_demo.py` 提供了一个
不接入生产 Memory 的可运行原型。它用 SQLite 的 `evidence` 表示 L1，
用条目化 `memories` 表表示 L2/L3；两条川菜偏好 L2 事实可归并出
带上游 memory id 的 L3 profile。暂时不能吃辣与恢复吃辣使用
`status=active|superseded` 和 `supersedes_id` 保留版本历史，召回只读取
active 条目。原型使用语义相似度、简化 BM25、concept 重合、importance
和 constraint 业务优先级的组合分数，再在近似 token budget 内组装上下文。
其中 `RuleBasedDemoExtractor` 和 `LocalHashEmbedder` 只是为了无模型、无外部服务
也能重现数据流；正式实现时应替换为结构化 LLM 抽取和真实 embedding，
并将全量 SQLite 扫描替换为可扩展索引。这一原型已有行为测试，
但尚未被 `MemoryStore`、Chat Tool 或 `turn_runtime` 调用。

#### 目标架构的面试表达与纠错顺序

目标方案按两次设计迭代说明，但这不是当前代码已验证的两次完整生产发布历史：

1. V1 使用关系数据库保存对话记录，并维护一份滚动用户总结。它实现简单，但总结缺少
   原始来源，一次偶然现象容易被写成长期结论。测试中还明确了 Conversation History 与
   长期 Memory 的边界：用户问“刚刚这个是什么意思”属于当前会话指代消解，应固定携带
   最近 History，不能让长期记忆代替短期上下文。
2. V2 在关系数据库中形成 L1 原始事件与语义标签、L2 追加式场景记忆和 L3 当前综合
   用户模型。每个完整回合先同步保存 L1 原始事件，再由 Flash 模型异步生成 summary、
   tags、importance 等结构化标注。L2 默认在当前 Session 累计 10 个未处理回合后由轻量模型批量提炼，
   会话结束或连续 30 分钟没有新回合时处理不足 10 轮的尾批；每条 L2 通过 `l2_l1_source` 保存来源 L1 IDs。
   L3 在会话结束或连续 30 分钟没有新回合后使用“当前 L3 + 新增 L2”增量更新，每天凌晨 3 点仅扫描仍有
   pending 数据的用户作为补偿。

这里的 L1-L2 多对多关系不表示复制原始事件：一条 L1 只保存一次，但如果同一轮内容同时包含
学习薄弱点和回答偏好，它可以分别被 Quiz L2 与 Chat L2 引用；反过来，一条 L2 也可以由多条
L1 共同支撑。因此来源应使用 `l2_l1_source(l2_id, l1_id)` 关联表保存。

目标方案的运行时上下文固定由三部分组成：按 `session_id` 读取最近 10 个完整回合的原始消息，
读取当前 Session 已生成的 L2，再按 `user_id` 读取当前 L3。前者写入 `UnifiedContext.conversation_history`，
后两者与记忆说明一起写入 `UnifiedContext.memory_context`，由 Chat Prompt 统一组装。这里的
`Token Budget` 是整个请求的上下文长度约束，而不是 L3 的单独召回开关；正常情况下三部分都注入，
只有接近模型窗口时才对 Session L2 或 L3 做压缩，并为当前回答保留输出空间。

L1 原始事件是审计证据，模型标签只是可重试的派生数据。标注失败不能影响回答返回和
原始事件落库；L2 模型返回的 L1 IDs 还必须由服务端校验存在性、用户归属和本批输入范围。
L2、来源关联和 L1 已处理标记应在同一事务中提交，并用 user id 与排序后的本批 L1 IDs 哈希形成
幂等键。L3 更新则先确定本批最大 L2 ID，模型返回后在同一事务中写入新 L3 并推进游标；
事务失败时游标不前进，可由补偿任务安全重试。

截至 2026-08-22，阿里云百炼官方模型目录提供托管的 `qwen3.7-flash`，不需要自行部署；
文本模型规格页将其列为支持结构化输出的低成本模型，结构化输出文档也明确支持
`response_format={"type":"json_schema", ...}` 和 `strict=true`。因此 L1 标注与 L2 提炼
可以先使用云端 Flash 模型的非思考模式、JSON Schema 和少量示例，无需微调。模型 ID
应通过运行时配置管理，并用人工标注的小型评测集验证 JSON 合法率、事实准确率、来源归属
和漏标率；只有错误模式稳定、已有足够训练样本且 API 成本或精度不达标时，才考虑微调。

官方依据：

- `https://help.aliyun.com/zh/model-studio/models`
- `https://help.aliyun.com/zh/model-studio/text-generation-model/`
- `https://help.aliyun.com/zh/model-studio/qwen-structured-output`

当前目标方案只使用关系数据库。它需要的是按 user id 读取 L3、按游标读取新增 L2、
按关联表追溯 L1，以及事务和唯一约束，这些都是关系数据库擅长的精确操作。只有未来
单用户 L2 大量增长，且场景、标签和时间过滤的召回评测无法覆盖同义表达时，才考虑增加
`pgvector` 或独立向量索引。向量检索只是可选的查询优化，不是第三次版本迭代，也不能替代
L1 到 L3 的提炼和来源关系。

审计按抽象程度从小到大执行：先确认 L1 原始事件真实且归属正确，再检查 L2 是否被引用
证据支持，最后检查 L3 是否过度归纳。纠错则从受影响 L1 出发，通过 `l2_l1_source` 失效
或重算相关 L2，再刷新 L3。当前不设计复杂版本链，先保证来源关联、幂等执行和可重跑。

以上是目标架构，不是当前正式链路：当前实现仍是 Snapshot/Trace + L2/L3 Markdown，
归并主要由 Workbench/API 触发，Chat 主要整体读取 L3；关系库表、Flash 自动标注、十轮
触发、处理游标和补偿任务尚未完整接入。对应的 3、5 分钟口述稿和面试追问见
`learning/interview-scripts/DeepTutor三层记忆多时长介绍.md`。

关键证据：

- `deeptutor/services/memory/__init__.py`
- `deeptutor/services/memory/paths.py:1-103`
- `deeptutor/services/memory/snapshot/__init__.py`
- `deeptutor/services/memory/snapshot/adapters.py`
- `deeptutor/services/memory/snapshot/entity.py`
- `deeptutor/services/memory/trace.py`
- `deeptutor/services/memory/consolidator/meta.py`
- `deeptutor/services/memory/consolidator/modes/update.py`
- `deeptutor/services/memory/consolidator/modes/audit.py`
- `deeptutor/services/memory/consolidator/modes/_runtime.py:216-278`
- `deeptutor/services/memory/consolidator/modes/dedup.py`
- `deeptutor/services/memory/store.py:47-216`
- `deeptutor/api/routers/memory.py:140-345,680-785`
- `deeptutor/services/session/turn_runtime.py:1364,1616-1625`
- `deeptutor/agents/chat/prompt_blocks.py:71-72`
- `deeptutor/tools/builtin/__init__.py:633-750`
- `web/components/memory/MemorySection.tsx:653-890`
- `web/components/memory/MemoryRunPanel.tsx:52-170`
- Mem0 `4fa483907704735ba0bec030e3c946ee1614b50e`：
  `mem0/memory/main.py:487-580,760-1196,1255-1522,1628-1813`
- Mem0 `mem0/utils/scoring.py:16-139`、`mem0/memory/storage.py:102-324`、
  `mem0/configs/prompts.py:468-944,1016-1061`、`mem0/client/types.py:41-85`、
  `docs/changelog/sdk.mdx:322-343`
- `learning/demos/memory_hybrid_demo.py`
- `tests/learning/test_memory_hybrid_demo.py`

### 5.7 BookEngine 的页面规划器：`SectionArchitect`

**状态：已验证当前调用链；实现偏差单独标为待修正项**

项目里没有一个供所有 Capability 共用的全局 `Planner`。当前最直接以 planner 命名的
实现位于 `deeptutor/book/agents/page_planner.py`，它属于独立的 BookEngine，职责不是
直接写出完整页面，而是把一个 `Chapter` 翻译成有顺序的 `Block` 骨架：决定 block 的
`type`、生成参数 `params`，以及用于块间衔接的 `metadata["transition_in"]`。真正的正文、
图、题目和代码随后才由 `BookCompiler` 按 block 类型查找对应 `BlockGenerator` 生成。

当前真实调用链是：

```text
BookEngine.compile_page()
  -> BookCompiler.compile_page()
  -> _plan_if_needed()                 # 仅 page.blocks 为空时进入
  -> SectionArchitect.plan_blocks_async()
       -> LLM 规划成功：校验并构造 Block 骨架
       -> 调用/解析/结果校验失败：退回静态模板
  -> page.blocks 持久化
  -> BookCompiler 逐块调用 BlockGenerator
```

`BookEngine` 默认创建 `CompilerOptions(phase=2)`；`BookCompiler` 再按
`architect_llm_enabled` 构造 `SectionArchitect`，该开关默认是 `True`。规划前页面状态会
写成 `PLANNING`，并发出 `page_planning`；规划完成后保存 blocks 并发出
`page_planned`。因为 `_plan_if_needed()` 发现 `page.blocks` 已存在就直接返回，所以普通
恢复和单页 `force` 重生成会复用原 block 结构；只有删除/重建页面等路径才会重新规划。

LLM 规划只调用一次模型。提示词来自
`deeptutor/book/prompts/{en,zh}/page_planner.yaml`，输入包括章节标题、摘要、
`ContentType`、学习目标，以及 `ExplorationReport.summary`；当前并没有把完整
`ExplorationReport.chunks` 直接塞给规划器。模型应返回 `{"blocks": [...]}`。服务端随后：

- 最多读取前 12 项，只接受 `_ALLOWED_LLM_TYPES` 中的类型；
- 丢弃非法类型，把非字典 `params` 归一为空字典；
- 把 `focus` 和 `transition_in` 截断到 240 字符；
- 若最终一个 block 都没有，则整体退回静态模板；
- 若结果中没有 `section`，在 `phase >= 1` 时自动在最前面补一个核心 `section`，防止
  页面失去承担长文讲解的主体块。

静态兜底由 `_TEMPLATES_V2` 提供，按 `ContentType.THEORY / DERIVATION / HISTORY /
PRACTICE / CONCEPT` 选择确定性的 block 序列，并把章节标题、摘要、学习目标和来源锚点
合并进每个 block 的 `params`。因此模型服务不可用或 JSON 不合法时，页面仍能获得一个
可执行的内容结构，而不是整页直接失败。

`PagePlanner` 这个名称目前只是向后兼容类：它继承 `SectionArchitect`，但构造时强制
`llm_enabled=False`，所以只走静态模板。当前 `BookCompiler` 已直接导入并使用
`SectionArchitect`。学习源码时可以把它记成：**旧名叫 PagePlanner，当前活跃实现叫
SectionArchitect；它规划页面结构，不生成 block 内容。**

#### 已验证的待修正项

1. `CompilerOptions.phase`、`SectionArchitect` 注释声称 phase 1 只输出有限 block 类型，
   但 `_static_plan()` 当前完全没有使用收到的 `phase`，`_PHASE1_TYPES` 和
   `_PHASE1_SUBSTITUTES` 也没有进入任何过滤路径；LLM 路径的允许类型同样不按 phase
   缩减。因而现状是 phase 1 与 phase 2 都可能产生 figure、code、animation 等块。
2. Prompt 要求“5-10 个 block、追求多样性”，这是软约束。Python 侧只截取前 12 项，
   没有强制最少 5 项、最多 10 项或禁止重复类型。
3. `tests/book/` 当前没有针对 `SectionArchitect/PagePlanner` 的直接单元测试；上述 fallback、
   JSON 清洗、section 保底以及 phase 语义缺少专门的回归保护。

不要把这里的页面规划器和 `deep_solve` 混为一谈。当前 `deep_solve` 已没有独立
`PlannerAgent`：`DeepSolveCapability` 复用 chat agent loop，由模型调用 `solve_plan`、
`solve_finish_step`、`solve_replan` 三个工具维护单回合的 `SolveSession`。`deep_question` 和
`deep_research` 也各自在自己的 pipeline 中包含 planning 阶段，它们都不调用
BookEngine 的 `SectionArchitect`。

关键证据：

- `deeptutor/book/agents/page_planner.py:40-364`
- `deeptutor/book/prompts/zh/page_planner.yaml`
- `deeptutor/book/compiler.py:54-84,95-165,305-343`
- `deeptutor/book/engine.py:101-114,699-756,769-856`
- `deeptutor/book/models.py:83-91,323-376`
- `deeptutor/book/streaming.py:22-31`
- `deeptutor/capabilities/solve/capability.py:1-91`
- `deeptutor/capabilities/solve/session.py:1-97`
- `deeptutor/capabilities/solve/tools.py:1-287`

### 5.8 RAG 的可量化执行口径

**状态：已验证当前代码与默认配置；业务数据和效果指标仍待真实报表验证**

当前 RAG Factory 注册 **5 类后端**：LlamaIndex、PageIndex、GraphRAG、LightRAG 和
LightRAG Server。知识库创建时会绑定一个 provider，后续追加文档和检索继续使用同一条
pipeline。文档接入侧另有 **5 类解析引擎**；`FileTypeRouter` 的静态集合共覆盖
**116 种扩展名**，其中包括 4 种交给解析器的 PDF/Office 类型、104 种直接读取的
文本或代码类型，以及 8 种图片类型。这里的数量描述的是平台接入面，不等于 116 种格式
都具有相同的解析质量。

默认 LlamaIndex 配置采用 hybrid profile：chunk size 为 **512 Token**、overlap 为
**50 Token**，最终 `top_k=5`，Vector 和 BM25 的候选倍率均为 2。因此默认执行语义是
“Vector 取 Top 10、BM25 取 Top 10，再经 RRF 融合返回 Top 5”，不是先后串行调用两个
Retriever，也不能据此声称 Recall 提升了某个百分比。

三部分的职责不同：Dense Embedding 将 Query 和 Chunk 映射为向量，擅长召回用词不同但
语义相近的内容；BM25 根据关键词词频、稀有度和文档长度排序，擅长专有名词、公式、编号
等精确词；RRF（Reciprocal Rank Fusion）不直接比较两路不可比的原始分数，而是按
`sum(1 / (k + rank))` 累加名次分，某个 Chunk 在一路排名很高或在两路都进入前列时，
融合分会更高。这里的 `k` 是平滑常数，不是最终返回数量 `top_k`。

Recall@5 的严格口径是：对每条标注问题，检查返回前 5 个 Chunk 覆盖了多少人工标注的
相关 Chunk，再对全部问题求平均。如果每题只有一个 gold Chunk，它实际等价于 Top-5
命中率；600 题中 73% 和 86% 分别对应 438 题和 516 题命中，即多命中 78 题。若每题有
多个 gold Chunk，则必须按 `命中的相关 Chunk 数 / 该题全部相关 Chunk 数` 逐题计算，
不能把百分比直接换算成命中题数。73% 到 86% 是提升 13 个百分点，相对提升约 17.8%。

要把“600 条标注问题上 Recall@5 从 73% 提升到 86%”写成实测结论，必须固定同一份语料、
切块、问题集和 Top-5 口径，明确 73% 是 Dense-only 还是其他旧方案，并保留问题到 gold
Chunk 的标注、两组逐题检索结果和评测脚本。当前仓库尚无这些评测产物，所以这组数字只能
视为待业务报表验证的简历口径，不能由 hybrid 配置本身推导出来。

Faithfulness 属于生成阶段指标，不是“回答引用了多少召回文本”，也不是 Recall 或答案正确率。
它先把回答拆成可验证的原子陈述，再判断每条陈述能否由本次实际提供给模型的
`retrieved_contexts` 推出，单条样本可概括为
`被上下文支持的陈述数 / 回答中的全部陈述数`；允许改写，不要求逐字引用。它检验的是
“回答有没有超出证据”，无法证明模型内部是否真的使用了某段文本，也不直接检验引用标注是否
指向正确来源。后两项需要另做 citation 或人工评测。

要把 `Faithfulness 0.82 -> 0.90` 归因于元数据过滤和 Top-5 收敛，必须固定测试集、语料、
生成模型、Prompt、生成参数、评审模型及其版本，保存每题的 Query、实际检索上下文、回答、
原子陈述和逐条判定，再对每题分数求平均。若过滤和 Top K 同时变化，只能归因于组合方案；
要区分贡献，应分别评测“无过滤 + 原 Top K”“过滤 + 原 Top K”和“过滤 + Top 5”。当前
`learning/notes/鼎校伴学-STAR简历改写.md:80-93` 明确把这组数标为模拟口径，仓库也没有
对应 RAGAS 报告，因此不能当作当前源码已经验证的效果。官方定义参考 Ragas
[Faithfulness](https://github.com/vibrantlabsai/ragas/blob/main/docs/concepts/metrics/available_metrics/faithfulness.md)。

600 条问题的抽样依据不应是“旧系统已经回答正确”，否则会产生幸存者偏差。合理做法是
先定义一个固定时间窗口内所有触发 RAG 的脱敏有效 Query 作为候选池，去除寒暄、重复、
缺少必要上下文和知识库中不存在证据的问题；再按照业务场景/学科、资料类型、问题意图以及
检索难度分层随机抽样，并尽量保持主评测集与真实流量分布一致。检索难度至少应覆盖精确术语、
语义改写、长问题和跨 Chunk 问题。入选条件是“知识库中存在可人工确认的 Gold Chunk”，
而不是 Dense 基线已经命中；原系统未命中但确有证据的问题同样必须保留。

评测集确定后不能再用它反复选择切块、TopK 或融合参数；调参应使用独立开发集，600 条作为
冻结测试集，或者在报告中明确它只是验证集。600 不是算法要求，只是覆盖度、统计波动与人工
标注成本之间的工程取舍。在命中率约 80%、样本近似独立随机的理想假设下，600 条对应的
95% 置信区间半宽粗略约为 3.2 个百分点；实际分层、重复用户和问题相关性会改变该估计。

检索结果不自动进入长期记忆，并不妨碍离线评测。评测 Harness 应直接调用固定版本的
Retriever/Pipeline，为每条 Query 单独保存 `gold_chunk_ids`、Dense Top 5、Hybrid Top 5、
每个候选的 `chunk_id/score` 和是否命中，形成独立 JSONL、数据库表或评测报告，而不是从
聊天 Session 历史中反推。当前 LlamaIndex `_nodes_to_result()` 已返回 `chunk_id`、score、
来源文件和页码，可以用于比对。由于重新切块或重建索引可能改变 `chunk_id`，必须冻结语料、
切块配置和索引版本，或额外保存 `source + page + content_hash` 作为稳定 Gold 定位。

面试中可以把这组数字解释为三层价值：5 类 provider 表示检索后端可替换，5 类解析引擎
和 116 种扩展名表示异构资料接入范围，`10 + 10 -> Top 5` 表示默认候选扩召与证据收敛。
仓库当前没有可复现的 Recall@5、MRR、nDCG、RAGAS、检索 P95 或教材总量报表；
`891 本教材`属于简历业务自述，不能当作源码已验证事实。

关键证据：

- `deeptutor/services/rag/factory.py:27-42`
- `deeptutor/services/config/runtime_settings.py:200-207`
- `deeptutor/services/rag/pipelines/llamaindex/retrievers.py:132-146`
- `deeptutor/services/parsing/engines/factory.py:22-65`
- `deeptutor/services/rag/file_routing.py:34-177`

### 5.9 Mastery Path 的量化学习规则

**状态：已验证当前策略代码；这些数字是产品规则，不是线上转化效果**

Mastery Path 按 memory、concept、procedure、design **4 类知识点**选择掌握策略。
memory 和 procedure 使用 **90%** 的量化门槛；concept 和 design 不使用字符串准确率，
而由 Tutor 通过 `mastery_assess` 记录定性通过。掌握分只看最近 **5 次练习**并让较新的
结果权重更高；只有 1 次或 2 次证据时，得分上限分别是 50% 和 80%，避免一次幸运答对
直接解锁知识点。

间隔复习按知识类型使用不同序列：memory 最多推进到 **60 天**，其余类型采用更短序列；
`get_due_tasks()` 单次默认最多返回 **5 个**到期任务。这些规则体现的是“有证据才推进、
按类型安排复习”的业务机制，不能在没有用户实验数据时写成完成率或留存率提升。

关键证据：

- `deeptutor/learning/policy.py:34-63`
- `deeptutor/learning/mastery.py:17-37`
- `deeptutor/learning/scheduler.py:13-17,72-76`

## 6. 一次对话的主调用链

**状态：已验证到默认 chat Agent Loop**

先回答“谁调用 `ChatOrchestrator`”：标准 CLI、WebSocket 和 Python SDK
入口不会直接把原始请求交给它，而是先汇合到 `TurnRuntimeManager`。WebSocket
收到 `message` / `start_turn` 后调用 `runtime.start_turn(msg)`；CLI 和 Python SDK
通过 `DeepTutorApp.start_turn()` 调用同一个 Runtime。`start_turn()` 建立回合并启动
`_run_turn()` 后台任务，后者装配历史、Memory、Skill、附件等数据，构造
`UnifiedContext`，然后执行：

```text
orch = ChatOrchestrator()
async for event in orch.handle(context):
    ...
```

因此 `ChatOrchestrator` 位于“入口和会话运行时已经准备好本回合数据”之后、
“选择并运行具体 Capability”之前。证据：
`deeptutor/api/routers/unified_ws.py:113-133`、
`deeptutor/app/facade.py:114-125`、
`deeptutor/services/session/turn_runtime.py:668-836,1155,1613-1663`。

名字容易误导：`ChatOrchestrator` 并不只运行 `ChatCapability`。它读取
`context.active_capability`，默认值才是 `chat`；例如传入 `deep_solve` 时，同一个
Orchestrator 会从 `CapabilityRegistry` 取出 `DeepSolveCapability`。因此它在架构上的
真实角色更接近“统一 Capability/Turn Orchestrator”。`TurnRuntimeManager` 负责回合记录、
上下文装配和订阅生命周期，随后固定交给这个统一路由器；各能力的差异由 Capability
多态实现，而不是为每种能力再建立一个 Orchestrator。内置映射见
`deeptutor/runtime/bootstrap/builtin_capabilities.py`。

`ChatOrchestrator.handle()` 当前已确认的流程：

1. 接收 `UnifiedContext`。
2. 如果没有 `session_id`，生成 UUID。
3. 读取 `context.active_capability`；未指定时使用 `chat`。
4. 从 `CapabilityRegistry` 获取 Capability 实例。
5. 先产生一个 `SESSION` 事件。

   第 5 步的细节：`SESSION` 由编排器**直接 `yield`** 给调用方，**不走 bus**（它在这一刻还没有 bus）。`handle()` 是个 async 生成器，`yield` 就是它的输出，所以 SESSION 与后面 capability 的内容流走**两条出口路径**——SESSION 直接 yield、bus 事件经 `async for event in bus.subscribe(): yield event` 转发。调用方看一条事件流分不出路径，唯一区别是时机：SESSION 永远在 bus 建好、capability 开跑之前的开场第一个。它携带 `session_id + turn_id`，是编排器的「回合开始」元信息，使命调用方第一时间拿到本轮身份证号。不分走 bus 的原因有二：SESSION 是编排器元信息而非 capability 业务流，混进 bus 会让 bus 职责变糊；且它能在 bus 这个对象还没建好的瞬间就发，调用方不必等 bus 起来。

6. 为本回合创建 `StreamBus`。

   第 6 步的子动作：建好 bus 后，若有 `turn_id`，`register_bus(turn_id, bus)` 把这个回合的 bus 挂进一张进程级全局表（turn_id → bus）。它的作用是**让别处能按 turn_id 找回本次回合的 bus 对象**——尤其 ask_user 暂停恢复：用户按下 `submit_user_reply` 起的新请求手里只有 turn_id 字符串，没有旧 bus 引用，必须能从全局表定位到正在暂停的那个回合、把回答塞回同一个 bus，让暂停的 `_run_loop` 继续下一轮（见 6.9）。
回合结束的 `finally` 里再 `unregister_bus(turn_id)` 把它从全局表摘掉，防内存泄漏。铁序：register 必须在 `create_task` 跑 capability 之前，否则 capability 跑到一半时需要被别处找回的请求就晚了。证据 `orchestrator.py:79-82`、`stream_bus.py`（register_bus/unregister_bus）。

7. 在异步任务中执行 `capability.run(context, bus)`。
8. 通过 `bus.subscribe()` 持续向调用方返回流式事件。
9. 无论成功失败，最终产生 `DONE` 事件并关闭 Bus。
10. 执行结束后向全局 EventBus 发布 `CAPABILITY_COMPLETE`。

   第 10 步的关键：`EventBus` 是**另一条总线**，不要和 StreamBus 混。两条总线对照——StreamBus 是这次回合内的实时流，给 UI 看、回合结束就 close；EventBus 是项目级的长期公告板，进程生命周期挂着，给**不直接参与这次对话的监听者**（统计/记账、cron、memory 触发、生命周期钩子等）用。这些听众不需要实时事件流，只要「这个回合完成了」这一个里程碑信号——`_publish_completion` 就是往公告板上贴这张告示。它两个工程取舍值得记：**吞异常**（`publish` 失败只记 debug 日志、不影响回合结果），因为它是**公告不是命脉**——StreamBus 才是命脉（UI 全靠它），EventBus 发失败最坏是统计这次没收到；**放在 StreamBus 收尾之后**才发，保证公告时回合真的完整结束（不先公告再收尾，避免公告与实际状态不符）。证据 `orchestrator.py:96-114`。

第 8、9 步背后的并发结构：`capability.run(context, bus)` 跑在后台任务里（`asyncio.create_task(_run())`），它边跑边向 bus 喊事件；主协程同时 `async for event in stream: yield event` 把事件一条条吐给调用方。`_run()` 用 `try/finally` 包住 `capability.run`：`finally` 里**先 `bus.emit(DONE)` 再 `bus.close()`**——`emit(DONE)` 发出最后一条会被消费的事件，`close()` 给订阅迭代器打上「不会再有下一条」标记。消费者那侧的 `async for` 能一直收，是因为 producer 在源源不断塞事件；它之所以会停，**不是因为队列瞬时空了一下**（空了只会挂起等下一条），**而是因为 `bus.close()` 那个结束标记**——吐完残留事件后迭代器见到「已关」，自然抛 `StopAsyncIteration` 退出。所以「发 DONE」「让流收尾」是两件不同的事：前者是事件，后者是管道状态，两者同在 `finally` 里发、互相配合。


对应核心代码：

```text
deeptutor/runtime/orchestrator.py
```

异常策略也在这一层统一处理：Capability 抛出的异常会被记录，并转换成 StreamBus 错误事件，而不是直接让所有消费者各自处理一遍。

#### 当前源码与“鼎校伴学口述口径”的边界

**状态：已验证当前源码；TurnOrchestrator/ChatPipeline 是简历项目口径，不是当前类名**

当前 DeepTutor 源码使用 `ChatOrchestrator -> CapabilityRegistry -> ChatCapability ->
AgenticChatPipeline -> AgentLoop`：Orchestrator 支持多个 Capability，默认值才是 `chat`；
`ChatCapability.run()` 则把 Context 交给 `AgenticChatPipeline`。因此不能把当前源码说成
只有一条 Web Chat 链，也不能把源码类直接称为 `TurnOrchestrator` 和 `ChatPipeline`。

鼎校伴学简历口径已经收敛为另一条更薄的链路：

```text
Turn Runtime -> UnifiedContext -> TurnOrchestrator
             -> ChatPipeline -> AgentLoop
```

其中 `TurnOrchestrator` 只负责调度、Stream、异常边界和 `DONE`；`ChatPipeline` 只做
System Prompt、messages、工具 Schema、模型参数和预算等确定性准备；不再保留 Capability
路由，也不在 Agent Loop 前额外调用 LLM 做意图分类。真正的意图判断由 Agent Loop 第一轮
统一完成：无 Tool Call 就直接回答，需要已有业务入口就调用受控的 Action Tool，需要教材、
题库或 OCR 就调用对应工具。这样 Tool Selection 与 Agent 决策是同一次模型推理。

如果未来把这一口径移植到当前仓库，可把现有 Orchestrator 的多 Capability 路由职责裁掉，
将其收敛为 Turn 级协调器；把 `AgenticChatPipeline` 简化为 `ChatPipeline`；Action 则作为
受 Tool Schema 和服务端 Action Registry 约束的普通 Tool 接入 Agent Loop。以上是目标架构
建议，不是当前 DeepTutor 已实现的行为。

关键证据：

- `deeptutor/runtime/orchestrator.py:39-55`
- `deeptutor/agents/chat/capability.py:25-27`
- `deeptutor/agents/chat/agentic_pipeline.py:301-329`
- `deeptutor/agents/chat/agent_loop.py:162-249`
- `deeptutor/runtime/bootstrap/builtin_capabilities.py`

### 6.1 当前默认 Chat 实际使用哪一个 Agent Loop

**状态：已验证**

仓库里有两个容易混淆的循环实现：

1. `deeptutor/agents/chat/agent_loop.py`
   - 默认 `chat` 真正使用的循环。
   - 使用模型原生 function calling。
   - 判断“是否结束”的核心条件是本轮有没有 `tool_calls`。
2. `deeptutor/core/agentic/loop.py`
   - 可复用的标签协议循环。
   - 要求模型使用类似 ``THINK``、``TOOL``、``FINISH`` 的首行标签。
   - 当前实际调用方主要是 `deep_research` 和 `deep_question`。

虽然 `deeptutor/core/agentic/labels.py` 的模块注释仍提到 chat 使用标签协议，但当前运行链路中，chat 没有调用 `run_agentic_loop()`。定位这类冲突时，应以当前调用代码和测试为准。

默认 chat 的入口链是：

```text
ChatOrchestrator.handle()
  -> CapabilityRegistry.get("chat")
  -> ChatCapability.run()
  -> AgenticChatPipeline.run()
  -> AgentLoop.run()
  -> AgentLoop._run_loop()
```

关键证据：

- `deeptutor/runtime/bootstrap/builtin_capabilities.py`
- `deeptutor/agents/chat/capability.py:25`
- `deeptutor/agents/chat/agentic_pipeline.py:301`
- `deeptutor/agents/chat/agent_loop.py:162`

### 6.2 “单循环”是什么意思

**状态：已验证**

当前 chat 不是“先隐藏探索，再单独调用一次模型写回答”的双阶段流水线，而是一份不断增长的 `messages` 列表驱动一个循环：

```text
调用 LLM
  |
  +-- 没有 tool_calls
  |      -> 本轮文本就是最终答案
  |      -> 结束循环
  |
  +-- 有 tool_calls
         -> 本轮文本作为 narration
         -> 执行工具
         -> 把 assistant tool_calls 和 role=tool 结果追加到 messages
         -> 进入下一轮 LLM 调用
```

因此：

- 第一轮不调用工具时，只需一次 LLM 请求即可直接回答。
- 调用一次工具再回答时，通常是两次 LLM 请求。
- 工具轮和最终回答轮使用同一份对话上下文。
- 没有额外的固定 respond pass；“停止调用工具的那一轮”本身就是 respond。

`ChatCapability.manifest` 仍声明 `exploring`、`responding` 两个 stage，描述中也保留“exploring 后 responding”的说法；但当前 `AgentLoop` 的实际主循环统一运行在 `responding` stage，并通过 `call_role=narration|finish` 区分工具前导文本和最终回答。这里应把 manifest 理解为产品级阶段描述，而不是两次独立模型调用的保证。

### 6.3 初始化：每轮开始前准备什么

**状态：已验证**

`AgenticChatPipeline.run()` 在创建 AgentLoop 前完成以下工作：

1. 加载 MCP 等 deferred tools，并应用用户或 Partner 的工具白名单。
2. 检查当前用户是否允许使用 `exec` 和 `code_execution`。
3. 根据用户开关、上下文和权限组合本轮工具列表。
4. 判断当前 Provider/Model 是否支持原生 tool calling。
5. 从 `ToolRegistry` 生成 OpenAI function schemas。
6. 创建 Provider 客户端。
7. 把以上对象交给 `AgentLoop`。

核心代码：

- `deeptutor/agents/chat/agentic_pipeline.py:301-321`
- `deeptutor/agents/_shared/tool_composition.py:95-170`
- `deeptutor/core/agentic/client.py:330-357`

#### 工具列表的组合顺序

普通 chat 的工具列表按以下顺序组合并去重：

1. 用户主动开启的工具。
2. 满足上下文条件后自动挂载的工具。
3. 当前 Loop Capability 自己拥有的工具。
4. 永久在线工具：`write_memory`、`web_fetch`、`github`、`ask_user`、`cron`。
5. Partner 强制工具。
6. 最后移除被当前运行模式禁止的工具。

条件挂载包括：

| 条件 | 自动挂载 |
| --- | --- |
| 已选择知识库 | `rag` |
| 当前用户已有记忆 | `read_memory` |
| 当前用户已有笔记本 | `list_notebook`、`write_note` |
| 有 Skill manifest | `read_skill` |
| 有 deferred tools | `load_tools` |
| 沙箱策略允许 | `exec`、`code_execution` |

当前 chat 回答循环特意把 `has_sources` 设为 False，因为附件来源由 `explore_context` pre-loop 能力负责，不让 answer loop 再直接挂载 `read_source`。

#### Provider 不支持原生工具时

如果 Provider 被判定不支持可靠的原生 tool calling：

- 不向模型传入 `tools` schema。
- Agent Loop 仍然运行，但退化成普通流式文本回答。
- 本轮无法由模型产生可执行的原生 `tool_calls`。

Anthropic 后端通过适配器转换为 OpenAI Chat Completions 形态；Azure 使用 `AsyncAzureOpenAI`；其他 OpenAI-compatible Provider 通常使用 `AsyncOpenAI`。

### 6.4 初始 messages 如何构造

**状态：已验证**

`AgentLoop.run()` 先执行可选的 capability pre-loop briefing，并预检索已挂载知识库，然后调用 `_build_loop_messages()` 构造一次回合的初始消息。

消息顺序：

```text
1. system: ChatPromptAssembler 组装的系统提示词
2. system: 可选的压缩历史摘要
3. user/assistant: 未压缩的会话历史
4. user: 当前用户消息 + KB seed + capability seed/briefing
```

最后再把附件转换为 Provider 能接受的多模态消息。

系统提示词的主要块包括：

- 产品或 Partner 身份。
- 运行时规则。
- Agent Loop 行为规则。
- 激活的 Loop Capability 规则。
- Persona/Soul。
- Memory。
- Tools manifest。
- Skills manifest。
- Sources manifest。
- Deferred tools manifest。
- Notebook manifest。
- 本轮工作区说明。

设计上的一个重要细节：KB seed 等易变化内容放在最后一条 user message，而不是 system prompt。这样整个循环的 system prompt 保持字节稳定，更有利于 Provider 的前缀缓存。

#### system prompt 的组装时机与位置

每条用户回合都重新组装一份 system prompt，并不区分“第一次”或“往后”。

- **跨回合**：每发一条用户消息进入 `AgentLoop.run()`，都会再调一次 `AgenticChatPipeline._build_loop_messages()`，其中 `_build_system_prompt()` 重新拼出整个 system 文本；历史由 `turn_runtime` 把上一回合存下的 `conversation_history` 装回 `UnifiedContext` 后一并注入。`_build_loop_messages` 是总入口、`_build_system_prompt` 是其子步骤，两者面对同一份 `UnifiedContext` 取料——总入口自己取历史与当前用户消息，子步骤取 capability/tools/记忆等料拼 system；成品写进 `messages`，从不写回 `UnifiedContext`。
- **回合内的多轮 LLM 调用**：system prompt 不再重建。它作为 `messages[0]` 一直留在列表里，后续轮次只向列表追加 assistant（含 tool_calls）和 `role=tool` 消息。

`messages[0]` 即 system，固定 role=system、位于列表第一条，由 `_build_loop_messages` 直接写入：

```python
messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
```

因此一条 `[TRACE] 初始 messages 组装完成 | total=N` 里的 `N` 能反推本回合形态：新会话第一条消息时历史为空，`N = 2`（system + user）；续聊则有 `1 + 2k(历史) + 1 = 奇数`。

#### 历史消息的 role 由上一回合盖好章，本轮只搬运

`_build_loop_messages` 遍历 `context.conversation_history` 时**不重新分配 role**，沿用每条历史条目在上一回合产生时已有的 role，只做「过滤 + 搬运」：

| 历史条目 role | 进 messages 的 role | 处理 |
| --- | --- | --- |
| `user` | `user` | 原样照搬 |
| `assistant` | `assistant` | 原样照搬 |
| `system` | `system` | 加 header「[Conversation summary]」，role 仍为 system（这类条目是 `ContextBuilder` 在历史过长时压缩出的摘要） |
| 其它 / content 为空 | —— | 被丢弃，不 append |

关键认知：role 盖章发生在**上回合产生消息的那一刻**（用户发消息存为 `role=user`、模型回答存为 `role=assistant`），到这一回合历史已是带标签的干净数据，代码只读签不改签——只有 `system`（压缩摘要）那一类加 header，role 不变。等价的源码骨架：

```python
for item in context.conversation_history:
    role = item.get("role")
    content = item.get("content")
    if role in {"user", "assistant"} and isinstance(content, (str, list)):
        messages.append({"role": role, "content": content})   # 原样照搬
    elif role == "system" and isinstance(content, str) and content.strip():
        messages.append({"role": "system", "content": f"{header}\n{content}"})
    # 其它情况:丢弃
```

证据：

- `deeptutor/agents/chat/agentic_pipeline.py:340`（`_build_system_prompt`）
- `deeptutor/agents/chat/agentic_pipeline.py:360-401`（`_build_loop_messages`，写入 `messages[0]` 并遍历 `context.conversation_history`）
- `deeptutor/agents/chat/agentic_pipeline.py:385-399`（历史 role 沿用 + system 摘要加 header）
- `deeptutor/agents/chat/prompt_blocks.py:19-93`（`ChatPromptAssembler.system_prompt` 拼装各块）
- `deeptutor/agents/chat/prompts/zh/agentic_chat.yaml`
- `deeptutor/services/session/turn_runtime.py:1616`（每回合把上一回合历史装回 `UnifiedContext`）

### 6.5 AgentLoop 核心算法

**状态：已验证**

下面是 `_run_loop()` 的等价伪代码：

```python
for round in range(effective_max_rounds):
    result = await call_llm(messages, tools=live_tool_schemas)
    state.rounds += 1

    if not result.tool_calls:
        final_text = clean(result.text)
        if final_text is empty and not nudged_before:
            messages += [raw_assistant_reasoning, continue_nudge]
            continue
        return finalize(final_text)

    messages.append(assistant_message_with_tool_calls(result))
    dispatch = await dispatch_tool_calls_in_parallel(result.tool_calls)
    messages.extend(dispatch.tool_messages)
    state.tool_steps += 1

    if dispatch.pause:
        if not await resolve_user_reply(dispatch):
            return incomplete
        continue

    fold_context_checkpoint_if_present()

    if dispatch.terminate:
        return terminator_result

return await forced_finish_without_tools()
```

默认最大轮数是 8，来自：

```text
data/user/settings/agents.yaml
  -> get_chat_params()
  -> AgenticChatPipeline._max_rounds
```

当前本地 `agents.yaml` 没有显式写 `max_rounds`，因此深度合并默认值后仍为 8。
某些复用 chat loop 的能力可以通过
`context.metadata["_min_loop_rounds"]` 提高本回合的最低轮数，实际预算取配置值和该最低值中的较大者。

需要注意：

- `max_rounds` 限制的是正常循环轮数。
- 如果预算耗尽，会额外执行一次禁用工具的 forced finish。
- 当前合并后的 chat loop 每轮都使用 `responding.max_tokens`，本地是 8000。
- 配置中仍保留 `exploring.max_tokens=1600` 默认值，但当前 `loop_max_tokens` 实际返回 `responding.max_tokens`。
- `finish_reason` 会被记录，但是否结束主要由最终累计出的 `tool_calls` 是否为空决定。

### 6.6 一轮 LLM 调用内部发生什么

**状态：已验证**

`AgentLoop._call_llm()` 的关键步骤：

1. 运行上下文窗口保护。
2. 生成本次调用的 trace metadata。
3. 发出 `PROGRESS(call_state=running)`。
4. 调用 `client.chat.completions.create(stream=True)`。
5. 如果存在工具 schema，设置：

```python
tools = tool_schemas
tool_choice = "auto"
```

6. 消费 Provider 的流式 chunk：
   - `reasoning_content` / `reasoning` -> `THINKING`
   - 普通 `content` -> `CONTENT`
   - 分片的 tool call id/name/arguments -> 按 index 累积
   - usage chunk -> `UsageTracker`
7. 流结束后组装完整 tool call。
8. 发出 `PROGRESS(call_state=complete)`，并标记：
   - 有 tool call：`call_role=narration`
   - 无 tool call：`call_role=finish`

部分 Provider 把思考内容放在普通 `content` 内，并用 `<think>` 或 `<thinking>` 包裹。`InlineThinkFilter` 会在流式阶段拆分：

- 标签内文本进入 `THINKING`。
- 标签外文本进入用户可见的 `CONTENT`。
- 原始文本仍保留在传给下一轮模型的 conversation 中。

### 6.7 Tool Call 如何执行并回到下一轮

**状态：已验证**

模型的 tool call 会被转换为：

```python
{
    "id": "call_xxx",
    "name": "web_search",
    "arguments": "{\"query\":\"...\"}"
}
```

`dispatch_tool_calls()` 的处理流程：

1. 单轮最多接受 8 个 tool calls，多余部分截断并发出警告。
2. 使用容错 JSON 解析器解析参数。
3. 通过 `_augment_tool_kwargs()` 注入服务端上下文。
4. 检测本批次重复调用。
5. 为每个工具发出独立 `TOOL_CALL` trace。
6. 使用 `asyncio.gather()` 并行执行。
7. 发出 `TOOL_RESULT`。
8. 为每个 call 生成标准 OpenAI 协议的 `role=tool` 消息。
9. 聚合 sources、pause 和 terminate 信号。

这里的 `DispatchOutcome` 不是某一个工具的返回值，而是
`dispatch_tool_calls()` 对“这一批并行工具执行结果”的汇总信封。它主要携带：

- `tool_messages`：每个工具对应的标准 `role=tool` 消息，追加回 AgentLoop 的
  `messages`，供下一轮 LLM 读取。
- `sources`：这一批工具产生的引用来源。
- `tool_metadata_by_id`：按 `tool_call_id` 保存的结构化元数据。
- `pause` / `pause_payload` / `pause_tool_call_id`：某个工具要求暂停并等待用户输入。
- `terminate` / `terminate_payload`：某个工具要求本回合立即结束，并把其内容作为
  最终产物。

普通工具的两个控制信号都为假，AgentLoop 会自然进入下一轮。`pause` 和
`terminate` 的区别是：

- `pause` 是“同一回合暂时挂起”。当前使用者是 `ask_user`；收到回答后，运行时把
  回答替换进对应的 `role=tool` 消息，再继续下一轮 LLM。
- `terminate` 是“同一回合已经有最终产物，立即结束”。不会再调用 LLM；当前内置
  Chat 工具没有实际使用它，它是为真正的终止型工具保留的协议能力。

聚合时分别采用第一个 `pause` 和第一个 `terminate` 请求；但在 AgentLoop 层
`pause` 优先处理，因此发生暂停时不会立即发出终止结果。证据：
`deeptutor/core/agentic/tool_dispatch.py:61-81,492-573`、
`deeptutor/agents/chat/agent_loop.py:346-414`。

服务端参数注入很重要。模型只提供业务参数，运行时负责补充它不应该控制的内容，例如：

- `rag` 默认 `mode=hybrid`。
- `exec` 的用户 ID、工作目录和沙箱挂载。
- `code_execution` 的隔离工作目录。
- `load_tools` 的内部 loader 对象。
- `cron` 的 owner 路由。
- `web_search` 的默认查询和输出目录。

工具异常不会默认炸掉整个 Agent Loop。`execute_tool_call()` 会把异常转换成失败的工具结果，下一轮模型可以看到错误文本并决定重试、换工具或直接回答。

工具结果回填格式：

```python
{
    "role": "tool",
    "tool_call_id": "call_xxx",
    "name": "web_search",
    "content": "工具返回文本"
}
```

下一轮 LLM 同时看到：

1. 上一轮 assistant 的 narration 和 tool_calls。
2. 与每个 tool_call 对应的 `role=tool` 结果。

这就是 Agent 获得“观察结果”并继续决策的闭环。

#### Tool Runtime 与并发执行的真实边界

**状态：已验证**

当前代码没有一个名为 `ToolRuntime` 的独立类。Tool 运行时职责由三层共同组成：

1. `ToolRegistry` 是进程级工具目录。`get_tool_registry()` 首次调用时实例化
   `BUILTIN_TOOL_TYPES` 并保存为 `name -> BaseTool 实例`；插件/MCP 工具也注册到这里。
   它负责别名解析、schema 生成和 `await tool.execute(**kwargs)`，但不负责并发调度。
2. `dispatch_tool_calls()` 是批次调度与协议适配层。它负责参数解析、服务端参数注入、
   去重、最多 8 个的批次上限、并发执行、事件和 `role=tool` 结果封装。
3. 每个 `BaseTool.execute()` 及其下游 Service 是真正执行层。RAG 可以等待异步检索，
   `web_search` 用 `asyncio.to_thread()` 把同步搜索移出事件循环，`exec` 则进入
   `SandboxService`，由异步 HTTP/子进程 backend 执行，并另受每用户 semaphore 与
   每分钟速率配额限制。

因此准确调用链是：

```text
模型返回 tool_calls[]
  -> AgentLoop 把 assistant(tool_calls) 写入 messages
  -> dispatch_tool_calls()
       -> 截断 / 解析 / 注入私有参数 / 批内去重
       -> 为每项构造 _run_one(i) 协程
       -> await asyncio.gather(*coroutines)
            -> execute_tool_call()
                 -> ToolRegistry.execute(name, **args)
                      -> BaseTool 子类实例.execute(**args)
       -> _collect_outcome()
            -> TOOL_RESULT 事件
            -> role=tool 消息
            -> sources / pause / terminate
```

这里不是在普通 `for` 循环中逐个 `await`。下面两段语义不同：

```python
# 串行：a 完成后才启动 b
a = await run_a()
b = await run_b()

# 并发：a/b 一起进入事件循环，本协程等待整批结束
a, b = await asyncio.gather(run_a(), run_b())
```

`asyncio.gather()` 本身提供的是单事件循环上的协作式并发，不会自动创建 8 个 CPU 线程。
当某个工具等待 HTTP、数据库、异步子进程等 I/O 时，它让出控制权，事件循环才会推进其他
工具；若某个 `async def execute()` 内部直接运行长时间同步 CPU/阻塞 I/O，仍会卡住整个
事件循环。同步工具需要像 `WebSearchTool` 一样使用 `asyncio.to_thread()`，或交给外部
进程/服务，才能保留批次并发效果。

当前批次还有几个容易误解的细节：

- “8 个”是**单次模型回复、单次 dispatch 的上限**，不是进程或全系统的全局上限；
  dispatcher 没有跨 turn 的全局 semaphore，不同 turn 可以各自发起一批。具体工具服务
  可以再施加自己的限流，例如 Sandbox 的每用户并发和速率配额。
- 执行前的 `TOOL_CALL` 事件先按输入顺序逐个 `await` 发出，然后才进入 `gather()`；真正的
  `tool.execute()` 阶段才并发。
- `gather()` 返回结果时保持输入顺序，不按实际完成顺序排列。当前 `_collect_outcome()` 在
  整批 gather 完成后才按该顺序发送最终 `TOOL_RESULT`，因此一个快速工具的最终结果事件
  可能要等同批最慢工具结束；支持 `event_sink` 的长任务仍可在执行中发送进度事件。
- 普通工具异常会在 `execute_tool_call()` 内转换成 `success=False` 的工具结果，所以通常
  不会让 `gather()` 因单个工具异常取消整个批次；下一轮模型能读到错误并调整策略。
- 批内同名同参数调用只真正执行第一项，后续项产生占位 `role=tool` 结果；`ask_user`
  在同批中无论参数是否相同，也只保留第一个暂停请求。

#### 工具参数校验和重试触发的实际边界

**状态：当前行为已验证**

`ToolDefinition.to_openai_schema()` 会把工具参数定义转换成提供给模型的 JSON Schema，但这不
等于服务端在执行前已经按同一份 Schema 做了完整校验。当前 `_prepare_tool_args()` 使用
`parse_json_response()` 解析并尝试修复模型参数；完全无法解析或解析结果不是对象时退化为
`{}`。随后 `ToolRegistry.execute()` 直接调用 `await tool.execute(**kwargs)`，没有统一调用
`jsonschema.validate()`、Pydantic model 或等价的中央参数 Validator。

因此当前缺失必填字段、类型错误和业务前置条件主要有两种结果：具体工具主动返回
`ToolResult(success=False)`，或者 Python 调用/工具实现抛出异常，再由 `execute_tool_call()`
捕获并转换成失败结果。下一轮模型可以根据错误重新生成一个 Tool Call，但这不是 Runtime
基于错误类型执行的自动重试。若增加通用重试层，建议先把错误标准化为 `code`、`retryable`、
`retry_after_ms`、`side_effect_state` 和 `attempt`；参数、权限及确定性业务错误不应按原参数
重试，临时网络错误才进入有上限的退避策略。

另一个容易遗漏的迁移点是：节点返回 `success=False` 在图运行时看来仍可能是一次正常返回。
若以后接入 LangGraph `RetryPolicy`，包装节点必须检查结构化错误并对可重试类别抛出明确异常，
或者用条件边路由到自定义 `RETRY_WAIT`；仅配置 `RetryPolicy` 不会自动理解 DeepTutor 的
`ToolResult.success`。

关键证据：`deeptutor/core/tool_protocol.py:47-94,121-153`、
`deeptutor/core/agentic/tool_dispatch.py:268-292,337-467`、
`deeptutor/utils/json_parser.py:34-105`、
`deeptutor/runtime/registry/tool_registry.py:138-151`。

#### Agent Loop、批次 Dispatcher 与显式 Plan Scheduler 的边界

**状态：当前行为已验证；Planner 部分为演进设计，尚未实现**

默认 Chat 当前采用边执行边决策的方式，没有先调用一个全局 Planner 生成完整工具 DAG。
模型每轮返回的 `tool_calls` 只有调用 ID、工具名和参数，没有 `depends_on`；
`dispatch_tool_calls()` 会把本轮收到的调用全部视为同一批，在去重和数量裁剪后并发执行，
不会跨模型轮次维护节点依赖或 `PENDING/READY/RUNNING` 状态。因此它是批次 fan-out/fan-in
执行器，不是持续运行的 Tool Loop 或 DAG Scheduler。

假设逻辑依赖是 `A -> [B, C] -> D`，当前主链需要按下面的模型轮次展开：

```text
Round 1: LLM -> A       -> A 结果回填
Round 2: LLM -> B || C  -> B、C 结果回填
Round 3: LLM -> D       -> D 结果回填
Round 4: LLM -> 无 tool call，生成最终回答
```

最后一步仍是同一个 Agent Loop 的下一轮模型调用，不是重新启动第二个 Agent Loop。如果模型
在一次回复中同时发出 A、B、C、D，当前 Dispatcher 无法得知上述依赖，会把它们按同批并发
处理。普通异常会由 `execute_tool_call()` 转成失败结果，但 `ToolRegistry.execute()` 只是直接
调用具体工具；当前没有对所有工具统一生效的自动重试、退避或节点失败传播状态机。模型可以
在下一轮再次发起调用，具体工具也可以自行实现重试，但 `max_iterations` 只限制模型轮次，
不等于工具超时或通用重试预算。

若以后要支持依赖稳定、需要断点恢复和审计的长任务，可以增加可选的结构化 Planner：先输出
包含 `id`、`tool`、`depends_on`、`timeout`、`retry_policy`、`required` 和 `side_effect` 的
PlanGraph，经 Runtime 校验工具白名单、权限、预算和依赖环后，再交给 Plan Scheduler Loop。
Scheduler 维护 `PENDING -> READY -> RUNNING -> SUCCEEDED/FAILED`，以及 `RETRY_WAIT`、
`BLOCKED`、`CANCELLED`；只释放依赖满足的节点，在并发配额内执行 READY 集合。并行分支部分
失败时保留成功结果，阻断依赖失败节点的下游，独立节点是否继续及整个计划是否 fail-fast 由
节点策略决定。只对可重试且幂等的错误做有上限的退避重试；写操作结果未知时先用幂等键或
状态查询确认，不能盲目重放。该方案属于明确的后续实现路径，不能表述为当前默认 Chat 已有能力。

#### LangGraph 参考语义与演进注意事项

**状态：LangGraph 官方语义已核对；以下接入方式是演进设计，尚未实现**

LangGraph 是图运行时，不会自动生成符合鼎校伴学业务语义的 Planner。若用于上述演进路径，
可以把 Planner、Plan Validation Gate、Scheduler/Worker 和 Evaluator/Replanner 建成节点或
子图，同时注意以下边界：

1. `StateGraph` 可以用边表达 `A -> [B, C] -> D`：`A -> B` 和 `A -> C` 让 B、C 在同一
   superstep 并行；若 D 必须严格等待两个前置节点，应使用列表形式
   `add_edge(["B", "C"], "D")`。它不是两条独立 `B -> D`、`C -> D` 边的缩写：分支长度不同时，
   独立边可能让 D 在不同 superstep 执行多次；列表边则只在列出的节点都实际执行后运行一次，
   若条件分支跳过其中一个节点，D 将不会运行。需要等待所有实际选中分支结束时，可以评估
   `defer=True`，但它等待的是整张图没有 pending task，而不只是局部上游。调用图时还可传入
   `config={"max_concurrency": N}` 限制同一时间的任务数。并行节点若更新同一个 state key，必须定义
   reducer，或将结果按节点 ID 写入独立字段，否则会产生并发更新冲突。
2. LangGraph 将并行 superstep 作为事务边界。某个分支抛出未捕获异常时，本 superstep 的
   更新不会直接应用；配置 checkpointer 后，成功分支的 pending writes 会被保存，恢复时
   不必重复执行成功分支。DeepTutor 当前 Dispatcher 则先在每个调用内部把普通异常转换为
   结果，再整批回填，二者不是同一种故障语义。
3. 节点级 `RetryPolicy` 只在节点尝试抛出符合 `retry_on` 的异常时重试，可以结合 attempt
   timeout；节点正常返回 `success=False` 之类业务对象并不会自动触发它。重试耗尽后再进入
   `error_handler` 或补偿路径。它仍要求应用定义错误分类、最大次数、总 deadline 和写操作
   幂等，不能把参数错误、权限错误和确定性业务错误都设为可重试。
4. Checkpointer 保存 thread 范围内的图状态，用于中断、故障恢复和回放；Store 用于跨 thread
   的用户偏好、事实等长期数据。它们分别对应“执行恢复状态”和“长期用户画像”，不能混用。
5. `interrupt()` 适合缺少用户信息或写操作审批。恢复会从当前节点开头重新执行，所以中断前
   的副作用必须幂等；中断使用运行时控制异常，也不能被宽泛异常捕获当成普通失败。
6. `ToolNode` 可以执行一条 AI 消息中的多个工具调用，并自动注入 `ToolRuntime`。后者可提供
   state、只读 invocation context、Store、stream writer、执行次数和 tool-call ID，而且
   `runtime` 参数不会暴露给模型；但这只是运行时依赖注入，不是权限系统。生产代码仍应在构造
   tool schema 时做可见性白名单，在工具执行入口再次校验用户和资源归属，把写文件/执行命令等
   副作用放进沙箱或受限服务，并对高风险操作用 `interrupt`/HITL 做 approve/edit/reject。截至
   2026-09-08，上游 Python `ToolNode._afunc()` 对单个 ToolNode 内的多个异步调用仍直接使用
   `asyncio.gather(*coros)`；因此图调用的 `max_concurrency` 不应被当作可靠的逐工具外部服务限流，
   工具或 Service 层仍需独立的 semaphore、连接池和速率配额。
7. DeepTutor 当前对应的是分层执行授权：`turn_runtime` 先按用户 grant 过滤可选工具，chat
   pipeline 再按上下文、Partner built-in 白名单和 MCP 白名单决定 schema，`_augment_tool_kwargs()`
   注入模型不可控的用户、workspace 和 owner 信息；`exec` 最后还经过 isolation level、账号开关、
   SandboxService 二次检查及每用户并发/频率配额。UI toggle 只是用户选择，不应被当成唯一权限边界。
   当前仍有一个中央校验缺口：`dispatch_tool_calls()` 没有收到本轮 allowed tool set，
   `ToolRegistry.execute()` 也会直接执行任意已注册名称；所以“未向模型暴露 schema”不能视为强制
   执行授权。除 `exec` 等已有 Service 二次检查的工具外，后续还应在 dispatcher/registry 边界传入
   并校验本轮不可扩大的白名单，防止模型或上游 Provider 产出未挂载但全局已注册的工具名。
8. `recursion_limit` 限制图的 superstep 数，不等于节点 `max_attempts`、LLM Token Budget、
   工具 timeout 或整次 Turn 的 deadline，这些预算仍需分别维护。

官方参考：LangGraph [Graph API Overview](https://docs.langchain.com/oss/python/langgraph/graph-api)、
[Use the Graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api)、
[Fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance)、
[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)、
[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)、
[Functional API](https://docs.langchain.com/oss/python/langgraph/functional-api)、LangChain
[Tools / ToolRuntime](https://docs.langchain.com/oss/python/langchain/tools)、
[Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)，以及
[INVALID_TOOL_RESULTS](https://docs.langchain.com/oss/python/langchain/errors/INVALID_TOOL_RESULTS)；
当前 `ToolNode` 实现见上游
[`tool_node.py`](https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/langgraph/prebuilt/tool_node.py)。

关键证据：`deeptutor/agents/chat/agent_loop.py:333-365`、
`deeptutor/core/agentic/tool_dispatch.py:84-201,337-467`、
`deeptutor/runtime/registry/tool_registry.py:138-151`、
`deeptutor/agents/chat/agentic_pipeline.py:448-570,860-970`、
`deeptutor/multi_user/tool_access.py:32-83`、
`deeptutor/services/session/turn_runtime.py:767-791`、
`deeptutor/services/sandbox/service.py:65-95`。

#### 已验证的 8 项截断协议风险

Chat Loop 当前先把模型返回的**全部** `result.tool_calls` 写入 assistant message，随后
`dispatch_tool_calls()` 才在内部截断为前 8 项。于是模型若一次产生超过 8 个 call，
`messages` 中第 9 项之后仍有 assistant tool-call 声明，却没有对应的 `role=tool` 结果；
严格遵守 OpenAI tool-call 配对协议的 Provider 可能在下一轮拒绝这份消息。当前测试也没有
覆盖超过 8 项的 Chat 回填场景。较稳妥的修正方向是在写 assistant message 前统一裁剪，
或为被裁剪的每个 call 补一条“超过上限、未执行”的占位 `role=tool` 结果。

关键证据：

- `deeptutor/runtime/registry/tool_registry.py:21-163`
- `deeptutor/core/tool_protocol.py:122-208`
- `deeptutor/core/agentic/tool_dispatch.py:84-201,337-573`
- `deeptutor/agents/chat/agent_loop.py:333-356`
- `deeptutor/tools/builtin/__init__.py:87-156`
- `deeptutor/tools/exec_tool.py:64-137`
- `deeptutor/services/sandbox/service.py:29-96`
- `deeptutor/services/sandbox/quota.py:22-75`

#### 工具执行日志

所有经过 `execute_tool_call()` 的工具现在都会输出统一的后端 TRACE：

```text
[TRACE] 工具调用开始 | name=web_search call_id=call_xxx args={"query":"..."}
[TRACE] 工具调用结束 | name=web_search call_id=call_xxx success=True result_len=1234 elapsed_ms=85.2 pause=False terminate=False
```

异常时输出：

```text
[TRACE] 工具调用失败 | name=exec call_id=call_xxx elapsed_ms=12.4 error=...
```

日志中的参数最多保留 500 个字符；以下划线开头的服务端私有参数不会输出，
`token`、`password`、`secret`、`api_key` 等密钥类字段会显示为
`<redacted>`。日志只记录结果长度和执行状态，不输出完整工具结果。

#### 工具状态标识的真实边界

**状态：已验证**

当前实现有轻量级状态信号，但没有一套持久化的通用工具状态机：

- 工具返回契约中的 `ToolResult.success` 表示本次执行的业务成功或失败，此外还可携带
  `pause_for_user` 和 `terminate_turn`。
- 通用流事件以相同的 `tool_call_id` 配对：执行前发出 `TOOL_CALL`，执行结束后发出
  `TOOL_RESULT`。普通异常会在 dispatcher 内转换为失败结果，随后仍发出 `TOOL_RESULT`，
  因此不会破坏 tool call/result 配对。
- 检索类调用还会额外发出 `PROGRESS(call_state=running|complete|error)`；这里的
  `complete` 表示调用协程已经正常返回，最终业务是否成功仍应以 `ToolResult.success` 为准。
- 当前通用 `TOOL_RESULT` 事件的 metadata 没有统一透传 `success`，`role=tool` 消息也主要承载
  文本内容；因此不能把“收到了 `TOOL_RESULT`”等同于“工具执行成功”。后端 TRACE 会单独记录
  `success=True/False`。

也就是说，当前可以观测“已发起、已返回以及返回是否成功”，但没有跨轮维护
`PENDING/READY/RUNNING/SUCCEEDED/FAILED/RETRY_WAIT/BLOCKED`。这些节点状态只有引入显式
Plan Scheduler 后才需要成为 Runtime 的一等状态。若后续要强化前端展示、自动重试和审计，
至少应在标准事件中增加 `state`、`success`、`attempt`、`error_code`、`started_at` 和
`finished_at`，并继续使用 `tool_call_id` 做关联。

关键证据：`deeptutor/core/tool_protocol.py:121-153`、
`deeptutor/core/agentic/tool_dispatch.py:337-467,492-573`、
`deeptutor/core/stream_bus.py:157-190`。

### 6.8 重复调用、Deferred Tools 和 Context Checkpoint

**状态：已验证**

#### 重复调用

同一批并行请求中，如果工具名和 JSON 规范化后的参数都相同，只执行第一次。后续重复 call 仍会生成占位 `role=tool` 消息，保证 tool call/result 协议配对完整。

`ask_user` 更严格：同一批次只允许第一个，避免前端同时出现多个等待卡片。

#### Deferred Tools

MCP 工具默认不把完整 schema 全部塞进模型上下文：

1. 系统提示词只列出工具名称和简介。
2. 模型先调用 `load_tools(names=[...])`。
3. `DeferredToolLoader` 原地修改当前回合的 `tool_schemas` 列表。
4. 下一轮 LLM 调用立即看到新 schema。
5. 已加载名称按 session 保存，后续回合可以直接带上。

这是 progressive disclosure：减少初始 schema token，同时保持工具可动态加载。

#### Context Checkpoint

先区分三个层级：一个 session 可以包含多个用户回合；一次用户回合启动一个
AgentLoop；一个 AgentLoop 内部又可能执行多轮 LLM round。Context Checkpoint
压缩的是**同一次用户回合内，上一个 checkpoint 边界之后积累的若干轮中间交互**，
不是把多个用户回合合并，也不是生成一条用户可见的最终回答。

某些工具可以在 metadata 中返回：

```python
{
    "_context_checkpoint": {
        "summary": "到目前为止的压缩摘要"
    }
}
```

Agent Loop 收到后，会删除 checkpoint 边界之后积累的 narration 和原始 tool results，改为一条 `[Context checkpoint]` system 摘要。后续 checkpoint 会保留之前的摘要并继续追加。

因此，同一用户回合的内部 `messages` 可能从：

```text
system -> user -> assistant(tool_calls) -> tool -> assistant(tool_calls) -> tool
```

折叠为：

```text
system -> user -> system([Context checkpoint] 阶段摘要)
```

这条 checkpoint 是只供后续 LLM round 使用的内部上下文，最终用户仍然看到
`user -> assistant` 的对话结果。**已验证事实**是实现明确写入
`{"role": "system"}`，而不是 `assistant`。从角色语义看，原因是 checkpoint
由 Runtime 注入，用来描述已经完成的阶段状态，不是模型曾经说过的一句话；若写成
`assistant`，它会被解释成模型的历史输出。使用 `system` 能把运行时状态与模型回答
明确分开，并让后续 round 把它作为背景上下文继续执行。

`checkpoint_boundary` 就是当前 `messages` 列表里的一个整数下标，表示“这个位置之前的
消息已经是必须保留的稳定前缀”。它在循环开始时等于初始 messages 的长度，因此
system、历史消息和当前用户消息不会被 checkpoint 删除。工具返回新摘要后，循环执行：

```python
prefix = messages[:checkpoint_boundary]
prefix.append({"role": "system", "content": checkpoint_summary})
messages[:] = prefix
checkpoint_boundary = len(messages)
```

因此每次 checkpoint 都会删除“上一个边界之后”刚积累的 assistant narration、
tool calls 和原始 `role=tool` 结果，只留下工具提供的短摘要；新的边界又包含旧摘要，
所以后续 checkpoint 会在保留已有摘要的基础上继续压缩。这个变量只服务于当前
AgentLoop 的内存消息列表，不是数据库事务 checkpoint，也不是持久化进度游标。
证据：`deeptutor/agents/chat/agent_loop.py:190-205,396-441,769-780`。

它和普通窗口裁剪的区别：

- Checkpoint 是工具主动提供的语义摘要。
- Context window guard 是达到窗口阈值后的被动降载。

### 6.9 ask_user 如何暂停并恢复同一个回合

**状态：已验证**

`ask_user` 不是结束当前消息后再开一个新回合，而是暂停同一个 Agent Loop：

```text
模型调用 ask_user
  -> AskUserTool 返回 ToolResult.pause_for_user
  -> dispatch 产生 pause=True
  -> AgentLoop 等待 context.metadata["wait_for_user_reply"]
  -> 前端发送 submit_user_reply
  -> TurnRuntimeManager 把回答写入该 turn 的 reply_queue
  -> AgentLoop 用回答替换对应 role=tool 的 content
  -> 下一轮 LLM 在同一 messages 列表中继续
```

如果入口没有提供 waiter，或者用户放弃回答：

- 循环停止。
- `completed=False`。
- 问题卡成为当前回合的最终产物。

主要证据：

- `deeptutor/tools/builtin/__init__.py:1059-1200`
- `deeptutor/agents/chat/agent_loop.py:313-325`
- `deeptutor/agents/chat/agentic_pipeline.py:792-843`
- `deeptutor/services/session/turn_runtime.py:1191-1199`
- `deeptutor/services/session/turn_runtime.py:1652-1657`
- `deeptutor/api/routers/unified_ws.py:225-251`

### 6.10 循环如何结束和兜底

**状态：已验证**

| 场景 | 行为 |
| --- | --- |
| 本轮没有 tool calls 且有可见文本 | 该文本作为最终答案，正常结束 |
| 本轮只有 `<think>` 内容 | 保存原始推理并提示模型继续；最多主动纠正一次 |
| 达到正常轮数上限 | 追加“停止工具并回答”指令，禁用 tools，额外调用一次 LLM |
| 中途 LLM 调用失败 | 如果已有成功轮次，执行 forced finish；否则向上抛出 |
| forced finish 也失败或为空 | 发出本地化 fallback 文本 |
| 工具返回 pause | 等待用户；无法恢复时 `completed=False` |
| 工具返回 terminate | 工具内容直接成为最终产物 |

这里体现的策略是：

- 首轮失败没有材料可挽救，因此让 Orchestrator 统一发出错误。
- 已经完成过工具工作的中途失败，优先基于已收集材料给出 best-effort answer。
- 轮数预算限制工具探索，但仍尽量保证用户最终拿到一段回答。

### 6.11 流式显示和最终持久化为什么不会混在一起

**状态：已验证**

每一轮 LLM 的普通文本都会实时产生 `CONTENT`，包括：

- 工具轮前的简短说明。
- 最终答案。

等本轮结束后，`call_role` 才能确定：

- `narration`：本轮还调用了工具。
- `finish`：本轮没有调用工具，是最终答案。

前端可以据此把 narration 和 answer 分组。会话持久化层也会记录 narration 的 call id，并在生成最终 assistant message 时排除这些片段，只保存 finish 文本。

最终 `RESULT` 事件包含：

```python
{
    "response": final_text,
    "completed": True,
    "engine": "agent_loop",
    "rounds": 2,
    "tool_steps": 1,
    "metadata": {
        "cost_summary": {...}
    }
}
```

其中：

- `rounds` 是实际成功完成的 LLM 轮数，forced finish 也会计入。
- `tool_steps` 是发生工具分发的轮数，不是工具总调用数。
- `sources` 通过单独的 `SOURCES` 事件发送。

### 6.12 Token 和费用如何统计

**状态：已验证**

每个 Pipeline 创建一个回合级 `UsageTracker`：

1. Provider 返回 usage chunk 时，累加 prompt/completion/total tokens。
2. Provider 不返回 usage 时，使用 `字符数 / 3.5` 粗略估算。
3. 一次回合中的多次 LLM 调用累计到同一个 Tracker。
4. 最终通过模型定价表计算 `total_cost_usd`。
5. `emit_capability_result()` 把摘要写入 `metadata.cost_summary`。

需要注意：估算路径只是兜底值，不等同于 Provider 的精确计费数据。

证据：

- `deeptutor/core/agentic/usage.py`
- `deeptutor/agents/_shared/capability_result.py`
- `deeptutor/agents/chat/agent_loop.py:467-553`

### 6.13 上下文窗口和 Provider 兼容性保护

**状态：已验证**

每轮调用前都会估算 messages token。当超过有效上下文窗口的 90% 时：

1. 从较早的 `role=tool` 消息开始。
2. 把原始内容替换为“结果已裁剪，需要时重新调用”的短标记。
3. 直到估算值降到预算内。

Provider 兼容性还有三条降级路径：

- 不支持 `stream_options`：去掉该参数重试。
- 拒绝 native tool schema：去掉 tools/tool_choice 重试，并让后续循环不再带 schema。
- 不支持图片输入：在允许降级的模型上去掉图片，保留文本后重试。

### 6.14 通用 Labeled Agentic Loop

**状态：已验证**

`deeptutor/core/agentic/loop.py` 提供另一种能力无关的调度器：

```python
run_agentic_loop(
    initial_messages=...,
    protocol=LabelProtocol(...),
    host=capability_specific_host,
    ...
)
```

`LabelProtocol` 声明：

- `allowed`：允许的标签。
- `terminal`：结束循环的标签。
- `intermediate`：继续循环的标签。
- `final`：需要输出到用户界面的标签。
- `tool_label`：代表本轮调用工具的标签。

通用循环负责：

- 解析首行标签。
- 验证一个回复是否出现多个动作标签。
- 约束只有 tool label 能携带 tool calls。
- 分发工具。
- 处理中间状态。
- 对协议违规添加修复消息并重试。
- 达到最大迭代次数后调用 Host 的强制收尾。

Capability 通过 `LoopHost` 提供上下文裁剪、trace、工具执行、pause、terminate、终态校验和强制收尾等具体行为。

当前代码搜索到的实际调用方：

- `deeptutor/agents/research/pipeline.py`
- `deeptutor/agents/question/pipeline.py`

所以可以把两个循环这样记：

| 实现 | 决策协议 | 当前主要用途 |
| --- | --- | --- |
| Chat `AgentLoop` | 原生 tool calls；无工具即结束 | 默认 chat、复用 chat loop 的能力 |
| Core `run_agentic_loop` | 首行标签 + 可选原生 tool calls | Research、Question 等显式状态机 |

### 6.15 已完成的验证

**状态：已验证**

本次使用当前 `.venv` 安装了项目 `dev` 分组声明的：

- `pytest`
- `pytest-asyncio`

执行：

```powershell
& .\.venv\Scripts\python.exe -m pytest `
  tests\agents\chat\test_agent_loop.py `
  tests\core\test_agentic_loop_intermediate.py `
  tests\core\agentic\test_tool_dispatch_events.py `
  tests\core\test_agentic_client_provider_kwargs.py -q
```

结果：

```text
48 passed
```

覆盖的关键行为包括：

- 第一轮直接回答。
- 工具轮后再回答。
- narration/finish 区分。
- `<think>` 流式拆分。
- 空答案纠正。
- ask_user 暂停与恢复。
- 上下文 checkpoint。
- 轮数耗尽后的强制回答。
- 中途 LLM 失败后的挽救。
- 通用标签循环的中间状态和协议修复。
- 工具事件不泄露服务端私有参数。
- Provider adapter 的工具调用转换。

## 7. 目录与关键文件

| 路径 | 职责 |
| --- | --- |
| `deeptutor/runtime/orchestrator.py` | 单回合统一编排 |
| `deeptutor/runtime/launcher.py` | 前后端进程启动、端口和生命周期 |
| `deeptutor/runtime/registry/` | Tool 与 Capability 注册表 |
| `deeptutor/runtime/bootstrap/` | 内置能力启动注册 |
| `deeptutor/core/context.py` | 统一输入上下文 |
| `deeptutor/core/tool_protocol.py` | Tool 基础协议 |
| `deeptutor/core/capability_protocol.py` | Capability 基础协议 |
| `deeptutor/core/stream.py` | 流事件结构和类型 |
| `deeptutor/core/stream_bus.py` | 异步流事件总线 |
| `deeptutor/core/agentic/` | Agent 循环、工具调度和用量跟踪 |
| `deeptutor/capabilities/` | 内置 Capability 实现 |
| `deeptutor/tools/` | Tool 实现 |
| `deeptutor/api/main.py` | FastAPI 应用入口和路由装配 |
| `deeptutor/api/routers/unified_ws.py` | 统一 WebSocket 入口 |
| `deeptutor/app/facade.py` | Python SDK 门面 |
| `deeptutor_cli/main.py` | Typer CLI 入口 |
| `deeptutor/services/config/runtime_settings.py` | 运行时设置读取 |
| `web/` | Next.js 前端 |
| `data/user/settings/` | 当前工作区运行时设置 |
| `pyproject.toml` | Python 包和依赖真相源 |

## 8. 本地启动

**状态：已验证**

当前 Windows 工作区已经有 `.venv` 和前端依赖，可以直接启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-deeptutor.ps1
```

该本地脚本额外设置了 `127.0.0.1:7897` 代理。没有运行对应代理时，可直接执行：

```powershell
& .\.venv\Scripts\deeptutor.exe start
```

启动后默认访问：

```text
http://127.0.0.1:3782
```

只启动 FastAPI 后端：

```powershell
& .\.venv\Scripts\deeptutor.exe serve --port 8001
```

## 9. 推荐学习路线

建议按一条完整请求链学习，而不是一开始逐个浏览目录：

### 第一阶段：建立整体地图

1. `deeptutor/core/context.py`
2. `deeptutor/runtime/orchestrator.py`
3. `deeptutor/core/stream.py`
4. `deeptutor/core/stream_bus.py`
5. Tool 和 Capability 两个 Registry

目标：能够口述“一条消息如何进入系统、如何选择能力、如何流式返回”。

### 第二阶段：追通默认 chat（已完成）

本阶段已经验证：

1. chat 实现类的注册与创建。
2. 系统提示词和初始 messages 的组装。
3. ToolMountFlags 和权限如何决定挂载工具。
4. LLM tool call 的解析与并行分发。
5. 工具结果如何回到下一轮模型请求。
6. 循环的正常退出、暂停、异常与强制收尾。
7. 流式事件、最终结果和用量统计。

详细结论见[第 6 章](#6-一次对话的主调用链)。

#### 初学者第一遍阅读顺序

第一遍只沿默认 Chat 主链阅读，不要从大目录中随机挑文件：

1. `deeptutor/core/context.py`
   - 只回答：一次用户回合携带哪些统一数据？
2. `deeptutor/runtime/orchestrator.py`
   - 只回答：如何选择 Capability，如何管理 StreamBus？
3. `deeptutor/agents/chat/capability.py`
   - 只回答：ChatCapability 把工作交给了谁？
4. `deeptutor/agents/chat/agentic_pipeline.py`
   - 第一遍只看 `__init__()`、`run()`、`_build_loop_messages()`、
     `_compose_enabled_tools()` 和 `_dispatch_tool_calls()`。
5. `deeptutor/agents/chat/agent_loop.py`
   - 先看顶部设计说明，再看 `run()`、`_run_loop()`、`_call_llm()`、
     `_forced_finish()`。
6. `deeptutor/core/agentic/tool_dispatch.py`
   - 重点看 `dispatch_tool_calls()`、`execute_tool_call()`、
     `_collect_outcome()`。

每个文件第一遍只回答两个问题：

1. 它接收什么？
2. 它把结果交给谁？

第一遍暂缓阅读：

- `deeptutor/core/agentic/loop.py` 和 `labeled_step.py`：这是另一套标签协议循环。
- `deeptutor/agents/research/`、`question/`：先理解默认 Chat，再学习复杂状态机。
- `deeptutor/services/`：目录很大，等主链遇到具体服务时再向下追。
- `web/`：先理解后端事件生产，再追前端事件消费。
- `deeptutor/agents/chat/chat_agent.py`、`session_manager.py`：不在当前默认 Chat
  Agent Loop 的最短核心阅读路径上。

### 第三阶段：追通 Web 入口

从 `deeptutor/api/routers/unified_ws.py` 向内追踪：

1. 前端发送的消息格式。
2. WebSocket 鉴权和会话恢复。
3. 请求如何转换成 `UnifiedContext`。
4. StreamEvent 如何序列化并返回前端。
5. 前端如何消费不同事件类型。

### 第四阶段：选择专题

- RAG 和知识库。
- Deep Research 多阶段流程。
- Memory、Skill 和 Source 注入。
- Partner 渠道。
- 多用户权限。
- 沙箱代码执行。
- 可视化和数学动画。

## 10. 待深入的问题

以下问题尚未在本文档中完整验证：

- [x] 默认 `chat` Capability 从注册到执行的完整调用链。
- [x] Agentic loop 的循环退出条件和最大轮次控制。
- [x] Tool 的自动挂载规则和权限过滤顺序。
- [ ] WebSocket 请求与 StreamEvent 的完整消息协议。
- [x] 默认 chat Prompt 的分层和动态上下文组装顺序。
- [ ] LLM Provider 的完整选择和配置覆盖链；chat 的客户端适配及降级已验证。
- [x] UsageTracker 如何聚合 token 与费用。
- [ ] 会话、Memory 和 Notebook 分别持久化到哪里。
- [ ] 知识库从文档解析到检索返回的完整链路。
- [ ] 前端状态管理和 WebSocket 重连策略。
- [ ] 多用户模式下的资源隔离和鉴权边界。

## 11. 术语表

| 术语 | 当前理解 |
| --- | --- |
| Agent-native | Agent 循环、工具和多阶段能力是核心架构，不是附加功能 |
| Tool | LLM 在一次 agent 循环内按需调用的单次函数 |
| Capability | 接管整个用户回合的多阶段业务流程 |
| Orchestrator | 根据统一上下文选择并执行 Capability 的编排器 |
| Registry | 注册、发现和获取 Tool/Capability 的目录 |
| UnifiedContext | 在不同入口和能力之间传递的统一回合上下文 |
| StreamEvent | 与具体 UI 无关的流式输出事件 |
| StreamBus | Capability 发布、消费者订阅 StreamEvent 的异步总线；回合内活、回合结束 close |
| EventBus | 项目级长期公告板（区别于回合内 StreamBus）；回合结束发 `CAPABILITY_COMPLETE` 给非 UI 监听者（统计/钩子/cron），非命脉、吞异常 |
| session | 一次连续对话的关系，跨多个回合；标识为 `session_id` |
| turn | 一次「用户发消息 → AI 答」的回合；同 session 内多个 turn 各有 `turn_id`。ask_user 暂停恢复属于同一 turn、不开新 turn |
| session_id | 标识「哪一段会话」，长期关系 |
| turn_id | 标识「会话内第几回合」，被 `register_bus` 用作 key 让别处能按它找回当前回合的 bus |
| RAG | 先从知识库检索相关内容，再让模型基于内容生成回答 |
| Mount | 在当前上下文中把某个 Tool 暴露给 LLM |
| Narration | 调用工具的 LLM 轮次中，展示给用户的简短前导文本 |
| Finish | 没有 tool call 的 LLM 轮次；其文本作为最终回答 |
| Forced finish | 预算耗尽或中途失败后，禁用工具并要求模型立即回答的兜底调用 |
| Context checkpoint | 用语义摘要替换一段已完成工具交互，降低上下文占用 |
| Deferred tool | 初始只展示简介，需要 `load_tools` 后才注入完整 schema 的工具 |

## 12. 后续记录模板

研究一个新主题时，优先使用下面的结构：

```markdown
### 主题名称

**状态：已验证 / 部分验证 / 待验证**

#### 它解决什么问题

用业务语言说明目的。

#### 核心对象

- `ClassA`：职责。
- `ClassB`：职责。

#### 调用顺序

1. 输入从哪里进入。
2. 中间经过哪些关键分支。
3. 状态在哪里读取或修改。
4. 结果如何返回。

#### 关键证据

- `path/to/file.py:行号或函数名`

#### 容易混淆的点

说明相似概念之间的区别。

#### 尚未确认

- [ ] 仍需验证的问题。
```

## 13. 更新记录

### 2026-09-08

- 扩充 6.7 节的 LangGraph DAG 学习口径：区分 list-form join、独立入边和 `defer=True`，补充
  `max_concurrency`、并行 state reducer、`ToolNode`/`ToolRuntime` 与节点异常重试边界；并把
  LangGraph 的上下文注入和 HITL 映射到 DeepTutor 的用户 grant、MCP 白名单、服务端私参注入、
  exec isolation、SandboxService 二次校验及配额，明确“工具可见”不等于“已完成执行授权”，
  同时记录当前异步 `ToolNode` 内部 gather 不应被图级 `max_concurrency` 替代逐工具限流，并指出
  DeepTutor Dispatcher/Registry 尚未对本轮 allowed tool set 做中央二次校验的现状风险。

### 2026-09-07

- 在 6.7 节补充 Agent Loop、批次 Tool Dispatcher 与显式 Plan Scheduler 的边界：确认默认
  Chat 没有全局 Planner、跨轮 `depends_on`、节点状态机或通用自动重试；用
  `A -> [B, C] -> D` 说明当前多轮执行方式，并记录可选 Planner + Scheduler 的演进路径。
- 补充工具参数校验的真实边界，并对照 LangGraph 官方语义记录并行 superstep、`RetryPolicy`、
  timeout、error handler、checkpointer、interrupt、幂等副作用和长期 Store 的演进注意事项。
- 补充工具状态标识的真实边界：区分 `ToolResult.success`、`TOOL_CALL/TOOL_RESULT` 生命周期
  事件、检索 trace 的 `call_state`，并明确当前尚无通用持久化节点状态机。
- 补充 RAGAS Faithfulness 的陈述级评测口径，区分它与 Recall、答案正确率和引用准确性，并
  明确 `0.82 -> 0.90` 当前仍是缺少评测产物的模拟简历口径。
- 在 3.2 节补充 React Hook 与状态管理的项目实例：说明 `useReducer`、`useRef`、
  `useEffect`、`useMemo`、`useCallback` 和自定义 Hook 在聊天流式界面中的实际职责与清理边界。

### 2026-09-06

- 修正 5.4 节的 StreamBus 队列描述：当前为每订阅者无界队列、共享事件引用，
  而非有界背压或深拷贝；补充 `_history`、外层事件缓冲与关闭后的对象生命周期，
  明确 Prompt 大小、活跃 Turn 内存和在线用户容量是不同口径，人数上限仍需压测。
- 在 5.6 节补充 Redis 保存 Agent Loop `messages` 的边界：确认当前主链路仍使用
  SQLite/PocketBase 保存会话、本地列表承载本轮循环；给出 Redis 作为跨 worker 活跃
  Turn checkpoint 的推荐路径、协议配对边界、并发版本控制和 TTL 要求。

### 2026-08-31

- 在第 6 章补充当前源码与鼎校伴学简历口述的边界：确认当前 DeepTutor 仍是
  `ChatOrchestrator -> Capability -> AgenticChatPipeline`；简历口径则收敛为
  `TurnOrchestrator -> ChatPipeline -> AgentLoop`，取消 Capability 路由和前置 LLM 意图
  分类，由 Agent Loop 通过直接回答或 Tool Selection 完成判断，业务跳转统一通过受控的
  Action Tool 触发。

### 2026-08-30

- 补充 5.6 节跨 Session 情景记忆边界：确认当前 Chat L1 是按 Session 构造 Entity，
  当前 L2 则是 Markdown 事实文档，并非一对一的数据库摘要表；记录“L2 定位、L1 取证”
  的 `recall_conversation` 设计、消息级来源引用、结构化 SQL 筛选与候选重排方案，并将
  FTS5/BM25 或 Embedding 明确为规模扩大后的可选召回增强。
- 补充 5.6 节广义用户画像边界：对外可用“用户画像”统称全部 L3，内部仍以 `profile`、
  `recent`、`scope`、`preferences` 管理不同维度；区分各维度的更新触发、时效和 Agent
  用途，并明确差异化更新频率是推荐设计而非当前已实现的自动调度；补充“同表按 slot
  分行、组合读取”原则。
- 补充 5.6 节 RAG/Tool Result 上下文与持久化边界：确认二者由 Agent Loop 动态加入本轮
  messages，而非预存于 UnifiedContext；记录 Tool Result 事件持久化、跨轮不自动回放、
  不自动进入长期记忆，以及 KB Seed 和主动 RAG Tool 两条证据注入路径；补充 Tool 审计、
  领域副作用、Retrieval Trace、证据引用和画像晋升的选择性持久化建议，并给出 Tool/RAG
  关系表与大结果对象引用的落地模型。
- 补充 5.8 节混合检索指标口径：说明 Dense、BM25 与 RRF 的互补关系、RRF 排名融合公式、
  Recall@5 在单/多 gold Chunk 下的不同算法，以及 600 条评测集的分层抽样、防幸存者偏差、
  防调参泄漏原则和需要保留的自证材料；明确评测结果应独立保存并按稳定 Chunk 标识比对，
  不依赖 RAG passage 是否进入聊天长期记忆。

### 2026-08-29

- 新增 5.7 节，追通 BookEngine 页面规划链路，明确 `SectionArchitect` 只生成 block 骨架、
  `BookCompiler` 才负责逐块生成，以及 LLM-first、静态模板 fallback、持久化与事件边界。
- 区分兼容类 `PagePlanner`、当前 `SectionArchitect` 和 `deep_solve` 的工具化规划机制；记录
  `phase` 未实际过滤 block 类型、Prompt 数量/多样性约束未被代码硬校验和缺少直接单测等
  已验证的待修正项。
- 深化 6.7 节的 Tool 执行链：区分 `ToolRegistry`、批次 dispatcher 与具体 Service
  运行时，说明 `asyncio.gather()` 的协作式 I/O 并发、事件与结果顺序、工具级二次限流，
  并记录超过 8 项时 assistant tool-call 与 `role=tool` 可能失配的协议风险。
- 新增 5.8 节，记录 5 类 RAG 后端、5 类解析引擎、116 种扩展名以及默认
  `512/50` 切块、双路 Top 10 经 RRF 收敛为 Top 5 的可核验口径，并明确这些配置不能
  替代 Recall、延迟或教材规模等真实评测。
- 新增 5.9 节，记录 4 类知识点、90% 量化门槛、最近 5 次练习加权、低样本置信度上限
  和最长 60 天复习周期，区分产品学习规则与线上业务效果。

### 2026-08-23

- 在 5.6 节补充 LangChain/LangGraph 与 DeepTutor Memory 的职责边界：前者是组件或
  工作流编排，后者负责 L1/L2/L3 领域数据模型、来源追溯和增量生命周期；记录当前
  运行时依赖与 `MemoryStore`、`UnifiedContext`、`AgentLoop` 的自有边界，并补充可在
  未来通过适配器选择性引入 LangGraph 的评估口径。
- 补充 LangChain 旧版 `BaseMemory`/消息历史与当前 LangGraph checkpointer、Store 的
  实现模型：前者解决会话消息加载与写回，后两者分别负责 thread 级 workflow state
  持久化和跨 thread 长期数据；明确 trim/summary、namespace、语义搜索以及应用自行
  决定抽取、去重和冲突策略的边界。

### 2026-08-22

- 统一三层记忆目标架构的面试表达：只保留“对话记录与滚动总结 → 关系库 L1/L2/L3”
  两次设计迭代；明确 L1 每轮保存原始事件并由 Flash 异步标注、L2 每十轮或尾批追加、
  L3 使用当前画像与新增 L2 增量更新，凌晨 3 点仅作失败补偿。
- 补充异步任务的可靠性口径：L2 使用批次幂等键并在事务中提交记忆、来源和处理标记，
  L3 在同一事务中写画像并推进游标；明确当前关系数据库足够，向量检索只作为未来由
  召回评测驱动的查询优化。
- 修正目标方案的运行时上下文口径：每轮将当前 Session 最近 10 轮原始消息、该 Session
  已生成的 L2 和当前用户 L3 组装进 `UnifiedContext`；`Token Budget` 约束整个请求，而非仅限制 L3。
- 补充阿里云百炼托管小模型选型：验证 `qwen3.7-flash` 支持结构化输出，建议先采用云端
  API、JSON Schema 和小型评测集，而不是在没有数据集时微调或自部署。

### 2026-08-21

- 在 5.6 节加入 Mem0 OSS 当前写入、条目存储和混合召回链路对照，
  区分 OSS 与 Platform 能力，并记录该版本 `linked_memory_ids` 提示词与
  主记忆 payload 实际落盘之间的实现缺口；补充保留内部 L1/L2/L3、
  将存储和召回演进为条目化混合检索的可选路径。
- 增加不接入生产链路的 Memory 混合召回学习原型，可直接演示
  L1 evidence、L2 事实、L3 profile、组合召回、token budget 组装，以及
  `supersedes_id` 与 active/superseded 事实版本机制。
- 补充 5.6 节 Memory 分层的执行边界：明确 L2 更新会现场读取 L1 Snapshot
  视图，但不会启动或刷新 L1；同时区分 L2 “反复出现”和 L3 `profile`
  “多场景支撑”的提示词目标与当前引用校验器真正强制的硬规则。
- 补充 L1/L2/L3 从触发、运行时对象、落盘到后续消费的完整生命周期；明确
  Snapshot Refresh 只提交差异账本、当前通用 Trace 不输入 L2 Update、归并无自动
  跨层触发，并记录 L2 增量判断只比较 Entity id 而不比较 fingerprint 的实现边界。

### 2026-08-19

- 重写 5.6 节三层记忆链路：补充 L1 Workspace Snapshot 与 Trace 两类原始来源，
  说明 L2 基于实体引用集合的增量事实抽取、引用校验和去重，明确 L3 的四类 slot、
  当前 surface 级追溯关系，以及长期记忆通过显式 Prompt 注入和 `read_memory` Tool
  按需读取的两条回流路径。

### 2026-08-20

- 补充 5.6 节的持久化边界，区分业务原始存储、L1 文件型 Snapshot/Trace，以及
  L2/L3 Markdown + meta JSON；明确三层均持久化但不统一写入关系型数据库，且
  L2/L3 由更新流程触发而非每条消息同步归并。
- 补充 Memory 模块的职责边界，区分长期记忆、当前会话历史和知识库 RAG，并记录
  `MemoryStore`、Snapshot、Trace、consolidator 及记忆 Tool 的分工。
- 补充“业务原始数据”和 L1 逻辑层的关系，明确 L1 通过 Adapter 建立原始证据视图，
  当前实现不要求将所有业务原文复制到 memory 目录。
- 补充 L1/L2/L3 的使用时机，区分记忆生成、审计追溯与 Chat Agent 运行时消费，
  明确当前默认对话主要直接读取 L3。

### 2026-08-18

- 6.8 节补充 session、用户回合与 AgentLoop 内部 round 的层级关系，明确 Context
  Checkpoint 压缩的是同一用户回合内的中间工具交互，而非用户可见输出；同时解释
  checkpoint 使用 `system` 角色是为了表达 Runtime 注入的阶段状态，而不是模型历史回答。

### 2026-08-10

- 第 4、6 章补充入口到 `ChatOrchestrator` 的真实调用方：CLI/SDK 通过
  `DeepTutorApp`，WebSocket 直接进入 `TurnRuntimeManager`，最终由
  `_run_turn()` 构造 `UnifiedContext` 并调用 `ChatOrchestrator.handle()`。
- 4.1 节区分 HTTPS、WebSocket 与 SSE，明确 `done` 是 turn 级业务完成事件而非
  WebSocket 关闭帧；补充前端按回合需要懒连接、active turn 恢复、断开与重连条件，
  区分 WebSocket/turn/订阅三个生命周期，并记录当前前端为接收尾随
  `session_meta` 而延迟 15 秒断开连接。
- 第 6 章澄清 `ChatOrchestrator` 的名字不代表只运行 Chat：它是所有内置
  Capability 的统一路由器，默认分支才是 `ChatCapability`。

### 2026-08-09

- 5.5 节增加 Skill 存储、用户覆盖内置、Manifest 注入、`read_skill`
  按需读取及 `always` 预加载链路。
- 5.6 节增加三层记忆的 L1/L2/L3 存储结构、场景列表、
  `MemoryStore` 归并入口以及 L3 记忆注入 Chat System Prompt 的实际路径。

### 2026-08-07

- 5.2 节增加 `brainstorm` 真实 Tool 案例，串联定义、注册、Schema、
  外层 tool call、分发、内层单次 LLM 调用和 `role=tool` 回填，并区分
  外层 Chat LLM 与内层 Brainstorm LLM 的职责。

### 2026-08-03

- 6.7 节补充 `DispatchOutcome` 的聚合信封定位和字段职责，明确普通继续、
  `pause` 同回合等待并恢复、`terminate` 直接结束回合三种控制结果，以及
  AgentLoop 中 `pause` 优先于 `terminate` 的处理顺序。
- 6.8 节解释 `checkpoint_boundary` 是当前 messages 的稳定前缀下标，补充其初始化、
  裁剪、追加 checkpoint 摘要和更新边界的完整过程，并明确它不是持久化进度游标。

### 2026-07-30

- 第 6 章第 6 步补 `register_bus` 子动作：建好 bus 后把 turn_id → bus 挂全局表，让 ask_user 暂停恢复等「中途找回本次回合 bus」的请求能按 turn_id 定位；回合结束 `unregister_bus` 摘掉防泄漏。铁序在 `create_task` 之前。证据 `orchestrator.py:79-82`、`stream_bus.py`。
- 第 11 章术语表补 session/turn/session_id/turn_id 条目：session 是长期关系、turn 是单次发答、ask_user 暂停恢复同 turn 不开新 turn、turn_id 是 `register_bus` 的查找 key；并补 EventBus 条目（区别于 StreamBus）。

### 2026-07-29

- 6.4 节补充「历史消息的 role 由上一回合盖好章、本轮只搬运」：`_build_loop_messages` 沿用历史条目原有 role，只做过滤+搬运，唯 `system` 压缩摘要加 header。证据 `agentic_pipeline.py:385-399`。
- 6.4 节明确 `_build_loop_messages` 与 `_build_system_prompt` 是父子关系、面对同一份 `UnifiedContext`：总入口取历史与当前用户消息，子步骤取 capability/tools/记忆等料拼 system；成品写进 `messages` 不写回 `UnifiedContext`。
- 第 6 章第 8/9 步补充「bus 收尾机制」：`capability.run` 跑在后台 task、主协程并发 `async for` 收事件；`finally` 里 `emit(DONE)` + `close()` 才让消费者循环退出——退出靠 `close()` 的结束标记，而非队列瞬时空。证据 `orchestrator.py:84-95`、`stream_bus.py`。
- 5.4 节补充 StreamBus 机制三件套：异步队列（`asyncio.Queue`、空/满自动挂起）、多订阅者（各收各的副本）、显式收尾标记（`close()` 让 `async for` 退出而非靠队列自然空）。
- 第 6 章第 5 步补 SESSION 机制：SESSION 由编排器直接 `yield` 给调用方、不走 bus（此刻 bus 未建），是「回合开始」元信息（session_id + turn_id）；它在 bus 建好、capability 开跑之前最早发。编排器元信息与 capability 业务流分两路：直接 yield vs 经 bus 转发。证据 `orchestrator.py:70-77`。
- 第 6 章第 10 步补 EventBus 与 StreamBus 的区分：EventBus 是项目级长期公告板、给不在 UI 链路上的统计/钩子/cron/memory 用；`_publish_completion` 发 `CAPABILITY_COMPLETE` 是公告、非命脉（吞异常不影响回合），置于 StreamBus 收尾之后才发。证据 `orchestrator.py:96-114`。

### 2026-07-28

- 扩展 `UnifiedContext`：补充其请求包定位、字段职责、数据流和与会话存储/循环状态的区别。
- 补充 Tool 完整调用链：区分源代码、运行时注册表、当前回合 schema 和对话消息，并说明工具如何交给 AgentLoop。
- 为统一工具执行入口增加开始、成功和失败 TRACE，并对参数预览进行长度限制和敏感字段脱敏。
- 在 6.4 节补充 system prompt 的组装时机与位置：每条用户回合重建一次 system，回合内多轮 LLM 复用同一条 `messages[0]`；由 `_build_loop_messages` 写入，历史由 `turn_runtime` 每回合装回 `UnifiedContext`。

### 2026-07-27

- 建立学习手册。
- 记录已确认的技术栈、总体架构、核心上下文和 Orchestrator 主流程。
- 建立推荐学习路线、待验证问题和后续记录模板。
- 完整追踪默认 chat Agent Loop：工具挂载、Prompt、流式模型调用、并行工具执行、暂停恢复、上下文保护、退出与兜底。
- 区分 chat 专用原生 tool-call loop 与 Research/Question 使用的通用 labeled loop。
- 安装 `pytest`、`pytest-asyncio`，Agent Loop 相关 48 项测试全部通过。
- 增加初学者阅读顺序和第一遍暂缓目录，避免从大目录随机阅读。
