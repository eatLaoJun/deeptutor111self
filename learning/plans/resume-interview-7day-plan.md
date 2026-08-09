# DeepTutor 简历项目一周面试准备计划

> 目标：用 7 天把简历中的“极光智能学习机”从“看过代码”练到“能脱稿讲、能承受追问、能指出代码证据”，下周开始投递。
>
> 当前起点：默认 Chat 主链已经过完第一遍，但口述不够流畅；Tool、稳定性、Skill、ask_user、Memory 仍需系统准备。
>
> 每日建议投入：3 小时。时间不足时优先完成“闭卷输出”和“当日验收”，减少继续浏览代码的时间。

## 0. 一周完成标准

投递前至少达到以下标准：

- [ ] 能用 30 秒、90 秒、3 分钟三个版本介绍项目。
- [ ] 能闭卷画出默认 Chat 主链，并说明每个节点的输入、输出和职责。
- [ ] 简历 5 条责任描述，每条都有“业务问题、设计方案、调用链、异常处理、代码证据、个人贡献”。
- [ ] 至少准备 2 个真实难点故事，能按 STAR 结构讲清楚。
- [ ] 能回答本计划中的核心追问，答案不是背概念，而是能落到 DeepTutor 的具体实现。
- [ ] 完成一次 45 分钟模拟面试和一次压力追问。
- [ ] 审核简历措辞，只保留自己确实做过、改过并能解释的内容。

## 1. 每天固定训练模板（180 分钟）

1. **20 分钟：闭卷复习**
   - 不看代码画昨天的调用链。
   - 用 90 秒复述昨天主题。
2. **60 分钟：带问题读代码**
   - 只围绕当天责任描述阅读指定文件。
   - 每个文件只回答：接收什么、处理什么、交给谁。
3. **30 分钟：形成一张图**
   - 图中必须有关键对象、数据形态和异常分支。
4. **30 分钟：回答面试追问**
   - 每题先闭卷回答，再回代码纠错。
5. **25 分钟：录音复述**
   - 录制 90 秒和 3 分钟两个版本。
6. **15 分钟：复盘**
   - 只记录三个问题：哪里卡顿、哪里不准确、明天先复习什么。

每天的笔记放到：

```text
learning/notes/day1-agent-main-chain.md
learning/notes/day2-tool-dispatch.md
learning/notes/day3-runtime-stability.md
learning/notes/day4-skill-ask-user.md
learning/notes/day5-memory.md
learning/notes/day6-project-story.md
learning/notes/day7-mock-interview.md
```

---

## Day 1：把责任描述 1 练到能脱稿

### 对应简历

> 设计并实现 Agent 多轮对话核心链路，完成会话上下文组装、Capability 路由、LLM 多轮调用、Tool 执行及流式事件输出。

### 今天只解决的问题

一条用户消息进入系统后，如何变成上下文、选择 Capability、进入 AgentLoop、调用工具并流式返回？

### 阅读路径

```text
deeptutor/core/context.py
deeptutor/runtime/orchestrator.py
deeptutor/agents/chat/capability.py
deeptutor/agents/chat/agentic_pipeline.py
deeptutor/agents/chat/agent_loop.py
deeptutor/core/stream_bus.py
```

第一遍只定位这些对象或函数：

```text
UnifiedContext
ChatOrchestrator.handle()
ChatCapability.run()
AgenticChatPipeline.run()
_build_loop_messages()
AgentLoop.run()
AgentLoop._run_loop()
AgentLoop._call_llm()
```

### 必须能画出的主链

```text
WebSocket / CLI / SDK
        -> UnifiedContext
        -> ChatOrchestrator
        -> CapabilityRegistry
        -> ChatCapability
        -> AgenticChatPipeline
        -> AgentLoop
        -> LLM
             无 tool_calls -> 最终回答
             有 tool_calls -> 工具执行 -> role=tool 回填 -> 下一轮 LLM
        -> StreamBus
        -> 调用方
```

### 当天追问

1. 为什么需要 `UnifiedContext`，直接把 HTTP Request 传下去不行吗？
2. Tool 和 Capability 的职责有什么区别？
3. 默认 Chat 为什么是一个不断增长的 `messages` 单循环？
4. 模型没有返回 `tool_calls` 时，系统如何判断结束？
5. StreamBus 为什么要显式发送 DONE 后再 close？
6. StreamBus 和项目级 EventBus 有什么区别？
7. Provider 不支持原生 Tool Calling 时如何降级？

### 当日产出与验收

- [ ] 一张闭卷主链图。
- [ ] 30 秒、90 秒、3 分钟口述各一版。
- [ ] 能指出上述 8 个关键函数所在文件。
- [ ] 随机抽 5 个追问，至少 4 个能在 90 秒内回答清楚。

---

## Day 2：责任描述 3——Tool 注册、Schema、执行与回填

### 对应简历

> 构建 Tool 注册与调度体系，实现 Function Schema 转换、Tool Calling、并行工具执行、`role=tool` 结果回填、异常处理及重复调用去重。

### 今天只解决的问题

Python 工具是怎样注册到服务端、怎样变成模型看得懂的 Schema、又怎样从模型的 tool call 回到真正的 Python 执行？

### 阅读路径

```text
deeptutor/core/tool_protocol.py
deeptutor/runtime/registry/tool_registry.py
deeptutor/agents/_shared/tool_composition.py
deeptutor/core/agentic/tool_dispatch.py
deeptutor/tools/builtin/__init__.py
deeptutor/tools/brainstorm.py
tests/agents/chat/test_agent_loop.py
tests/core/agentic/test_tool_dispatch_events.py
```

### 必须能画出的闭环

```text
BaseTool / ToolDefinition
  -> ToolRegistry 注册实例
  -> 当前回合筛选 enabled_tools
  -> ToolDefinition.to_openai_schema()
  -> LLM 返回 tool_calls
  -> dispatch_tool_calls()
  -> asyncio.gather() 并行执行
  -> ToolResult
  -> role=tool + tool_call_id
  -> 下一轮 LLM
```

### 当天追问

1. 模型看到的是 Python 函数还是 JSON Schema？
2. `enabled_tools` 和 `tool_schemas` 有什么区别？
3. 为什么工具结果必须携带原来的 `tool_call_id`？
4. 多个工具为什么可以并行，结果顺序如何保持协议对应？
5. 某个工具异常时为什么不直接让 AgentLoop 失败？
6. 相同工具和相同参数为什么要去重？去重后如何保持 call/result 配对？
7. 模型传入的参数和服务端注入参数如何隔离？
8. `brainstorm` 为什么会出现“外层 Chat LLM + 内层工具 LLM”两类模型调用？

### 当日产出与验收

- [ ] 一张 Tool 完整闭环图。
- [ ] 以 `brainstorm` 为例，脱稿讲清一次真实工具调用。
- [ ] 手写一个简化的 `ToolDefinition -> OpenAI Schema` 示例。
- [ ] 能解释异常、并行、去重三个分支。

---

## Day 3：责任描述 5——稳定性、上下文和可观测性

### 对应简历

> 完善 Agent Runtime 稳定性与上下文管理，通过 Context Checkpoint、最大轮次限制、Forced Finish、Tool 异常降级及 TRACE 日志等机制，提高长任务执行的稳定性和可观测性。

### 今天只解决的问题

Agent 为什么不会无限调用工具、工具失败后为什么还能回答、上下文过长时如何继续、排障时能看到什么？

### 阅读路径

```text
deeptutor/agents/chat/agent_loop.py
deeptutor/core/agentic/tool_dispatch.py
deeptutor/core/agentic/usage.py
data/user/settings/agents.yaml
tests/agents/chat/test_agent_loop.py
```

重点函数：

```text
AgentLoop._run_loop()
AgentLoop._forced_finish()
AgentLoop._guard_context_window()
AgentLoop._fold_context_checkpoint()
execute_tool_call()
```

### 必须掌握的 5 个失败场景

1. 达到最大轮次：禁用工具，额外调用一次 LLM 强制收尾。
2. 中途 LLM 失败：已有材料时尝试 Forced Finish；首轮失败则向上抛错。
3. Tool 执行失败：转换成失败的 `role=tool` 结果，让模型决定重试或降级回答。
4. 上下文逼近窗口：优先裁剪早期工具结果；Checkpoint 则用语义摘要折叠工具过程。
5. 最终回答仍为空：使用本地化 fallback，保证回合有明确结果。

### 当天追问

1. 最大轮数限制的是什么？Forced Finish 是否算额外一轮？
2. Forced Finish 为什么必须禁用工具 Schema？
3. Context Checkpoint 和普通窗口裁剪有什么区别？
4. Checkpoint 为什么不能删除初始 system、历史和当前用户消息？
5. TRACE 日志怎样避免泄露 Token、Cookie、API Key？
6. `rounds`、`tool_steps`、工具调用总数为什么不是同一个指标？
7. Provider 不返回 Usage 时如何估算 Token？

### 当日产出与验收

- [ ] 一张“正常结束 + 五类异常结束”状态图。
- [ ] 准备一个“长任务为什么需要 Forced Finish”的设计取舍回答。
- [ ] 能用 3 分钟解释 Checkpoint、窗口裁剪和最大轮次三者的边界。
- [ ] 从测试中找出至少 3 个对应场景，并说明它们验证了什么。

---

## Day 4：责任描述 4——Skill 按需加载与 ask_user 暂停恢复

### 对应简历

> 设计 Skill 动态加载机制，仅向模型注入 Skill Manifest，在任务匹配时按需加载完整 `SKILL.md`；同时支持 `ask_user` 暂停/恢复机制，完善 Agent 与用户的多轮交互能力。

### 今天只解决的两个问题

1. 为什么 Skill 先注入 Manifest、命中任务后才读取全文？
2. `ask_user` 为什么能暂停并恢复同一个 Agent 回合，而不是开启新回合？

### Skill 阅读路径

```text
deeptutor/services/skill/service.py
deeptutor/services/session/turn_runtime.py
deeptutor/agents/chat/prompt_blocks.py
deeptutor/agents/chat/agentic_pipeline.py
deeptutor/tools/builtin/__init__.py
tests/services/skill/test_skill_service_v2.py
```

### ask_user 阅读路径

```text
deeptutor/tools/builtin/__init__.py
deeptutor/agents/chat/agent_loop.py
deeptutor/agents/chat/agentic_pipeline.py
deeptutor/core/stream_bus.py
deeptutor/services/session/turn_runtime.py
deeptutor/api/routers/unified_ws.py
```

### 必须能画出的两张图

```text
Skill 目录
  -> SkillService.summary_entries()
  -> skills_manifest
  -> System Prompt 只出现名称和简介
  -> 模型调用 read_skill
  -> 读取完整 SKILL.md / references
```

```text
LLM 调用 ask_user
  -> ToolResult.pause_for_user
  -> AgentLoop 等待 waiter
  -> 前端 submit_user_reply(turn_id)
  -> reply_queue
  -> 替换对应 role=tool 内容
  -> 同一 messages 列表继续下一轮 LLM
```

### 当天追问

1. Skill 与 Tool 的根本区别是什么？
2. 为什么不把所有 `SKILL.md` 一次性放入 System Prompt？
3. 内置 Skill 和用户 Skill 同名时如何处理？
4. `read_skill` 如何防止绝对路径或 `..` 路径穿越？
5. `ask_user` 暂停期间，运行中的 AgentLoop 状态保存在什么地方？
6. 新请求只有 `turn_id`，如何找到原回合对应的 StreamBus？
7. 用户不回答或入口没有 waiter 时如何结束？

### 当日产出与验收

- [ ] Skill 按需加载图。
- [ ] ask_user 同回合暂停恢复图。
- [ ] 用“Token 成本、相关性、安全性”三个角度解释 Manifest 设计。
- [ ] 不看代码讲清 `turn_id -> bus registry -> reply_queue -> role=tool`。

---

## Day 5：责任描述 2——L1/L2/L3 三层长期记忆

### 对应简历

> 设计 L1 / L2 / L3 三层长期记忆体系，通过 LLM 对原始交互进行提取、归并和去重，形成场景记忆及跨会话用户画像，并按需注入当前对话上下文。

### 今天只解决的问题

三层分别存什么、为什么分层、如何归并、如何追溯、最终怎样注入下一次对话？

### 阅读路径

```text
deeptutor/services/memory/paths.py
deeptutor/services/memory/trace.py
deeptutor/services/memory/store.py
deeptutor/services/memory/document.py
deeptutor/services/memory/ops.py
deeptutor/services/memory/consolidator/
deeptutor/services/session/turn_runtime.py
deeptutor/agents/chat/prompt_blocks.py
```

### 必须能画出的主链

```text
用户原始交互
  -> L1: trace/<surface>/<date>.jsonl
  -> LLM Consolidator
  -> L2: 各场景结构化记忆 + 来源引用
  -> LLM 跨场景聚合
  -> L3: recent / profile / scope / preferences
  -> read_l3_concat()
  -> UnifiedContext.memory_context
  -> System Prompt 的 Memory 块
```

### 当天追问

1. L1 为什么保留原始事件而不直接存用户画像？
2. L2 为什么按 chat、quiz、kb 等 surface 分开？
3. L3 的 recent、profile、scope、preferences 分别解决什么问题？
4. 为什么记忆条目要保留来源引用？
5. LLM 归并出现错误时如何审计和人工修改？
6. 如何处理重复、冲突和过期记忆？
7. 为什么不是每轮都把全部记忆注入 Prompt？
8. 多用户场景如何保证记忆隔离？

### 当日产出与验收

- [ ] 一张 L1 -> L2 -> L3 -> Prompt 图。
- [ ] 准备一个具体例子，例如“用户正在学傅里叶变换且偏好图示讲解”如何逐层变化。
- [ ] 能解释三层设计相对“直接存对话历史”的优势与代价。
- [ ] 对“LLM 记错了怎么办”给出审计、引用、编辑、原子更新的完整回答。

---

## Day 6：把五条责任整合成一个可信的项目故事

### 今天的目标

不再逐模块讲代码，而是形成“项目背景 -> 架构选择 -> 我的贡献 -> 难点 -> 结果 -> 反思”的完整叙事。

### 任务 1：制作简历主张审计表

对每条责任描述填写：

| 简历主张 | 对应代码/函数 | 我实际写过或改过什么 | 能否闭卷讲 | 处理 |
| --- | --- | --- | --- | --- |
| 多轮对话链路 |  |  |  | 保留/改写/删除 |
| 三层记忆 |  |  |  | 保留/改写/删除 |
| Tool 调度 |  |  |  | 保留/改写/删除 |
| Skill / ask_user |  |  |  | 保留/改写/删除 |
| 稳定性 |  |  |  | 保留/改写/删除 |

审核原则：

- 只看过代码、没有实现或改造过的内容，不使用“主导设计并实现”。
- 基于 DeepTutor 二次开发时，使用“基于……搭建/参与改造/负责……模块”更可信。
- 每一条保留的描述，必须能提供代码证据、设计取舍和异常场景。

### 任务 2：准备三个版本的项目介绍

1. **30 秒**：项目是什么、解决谁的问题、你负责什么。
2. **90 秒**：总体架构、核心调用链、两个主要贡献。
3. **3 分钟**：再增加技术难点、稳定性方案和实际取舍。

### 任务 3：准备两个 STAR 故事

每个故事必须包含：

```text
S：当时出现了什么具体问题
T：你的目标和约束是什么
A：你做了哪些设计、编码、验证
R：最后结果如何，有什么证据
```

优先准备：

1. Tool 异常、重复调用或长循环导致稳定性问题。
2. 上下文膨胀、Skill 全量注入或记忆注入带来的 Token/相关性问题。

不能证明线上数据时，不虚构 QPS、准确率或成本下降数字；可以使用测试通过数、调用轮数变化、日志证据或行为验证。

### 当日产出与验收

- [ ] `learning/notes/day6-project-story.md` 中完成主张审计表。
- [ ] 完成项目 30 秒、90 秒、3 分钟三个版本。
- [ ] 完成两个真实 STAR 故事。
- [ ] 根据审计结果修改简历措辞，确保每个动词都能自证。

---

## Day 7：模拟面试、补洞和投递前检查

### 第一轮：基础面试（20 分钟）

1. 1 分钟自我介绍。
2. 3 分钟介绍极光智能学习机。
3. 画默认 Chat 主链。
4. 解释 Tool 和 Capability。
5. 解释三层记忆。

### 第二轮：项目深挖（30 分钟）

按下面顺序随机追问：

```text
UnifiedContext
-> Capability 路由
-> messages 组装
-> LLM Tool Calling
-> Tool 并行、异常、去重
-> role=tool 回填
-> ask_user 暂停恢复
-> Context Checkpoint
-> Forced Finish
-> Skill Manifest
-> L1/L2/L3 Memory
```

每个回答使用统一结构：

```text
它解决什么问题
-> DeepTutor 怎么实现
-> 关键调用链或数据结构
-> 异常和边界
-> 为什么这样取舍
```

### 第三轮：压力追问（20 分钟）

1. 这是你从零设计的吗？哪些代码是你亲自完成的？
2. 如果不用三层记忆，最简单方案是什么？为什么没有选？
3. 为什么 Tool 异常不直接失败？这会不会掩盖问题？
4. `asyncio.gather()` 中一个工具失败会发生什么？
5. 如果模型连续 8 轮调用同一个工具怎么办？
6. 如果 ask_user 等待期间服务进程重启，能否恢复？
7. 模型把恶意路径传给 read_skill 怎么办？
8. 如果 Memory 中存在冲突信息，注入哪一条？
9. 如果 Provider 不返回 Usage，成本统计是否可信？
10. 这个架构目前最大的缺点是什么？如果再做一次会怎么改？

### 投递前最终检查

- [ ] 简历中的项目名称、时间、技术栈与实际经历一致。
- [ ] “设计、主导、实现、优化”等动词都有事实依据。
- [ ] 删除只能背概念、无法落到代码的责任描述。
- [ ] 项目介绍没有把开源原始能力全部描述成个人原创。
- [ ] 准备好可展示的架构图、代码片段、测试结果或本地 Demo。
- [ ] 手机录制一次完整模拟面试，卡顿问题已复盘。
- [ ] 最终简历导出 PDF 后检查排版、错别字和文件名。

---

## 2. 投递后继续维护方式

每天完成后，将标题前的状态从 `[ ]` 改成 `[x]`，并在当天笔记末尾填写：

```text
今日掌握：
仍然卡顿：
代码证据：
明天复习：
```

后续对话默认先读取：

```text
learning/plans/resume-interview-7day-plan.md
learning/notes/day*.md
DeepTutor项目学习手册.md
```

学习笔记是过程材料；确认无误且长期有效的技术结论，再合并到 `DeepTutor项目学习手册.md` 对应章节。
