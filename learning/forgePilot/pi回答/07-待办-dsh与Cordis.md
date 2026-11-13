# 待办：dsh（DeepSeek Harness）与 Cordis

> 状态：**已决策** —— 运行时用 pi，dsh/Cordis 只作架构参考，不进主栈。
> 记录于 2026-10-21。详见 [08](08-pi的插件化程度-vs-dsh的Cordis.md)。
> 起因：「之后还要看 dsh，要用到 dsh 中的 Cordis 部分。」

## 已定结论

- **运行时：pi**（JSON / RPC 子进程，见 02）。
- **Cordis 不引入。** 它是 TypeScript/Node 的插件框架，引入即等于把主栈改成 TS，
  与 Python 控制面冲突。
- **借鉴其「一切皆插件」的思想**，但只用在自己的平台层（阶段处理器、外部系统适配器、
  检索器、Judge 实现），状态机与检查点写入保持唯一实现。见 08 第五节。

## dsh 官方事实（补充）

| 项 | 值 |
| --- | --- |
| 仓库 description | **DeepSeek Harness: Everything is a Plugin.** |
| GitHub topics | `ai-agents` / `cordis` / `dsh` / `dsh-plugin` |
| 首页 | `https://deepseek.com/harness` |
| 运行 | `npx @deepseek-ai/dsh web` → 默认 `http://127.0.0.1:3080` |
| 状态 | developer preview，明示「THERE WILL BE COMPATIBILITY-BREAKING CHANGES」 |
| Cordis | `cordiverse/cordis`，TypeScript，9.3k star，自述 *Meta-Framework of Spatiotemporal Composability*，有论文 arXiv:2608.25512 |

§dsh 架构文档（`docs/architecture.md`）原文关键句：

> "Cordis is the framework under dsh: plugins contribute **services, typed events, and
> reversible effects** to a shared context. **Every part of the product is a plugin,
> including the model adapter, the tool registry, the session log, and the agent loop
> itself**, so each is replaceable from configuration."
>
> "**There is no privileged core to patch**: you extend dsh by mounting a plugin beside the
> others, and **registrations are effects that unwind when their plugin unloads**."

核心包的 `ctx` 键：`ctx.sessions` / `ctx.systemPrompt` / `ctx.tools` / `ctx.agents` /
`ctx.agentLoop` / `ctx.llm`。组合机制：profile + bundle + `cordis.patch.yml` 分层补丁 + HMR。

> 这三句是面试引用的黄金材料：**「没有特权内核可以打补丁」+「注册是可逆 effect」。**

## 一、本机探查结果（事实）

### dsh 已安装

```
C:\Users\EDY\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh
```

| 项 | 值 |
| --- | --- |
| 包名 | `@deepseek-ai/dsh` |
| 版本 | `0.2.0-rc.2` |
| 描述 | dsh CLI: profile launch, plugin management, and configuration inspection |
| 仓库 | `github.com/deepseek-ai/deepseek-harness`（monorepo，目录 `apps/cli`） |
| License | MIT |
| 命令 | `dsh` → `lib/bin.js` |

### 它的 Cordis 相关依赖（`package.json` 原文）

```
"@deepseek-ai/dsh-hmr":                    "0.2.0-rc.2"
"@deepseek-ai/cordis-plugin-include":      "~1.0.9"
"@deepseek-ai/cordis-plugin-loader":       "~1.0.5"
"@deepseek-ai/cordis-plugin-timer":        "~1.1.6"
"cordis-client-runner"
"@deepseek-ai/dsh-acp-app":                "0.2.0-rc.2"
```

→ **dsh 的插件装配确实建立在 Cordis 之上**（loader / include / timer 三个官方插件 + cordis 本体）。

### 本机 `~/.dsh/` 目录

```
.agent-presets/     .anonymous-user-id   .credentials.yaml
attachments/        dsh-purge/           plugins/           ← plugins/dsh-purge
profiles/           prompt-inject.md     redteam/
sessions/           storages/
```

→ 形态与 `~/.pi/agent/` 高度类似（profiles ≈ settings、sessions、storages、
prompt-inject.md ≈ 系统提示注入、plugins ≈ extensions、.credentials.yaml ≈ auth.json）。
说明 dsh 与 pi 是同类产品：**agent harness + 插件系统 + 会话存储 + 凭据管理**。

### 相关目录

- `/d/workfile/piagent` —— pi 的 monorepo 源码 checkout（含 `packages/`、`pi-test.sh`、`tui-plan.md`）
- `/d/workfile/pi-desktop-install` —— PI Desktop 安装包 0.20.1
- 全局还装了 `openclaw`、`codebuff`、`opencode-ai`

## 二、这个发现带来的冲突（必须先解决）

| 路线 | 语言 | 插件装配 | 与 `tau` 路线 |
| --- | --- | --- | --- |
| `pi` | TypeScript | pi extensions（TS） | 可行（走 RPC 子进程） |
| `tau` | **Python** | 无 Cordis，Python harness | 基座 |
| `dsh` + Cordis | **TypeScript** | **Cordis（TS 插件容器）** | ⚠️ **互斥** |

**核心矛盾：Cordis 是 TypeScript/Node 生态的插件框架（`@deepseek-ai/cordis-*`）。
如果 ForgePilot 要用 Cordis 做插件装配，那整个控制面就会回到 TypeScript，
与"纯 Python 后端 + tau in-process"的结论直接冲突。**

## 三、三条可选路线（历史记录，已选路线 C + A 的合集：pi 运行时 + 借鉴思想）

### 路线 A：Cordis 只做局部，不侵入主栈

- 控制面（Python）+ 执行面（tau in-process）保持不变
- Cordis 只用来装配**执行面里的工具插件**（如检索器、验证器），作为独立 Node 进程被调用
- 代价：又引入一个 Node 进程，且多一套插件协议
- 收益：可以复用 dsh 生态已有的插件

### 路线 B：全栈转 TS，用 dsh + Cordis 重做

- 控制面也改成 TypeScript，直接复刻 dsh 的插件装配方式
- 代价：放弃 tau，放弃 Python 侧 SWE-bench / 状态机的语言一致性；
  业务代码全部重写
- 收益：与 dsh/pi 生态完全对齐，插件化程度最高
- ⚠️ 注意：**这条路线会让此前的 Python 论证全部作废**

### 路线 C：先不动 dsh，只做 Python 纵切

- 先把 M1（单 Bug 端到端）用 tau 打通，产出可运行代码与真实证据
- Cordis 作为**架构参考**而非依赖：读懂它的插件生命周期/依赖注入思想，
  在 Python 侧用等价的注册表/依赖注入实现（你的 TMAP 简历里已有"单例 + 注册表统一管理 20+ 场景"的经验）
- 收益：不被技术选型阻塞；面试时可以说"我参考了 Cordis 的插件装配模型，
  但按团队语言栈用 Python 实现了等价机制"
- 代价：不是"真的用了 Cordis"

## 四、待确认问题清单

- [ ] **使用 dsh 的目的是什么？** 是（a）作为 ForgePilot 的 agent 运行时，
      （b）作为 Cordis 插件机制的学习对象，（c）作为独立工具提升自己日常效率？
      三者的结论完全不同。
- [ ] dsh 是否有 SDK / 可编程接口（还是只有 CLI）？需要读 `deepseek-harness` 仓库的
      `apps/` 与 `packages/` 结构。
- [ ] Cordis 的插件模型具体是什么（服务注册 / 依赖注入 / 生命周期 hook / 热重载）？
      能否映射到 Python（如 `dependency-injector`、`pluggy`、自写注册表）？
- [ ] dsh 与 pi 的事件/会话契约是否一致（若一致，`AgentRuntime` 抽象可以三实现：
      tau / pi / dsh）。
- [ ] 简历技术栈那一行要不要写 Cordis？（**只有真的用了才写**）

## 五、下一步建议（已执行结论）

**运行时定为 pi，Cordis 只作参考思想。** 不要为了 Cordis 阻塞 M1。
M1 的价值是"让项目从 0 行代码变成可运行"，这个价值与插件框架无关。
等 M1 跑通、`AgentRuntime` 抽象落地后，Cordis 的任何结论都只是"多一个实现"，
不会推翻已有代码。

同时并行做一件事：读 `deepseek-harness` 仓库结构，把 Cordis 的插件模型
用 500 字写清楚（服务、依赖、生命周期、加载顺序、冲突处理），
这份笔记本身就是面试里"你理解插件化架构"的证据。
