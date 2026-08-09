# DeepTutor 简历项目介绍

## 目录

- [简历项目版本](#简历项目版本)
- [面试口述版本](#面试口述版本)

## 简历项目版本

### DeepTutor — Agent-Native 智能学习平台

**技术栈：** Python、AsyncIO、FastAPI、WebSocket、LLM Function Calling、LlamaIndex、Typer

**项目介绍：**  
DeepTutor 是一个面向智能学习场景的 Agent-Native 平台，统一支持 CLI、WebSocket API 和 Python SDK 三种入口。项目通过 Tool 与 Capability 扩展体系，实现多轮对话、三层记忆、知识检索、深度解题、Skill 动态加载及多工具协同执行。

**项目职责：**

- 参与多轮对话核心链路建设，基于 `UnifiedContext`、`ChatOrchestrator`、`AgentLoop` 和 `StreamBus` 实现会话历史组装、Capability 路由、多轮 LLM 调用及流式事件输出。
- 参与三层记忆模块设计与构建：L1 以追加式 JSONL 记录用户与各功能场景的原始事件，L2 按 Chat、Notebook、Quiz、KB 等场景生成带来源引用的结构化总结，L3 进一步聚合用户近期状态、画像、上下文范围和偏好，形成跨会话长期记忆。
- 实现 LLM 驱动的 `L1 → L2 → L3` 记忆归并链路，支持更新、审计、去重、条目级编辑及原子写入；对长期记忆进行按需读取并注入当前回合的 System Prompt。
- 参与 Tool 协议、注册及调度体系建设，完成 `ToolDefinition → Function Schema → LLM tool_calls → ToolRegistry → 并行执行 → role=tool 回填` 的闭环，支持工具异常回填、重复调用去重、暂停恢复与轮次兜底。
- 参与内置 Tool 的集成与构建，接入 `brainstorm`、`web_search`、`rag`、`reason`、`read_memory`、`write_memory` 及 `ask_user` 等工具，并为公共执行入口增加 TRACE 日志、参数长度限制和 API Key、Token、Cookie 等敏感字段脱敏。
- 参与 Skill 体系的集成与构建，实现内置 Skill 与用户 Skill 的分层存储、导入、覆盖及运行时加载；默认仅将 Skill Manifest 注入 Prompt，由模型在任务匹配时通过 `read_skill` 按需读取完整 `SKILL.md` 及其附属资源，减少无关上下文占用。
- 完善 Agent 运行时稳定性，处理 `ask_user` 同回合暂停恢复、Context Checkpoint 上下文折叠、最大轮次 Forced Finish 以及 Tool 执行失败后的降级回填。

## 面试口述版本

> 我参与了 DeepTutor 智能学习平台的开发，重点负责多轮对话、三层记忆、Tool 和 Skill 等 Agent 核心模块。
>
> 多轮对话部分通过 UnifiedContext 统一承载当前消息、历史对话、记忆和可用工具，由 ChatOrchestrator 选择 Capability，再交给 AgentLoop 进行多轮 LLM 与工具调用，结果通过 StreamBus 流式返回。
>
> 记忆模块采用三层结构：L1 保留原始事件，L2 归并各业务场景的结构化记忆，L3 再聚合成跨场景的用户画像、近期状态和长期偏好。归并过程由 LLM 驱动，同时保留来源引用，便于追溯、审计和人工编辑。
>
> Tool 部分通过 ToolDefinition 把函数协议暴露给模型，模型返回 tool_calls 后由统一 Dispatcher 并行执行，再将结果以 role=tool 回填给下一轮模型。Skill 则采用 Manifest 与按需加载机制，先让模型知道有哪些 Skill，任务匹配后再通过 read_skill 读取完整内容，避免一次性把所有 Skill 塞进上下文。
