# 鼎校伴学 Agent Runtime 面试口述稿

> 对应简历第一条职责：参与 Agent Runtime 核心能力建设。
>
> 本文以简历中的鼎校伴学项目口径为主，不把当前学习仓库的多 Capability 实现硬套进来。
> 当前只有一条 Web Chat 执行链，不设置独立 Capability 路由，也不在 Agent Loop 前额外调用
> 一次 LLM 做意图分类。

配套复习：[Agent Runtime 面试追问与回答](C:/file/ownWork/DeepTutor/learning/interview-scripts/鼎校伴学-Agent-Runtime-面试追问.md)，
覆盖 Subagent、Skill、DAG、Plan 模式、项目指标和亮点。

## 讲解主线

这部分要突出：不是简单封装模型接口，而是让模型决策、工具执行和任务结束形成可控的
执行闭环。面试时按“为什么做 -> 如何执行 -> 如何处理异常 -> 业务价值”展开，内部类名
只用于说明职责，不要开头就逐个背诵调用链。

> 模型负责决定下一步做什么，Runtime 负责按规则执行、回填结果，并控制异常和结束边界。

## 先统一执行主线

```text
用户消息
  -> Turn Runtime 补齐会话数据
  -> UnifiedContext
  -> TurnOrchestrator（调度与回合生命周期）
  -> ChatPipeline（组装 Prompt、工具和运行参数）
  -> Agent Loop
       -> 无 Tool Call 且有有效文本：直接回答
       -> Action Tool：返回受控的业务入口数据，由前端展示按钮
       -> RAG / 题库等 Tool：结果回填后继续推理
  -> 统一输出
  -> Session 消息与 Trace 持久化

用户点击入口后，由独立业务服务执行学习任务
  -> 任务结果回写 Session
  -> 异步更新长期记忆和用户画像，供后续对话使用
```

这里没有单独的“意图识别阶段”。LLM 在 Agent Loop 的第一轮中同时理解需求并选择下一步：
能回答就直接回答，需要业务入口就调用 Action Tool，需要教材、题库或 OCR 就调用对应工具。
这里省去的是单独的前置分类调用，不是说模型只决策一次；后续轮次仍会根据工具结果调整行动。

## TurnOrchestrator 与 ChatPipeline 的职责

### TurnOrchestrator：管理一次回合怎么运行和结束

`TurnOrchestrator` 接收已经组装好的 `UnifiedContext`，创建本轮流式通道，启动
`ChatPipeline`，转发执行事件，并把未处理异常转换成统一错误事件。无论成功还是失败，它
都要发送 `DONE`、关闭本轮 Stream，并发布回合完成信号。

它不读取业务字段来判断用户意图，不组装 Prompt，不调用模型或工具，也不直接保存消息。
消息加载与落库属于 Turn Runtime，推理和工具选择属于 Agent Loop。

`DONE` 表示本轮事件流结束，不代表业务成功；关闭 Stream 是通知订阅者后续不再产生事件，
让等待事件的 `async for` 正常退出，不是关闭 WebSocket 或 Session，也不是直接取消正在
执行的模型或工具。下一条用户消息会启动新的 Turn 和事件流。

### ChatPipeline：准备一次 Chat Agent 怎么执行

`ChatPipeline` 是确定性的运行准备层，不额外调用 LLM。它读取 `UnifiedContext`，组装
System Prompt、历史消息和当前问题，根据上下文挂载 RAG、题库、OCR、Action 等工具，生成
Tool Schema，应用模型参数、Token 预算和最大轮次，最后创建并启动 Agent Loop。

它不提前把用户分类为“聊天”或“业务”，也不管理整个 Turn 的 Stream 和持久化。模型进入
Agent Loop 后，通过“直接回答或选择某个 Tool”完成真正的意图判断。

| 组件 | 核心问题 | 主要职责 |
| --- | --- | --- |
| Turn Runtime | 本轮数据从哪里来、结果存到哪里 | Context 组装、消息与 Turn 状态持久化 |
| TurnOrchestrator | 本轮怎么启动、转发和结束 | 调度、Stream、异常边界、`DONE` |
| ChatPipeline | AgentLoop 启动前需要准备什么 | Prompt、messages、tools、Schema、模型与预算参数 |
| Agent Loop | 当前应该回答还是行动 | LLM 推理、Tool Calling、结果回填和收敛 |
| Tool Runtime | 被选中的工具怎么执行 | 参数解析与校验、可信参数注入、异步执行、结果封装与失败隔离 |

Agent Runtime 是覆盖回合执行、上下文、事件、工具调度和异常收尾的整体运行体系。
Agent Loop 是其中的决策循环，Tool Runtime 是其中的工具执行模块，并不是两套互不相关的系统。

面试中可以用一句话概括：

> TurnOrchestrator 管一次回合，ChatPipeline 准备一次 Agent 运行，Agent Loop 负责理解意图并
> 决定直接回答还是调用工具。

## 为什么拆成三层

拆分依据是三类不同的变化：回合生命周期、场景化运行准备、多轮执行逻辑。
不是为了凑三个类，也不是三个 Agent 或三个独立服务。

| 层次 | 负责的问题 | 典型变化 |
| --- | --- | --- |
| TurnOrchestrator | 本次执行如何启动、输出和结束 | 调整统一错误通知、结束事件和回合资源收尾 |
| ChatPipeline | 当前场景需要哪些 Prompt、工具和参数 | 调整学段讲解规则，根据知识库或附件挂载工具 |
| Agent Loop | 模型读取当前信息后，下一步如何决策 | 调整轮次限制、空响应纠正和 Forced Finish |

这样业务配置变化不必重写循环，循环策略变化也不会直接改变外层事件收尾。如果全部写进
一个函数，加载画像、拼接 Prompt、模型循环、工具执行和事件输出就会互相耦合。

### 为什么中间还需要 ChatPipeline

ChatPipeline 把具体业务场景转换成 Agent Loop 可以消费的输入。例如教材问答准备讲解
Prompt 和 RAG 工具；图片提问加入附件信息，按需挂载 OCR；业务引导准备服务说明和 Action
工具。Agent Loop 不必知道画像从哪里加载、为什么该场景允许使用 OCR，只使用准备好的
消息、工具协议和运行参数。

如果准备逻辑放进 Orchestrator，生命周期管理就会耦合具体聊天业务；如果放进 Agent Loop，
通用循环就会耦合画像、教材、附件和业务配置。准备层解决的正是这个适配问题。

分层也方便独立验证：准备层检查 Prompt、消息和工具挂载，循环层用模拟模型与工具验证
执行和退出，编排层验证正常与异常情况下的事件收尾，不必每次都调用真实模型跑完整链路。

### 面试口述

> 我们按职责和变化原因拆成三层。TurnOrchestrator 管一次用户回合的生命周期，包括启动、
> 事件转发和异常收尾；ChatPipeline 把当前场景的上下文、Prompt、工具和预算准备好；
> Agent Loop 则负责模型决策、工具结果回填和多轮收敛。这样业务配置变化不需要修改循环，
> 循环策略变化也不会影响外层事件处理，同时便于分别测试。三层不是固定标准，如果 Pipeline
> 只是简单转调，没有实际准备逻辑，就没有必要单独保留这一层。

## Agent Loop 如何实现

### 面试口述

> 我把 Agent Loop 定位为一次用户 Turn 内的受控决策执行闭环。它维护本轮消息状态，反复
> 完成模型推理、工具调用、结果回填和结束判断，直到生成最终回答或触发收敛机制。它是
> Agent Runtime 的决策核心，但不等于完整的 Agent Runtime。
>
> Loop 接收 Pipeline 准备好的初始 messages、工具 Schema、Token Budget 和最大轮次等参数，
> 内部维护模型轮次、工具步骤和用量信息。这里一次循环对应一次模型调用，不是一次用户发
> 消息；一个用户请求可能经过多轮模型调用才完成。
>
> 每轮先做上下文窗口检查，再把 messages 和可用工具交给模型。模型返回流式结果时，文本
> 可以通过事件通道持续输出，但工具参数要聚合完整后再解析执行，不能收到一小段 JSON 就
> 立刻调用工具。
>
> 模型结果聚合完成后分两条路径。如果没有 Tool Call，而且有有效文本，就把它作为最终
> 回答结束。如果有 Tool Call，先把包含工具调用声明的 assistant 消息加入 messages，再
> 交给 Tool Runtime 执行。工具返回后，按 tool_call_id 转成对应的 role=tool 消息追加回来，
> 下一轮模型读取这些观察结果，再决定继续行动还是回答。
>
> 同一批独立工具由调度层异步执行，有依赖的步骤分轮完成。普通工具失败也会转成结构化
> 结果，因此模型可以调整参数、换工具或说明无法完成的部分。Loop 负责消费结果和继续
> 决策，不需要包含每个工具具体的业务实现。
>
> 最后是退出和兜底。正常情况是没有工具调用并且输出有效答案；空响应只做有限纠正；达到
> 最大轮次后禁用工具，进行一次 Forced Finish。模型中途失败且已有成功轮次时，可以尝试
> 基于已有信息收尾；首轮就失败则交给外层统一处理。收尾也失败时返回明确的兜底信息，而
> 不是伪造任务完成。Loop 返回结果后，TurnOrchestrator 再统一发送结束通知并关闭事件流。

### 核心数据和状态

| 内容 | 作用 |
| --- | --- |
| messages | 本回合工作上下文，包括初始消息、assistant 工具调用声明和工具观察 |
| tool_schemas | 当前模型可以选择的工具协议，不是工具实现代码 |
| round_index / max_rounds | 当前探索轮次与正常循环上限，防止无限追加探索轮次 |
| rounds / tool_steps | 成功完成的模型调用轮数与发生工具分发的轮数，不能混成工具调用总数 |
| usage / trace | 用量统计，以及 Turn、模型调用和 Tool Call 的关联信息 |
| outcome | 最终文本和退出状态；不能只用“返回了一段文字”判断业务是否成功 |

初始上下文由 Pipeline 准备；运行中新增工具结果由 Loop 回填。对话历史持久化由外层负责，
Loop 的内存 messages 不等于数据库中的历史消息表，工具自身的业务写入则属于对应服务。

### 核心循环示意

以下是用于白板讲解的伪代码，不是可直接运行的源码。省略流式聚合、Trace、用量统计、
暂停恢复和工具主动终止等细节；call_llm 返回的是聚合完整的本轮结果。

```python
async def run_loop(messages, tools, max_rounds):
    successful_rounds = 0
    nudged_empty = False

    for round_index in range(max_rounds):
        guard_context_window(messages)

        try:
            result = await call_llm(messages, tools=tools)
        except Exception:
            if successful_rounds == 0:
                raise
            return await forced_finish_without_tools(messages)

        successful_rounds += 1

        if result.tool_calls:
            messages.append(assistant_message_with_calls(result))
            dispatch = await tool_runtime.dispatch(result.tool_calls)
            messages.extend(dispatch.tool_messages)
            continue

        final_text = clean_visible_text(result.text)
        if final_text:
            return final_text

        if not nudged_empty:
            nudged_empty = True
            append_empty_response_correction(messages, result)
            continue

        return fallback_response()

    return await forced_finish_without_tools(messages)
```

forced_finish_without_tools 会补充停止探索的指令，不允许继续调用工具，再尝试一次模型
回答；这次调用失败或为空则使用兜底文本。它不是提前准备好的正确答案，也不能替代工具
超时和任务取消。普通工具错误由 Tool Runtime 转成结果；取消信号不能当作可重试的普通
业务错误吞掉。

### 白板上要讲清的协议配对

```text
初始：system + 历史消息 + user

第 1 次模型调用：assistant(tool_calls=[call_1])
执行工具后：     tool(tool_call_id=call_1, content=检索结果)

第 2 次模型调用：读取上述全部消息，继续调用工具或直接回答
```

不能只追加工具结果而遗漏 assistant 的调用声明。每个已记录的 Tool Call 都需要对应结果，
失败、去重或拒绝执行也应保持协议配对，不能直接丢掉导致下一轮消息不完整。

例如用户说“结合我最近的词汇量检测结果给出学习建议”，第一轮模型发现当前上下文没有检测
结果，可以调用学习记录查询工具；结果回填后，第二轮再根据需要调用 RAG 查询对应年级的
学习材料；证据充分后生成个性化建议，也可以通过 Action Tool 返回词汇学习入口。这里的
“多轮”是同一用户请求内的模型 Round，不要求用户反复发送消息，也不表示 Agent Loop 要
等待用户在跳转页面完成整场测评。

### 如果面试官问：“不就是一个 while 循环吗？”

> 代码结构确实可以用 `for` 或 `while` 实现，但 Agent Loop 的重点不是循环语法，而是循环中
> 的运行时协议，包括消息状态管理、Tool Call 与 Tool Result 配对、并行工具调度、异常隔离、
> 上下文控制、退出条件、Forced Finish 和链路追踪。只有循环而没有这些机制，很容易出现
> 无限调用、消息协议不完整，或者单个工具异常导致整个 Turn 无响应。

### 一个 Turn 是否有一个 messages

在这里的单主 Agent 链路中，每个 Turn 的主 Agent Loop 都会构造自己的 messages 工作列表。
同一 Turn 内各轮模型调用使用这份持续更新的上下文；下一条用户消息进入时，会从会话历史、
相关记忆和新问题重新构造新的列表，不是整个 Session 永久共用一个全局 Python list。

```text
Session
  Turn 1：messages_1 -> 模型 Round 1 -> 工具回填 -> 模型 Round 2 -> 返回结果
  Turn 2：历史问答 + 新问题 -> messages_2 -> 新的 Agent Loop
```

列表可以包含之前 Turn 的历史问答，因此“属于当前 Turn 的工作列表”不等于“只含本轮
新产生的数据”。运行中也可以裁剪或压缩，不要求永远只增不减。如果以后加入 Subagent，
子任务还会有自己的消息状态，不能理解成整个 Turn 下所有 Agent 共用同一份列表。

### 工具调用声明具体怎样追加

下面仅展示消息协议，省略历史和 RAG 的其他参数。模型结果聚合完成后，由服务端把工具
调用请求整理成 assistant 消息，再通过普通的 list 操作追加：

```python
messages = [
    {"role": "system", "content": "你是学习助手。"},
    {"role": "user", "content": "根据教材讲一下同分母分数加法。"},
]

# 模型表示要调用工具，还不代表工具已经执行。
messages.append({
    "role": "assistant",
    "content": "我先检索相关教材。",
    "tool_calls": [{
        "id": "call_rag_01",
        "type": "function",
        "function": {
            "name": "rag",
            "arguments": '{"query": "同分母分数加法"}',
        },
    }],
})

# 工具执行完成后追加观察结果，多条结果用 extend。
tool_messages = [{
    "role": "tool",
    "tool_call_id": "call_rag_01",
    "content": "同分母分数相加，分母不变，分子相加。",
}]
messages.extend(tool_messages)
```

现在列表包含 system、user、assistant 工具调用声明和 tool 结果四条消息。下一次模型请求
提交当前整理后的消息上下文，而不是只发送最后一条工具结果。若同轮有多个 Tool Call，
通常是一个 assistant 消息中的 tool_calls 数组包含多个请求，再跟多条按 ID 配对的 tool 消息。

tool_schemas 是“当前可以调用哪些工具”的定义，tool_calls 是“模型这一次请求调用什么”的
具体声明，两者不要混淆。最终回答可以由 Loop 直接返回给外层保存，不要求先追加到这个
工作列表才算完成。

### append 会不会自动入库

不会。append 和 extend 只修改当前进程的内存列表，不会自动执行 SQL。持久化需要外层
明确调用存储服务；采用“会话消息 + 执行事件”的方案时，两类数据分开处理：

| 数据 | 保存方式 | 下一 Turn 是否直接作为历史使用 |
| --- | --- | --- |
| 用户问题、最终 assistant 回答 | 保存为会话消息 | 可经历史选择和摘要后使用 |
| assistant 工具调用声明、Tool Result | 作为工具调用和结果事件保存，便于回放与排查 | 不默认把全部事件原文重新注入模型 |
| 本轮 Python messages 对象 | 不因 append 自动整表或整对象入库 | 新 Turn 重新构造工作上下文 |
| 工具创建的测评任务、报告等业务对象 | 由对应业务服务持久化 | 根据业务引用或查询按需使用 |

如果需要多 Worker 故障恢复，可以把 Redis 放在内存工作状态和长期存储之间：Loop 仍然对
本地 messages 做 append；只在一批工具全部返回、assistant Tool Call 与 `role=tool` 已完整
配对，或者 `ask_user` 暂停等稳定边界写入 Turn checkpoint。checkpoint 可包含 `turn_id`、
版本号、当前轮次、messages 和过期时间；Turn 完成后将最终消息落长期存储，再删除 Redis key
或等待 TTL。不要每次 append 都覆写整份上下文，也不要把 Redis 当成长期会话的唯一事实库。

作为上述存储边界的实现参考，学习仓库将工具事件保存在 assistant 的 events_json 及
turn_events 中，不是逐条存成独立的 role=tool 历史消息；下一回合历史构造读取消息正文，
不会自动回填这些工具事件。事件持久化也不等于已经晋升为 L3 用户画像。

参考位置：[追加调用与结果](C:/file/ownWork/DeepTutor/deeptutor/agents/chat/agent_loop.py:353)、
[外层保存 assistant 与事件](C:/file/ownWork/DeepTutor/deeptutor/services/session/turn_runtime.py:1661)、
[历史正文读取](C:/file/ownWork/DeepTutor/deeptutor/services/session/sqlite_store.py:1218)。

**面试一句话：**

> 每个 Turn 的主 Agent Loop 都有一份运行中的 messages。模型返回工具请求后，我们先追加
> assistant 的调用声明，工具执行完再追加按 call_id 配对的结果，供下一轮模型读取。
> 这些操作只是内存更新；外层另外保存用户问答和工具执行事件，下一 Turn 再根据历史
> 重新构造上下文，不会把所有中间工具原文永久堆进 Prompt。

### 容易被继续追问的边界

1. Agent Loop 不负责直接操作 WebSocket，运行事件交给统一 Stream 和外层转发。
2. 流式请求结束只表示一次模型调用结束，不代表整个 Agent Loop 已完成。
3. 模型轮次数、工具批次数、工具调用总数分别统计；Forced Finish 是正常轮次预算之外的额外调用。
4. 批内去重不是跨轮业务幂等，工具重试也不能导致任务重复创建或结果重复回写。
5. 轮次限制不等于总超时；网络与工具等待需要独立的超时、取消和资源清理机制。
6. 若支持 ask_user，可以在原 Turn 内暂停并把用户补充作为观察继续；正式测评的页面跳转
   则交给独立业务任务，不能把两种等待混为一谈。

## Tool Runtime 与工具调度如何实现

### 简历推荐表述

> **工具调度：** 基于 Tool Registry 与统一 Tool Dispatcher，实现工具发现、可信参数注入、
> 批内异步调度及重复调用控制；通过 ToolResult 标准化结果并按 `tool_call_id` 回填，单工具
> 异常不阻断同批任务。

这里不要说成“通过 Tool Registry 和 ToolResult 实现所有调度能力”。三者职责不同：

| 组件 | 职责 |
| --- | --- |
| Tool Registry | 注册工具，按名称找到实现，并向模型提供 Tool Schema |
| Tool Dispatcher | 参数解析、可信参数注入、批内去重、并发执行和结果聚合 |
| ToolResult | 统一表达成功、失败、正文、来源和结构化元数据 |

### 面试口述

> 模型返回 Tool Call 后，里面只有工具名称、调用 ID 和模型生成的参数。Dispatcher 先解析
> 参数，再通过 Tool Registry 根据名称找到具体工具。执行前会注入真实的 `user_id`、
> `session_id`、`turn_id`、权限和工作目录等服务端可信参数；这些字段不由模型决定，避免
> 模型伪造身份或操作其他用户的数据。
>
> 对同一批没有依赖关系的工具，我们先按照“工具名称加规范化参数”识别重复调用，再使用
> `asyncio.gather()` 并发执行。它不是依次 `await tool1()`、再 `await tool2()`；而是同时
> 启动多个 I/O 协程，再等待这一批结果聚合。有依赖关系的调用不强行并发，而是结果回填后
> 交给下一轮模型继续决策。
>
> 每个工具调用外层都有独立的异常捕获，成功和失败都转换为统一结果。失败调用也会生成与
> 原 `tool_call_id` 配对的 `role=tool` 消息，因此不会破坏下一轮模型的消息协议；同批其他
> 工具仍然能够返回。Agent Loop 拿到结果后，再让模型选择降级回答、调整参数或更换工具，
> 但这只提供继续处理的机会，不承诺模型一定能够自动恢复。

### 业务示例

用户要求结合最近测评结果和教材内容给出建议时，模型可以在同一批调用学习记录查询和 RAG。
Runtime 注入当前用户身份并并发执行。假设 RAG 成功、学习记录查询超时，RAG 结果仍正常
回填，超时也被转换成失败 Tool Result。下一轮模型可以先根据教材给出通用建议，同时说明
暂时没有取得测评结果，而不是让整个 Turn 直接报错。

### 容易被追问的边界

1. `asyncio.gather()` 本身不会自动隔离异常；关键是每个工具协程内部先捕获普通异常并返回
   失败结果。超时、进程取消和资源清理还需要单独处理。
2. AsyncIO 主要改善外部接口、数据库和检索等 I/O 型任务；CPU 密集或阻塞型工具需要线程池、
   进程池或独立服务，否则会阻塞事件循环。
3. 当前所说的去重是同一模型响应内的批内去重，不等于跨轮业务幂等。创建任务或数据回写
   仍需幂等键、唯一约束或状态机保护。
4. 去重后的调用也应返回占位结果并保留 `tool_call_id`，不能直接删除模型已经声明的 Tool
   Call，否则下一轮消息会出现调用与结果不配对。

## 3 分钟版本

鼎校伴学面向鼎校甄选用户，既支持直接对话，也连接约 7 类学习服务。我参与 Agent Runtime
建设，主要解决模型决定下一步做什么之后，系统如何可靠执行、获取结果，并控制执行范围。

比如用户要求根据教材出题，模型可能先检索教材，再查询题库，最后生成讲解。这不是一次模型
调用就能完成的，中间还可能出现工具失败、重复调用和上下文增长。因此我们把共性逻辑抽成
统一 Runtime，我主要参与执行闭环、工具调度，以及异常隔离和任务收敛。

首先是执行闭环。上层通过 UnifiedContext 统一当前问题、近期对话、用户画像和知识库选择。
TurnOrchestrator 管理本轮的启动、事件转发和异常收尾，ChatPipeline 准备 Prompt、工具
Schema 和运行参数，然后进入 Agent Loop。

Loop 维护当前回合的消息列表。模型可以直接回答，也可以返回工具名称和参数。Runtime 执行
工具后，把结果按 tool_call_id 配对成 role=tool 消息，再交给下一轮模型。模型根据结果继续
行动或输出答案，而不是预先写死所有步骤。

第二是工具执行。Tool Runtime 是 Agent Runtime 中负责动作执行的模块，通过 Tool Registry
查找实现，解析参数，注入用户和 Session 等可信信息，统一返回 ToolResult。独立工具可以
异步并发，有依赖的步骤分轮完成。普通工具异常会转换成错误结果，不直接打断同批其他工具，
模型可以调整参数、换用其他工具，或者说明无法完成的部分。

第三是任务收敛和观测。通过最大轮次控制模型持续探索，对批内同名同参数调用去重，并裁剪
较早的大段工具结果。达到轮次上限后，通过 Forced Finish 禁用工具，让模型基于已有信息
回答。Trace 关联模型轮次和工具调用，便于定位异常；外层统一结束本轮事件流。

业务上，用户说“我想检测词汇量”，模型通过受控 Action Tool 返回服务入口，前端展示按钮。
这个 Turn 完成的是需求理解和入口引导，真正的测评由业务服务执行，Loop 不需要一直等待。
这套 Runtime 让知识检索和业务入口共享执行、异常处理与观测机制。我也参与了词汇量检测、
英语三合一和试卷学情分析本身的设计开发，不只是完成入口对接。

## 5 分钟版本

鼎校伴学面向鼎校甄选用户，既支持直接对话，也连接词汇量检测、英语三合一、试卷学情分析等
约 7 类学习服务。我参与 Agent Runtime 建设，主要解决的是：模型决定下一步做什么之后，
系统如何可靠地执行、获取结果，并在有限的执行范围内完成响应。

这里不是简单调用一次模型接口。比如用户要求根据教材出题，模型可能需要先检索教材，再
查询题库，最后根据结果生成讲解。过程中既有多轮决策，也可能发生工具失败、上下文增长和
重复调用。因此我们把这些共性的执行逻辑抽成统一 Runtime。我主要参与执行闭环、工具调度，
以及异常隔离和任务收敛这几部分。

首先是执行闭环。请求进入后，上层把当前问题、近期对话、用户画像和知识库选择整理成
`UnifiedContext`。`TurnOrchestrator` 负责本轮执行的启动、事件转发和异常收尾，
`ChatPipeline` 负责准备 Prompt、工具 Schema 和运行参数，然后进入 Agent Loop。

Loop 内部维护当前回合的消息列表。模型可以直接回答，也可以返回工具名称和参数。如果有
Tool Call，Runtime 就执行对应工具，将结果按 `tool_call_id` 配对成 `role=tool` 消息，
再交给下一轮模型。模型根据观察结果决定继续调用工具还是输出答案，形成“模型决策、工具
执行、结果回填、继续决策”的闭环，而不是预先写死所有步骤。

第二是工具执行。我们把工具运行职责集中到 Tool Runtime，它是 Agent Runtime 中负责动作
执行的模块。模型看到的是工具描述和参数协议，真正的工具实现留在服务端。Runtime 通过
Tool Registry 找到实现，解析参数，注入用户和 Session 等可信信息，再执行并统一封装
ToolResult。

同一批中独立的工具可以异步并发，有依赖的步骤通过多轮调用完成。普通工具异常会被捕获并
转换成错误结果，同批其他工具仍然可以完成。下一轮模型看到错误后，可以调整参数、换用
其他工具，或者说明当前无法完成的部分。这里的重点是故障隔离和结果可处理，而不是承诺
所有失败都能自动恢复。

第三是任务收敛和观测。我们通过最大轮次限制模型持续探索，对批内相同工具、相同参数的
请求去重，并裁剪较早的大段工具结果，控制上下文增长。达到轮次上限后，通过 Forced Finish
禁用工具，要求模型基于已有信息给出回答。外层统一处理未捕获异常，并结束本轮事件流；
Trace 则关联模型轮次和工具调用，帮助定位问题发生在决策、工具执行还是结果处理环节。

业务上，比如用户说“我想检测一下词汇量”，模型调用受控 Action Tool，后端返回对应服务
入口，前端展示“开始检测”按钮。这个 Turn 完成的是需求理解和入口引导，真正的测评由业务
服务执行，并不需要 Agent Loop 一直等待用户做完测评。

这套 Runtime 的价值，是把对话中的动态决策和后端确定性执行分开，让知识检索、业务入口和
后续新增工具共享同一套执行、异常处理与观测机制。同时，我也参与了词汇量检测、英语三合一
和试卷学情分析本身的设计开发，不只是完成入口对接。

## 速记主线

> 为什么需要多轮执行 -> 模型与工具闭环 -> 工具失败隔离 -> 收敛与 Trace ->
> 对话和服务入口复用 -> 个人参与的 3 类业务。

## 面试表达边界

1. **不要再使用 Capability 路由口径。** 当前只有 Web Chat 主链，TurnOrchestrator 只管理
   调度、Stream、异常和结束状态。
2. **不要说 ChatPipeline 做 LLM 意图识别。** Pipeline 只做确定性的 Prompt、消息、工具和
   参数准备；真正判断发生在 Agent Loop。
3. **Action 也走 Tool 协议。** 模型调用 Action Tool，后端映射白名单页面与可信参数，不让
   模型自由构造 URL。
4. **出题按交付形态选择工具。** 会话内动态出题调用教材、知识点或题库 Tool；进入正式测评
   调用 Action Tool。
5. **消息持久化和长期记忆不是一回事。** Session 先保存用户可见消息和结构化结果；记忆/画像
   再异步抽取和归并。
6. **Agent Runtime 不等于 Agent Loop。** Loop 是其中的决策循环，Tool Runtime 是工具
   执行模块；整体 Runtime 还包括上下文、事件、异常和收尾。
7. **轮次限制不等于超时控制。** 它限制模型探索次数；工具一直不返回，需要单独的超时和
   取消机制，不能靠 Forced Finish 解决。Forced Finish 也不保证答案正确或业务一定完成。
8. **DONE 不等于业务成功。** 它表示本轮事件流结束；返回测评入口不代表测评已经完成，
   Agent Loop 不需要跨越整段用户做题流程保持等待。
9. **失败隔离不等于自动恢复。** 错误回填后，模型仍可能无法解决问题；只能说明它有机会
   调整参数、选择其他工具或明确告知限制，不承诺任意工具都能安全重试。
10. 团队架构使用“我们建设”，个人职责使用“我主要参与”；入口连接约 7 类服务，个人
    重点参与词汇量检测、英语三合一和试卷学情分析，不要把团队成果全部说成个人独立完成。
