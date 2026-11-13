# 简历四条 × tau 覆盖度 × 面试问答

> 对应简历：`../../resume/岳明哲_简历_原结构优化版_20261020.md` 第 44–53 行
> 「ForgePilot｜研发 Bug 修复与评审平台 | 2026.03—至今」

## 一、简历原文（供核对）

**项目概述：** 面向研发 Bug 修复，串联工单理解、代码定位、自动改码、构建验证与 PR 交付。
已供 **500+ 名工程师使用**；**2026 年 Q2 组内累计修复 71 个 Bug**，单个 Bug 平均处理时间
由 **178 分钟缩短至 53 分钟，降低约 70%**。通过上下文治理、可恢复执行和评估机制支撑长任务推进，
保留人工审核与合并。

**技术栈：** Python / React / Agent Workflow / Tool Calling / Git / LLM Judge / SWE-bench

- **上下文管理与压缩：** 设计预算驱动的分层压缩，保留近期交互及完整工具调用关系；
  结构化保存目标、状态与证据引用，分层裁剪工具输出，原始制品按需读取。
- **PR Review 效果评估：** 历史缺陷与人工标签驱动的离线链路，以文件及代码区间生成匹配候选，
  结合独立 LLM Judge 与人工仲裁判断语义，输出 Precision、Recall 及根因归类。
- **长任务可靠执行：** 状态驱动的修复—验证流程，以检查点、操作幂等键、并发租约和重试预算约束推进；
  关联工作区快照、测试指纹及 PR 状态核对。
- **SWE-bench 修复 Agent 评估：** 固定样本上的基线与代码检索增强对照，控制模型、环境和执行预算，
  以官方测试判定补丁有效性。

> ⚠️ 技术栈这一行**目前没有写 pi / tau**。选定 runtime 后必须补上，因为这是可验证的事实。

## 二、tau 的覆盖度（逐条核过源码）

| 简历条目 | tau 现成的 | 必须自己写的 | tau 覆盖 |
| --- | --- | --- | --- |
| **① 上下文管理与压缩** | `context_window.py`：token 估算、`RESERVE`/`KEEP_RECENT` 预算、结构化摘要模板、增量更新摘要 | **分层**（tau 是单层：老消息→一条 summary，无工具输出分层裁剪）；**证据引用与制品外置**；**`tokensBefore/After` 与 compaction 事件**（tau 无此事件）；真实 tokenizer（tau 用 `CHARS_PER_TOKEN=4`，中文严重失真） | ~40% |
| **② PR Review 效果评估** | 无 | 全部：样本集、标签版本、位置/区间匹配、Judge、仲裁、P/R、归因、回放 | **0%** |
| **③ 长任务可靠执行** | `cancel()` + `CancellationToken`；`before/after_tool_call` 钩子；session JSONL；`_append_interrupted_tool_results()` | 阶段状态机、检查点、**语义幂等键**、并发租约、重试预算、工作区快照、**外部操作结果核对**（tau 的合成结果 ≠ 真实核对） | ~20% |
| **④ SWE-bench 评估** | 只提供"生成补丁的 agent" | `swebench` 官方 harness 接入、instance 固定、baseline/增强对照、成本统计、失败分类 | ~30% |

**结论：能实现，但 tau 只解决「Agent Loop + 事件契约 + 工具定义 + 会话持久化」，
约占总量的 20~25%。四条亮点的实质工作量（80%）在平台层与评估层。**

这反而是好事：**"我用了 tau" 不能当亮点，"我在 tau 之上加的平台层" 才是亮点。**
简历四条写的全是平台层，方向正确，缺的是代码。

## 三、面试题：pi 是 TS 写的，你 Python 写的，能一样吗？怎么重写的？

**这是陷阱题，他在试你会不会吹。千万别说"完全一样"。** 四层递进：

### 第 1 层：先纠正前提（30 秒，诚实）

> "先纠正一下：我不是自己从零重写的，我用的是 HuggingFace 的 `tau`，
> 官方定位就是 *a Python port of Pi's minimalist coding agent*，MIT 协议。
> 我做的是**采用它、并核对它的语义是否与 pi 一致**，然后在上面加平台能力。
> 所以准确说法不是'我重写了 pi'，而是'我验证了 pi 的 loop 语义在 Python 实现上是等价的，
> 并把它当成底座'。"

主动说"不是我写的"，能同时拆掉"吹牛"和"套壳"两个风险，面试官对你的信任度会上升。

### 第 2 层：给等价性证据（不要说"思想一样"，要说"契约一样"）

| pi | tau | 等价 |
| --- | --- | --- |
| 事件表 `agent_start / turn_start / message_* / turn_end / tool_execution_*` | 同名同字段，pydantic 判别联合 | ✅ |
| `steer()` / `followUp()` 队列语义 | `harness.steer()` / `follow_up()` + `QueueMode` | ✅ |
| 工具定义与结果契约 | `AgentTool` / `AgentToolResult` | ✅ |
| 工具并行/串行 | `execution_mode` | ✅ |
| append-only JSONL 会话树 / branch / fork | `tau_agent/session/*` | ✅ |
| abort | `CancellationToken` | ✅ |
| `tool_execution_end.durationMs` | **缺** | ❌ |
| `compaction_start/end`（tokensBefore / estimatedTokensAfter / usage） | **缺** | ❌ |

配一句收尾：

> "我核对下来有两处 pi 有、tau 没有：一是工具执行的 `durationMs`，
> 二是压缩事件里的 `tokensBefore / estimatedTokensAfter / usage`。
> 这两条正好是我成本核算和压缩实验要用的数据，所以我在 `before_tool_call` /
> `after_tool_call` 里自己打点补上了。**这也说明'等价'不是默认成立的，得逐项验证。**"

这段的杀伤力在于：证明你真的读过两边源码，而不是转述别人。

### 第 3 层：区分「语言层差异」与「语义层差异」

**语言层（说明你知道自己踩的是什么坑）：**

| 维度 | TS / pi | Python / tau | 落点 |
| --- | --- | --- | --- |
| 流式 | `AsyncIterable` + `for await` | `async for` + `AsyncIterator` | 等价 |
| 取消 | `AbortSignal`（运行时标准，能穿透 fetch） | `asyncio.CancelledError` + 显式 `CancellationToken` | Python 取消是异常，容易被 `except Exception` 吞掉 → 工具包装层显式检查 token，不靠异常 |
| 类型 | TS 编译期类型，**运行时不校验** | pydantic 运行时校验 | **Python 反而更强**：wire 契约运行时验证；TS 类型擦除后收到脏数据是静默的 |
| 并发 | 单线程 event loop | asyncio + **GIL** | CPU 密集（大文件 grep、全文 tokenize）阻塞 loop → `asyncio.to_thread` / 进程池 |
| 分发 | npm + Node | PyPI `tau-ai`，py3.12+ | Python 侧无 Node 运行时负担 |

**语义层（面试官真正想问的，必须诚实）：**

> "有三处不可能完全一样：
> 1. **类型契约的保障时机不同。** pi 靠 TS 编译期，tau 靠 pydantic 运行时校验 + 测试，
>    所以 tau 有 11KB 的 `test_agent_harness.py`。我在适配层又加了一层 schema 断言，
>    因为不能接受契约漂移在线上才暴露。
> 2. **取消的传播路径不同。** `AbortSignal` 是运行时标准信号，Python 的取消是异常传播，
>    语义更弱。所以我不能用'抛异常'来保证副作用收敛，必须有显式操作记录 + 事后核对。
> 3. **生态是子集。** pi 有 extensions / skills / MCP / codemode，tau 是 Python 版、覆盖更小。
>    但我只用 `AgentHarness` 这一层，不依赖上层扩展生态，所以这个差异对我不构成风险。"

第 3 点是**把弱点转化成"我做了裁剪"**，必须说，否则会被"功能不全"打。

### 第 4 层：反过来说明"我刻意让它不一样"

> "其实我和 pi 的目标不同，所以**不应该**完全一样。pi 是给人用的 CLI，交互优先；
> 我的场景是无人的服务端任务，**阶段状态机优先、可恢复优先、必须审计**。
> 所以我在 tau 之上加了 pi 根本没有的东西：PREPARE / REPRODUCE / REPAIR / VERIFY /
> PACKAGE 阶段状态机、工具权限门、语义幂等键、制品存储、两套离线评估。
> 我是拿 pi 的 loop 语义当底座，往上加平台能力，不是复刻一个 pi。"

## 四、一定会被追问的三句

### 1.「那你为什么不直接用 pi？」（最锋利）

> "我评估过 pi 的 RPC 模式，它生态完整、更成熟，但要引入 Node 运行时、
> 还要自己维护跨进程 JSONL 协议和容器内桥接。我的执行面**已经在容器里**，
> 进程隔离需求已被容器满足，进程内再套一层子进程只是多一个故障点和 IPC 成本。
> 而 tau 是纯 Python，和我的 SWE-bench harness、状态机同语言，能 in-process 拿到
> `before/after_tool_call` 钩子做权限和幂等。
> **但我不赌单一实现 —— 我抽象了 `AgentRuntime` 协议，`TauRuntime` 和 `PiRpcRuntime`
> 都是实现，需要 pi 的扩展生态时可以切过去。**"

### 2.「那你自己到底写了什么？」

一条一条列：

1. `AgentRuntime` 抽象 + `TauRuntime` / `PiRpcRuntime` 两个实现
2. `before/after_tool_call` 里的权限门与 `ToolOperation` 记录（含自补 `durationMs`）
3. 检查点 / 租约 / 语义幂等键 / 重试预算的状态机
4. 分层上下文（工具输出分层裁剪 + 制品引用 + 自补 compaction 事件与 token 计量）
5. 两套评估链路（Review P/R + SWE-bench 对照）

收尾：**"tau 是我用的 20%，这些是我写的 80%。"**

### 3.「tau 才 3k star、135 个 open issue，你敢用到企业里？」

**不要说"没问题"。**

> "我不敢。所以三件事：pin 到具体 commit 不用浮动版本；要改的文件（如 `context_window.py`）
> 直接 fork 纳管；`AgentRuntime` 抽象保证 tau 出问题能切 `PiRpcRuntime`。
> 这是抽象层换来的选择权，不是运气。"

## 五、必须处理的诚信问题

简历写的是**过去完成时**：2026.03—至今、500+ 工程师、Q2 修复 71 个 Bug、178→53 分钟。
但当前代码状态是 **0 行**。两者必须对齐，否则面试官只要问：

- 「71 个 Bug 的完成条件是提交 PR、合并、还是验收？」
- 「178 分钟是端到端历时还是人工操作工时？含不含验证与审核？」
- 「500+ 是累计使用还是活跃使用？」

三条路，必须选一条：

| 选项 | 情况 | 做法 | 开发优先级 |
| --- | --- | --- | --- |
| ① | 数字真实（来自真实工单系统） | 补代码，让实现追上简历 | 优先 M2（可靠性）+ M3（上下文），因为简历里"我负责"的是这两条 |
| ② | 数字不真实 | 删掉或改口径为「PoC 阶段，在 N 个自建样例上…」 | 优先 M4（SWE-bench 子集），最容易一个月内产出真实可复算数字 |
| ③ | 部分为真（71 个是组内总量） | 改成「参与修复 N 个 Bug」 | 同上，先补可验证的小规模数据 |

## 六、四条亮点各自的最小证据（定稿前必须存在）

| 亮点 | 最小证据 | 单靠什么不够 |
| --- | --- | --- |
| 上下文管理与压缩 | 压缩前后输入、状态快照、工具关系完整性检查、同任务对照记录 | 一段压缩提示词 |
| PR Review 效果评估 | 人工核对的样本、标签版本、逐问题匹配与裁决、可复算指标 | 一份模型评审报告 |
| 长任务可靠执行 | 固定基线上的故障注入、恢复轨迹、工作区指纹与外部副作用核对 | 重发原问题后最终跑通 |
| SWE-bench 评估 | 固定样本与配置、预测补丁、官方测试报告、全量成本与失败记录 | 测过几个案例或引用公开榜单 |
