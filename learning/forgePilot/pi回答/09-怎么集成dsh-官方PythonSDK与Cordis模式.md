# 怎么"集成" dsh —— 它确实是 TS 写的

> 结论：**dsh 有官方 Python SDK，但它的本质就是「Python 客户端 + 启动 dsh 子进程 + stdio 上的
> JSONL JSON-RPC」。而 dsh 的插件层只有 TS 一条路，没有 Python 出口。**
> 因此推荐：pi 当运行时 + 在 Python 里自建 Cordis 式插件容器。

## 一、关键事实：dsh 官方就是这么集成 Python 的

`python/sdk/README.md` 第一句原文：

> **Python subprocess SDK for driving DeepSeek Harness over newline-delimited
> JSON-RPC on stdio.**

PyPI 包 `deepseek-harness-sdk`，`requires-python = ">=3.10"`，依赖
`pydantic>=2.12` + `deepseek-harness-runtime-bin`（平台专用原生运行时 wheel）。

### 这直接回答了"企业级不能用一个子进程"的质疑

> **DeepSeek 自己对 Python 集成的官方方案，就是子进程 + stdio 上的 JSONL JSON-RPC。**

这不是谁偷懒，这是行业里**用其它语言驱动 agent 运行时**的标准做法。理由在
[04](04-企业级架构-控制面与执行面.md) 已论证：agent 会执行任意命令、会死循环、会 OOM，
必须在独立故障域里。

### 它的 API 形态（值得抄）

```py
from deepseek_harness import DeepSeekHarness

with DeepSeekHarness(
    dsh_home="/absolute/path/to/isolated-dsh-home",   # 必须显式给，SDK 故意不发现 ~/.dsh
    cwd="/absolute/path/to/workspace",                # agent 工作区
    runtime_cwd=None,                                 # 子进程自己的工作目录，可独立
    provider="deepseek-official",
    model="deepseek-v4-flash",
    reasoning_effort="max",
    max_tokens=49_152,
    profile="sdk",                                    # 决定 Cordis 插件树
    patches=("/abs/first.patch.yml", "/abs/last.patch.yml"),  # 分层补丁
    initialize_timeout_seconds=30,
) as harness:
    result = harness.run("Say hi.", session_id="example-001")

print(result.final_response)
```

`RunResult(session_id, final_response, finish_reason, events, notifications)`：

- `finish_reason` 取最后一个 `turn/end` 的 `data.reason.kind`（`completed` / `max-tokens` / `error`）
- `events` 只含根会话事件；子 agent 的输出走 `notifications`，**不会污染根响应**
- `on_notification` 回调按 wire 顺序推送根会话与已知后代

值得抄的设计点：

| 设计 | 为什么值得抄 |
| --- | --- |
| `dsh_home` 必须显式传，**永不自动发现 `~/.dsh`** | 多租户隔离：不会串到开发者本机配置 |
| 资源缺失时**不自动下载**，显式 `download_primary_runtime()` | 生产环境不能有隐式网络行为 |
| `cwd` 与 `runtime_cwd` 分离 | agent 工作区 ≠ 子进程 cwd，防止配置被 agent 改写 |
| `resume_session()` 恢复被中断的最后一轮 | 与 ForgePilot 的"断点续跑"同构 |
| 运行时打进 wheel（`...-runtime-bin`），**跑 SDK 不需要系统 Node.js** | 解决 Node 运行时依赖问题 |

## 二、但 dsh 的插件层没有 Python 出口

README「Customize plugins」一节的全部做法：

```sh
export DSH_HOME=/absolute/path/to/isolated-dsh-home
dsh --profile sdk --dump-default-config >/dev/null
dsh plugin --profile sdk add file:/absolute/path/to/my-plugin-bundle
```

- 插件是 **Cordis bundle**，只能是 TS/Node 包
- 用户定制落在 `$DSH_HOME/profiles/sdk/cordis.patch.yml`（YAML 补丁，按 row id 替换/插入）
- Python SDK 只暴露"启动 / prompt / 收事件 / resume / 改工作目录"，**没有注册工具、没有挂钩子的 API**

**所以：想用 Cordis 的插件化，就必须写 TypeScript。这一点没有捷径。**

## 三、四条集成路径（按侵入程度）

| 路径 | 做法 | 成本 | 结论 |
| --- | --- | --- | --- |
| **A. dsh 当运行时** | `pip install deepseek-harness-sdk`，子进程 + JSON-RPC | 插件要写 TS；控制面要再维护一套 provider/profile/patch 概念 | 不推荐（与你已定的 pi 路线重复） |
| **B. pi 当运行时（已定）** | `pi --mode rpc`，Python 侧只下命令收事件 | 0 行 TS（除了可选 extension） | ✅ 当前选择 |
| **C. 借 Cordis 思想，Python 自建插件容器** | ~150 行，见第四节 | 自己写，但完全可控 | ✅ 推荐 |
| **D. dsh 只当日常工具** | `~/.pi/agent/settings.json` 里 `defaultProvider: dsh` 已经在用 | 0 | ✅ 保持现状 |

## 四、把「一切皆插件」搬到 Python：核心洞察

Cordis 的架构文档说：

> registrations are **effects that unwind** when their plugin unloads.

**Python 里这个语义就是 `contextlib.ExitStack`。** 注册时压一个回滚回调，退出时自动逆序回滚。
所以"可逆 effect"不需要框架，标准库就够。

### 骨架（约 60 行，可直接落地）

```python
# forgepilot/plugins/container.py
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any, Callable, Protocol


class Plugin(Protocol):
    name: str
    requires: tuple[str, ...]          # 声明依赖的服务名，等价于 Cordis 的 inject
    def apply(self, ctx: "Context") -> None: ...


class Context:
    """Cordis ctx 的最小等价物：服务注册 + 显式依赖 + 可逆注册。"""

    def __init__(self, stack: ExitStack) -> None:
        self._stack = stack
        self._services: dict[str, Any] = {}
        self._hooks: dict[str, list[Callable[..., Any]]] = {}

    # ---- 服务：等价 ctx.set / ctx.get ----
    def provide(self, name: str, impl: Any) -> None:
        if name in self._services:
            raise RuntimeError(f"service already provided: {name}")
        self._services[name] = impl
        self._stack.callback(self._services.pop, name, None)   # ← 可逆 effect

    def require(self, name: str) -> Any:
        try:
            return self._services[name]
        except KeyError:
            raise LookupError(f"missing dependency: {name}") from None

    # ---- 钩子：等价 Cordis 的类型化事件 ----
    def on(self, event: str, handler: Callable[..., Any]) -> None:
        bucket = self._hooks.setdefault(event, [])
        bucket.append(handler)
        self._stack.callback(bucket.remove, handler)            # ← 可逆 effect

    async def emit(self, event: str, payload: Any) -> Any:
        """链式变换：上一个 handler 的返回值成为下一个的输入。"""
        for handler in list(self._hooks.get(event, ())):
            result = handler(payload)
            if hasattr(result, "__await__"):
                result = await result
            if result is not None:
                payload = result
        return payload


def load(plugins: list[Plugin], *, stack: ExitStack) -> Context:
    """按 requires 拓扑排序装配；依赖不满足就失败，不做隐式兜底。"""
    ctx = Context(stack)
    pending, done = list(plugins), set()
    while pending:
        progressed = False
        for plugin in list(pending):
            if set(plugin.requires) <= done:
                plugin.apply(ctx)          # 只在依赖就绪后激活，等价 Cordis 的 inject
                done.add(plugin.name)
                pending.remove(plugin)
                progressed = True
        if not progressed:
            raise RuntimeError(f"unresolved dependencies: {[p.name for p in pending]}")
    return ctx
```

使用：

```python
with ExitStack() as stack:                     # 退出即全部回滚，等价插件卸载
    ctx = load([RuntimePlugin(), StateMachinePlugin(), ToolsPlugin(), EvalPlugin()],
               stack=stack)
    ...
```

### 这个容器在你项目里的落点

| 插件 | 提供什么服务 | 依赖什么 |
| --- | --- | --- |
| `RuntimePlugin` | `runtime`：pi 子进程封装 / `abort` / 事件流 | — |
| `WorkspacePlugin` | `workspace`：git worktree 准备、diff 收集、指纹 | — |
| `StateMachinePlugin` | `task_state`：阶段、检查点、租约、幂等键 | `workspace` |
| `GatePlugin` | `permission`：工具权限门（**只能加严不能放宽**） | `task_state` |
| `TicketPlugin` | `ticket`：工单适配器 | — |
| `GitHostPlugin` | `codehost`：PR/MR 创建与状态核对 | `ticket` |
| `VerifierPlugin` | `verify`：可信构建/测试命令执行 | `workspace` |
| `RetrieverPlugin` | `retrieval`：符号检索 / 调用关系（**M4 增强组就是装这个插件**） | — |
| `JudgePlugin` | `judge`：LLM Judge 实现（**换插件即可做对照**） | — |

**M4 的 baseline vs 增强组对照，就是"装不装 `RetrieverPlugin`"** —— 同一份代码、
同一个模型、同一个预算，只改装配列表。这是"插件化"能拿出的最硬的实验证据。

### dsh 的 Cordis 与这个 Python 容器的对应关系

| Cordis / dsh | 本文的 Python 容器 |
| --- | --- |
| `ctx.sessions` / `ctx.tools` / `ctx.llm` | `ctx.provide("runtime", ...)` 等 |
| service get / inject | `require()` + `requires` 拓扑排序 |
| typed events | `on()` / `emit()` |
| reversible effects / unwind | `ExitStack.callback` |
| profile + bundle + `cordis.patch.yml` 分层补丁 | 插件列表 + 配置补丁（可后续加） |
| `dsh-hmr` 热更新 | **不做**（见下） |

## 五、必须承认的硬约束：Python 侧挂不上 agent 进程内的钩子

**无论 pi 还是 dsh，都不能从 Python 里注册 agent 内部的钩子。**

| | pi | dsh |
| --- | --- | --- |
| 钩子形态 | TS extension（`pi.on("tool_call")` / `context` / `tool_result`） | TS Cordis plugin（`tools/pre-execute`、`agent/pre-step`） |
| Python 侧能做的 | 下命令、收事件、事后校验、靠沙箱限制 | 同 |

这对四条亮点的影响：

| 亮点 | 影响 |
| --- | --- |
| ① 上下文管理与压缩 | ⚠️ **唯一受影响的一条**：不能在 Python 里注入压缩策略 |
| ② PR Review 评估 | ✅ 全在平台侧，完全不受影响 |
| ③ 长任务可靠执行 | ✅ 全在平台侧（`abort` + `agent_settled` + 检查点/幂等/核对） |
| ④ SWE-bench 评估 | ✅ 全在平台侧 |

### ① 的解法：用 session 边界做压缩，而不是在 agent 内部做

不要试图改 pi 的压缩算法，改成**平台层控制上下文**：

```
阶段边界（Python 侧）：
  1. 从前一阶段事件流中抽取 -> 结构化任务状态（DB）
  2. 关掉当前 pi session
  3. 起一个新 pi session，用 --session-dir 指向任务目录
  4. 把结构化状态渲染成首轮 prompt 注入
     （保留：目标/约束/已确认事实+证据引用/已尝试方案/待验证假设/下一步）
```

**好处（也是面试可讲的）：**

- 完全在 Python 里，零 TS
- 压缩点是**确定的、可审计的**（阶段边界），不是"消息多了随机触发"
- 每次压缩的输入输出都可完整落盘 → M3 的三组对照实验（仅截断 / 只有摘要 / 结构化状态）
  可以直接跑，数据全部自己掌控
- 顺带绕过 pi 的压缩不可控问题：pi 的 `compaction.*` 只能配
  `enabled` / `reserveTokens` / `keepRecentTokens` / `modelOverrides`，
  不能改摘要策略

**pi 侧仍然可用的压缩观测**：`compaction_start` / `compaction_end` 事件里带
`tokensBefore` / `estimatedTokensAfter` / `usage`，可作为基线组的成本数据。

## 六、最终集成形态

```
Python 控制面
  ├── 插件容器（ExitStack + 服务 + 可逆注册）        ← 借 Cordis 思想
  │     ├── RuntimePlugin  ──> pi --mode rpc 子进程   ← 运行时
  │     ├── StateMachinePlugin / GatePlugin
  │     ├── TicketPlugin / GitHostPlugin
  │     ├── VerifierPlugin
  │     └── RetrieverPlugin / JudgePlugin（M4 对照即换装配）
  └── 阶段边界压缩：结构化状态 DB + 新 session 注入

不用 dsh 当运行时；不需要写任何 TypeScript。
```

## 七、面试一句话

> "dsh 官方给 Python 的 SDK，本身就是『Python 客户端 + 起 dsh 子进程 + stdio 上的 JSONL
> JSON-RPC』——所以用子进程驱动 agent 运行时不是偷懒，这是 DeepSeek 自己的官方做法。
>
> 但 dsh 的插件层只有 Cordis bundle，也就是 TypeScript，没有 Python 出口。
> 我要的是它的**思想**而不是它的代码，所以我用 Python 标准库的 `ExitStack` 实现了等价的
> 可逆注册语义：provide 一个服务就压一个回滚回调，退出时逆序 unwind；插件通过 `requires`
> 声明依赖、拓扑排序后激活。150 行，没有引入任何框架。
>
> 这样 M4 的对照实验就变成『装不装检索插件』——同一份代码、同一个模型、同一个预算，
> 只改装配列表。"
