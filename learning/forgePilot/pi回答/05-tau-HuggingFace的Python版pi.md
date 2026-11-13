# tau：HuggingFace 的 Python 版 pi

仓库：<https://github.com/huggingface/tau> · 文档：<https://twotimespi.dev/>

## 一、基本事实（2026-10-21 通过 GitHub API 核查）

| 项 | 值 |
| --- | --- |
| 官方描述 | **A Python port of Pi's minimalist coding agent** |
| 语言 / License | Python / MIT |
| Stars / Forks / Open issues | 2981 / 385 / 135 |
| 创建 / 最后推送 | 2026-06-11 / 2026-10-19 |
| PyPI | `tau-ai`，命令 `tau` |
| 运行时要求 | **Python 3.12+**（源码用了 3.12 的 `type` 语句） |
| 分层 | `tau_coding` → `tau_agent` → `tau_ai` |

分层职责（README）：

- `tau_ai`：把各 provider 翻译成 Tau 的 provider-neutral 流
- `tau_agent`：可移植的"大脑" —— messages / tools / events / loop / harness / session
- `tau_coding`：把大脑包装成真正的编码应用 —— CLI、TUI、文件与 shell 工具、provider 配置、
  项目指令、skills、磁盘会话

边界：`AgentHarness = 可复用大脑`，`CodingSession = 编码环境`，`TUI = 一种前端`。
核心不认识 Textual / Rich / 本地配置路径 / 斜杠命令。

## 二、当库用（关键）

```python
from tau_agent import AgentHarness, AgentHarnessConfig

harness = AgentHarness(AgentHarnessConfig(
    provider=provider, model="my-model",
    system="You are a helpful coding agent.",
    tools=tools,
))

async for event in harness.prompt("Explain this package"):
    print(event)
```

**纯 Python、in-process、无子进程、无 Node、无 RPC 桥。**

## 三、与 ForgePilot 直接相关的接口（源码核查）

### `tau_agent/harness.py`

```python
@dataclass(slots=True)
class AgentHarnessConfig:
    provider: ModelProvider
    model: str
    system: str
    tools: list[AgentTool] = ...
    max_turns: int | None = None
    queue_mode: QueueMode = "one_at_a_time"       # 或 "all"
    session_id: str | None = None
    before_tool_call: BeforeToolCall | None = None   # ← 权限门 / 预算 / 幂等
    after_tool_call: AfterToolCall | None = None     # ← ToolOperation 记录
```

方法：`prompt()` / `prompt_message()` / `continue_()` / `steer()` / `follow_up()` /
`clear_queues()` / `cancel()` / `subscribe()` / `append_message()` / `replace_messages()`

内部细节值得记：`_run()` 里会先调 `_append_interrupted_tool_results()`
（给被中断的 dangling tool call 补合成结果），并且在取消后把修复后的消息推给订阅者。

> ⚠️ 这是"能跑"级别的修复，**不等于**"外部操作结果核对"。
> ForgePilot 的长任务可靠性亮点正因为这一点才有存在价值 —— 合成结果只是自洽，不代表真实。

### `tau_agent/tools.py`

```python
@dataclass(frozen=True, slots=True)
class AgentTool:
    name: str
    label: str
    description: str
    parameters: Mapping[str, JSONValue]
    execute_fn: ToolExecutor
    prompt_snippet: str | None = None
    execution_mode: ToolExecutionMode = "parallel"   # 或 "sequential"

@dataclass
class AgentToolResult(WireModel):
    content: list[TextContent | ImageContent]
    details: JSONValue = None
    added_tool_names: list[str] | None = None
    terminate: bool | None = None
```

`execute_fn(tool_call_id, arguments, signal, on_update)` —— 能拿到取消信号和流式回调。

### `tau_agent/events.py`

```python
type AgentEvent = Annotated[
    AgentStartEvent | AgentEndEvent | TurnStartEvent | TurnEndEvent
    | MessageStartEvent | MessageUpdateEvent | MessageEndEvent
    | ToolExecutionStartEvent | ToolExecutionUpdateEvent | ToolExecutionEndEvent,
    Field(discriminator="type"),
]
```

### `tau_coding/context_window.py`

- `CHARS_PER_TOKEN = 4`（粗糙估算，中文场景严重失真 → 这是可替换的改进点）
- `DEFAULT_CONTEXT_WINDOW_TOKENS = 128_000`、`COMPACTION_RESERVE_TOKENS = 16_384`、
  `COMPACTION_KEEP_RECENT_TOKENS = 20_000`
- `SUMMARIZATION_PROMPT` 要求固定结构：
  `## Goal / ## Constraints & Preferences / ## Progress(Done·In Progress·Blocked) /
  ## Key Decisions / ## Next Steps / ## Critical Context`
- 另有 `UPDATE_SUMMARIZATION_PROMPT` 做增量更新

## 四、与 pi 的逐项等价性核查（面试可直接引用）

| pi（TypeScript） | tau（Python） | 等价 |
| --- | --- | --- |
| 事件表 `agent_start / turn_start / message_start\|update\|end / turn_end / tool_execution_start\|update\|end` | 同名同字段，pydantic 判别联合 | ✅ |
| `steer()` / `followUp()` 队列 | `harness.steer()` / `follow_up()` + `QueueMode` | ✅ |
| `ToolCall{id, toolName, args}` / 结果 `{content, details}` | `AgentTool` / `AgentToolResult` | ✅ |
| 工具并行 / 串行 | `execution_mode: "parallel" \| "sequential"` | ✅ |
| append-only JSONL 会话树 / branch / fork | `tau_agent/session/{jsonl,tree,entries}.py` | ✅ |
| abort | `CancellationToken` 传入 loop 与 `execute_fn` | ✅ |
| `tool_execution_end.durationMs`（单调时钟） | **无此字段** | ❌ 缺 |
| `compaction_start` / `compaction_end`（含 `tokensBefore`、`estimatedTokensAfter`、`usage`） | **无此事件**（压缩在 `tau_coding` 层，不产生 agent 事件） | ❌ 缺 |
| 扩展生态：extensions / skills / prompt templates / MCP / codemode | Python 版子集，覆盖面较小 | ⚠️ 子集 |

**结论：loop 语义与事件契约基本一致，但成本计量（durationMs）和压缩可观测性（compaction 事件）缺失
—— 这两条正是成本核算与压缩实验要用的数据，必须自己在 `before/after_tool_call` 里打点补上。**

## 五、风险

1. **tau ≠ pi。** 是复刻，不是同一代码库。简历不能写"以 pi 为核心"，要写
   "基于 tau（Pi 的 Python 实现）"或"复刻 Pi 架构的 Python agent 运行时"。
2. **成熟度。** 2026-06 建的仓库，README 自称 teaching project、under active development，
   135 个 open issue。企业级对策：
   - pin 到具体 commit（不用浮动版本）
   - 需要改的文件（如 `context_window.py`）直接 fork 纳管
   - `AgentRuntime` 抽象保证能切回 `PiRpcRuntime`
3. **上游生态是子集**。只用 `AgentHarness` 这一层，不依赖上层扩展生态，可规避风险。

## 六、安装

```bash
uv tool install tau-ai     # 或 pipx install tau-ai
tau --version
```

本机当前 Python 是 3.10.10，tau 要求 3.12+ → 先用 `uv` 装一个隔离的 3.12。
自定义 provider 走 `~/.tau/catalog.toml`（与 `tau_coding/data/catalog.toml` 同 schema），
不改代码即可接现有的 `dsh`（`baseUrl` + `openai-completions`）。
