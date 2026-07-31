# DeepTutor 项目学习手册

> 本文档位于仓库根目录，是本项目学习过程的唯一主文档。

> 用途：持续记录对 DeepTutor 的技术栈、架构、调用链和具体实现的理解。
>
> 使用方式：既可以直接阅读，也可以把本文档交给 GPT，在语音通话中按章节讲解和提问。
>
> 当前基线：`main` 分支，提交 `c5195899`，最后更新于 2026-07-28。

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
CLI / WebSocket API / Python SDK
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

1. `UnifiedContext` 统一不同入口传入的数据。
2. `ChatOrchestrator` 决定本回合交给哪个 Capability。
3. Registry 负责发现和获取 Tool/Capability，不让编排器硬编码所有实现。
4. `StreamBus` 统一输出进度、内容、错误和完成事件。

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

**状态：已验证到主流程**

相关文件：

- `deeptutor/core/stream.py`
- `deeptutor/core/stream_bus.py`

Capability 不直接依赖某个 UI，而是向 `StreamBus` 发出统一事件。CLI、WebSocket 和 SDK 可以各自消费这些事件。

这是一种“执行逻辑和展示方式解耦”的设计：能力只描述发生了什么，入口决定如何显示。

StreamBus 的机制层可拆成三件套（实现细节在 `stream_bus.py`，第三阶段再核）：

- **异步队列**：内部用一个先进先出的 `asyncio.Queue` 存事件；队列空了消费者挂起等待、满了 producer 挂起等待，不丢不挤。
- **多订阅者**：`subscribe()` 给每个调用方返回各自独立的消费游标/副本，CLI/Web/SDK 同时订阅时各收各的同一份事件流。
- **显式收尾标记**：producer（capability）一停，`finally` 里 `emit(DONE)` 发最后一条事件、`close()` 打「不会再有下一条」标记；消费者那侧的 `async for` 不是靠队列瞬时空判定结束，而是看到这个标记才退出。

## 6. 一次对话的主调用链

**状态：已验证到默认 chat Agent Loop**

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

某些工具可以在 metadata 中返回：

```python
{
    "_context_checkpoint": {
        "summary": "到目前为止的压缩摘要"
    }
}
```

Agent Loop 收到后，会删除 checkpoint 边界之后积累的 narration 和原始 tool results，改为一条 `[Context checkpoint]` system 摘要。后续 checkpoint 会保留之前的摘要并继续追加。

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
