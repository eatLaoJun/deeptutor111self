# 鼎校伴学 Agent Runtime 面试口述稿

> 对应简历第一条职责：参与 Agent Runtime 核心能力建设。
>
> 本文以简历中的鼎校伴学项目口径为主，不把当前学习仓库的多 Capability 实现硬套进来。
> 当前只有一条 Web Chat 执行链，不设置独立 Capability 路由，也不在 Agent Loop 前额外调用
> 一次 LLM 做意图分类。

## 先统一执行主线

```text
用户消息
  -> Turn Runtime 补齐会话数据
  -> UnifiedContext
  -> TurnOrchestrator（调度与回合生命周期）
  -> ChatPipeline（组装 Prompt、工具和运行参数）
  -> Agent Loop
       -> 无 Tool Call：直接回答
       -> Action Tool：生成受控的业务跳转按钮
       -> RAG / 题库等 Tool：结果回填后继续推理
  -> 统一输出
  -> Session 消息与 Trace 持久化
  -> 学习任务结果回写，异步更新长期记忆和用户画像
```

这里没有单独的“意图识别阶段”。LLM 在 Agent Loop 的第一轮中同时理解需求并选择下一步：
能回答就直接回答，需要业务入口就调用 Action Tool，需要教材、题库或 OCR 就调用对应工具。
因此意图判断与 Agent 决策只发生一次。

## TurnOrchestrator 与 ChatPipeline 的职责

### TurnOrchestrator：管理一次回合怎么运行和结束

`TurnOrchestrator` 接收已经组装好的 `UnifiedContext`，创建本轮流式通道，启动
`ChatPipeline`，转发执行事件，并把未处理异常转换成统一错误事件。无论成功还是失败，它
都要发送 `DONE`、关闭本轮 Stream，并发布回合完成信号。

它不读取业务字段来判断用户意图，不组装 Prompt，不调用模型或工具，也不直接保存消息。
消息加载与落库属于 Turn Runtime，推理和工具选择属于 Agent Loop。

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

面试中可以用一句话概括：

> TurnOrchestrator 管一次回合，ChatPipeline 准备一次 Agent 运行，Agent Loop 负责理解意图并
> 决定直接回答还是调用工具。

## 3 分钟版本

我先按一条用户消息的完整执行链路来讲这套 Agent Runtime。

用户消息进入后不会直接交给模型。Turn Runtime 先根据 Session 补齐近期对话、用户画像、
知识库、附件和本轮配置，组装成 `UnifiedContext`，也就是本回合的执行快照。随后交给
`TurnOrchestrator`。它只负责调度和本轮执行生命周期：创建流式通道、启动
`ChatPipeline`、转发事件、统一处理异常，并确保最终发送 `DONE`。

`ChatPipeline` 不做额外的 LLM 意图分类，而是确定性地根据 `UnifiedContext` 组装 System
Prompt、历史消息和当前问题，挂载 RAG、题库、OCR、Action 等本轮工具，生成 Tool Schema
和运行参数，然后创建 Agent Loop。

真正的意图判断发生在 Agent Loop 第一轮。模型没有返回 Tool Call 时，当前文本就是普通问答
的最终回答；需要正式词汇量测评时，模型调用受控的 Action Tool，由后端映射业务编码和页面，
前端展示“开始测评”按钮；用户要求根据教材出题时，模型调用教材 RAG、知识点或题库工具，
工具结果以 `role=tool` 回填后继续生成题目。这样不需要前置分类模型，模型选择哪个工具本身
就是意图识别结果。

Tool Runtime 根据 Tool Registry 找到实现，完成参数校验和用户、Session 等可信参数注入，
再异步执行。结果统一封装成 `ToolResult`；单工具失败也会结构化回填，不直接让整个任务
崩溃，由此形成“模型推理—工具调用—结果回填—继续决策”的闭环。

循环结束后，输出层把文本、题目卡片、引用或 Action 统一返回前端。消息存储不放在 Loop
内部：Turn 开始时记录用户消息和执行状态，结束后保存 assistant 消息及结构化元数据；模型
轮次、工具耗时和异常写入 Trace。学习任务完成后，结果再回写 Session，并异步更新长期记忆
和用户画像，供下一轮 Context 使用。

最后，我们通过最大轮次、重复调用检测、上下文裁剪和 Forced Finish 保证任务有界结束。
这套链路复用到问答、测评、讲解和学情分析等约 7 类学习服务：开放式任务走 Agent Loop，
确定性业务通过 Action Tool 接入。

## 5 分钟版本

我按一条消息从进入系统到最后落库的顺序介绍这套 Agent Runtime。主链路是：
`UnifiedContext -> TurnOrchestrator -> ChatPipeline -> Agent Loop -> 输出与持久化
-> 业务结果回流`。

第一步是上下文组装。用户发送消息后，Turn Runtime 确认 Session，读取近期对话、相关用户
画像、教材或知识库、附件和本轮配置，统一整理成 `UnifiedContext`。这样执行层不需要理解
WebSocket、HTTP 或具体页面参数，每个业务也不必重复定义输入结构。`UnifiedContext` 只是
本回合的组合视图；会话原文仍在 Session Store，Tool Result 则由 Agent Loop 在运行时追加
到模型消息，并不是预先永久塞进 Context。

第二步是回合编排。Context 交给 `TurnOrchestrator` 后，它创建本轮 Stream，启动
`ChatPipeline` 并转发执行事件；出现未处理异常时统一转换为错误事件，最后保证发送
`DONE` 和关闭 Stream。它不读取业务字段、不组装 Prompt，也不参与模型推理。

第三步是 Chat Agent 的运行准备。`ChatPipeline` 读取 `UnifiedContext`，组装 System
Prompt、历史消息和当前问题，根据知识库、附件和业务权限挂载教材 RAG、知识点、题库、OCR
以及 Action Tool，生成 Tool Schema，并设置模型参数、Token 预算和最大轮次。整个过程是
确定性的，不会为了“识别意图”额外调用一次 LLM。Pipeline 准备完成后创建 Agent Loop。

第四步是 Agent Loop。模型在第一轮同时理解需求并决定下一步，不需要单独的分类阶段：
没有 Tool Call 时，当前文本就是普通问答；需要检索、出题或 OCR 时，选择对应 Tool；需要
进入已有业务流程时，调用 Action Tool。因此模型的 Tool Selection 本身就是意图识别结果。

例如用户说“帮我检查一下词汇量”，模型调用 `present_business_action`，只提交受 Schema
约束的业务编码和必要参数。后端通过 Action Registry 映射已注册页面并注入用户、Session，
前端展示“开始测评”按钮；模型不能自由拼 URL，也不会在聊天里伪造测评结果。如果用户说
“根据六年级上册第三单元给我出 5 道题并在这里讲答案”，模型则调用教材 RAG、知识点或题库
工具，拿到结果后继续生成题目。

工具执行后统一返回 `ToolResult`，成功结果和结构化错误都以 `role=tool` 追加到消息列表，
模型再决定继续调用、修改参数重试还是结束。同一轮独立工具通过 AsyncIO 并发执行，有依赖的
步骤分轮完成；单工具异常只影响对应结果，不直接打断整个 Loop。这就形成“模型推理—工具
调用—结果回填—继续决策”的闭环。

为了让循环可控，我们设置最大轮次、重复调用检测、Token 预算和上下文裁剪。达到上限时，
Forced Finish 会关闭工具调用，让模型基于已有证据给出 best-effort 回答。Trace 会关联
Session、Turn、模型轮次和 Tool Call，记录脱敏参数、状态、耗时与异常，帮助判断问题发生在
模型决策、工具执行还是循环收敛。

最后是输出和持久化。Agent Loop 只负责产生结果，不直接写数据库。Turn Runtime 在开始时
保存用户消息和 running 状态，执行中把文本、题目卡片、引用或 Action 流式返回前端，完成后
保存 assistant 内容及结构化元数据，并将 Turn 标记为 completed。Trace 与用户可见消息分开
保存，避免内部工具观察污染后续对话。

用户通过 Action 完成单词测评、英语三合一或试卷学情分析后，业务结果还会回写 Session，
并异步更新长期记忆和用户画像。下一轮 `UnifiedContext` 再读取相关结果，形成“对话理解—
任务执行—结果回流—后续个性化”的闭环。

这套 Runtime 接入了问答、测评、讲解和学情分析等约 7 类学习服务。核心价值不是把所有业务
都改造成 Agent，而是由同一个 Agent Loop 通过 Tool Selection 完成任务判断，让开放式任务
调用知识工具，让确定性流程通过 Action Tool 接入，同时统一
上下文、工具协议、收敛、观测和消息持久化。

## 速记主线

> 统一输入 -> TurnOrchestrator 管回合 -> ChatPipeline 准备 Prompt 和 Tools -> Agent Loop
> 通过直接回答或 Tool Selection 完成意图判断 -> 统一输出与持久化 -> 业务结果回写。

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
6. **Forced Finish 只保证有界结束和尽量给出结果，**不代表答案一定正确。
7. 团队架构使用“我们建设”，个人职责使用“我主要参与”，不要把团队成果全部说成个人独立完成。
