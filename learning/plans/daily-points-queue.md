# 逐日啃点队列（第二阶段）

> 用法：每天吃一个点。每个点 30 分钟内必须产出一个能贴进学习手册的小结论。
> 完成一个把 `[ ]` 改成 `[x]`，并在对应行补一句你产出的结论摘要 + 手册位置。
>
> 顺序按依赖排好，前面的不要跳——后面的点假设你懂了前面的。

## 阶段一：默认 chat 链内部细节（接续手册第 6 章）

- [ ] **第 1 点：ask_user 暂停恢复时 role=tool 内容被换成什么**
  - 切口：`deeptutor/agents/chat/agentic_pipeline.py:792` `_await_user_reply_and_resolve`
  - 要回答：用户回复后，原来那条 `role=tool` 消息的 content 被替换成什么字符串？谁换的？为什么这么做能在“同一回合内继续”？
  - 输出：手册 6.9 节补一段，或新开 6.9.x

- [ ] **第 2 点：context checkpoint 触发后 messages 被砍成什么样**
  - 切口：`deeptutor/agents/chat/agent_loop.py` `_fold_context_checkpoint`
  - 要回答：满足 checkpoint 时，messages 列表具体从哪里被截断？换成什么占位？边界变量 `checkpoint_boundary` 怎么变？
  - 输出：手册 6.8 “Context Checkpoint” 段补一句证据

- [ ] **第 3 点：forced finish 的“停止工具并回答”指令从哪来、为何 tool_schemas=None**
  - 切口：`agent_loop.py` `_forced_finish` + `agentic_pipeline.py` `_finish_exhausted_instruction`
  - 要回答：那条“停止工具并回答”文本在哪个 yaml / 函数？为什么这次 LLM 调用不带工具 schema？
  - 输出：手册 6.10 兜底表补一句

- [ ] **第 4 点：Provider 不返回 usage 时 chars/3.5 估算在哪、为何是 3.5**
  - 切口：`agent_loop.py:_call_llm` 末尾 `add_estimated` + `deeptutor/core/agentic/usage.py`
  - 要回答：估算调用在哪一行触发？3.5 这个系数什么含义？为何不是 4？
  - 输出：手册 6.12 补一句证据

- [ ] **第 5 点：_guard_context_window 从哪条消息开始砍、砍成什么**
  - 切口：`agentic_pipeline.py:_guard_context_window`
  - 要回答：超 90% 窗口时从什么 role 的消息开始裁？替换成什么占位文本？裁到多少为止？
  - 输出：手册 6.13 补一句

- [ ] **第 6 点：一个 Tool 怎么从 ToolDefinition 变成 OpenAI function schema**
  - 切口：`deeptutor/runtime/registry/tool_registry.py` `build_openai_schemas`
  - 要回答：一行 ToolDefinition 经哪几步变成传给 LLM 的 `tools=[...]`？参数描述从哪来？
  - 输出：补进手册 5.2 或第六章相关位置

- [ ] **第 7 点：WebSocket 入口怎么把前端消息变成 UnifiedContext**
  - 切口：`deeptutor/api/routers/unified_ws.py` + `deeptutor/services/session/turn_runtime.py:1616` 附近
  - 要回答：前端 JSON 到 UnifiedContext 中间经过谁？历史 conversation_history 在哪装进去的？
  - 输出：手册第 3 阶段（Web 入口）开个头

## 阶段二：候选（阶段一吃完再排）

- [ ] RAG 从文档解析到检索返回的完整链路（手册待验证项）
- [ ] Deep Research 多阶段流程
- [ ] Memory / Skill / Source 注入顺序
- [ ] 多用户模式下的资源隔离和鉴权边界
- [ ] 沙箱代码执行（exec / code_execution）
- [ ] 可视化和数学动物

## 笔记约定

- 每个点产出的小结论，写回 `DeepTutor项目学习手册.md` 对应章节（按 AGENTS.md 第三条：同一回合更新，中文、引证据、合并进现有节）。
- 这里 `daily-points-queue.md` 只记勾选 + 一句结论摘要 + 手册位置，不重复完整结论。
- 过程草稿放 `learning/notes/`，别和项目正式文档混。
