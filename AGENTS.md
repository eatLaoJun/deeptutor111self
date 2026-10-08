# DeepTutor — Agent-Native Architecture

## 当前工作约定：求职与面试学习优先

本节优先于本文后续的历史架构说明和学习手册维护规则。

- 当前目标是求职准备、技术方案理解和面试口述，不是开发、运行或核验 DeepTutor。
- 默认只读取和维护仓库根目录的 `learning/` 学习材料；用户所说的
  `leanring` 指的就是该目录。本文件作为工作约定可以读取和修改。
- 不再读取、搜索或分析 DeepTutor 的任何实现代码，包括后端、前端、CLI、
  测试和脚本；不要通过全仓搜索、Git 历史或工具委派绕过这一限制。
  不主动安装依赖、运行服务或测试，也不主动修改实现代码。
- 用户已确认：`learning/` 中描述的鼎校伴学业务（知识点学习闭环、双层编排、
  三层记忆、RAG 等）是用户已经实现的项目，是用户的真实项目经历。写面试稿、
  简历和口述时，按“已实现的生产项目”口吻，使用“我实现了/我负责/我做了”
  等完成式表达，不要写成“设计阶段”“原型”“玩具”或反复加“待实现”免责声明。
  回答“我的项目怎么设计”“能否融入某种思路”时，以 `learning/` 中的项目设定
  为上下文，讨论业务动机、架构、数据流、存储模型、取舍、异常处理及面试追问，
  不回到源码寻找对应功能。
- 输出以简体中文、适合口述的解释为主，优先帮助用户讲清楚“为什么做、
  怎么做、为什么这样选、有什么边界”，不默认生成源码课程或实现任务。
- 区分“已实现的项目内容”和“建议的演进方案”。学习材料中的已有业务按用户
  确认的已实现项目处理；只有用户明确标注为“后续想做/演进方向”的内容
  （如 Planner、Subagent 扩展等）才按计划口吻表达。
- 不虚构用户没有提供的具体数字：用户规模、性能指标、线上效果数据。缺少实测
  数字时，不编造，改用机制层面的说法，或标为“示例”，并提醒用户填入自己的
  真实数据。这是为了避免面试被追问时露馅，而不是削弱项目的完成度表述。
- 需要沉淀稳定结论时，合并到 `learning/` 下相关材料；
  不再自动读取或更新根目录的 `DeepTutor项目学习手册.md`，也不沿用下文
  “核验源码后更新手册”的工作流程。
- 只有用户后续明确要求恢复源码分析、开发或扩大资料范围时，才按该次明确
  要求调整范围；一般性的技术提问不视为解除以上限制。

## Overview

DeepTutor is an **agent-native** intelligent learning companion organized
around a two-layer plugin model — single-shot **Tools** invoked by the
LLM, and multi-stage **Capabilities** that take over a turn — exposed
through three entry points: CLI, WebSocket API, and Python SDK.

## Architecture

```
Entry Points:  CLI (Typer)  |  WebSocket /api/v1/ws  |  Python SDK
                    ↓                   ↓                   ↓
              ┌─────────────────────────────────────────────────┐
              │              ChatOrchestrator                    │
              │   routes UnifiedContext → selected Capability    │
              │   (defaults to `chat`)                           │
              └──────────┬──────────────┬───────────────────────┘
                         │              │
              ┌──────────▼──┐  ┌────────▼──────────┐
              │ ToolRegistry │  │ CapabilityRegistry │
              │  (Level 1)   │  │   (Level 2)        │
              └──────────────┘  └────────────────────┘
```

All capabilities emit on a shared `StreamBus`; the orchestrator fans
events out to consumers. Runtime settings live in
`data/user/settings/*.json` — project-root `.env` files are intentionally
ignored.

### Level 1 — Tools

Single-function tools the LLM picks on demand. Four user-toggleable tools
surface in `/settings/tools`:

| Tool           | Description                                   |
| -------------- | --------------------------------------------- |
| `brainstorm`   | Breadth-first idea exploration with rationale |
| `web_search`   | Web search with citations                     |
| `paper_search` | arXiv preprint search                         |
| `reason`       | Dedicated deep-reasoning LLM call             |

The rest are **context-gated**: the chat capability auto-mounts them from
`ToolMountFlags` (presence of a KB, attachments, sandbox availability, …), and
any of them can also be force-enabled via `--tool`. Auto-mounted set: `rag`,
`read_source`, `read_memory`, `write_memory`, `read_skill`, `load_tools`,
`exec`, `code_execution` (sandboxed Python: NL intent → code → run),
`list_notebook`, `write_note`, `web_fetch`, `github`, `cron`,
`ask_user` (pauses the turn and resumes with the user's reply), plus the
mastery-path tools. `geogebra_analysis` is parked under
`COMING_SOON_TOOL_TYPES`.

### Level 2 — Capabilities

Multi-stage pipelines that own the turn:

| Capability       | Stages                                                |
| ---------------- | ----------------------------------------------------- |
| `chat`           | exploring → responding (single agentic loop, default) |
| `mastery_path`   | responding (Guided Learning — chat loop + mastery tools, gated per topic type) |
| `deep_solve`     | planning → reasoning → writing                        |
| `deep_question`  | ideation → generation                                 |
| `deep_research`  | rephrasing → decomposing → researching → reporting    |
| `visualize`      | analyzing → generating → reviewing (SVG / Chart.js / Mermaid / HTML; or routes to Manim sub-stages via `render_type`) |
| `math_animator`  | concept_analysis → concept_design → code_generation → code_retry → summary → render_output |

All capabilities converge on `emit_capability_result()` in
`deeptutor/capabilities/_shared.py` so every turn emits the same envelope
(response payload + `cost_summary` from `UsageTracker`). Status copy and
prompts are i18n'd via `capabilities/prompts/{en,zh}/<name>.yaml`.

## CLI Usage

```bash
# Install
pip install deeptutor      # Full app (CLI + Web/API + packaged Web assets)
pip install deeptutor-cli  # CLI-only

# Run any capability
deeptutor run chat "Explain Fourier transform"
deeptutor run deep_solve "Solve x^2=4" -t rag --kb my-kb
deeptutor run visualize "Animate sine wave" --config render_mode=manim_video

# Interactive REPL
deeptutor chat
# (inside the REPL: /regenerate or /retry re-runs the last user message)

# Partners (IM-connected companions)
deeptutor partner list

# Knowledge bases, memory, server
deeptutor kb list
deeptutor kb create my-kb --doc textbook.pdf
deeptutor memory show
deeptutor serve --port 8001       # API server only
deeptutor start                   # backend + frontend together
```

## Key Files

| Path                                       | Purpose                              |
| ------------------------------------------ | ------------------------------------ |
| `deeptutor/runtime/orchestrator.py`        | `ChatOrchestrator` — unified entry   |
| `deeptutor/runtime/launcher.py`            | Backend + frontend lifecycle / port discovery |
| `deeptutor/runtime/registry/`              | Tool + Capability registries         |
| `deeptutor/runtime/bootstrap/builtin_capabilities.py` | Built-in capability class paths |
| `deeptutor/services/config/runtime_settings.py` | JSON settings + process-env overrides |
| `deeptutor/core/stream.py`, `stream_bus.py` | StreamEvent protocol + async fan-out |
| `deeptutor/core/tool_protocol.py`          | `BaseTool` + `ToolDefinition`         |
| `deeptutor/core/capability_protocol.py`    | `BaseCapability` + `CapabilityManifest` |
| `deeptutor/core/context.py`                | `UnifiedContext` dataclass            |
| `deeptutor/tools/builtin/__init__.py`      | All built-in tool wrappers           |
| `deeptutor/capabilities/`                  | Built-in capability implementations  |
| `deeptutor/app.py`                         | `DeepTutorApp` — Python SDK facade    |
| `deeptutor_cli/main.py`                    | Typer CLI entry point                |
| `deeptutor/api/routers/unified_ws.py`      | Unified WebSocket endpoint           |

## Dependency Layers

Public install paths and source extras are defined in `pyproject.toml`.
Requirements files mirror the same dependency groups for Docker/CI installs.

```
pip install deeptutor      — Full app (CLI + Web/API + packaged Web assets)
pip install deeptutor-cli  — CLI-only (LLM + RAG + providers + document parsing)
pip install -e .           — Source install for development

Source extras (.[ extra ], defined in pyproject.toml):
.[cli]            — CLI-only dependency set
.[server]         — Web/API server dependencies
.[partners]       — Partner channel SDKs + MCP client  (legacy alias: .[tutorbot])
.[matrix]         — Matrix channel for Partners (matrix-nio; needs libolm)
.[matrix-e2e]     — Matrix with end-to-end encryption (matrix-nio[e2e])
.[math-animator]  — Manim addon (powers `visualize` Manim renders + `deeptutor run math_animator`)
.[dev]            — Test / lint tooling
.[all]            — Everything above
```

## Project Learning Handbook

> 历史工作流程，当前暂停：以顶部“当前工作约定：求职与面试学习优先”为准。
> 以下规则不构成读取源码或自动更新本手册的授权。

`DeepTutor项目学习手册.md` is the durable, human-readable learning
record for this checkout. When project-related work establishes a stable and
useful fact about the technology stack, architecture, runtime behavior,
configuration precedence, or a concrete implementation path, update the
relevant handbook section in the same turn.

Handbook updates must:

- be written in Simplified Chinese and remain suitable for spoken explanation;
- distinguish verified facts from open questions or inference;
- cite concrete source paths, functions, configuration, or runtime evidence;
- merge into existing sections instead of appending duplicate conclusions;
- update the handbook change log only for meaningful additions;
- omit transient search history, raw logs, and unverified guesses;
- be applied **proactively and without asking for confirmation** when the fact
  is verified. Do NOT ask "should I add this to the handbook?" — verifying a
  fact in code is already the trigger; just merge it into the relevant section
  in the same turn. Only ask when there is genuine ambiguity about *which*
  section a fact belongs in.
