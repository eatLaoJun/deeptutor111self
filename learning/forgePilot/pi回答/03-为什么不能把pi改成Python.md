# 为什么不能把 pi 改成 Python

## 一、结论先行

1. **没有 Python 版 pi。** npm 包里没有任何 Python 产物，SDK 只有 `dist/index.d.ts`（TS 类型声明）。
2. **但你不需要写 TS。** 若走 RPC/JSON 子进程方案，你的业务代码 100% 是 Python，
   一行 TS 都不写。pi 只是一个外部命令，和你在 Python 里调 `git`、`ffmpeg` 同级。
3. **重写 pi 是一笔亏本买卖**，理由见第三节。
4. **现成的替代品已经存在**：`huggingface/tau`，见 [05](05-tau-HuggingFace的Python版pi.md)。

## 二、分清两件事

| 问题 | 答案 |
| --- | --- |
| pi 自身能不能换成 Python 实现？ | 不能（除非重写整个项目） |
| 用 Python 做项目，要不要写 TS？ | 走 RPC/JSON 子进程方案：**0 行 TS** |

方案对照（"你写多少 TS"这一列才是关键）：

| 方案 | 你的后端 | 你写的 TS | 备注 |
| --- | --- | --- | --- |
| A 全 TS + SDK | TypeScript | 全部 | 被迫用 TS 写业务 |
| **B pi 子进程** | **Python** | **0 行** | 从命令行驱动 |
| C Python + TS 薄 harness | Python + 子进程 | 一层 SDK 包装 | 最差，白养一层 TS |
| D tau（Python 版 pi） | Python | 0 行 | in-process，见 05 |

## 三、为什么不该重写 pi

### 1. 工作量

pi 的 agent loop、会话树（branch/fork/compaction entry）、工具系统、13 个内置扩展、
6 个 provider 适配、TUI —— 几万行。重写等于重新造一个 pi。

### 2. 简历四条亮点全部长在 pi 的现成能力上

| 亮点 | 依赖 pi 的什么 |
| --- | --- |
| 上下文管理与压缩 | `compaction_end` 事件直接给 `tokensBefore` / `estimatedTokensAfter` / `usage` |
| 长任务可靠执行 | RPC 的 `abort` + `agent_settled` 才能做取消收敛 |
| 会话 vs 任务状态 | pi 的 JSONL 会话树是现成的对照组 |
| SWE-bench 评估 | `--no-session`、工具集裁剪、`get_session_stats` 拿 token 成本 |

重写之后，"你说的 pi 是什么意思"这个问题就答不上来了。

### 3. 语言不是主要成本

Node 22.19+ 只是**运行时**，不是你要写的东西。部署时和装 Python 依赖没区别，
Dockerfile 里多一行 `npm i -g @earendil-works/pi-coding-agent`。
缓解依赖链风险的手段：固定版本 + pi 支持 bun 编译单文件二进制（`package.json` 的
`build:binary` → `dist/pi`）+ 镜像 SBOM 扫描。

## 四、想给模型加自定义工具，也不用写 TS

pi 的 extension 是 TS 模块（运行在 pi 进程内），但有两种纯 Python 路径：

```
pi ──MCP(stdio)──> 你的 Python MCP server ──> 工单系统 / Git 平台
```

```bash
pi mcp add ticket-tools -- python -m forgepilot.mcp_ticket
```

而且这条路径**在架构上比写 TS extension 更正确**，正好对上 ForgePilot 的设计原则：

> 「凭据由后端受控保管，不放入 Prompt、普通日志或交给模型读取」
> 「工单、评论和代码是任务资料，不是权限指令」

把 `get_ticket` / `create_merge_request` 放进 pi 进程内 = 把凭据送进 agent 进程。
放在 Python 侧、模型只能通过受限 MCP 调用、写操作永远由后端状态机校验，才安全。

**所以"不写 TS"在这里是架构优点，不是妥协。这句话面试可以直接讲。**

## 五、如果真的必须是"纯 Python + in-process"

那就不要用 pi，改用 `huggingface/tau`（Pi 的 Python 实现）。
代价与收益见 [05](05-tau-HuggingFace的Python版pi.md)，与 pi 的差异清单也在那里。
