# pi 的插件化程度 vs dsh 的「一切皆插件」

> 决策：**pi 当运行时**，借鉴 dsh（DeepSeek Harness）的插件化思想。
> 本文回答：pi 是不是「一切皆插件」？该借什么、不该借什么？

## 一、结论先行

**pi 不是「一切皆插件」，它是「边缘可插拔 + 装配期依赖注入」。**

| | pi | dsh + Cordis |
| --- | --- | --- |
| 自我定位 | minimal, extensible agent harness | **Everything is a Plugin**（仓库 description 原文） |
| 内核 | **有**：agent loop / session / compaction / model runtime 不是插件 | **无**：「There is no privileged core to patch」 |
| 扩展单元 | extension（TS 模块，default export 工厂） | plugin（向共享 `ctx` 贡献 service / event / effect） |
| 组合方式 | settings + extensions 路径 + `-builtin:<name>` | profile + bundle + `cordis.patch.yml` **分层补丁** + HMR |
| 卸载语义 | `ctx.reload()` **整体替换** extension runtime（文档要求 reload 后不得复用旧状态） | 注册是**可逆 effect**，插件卸载时自动回滚（`unwind`） |
| 插件间协作 | `pi.events`（弱广播） | 服务查找 + 依赖注入 |

## 二、pi 的插件化证据（它其实相当彻底）

### 1. 内置能力本身就是插件

`codemode`、`tool_search`、MCP 都以 `builtin:<name>` 形式作为 extension 加载，
可以用 `-builtin:codemode` 关掉（`docs/sdk.md`、`docs/settings.md`）。

### 2. 可以替换的东西非常多（`docs/extensions.md`「Choose an integration point」）

| 能力 | API |
| --- | --- |
| 观察/修改生命周期 | `pi.on()` |
| 新增模型可调用操作 | `pi.registerTool()` |
| 新增 `/` 命令 | `pi.registerCommand()` |
| 快捷键 / CLI flag | `pi.registerShortcut()` / `pi.registerFlag()` |
| 新增模型 provider | `pi.registerProvider()` |
| 新增 MCP server | `pi.registerMcpServer()` |
| 按请求路由到不同模型 | `pi.registerVirtualModel()` |
| 终端渲染 | renderer + `ctx.ui` |
| 扩展之间通信 | `pi.events` |

### 3. 事件钩子覆盖到几乎每一层（这是最值钱的部分）

| 意图 | 事件 |
| --- | --- |
| 检查/变换/消费原始用户输入 | `input` |
| 改 prompt 段、active tools、加上下文 | `before_agent_start` |
| 观察一次低层 run | `agent_start` / `agent_end` |
| 一次模型响应 + 它的工具调用之后 | `turn_end` |
| 为某次 provider 请求过滤对话消息 | `context` |
| 变换完整 transcript（含 system） | `context_with_system` |
| 改请求头或序列化后的 provider payload | `before_provider_headers` / `before_provider_request` |
| 观察 provider 响应元数据或流事件 | `after_provider_response` / `provider_stream_event` |
| **授权或修改工具调用** | **`tool_call`** |
| 脱敏/标注/替换工具结果 | `tool_result` |
| 追加最终 entry 或请求最后一次继续 | `agent_before_settle` |
| 自动处理全部停止后做通知类工作 | `agent_settled` |
| 初始化/释放会话级资源 | `session_start` / `session_shutdown` |

### 4. 装配期依赖注入（`docs/sdk.md`）

`createAgentSession()` 默认构造 `ModelRuntime`、`SettingsManager`、`SessionManager`、
`DefaultResourceLoader`、默认工具集，但每一个边界都能显式传入替换。
另有 `tools` / `noTools` / `excludeTools` / `customTools` 控制工具集。

**这就是依赖注入——只不过它只在装配那一次发生，之后不可热替换。**

### 5. 甚至「工具在哪台机器上执行」都可以外置

官方 example `examples/extensions/ssh.ts` 的定位是
*「Route built-in tools to another machine — reuses tool operation interfaces instead of
recreating tool contracts」*。说明 pi 的工具执行位置本身是可替换的。

## 三、pi 缺的那部分（dsh 有、pi 没有）

| 能力 | dsh/Cordis | pi |
| --- | --- | --- |
| agent loop 本身可替换 | ✅ `ctx.agentLoop` 是服务 | ❌ 不是插件 |
| 会话日志可替换 | ✅ `ctx.sessions` | ❌ `SessionManager` 只在装配期可注入 |
| 工具注册表可替换 | ✅ `ctx.tools`（带 scope） | ⚠️ 可增删工具，不是替换注册表 |
| 模型适配层 | ✅ `ctx.llm`（adapter seam） | ⚠️ 可注册 provider，不是替换 seam |
| 注册可逆（卸载即回滚） | ✅ effect unwind | ⚠️ 只有 `ctx.reload()` 整体换 |
| 分层补丁组合（base + patch） | ✅ profile / bundle / patch | ❌ settings 是平铺覆盖 |
| 依赖注入到插件之间 | ✅ 服务 + 等依赖就绪 | ❌ 只有 `pi.events` 广播 |
| 热更新 | ✅ `dsh-hmr` | ⚠️ 仅整体 reload |
| 运行期切换实现 | ✅ 配置驱动 | ❌ 需重建 session |

**一句话**：pi 是**「内核固定、边缘自由」**；dsh 是**「无特权内核、全部可换」**。

## 四、pi 的事件钩子 → ForgePilot 的落点（直接可用）

这是本文最实用的部分：四条亮点各自的机制都能挂在 pi 的现成钩子上。

| ForgePilot 需求 | pi 的落点 |
| --- | --- |
| **阶段受限工具集**（REPAIR 只给 read/edit/bash，PREPARE 不给写） | `before_agent_start` 改 active tools；或按阶段重建 session 传不同 `tools` |
| **工具权限门**（fail-closed） | `tool_call` —— 官方 `examples/extensions/permission-gate.ts` 就是范本 |
| **ToolOperation 记录**（幂等键、审计） | `tool_result` 做变换 + 订阅事件流里的 `tool_execution_end`（**pi 有 `durationMs`**） |
| **分层上下文裁剪**（工具输出分层、制品外置） | `context` / `context_with_system`（chained transformation，逐个 handler 传递） |
| **成本计量** | `turn_end` + 事件流里的 `usage` / `durationMs` / `get_session_stats` |
| **取消收敛** | `agent_settled`（唯一「pi 不会自己继续」的信号） |
| **分支持久状态**（结构化任务状态） | `pi.appendEntry()` + `ctx.sessionManager.getBranch()`（⚠️ 必须在 `session_start` 重建，不能用每条 file entry 重建，否则会读到被放弃的分支） |
| **系统提示注入**（阶段约束） | `before_agent_start.systemPromptOptions`（改段，不要整体替换 prompt） |
| **外部工具/凭据不外泄** | MCP（`pi.registerMcpServer()`）或 `ssh.ts` 式工具路由，凭据留在 Python 侧 |

⚠️ 一个必须提前处理的坑：**pi 没有 `compaction_start/compaction_end` 之外的压缩可观测性缺口？**
—— pi **有**这两个事件（含 `tokensBefore`、`estimatedTokensAfter`、`usage`），
所以压缩实验的数据在 pi 路线上是免费拿的。这是 pi 相对 `tau` 的一个明确优势
（tau 没有这两个事件，见 [05](05-tau-HuggingFace的Python版pi.md)）。

## 五、借鉴 dsh 思想时，该插件化什么

**核心洞见：既然 pi 锁死了 agent loop，那插件化的战场就在「pi 的外面」——
你自己的平台层。这正是简历四条所在的位置。**

### 该插件化（变化频繁、需要对照实验）

| 位置 | 做成插件形态的理由 |
| --- | --- |
| **阶段处理器**（PREPARE / REPRODUCE / REPAIR / VERIFY / PACKAGE / PUBLISH） | 每个阶段声明自己的工具集、验证器、上下文策略。新增阶段 = 加一个插件 |
| **工单适配器 / Git 适配器** | 每个外部系统一个插件（GitLab / Codeup / 内部工单），上层流程不感知字段与鉴权差异 |
| **验证器**（构建、测试、复现判定） | 不同项目不同命令，且需要「可信配置」来源 |
| **检索器 / 上下文提供者** | **M4 对照实验就是换插件**：baseline = 只装 read+grep；增强组 = 多装符号检索 / 调用关系插件。同一份代码、同一个 agent，只改装配 |
| **Review Judge 实现** | 换实现做对照、做人工仲裁的并行验证 |
| **模型/预算策略** | 不同阶段不同 thinking level、不同预算 |

### 不要插件化（契约必须唯一、必须可验证）

| 位置 | 理由 |
| --- | --- |
| **阶段状态机本体** | 幂等、租约、重试预算、取消收敛的正确性依赖唯一契约。插件化后无法证明「不会两个实现同时推进一个任务」 |
| **检查点 / ToolOperation / 制品的写入路径** | 审计与恢复的唯一真相源，不能有多个写入实现 |
| **权限判定的最终否决权** | **插件只能加严，不能放宽**。任何插件声明「允许」都不得覆盖平台的拒绝（fail-closed） |

这条「只能加严不能放宽」是安全设计的硬边界，**面试可以单独讲**：
它解释了为什么 `permission-gate` 类插件必须 fail-closed，
也解释了为什么「一切皆插件」在**有副作用、有审计要求**的系统里必须打折扣。

## 六、一句话总结（面试口径）

> "pi 的内核是固定的——agent loop、session、compaction 都不是插件，但它的边缘非常开放：
> 工具、命令、provider、MCP、上下文变换、工具授权、UI 全部可用 extension 注册，
> 连它的内置 codemode 和 tool_search 本身就是可以关掉的 extension。
> 所以 pi 是'内核固定、边缘自由'。
>
> dsh 走得更彻底，它基于 Cordis，官方描述就是 Everything is a Plugin，
> 声明 'There is no privileged core to patch'，连 agent loop 和 session log 都是 `ctx` 上的服务，
> 而且注册是可逆 effect，插件卸载会自动回滚。
>
> 我**没有**照搬'一切皆插件'。我把插件化限制在变化频繁的部分：阶段处理器、外部系统适配器、
> 检索器、Judge 实现——因为我的 M4 对照实验本质上就是'换插件'。
> 但状态机、检查点写入和权限否决权我保持唯一实现，因为幂等和审计的正确性不能有第二个真相源，
> 而且插件只能加严权限、不能放宽。"
