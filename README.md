# DeepTutor — Agent-Native Intelligent Learning Platform

**个人项目 | 设计并实现了一套完整的 Agent-Native 学习平台**

## 概述

从零开始构建一套基于 **Agent-Native** 架构的个性化学习平台。系统以统一 Agent 循环为核心，支持聊天、研究、问题解决、知识可视化、书籍生成和掌握路径等多个能力，在单一可扩展的引擎中运行。

## 核心技术贡献

### 1. Agent Orchestration Engine（Agent 编排引擎）
- 设计并实现了**统一 Agent 循环**（ChatOrchestrator + AgenticChatPipeline）
- 构建了所有 Agent 能力的基础（Chat、Research、Solve、Book、Quiz、Visualize、Mastery Path）
- 实现了高级**子 Agent 咨询**和实时多 Agent 协作机制

### 2. Three-Layer Persistent Memory System（三层持久化记忆系统）
- 设计并构建了**三层记忆架构**（L1/L2/L3）
- 开发了**Memory Graph**（记忆图谱），实现每条结论的可追溯性
- 创造了可检查、可审计、可编辑的持久化记忆系统
- 实现了跨多个表面（聊天、笔记本、书籍、Partner、Co-Writer）的持久化记忆

### 3. Multi-Agent Collaboration System（多 Agent 协作系统）
- 构建了**Partner 智能体**系统（每个 Partner 拥有独立人格、记忆、技能和 IM 通道）
- 实现了**My Agents / Subagents** 功能
- 完成了可扩展的 Skill 和 MCP 工具集成框架

## 技术栈

- **Agent 引擎**：Python + FastAPI + 自定义 Agent Orchestrator
- **LLM**：OpenAI 兼容客户端、Anthropic、本地模型（Ollama、vLLM）
- **RAG**：多引擎系统（LlamaIndex、GraphRAG、LightRAG、PageIndex）
- **记忆**：文件型三层持久化记忆系统 + Memory Graph
- **其他**：MCP、WebSocket、Docker、Windows 开发环境

## 产出与收获

- 深入掌握 **Agent 系统架构** 和多 Agent 协作机制
- 构建了高级**三层持久化记忆系统**和 Memory Graph
- 积累了 LLM 提供商集成、RAG 架构、本地开发环境优化等核心技能

## 技能栈

- 高级 Agent 系统设计与编排
- 三层持久化记忆架构与 Memory Graph
- 多 Agent 协作与子 Agent 咨询
- LLM 提供商架构与集成
- 多引擎 RAG 系统
- 可扩展的 Skill 与 Tool 框架

---

**这是一份技术深度强的个人项目描述，适合放在简历上。**
