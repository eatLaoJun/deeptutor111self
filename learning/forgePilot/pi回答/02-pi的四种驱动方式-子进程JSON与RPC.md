# pi 的四种驱动方式 · 「子进程 / CLI JSON / RPC」到底是什么意思

## 一、四种驱动方式

| 方式 | 启动 | 谁在控制 | 生命周期 | 适合 |
| --- | --- | --- | --- | --- |
| 交互 TUI | `pi` | 人在键盘上 | 直到退出 | 日常用 |
| Print | `pi -p "..."` | shell 脚本取最终文本 | 一次调用 | `$(...)` 命令替换 |
| **JSON 事件流** | `pi --mode json "..."` | 你的程序读 stdout | 一次调用 | 单次任务 + 要过程数据 |
| **RPC** | `pi --mode rpc` | 你的程序写 stdin 下命令 | 长驻 | 长任务 + 中途干预 |
| SDK | `createAgentSession()` | 同进程内调 TS 方法 | 宿主进程 | Node/Bun 宿主 |

四种模式共用同一套 agent、session、资源、工具（`docs/cli-integration.md`）。
**模式只决定输入怎么进、输出怎么出、进程是否继续存活。**

## 二、真实事件流（本机实测）

```bash
pi --mode json --no-session --no-tools "只回复两个字：收到"
```

输出（JSONL，一行一条）：

```
[session]  [agent_start]  [turn_start]
[message_start] [message_end]              ← 用户消息
[message_start]
  [message_update] text_start
  [delta] "收到"
  [message_update] text_end
[message_end]                              ← 助手消息（权威版本）
[turn_end]  [agent_end]  [agent_settled]   ← aborted: False
```

要点：

- `message_end` 是**权威**完整消息；`message_update` 里的 delta 只用于实时显示
- `agent_end` 只代表**一次低层 run** 结束，之后仍可能有重试 / 溢出恢复 / 压缩重试 / 排队消息
- **`agent_settled` 才代表"pi 不会自己继续了"** —— 平台判断任务阶段性完成必须等这个事件
- stdout 只放 JSONL；日志和诊断在 stderr

## 三、JSON 模式：单向广播，跑完就退

```bash
pi --mode json "修复分页逻辑" > events.jsonl
```

- 所有 prompt 在启动时给定，进程不接收后续命令
- 想让它停只能 `kill`
- 失败/中止会出现在事件流里，但**不一定**产生非零退出码 → 必须解析事件判断成败
- 首条记录是 session header：`{"type":"session","version":3,"id":...,"cwd":...}`

适用：M1 纵切、每个阶段一次调用、以及**故障注入实验**（进程边界清晰，`kill` 就是天然故障点）。

## 四、RPC 模式：双向协议，长驻

```bash
pi --mode rpc --no-session
```

stdin 写命令，stdout 收 `response` + 事件。命令用 `id` 关联：

```jsonc
// → 写入
{"id":"req-2","type":"prompt","message":"修复分页逻辑"}
// ← 只代表"已接受"，不代表模型干完了
{"id":"req-2","type":"response","command":"prompt","success":true,"data":{"disposition":"started"}}
// ← 继续吐事件，直到
{"type":"agent_settled","aborted":false}
```

可用的控制命令（详见 `docs/rpc-commands.md`）：

```
prompt / steer / follow_up / abort / clear_queue
compact / set_auto_compaction / get_session_stats
get_state / get_messages / set_model / cycle_model / get_available_models
set_thinking_level / switch_session / fork / clone / get_entries / get_tree
bash / abort_bash / export_html / get_last_assistant_text / set_session_name
```

**RPC 模式是唯一能做"精确取消"的方式**：`abort` → `agent_settled{aborted:true}`。
`kill -9` 拿不到这个确定的收尾信号。

## 五、状态与调用怎么分工（ForgePilot 口径）

| 场景 | 选哪个 | 理由 |
| --- | --- | --- |
| M1 纵切首通 | JSON | 一个阶段 = 一次调用 = 一个进程，退出即边界，无残留 |
| 正式 REPAIR 阶段 | RPC | 几十轮工具调用，需要 `steer` 注入新约束、需要 `abort` |
| 任务取消 | RPC `abort` | 需要"在途外部操作核对"后再收敛，`kill` 做不到 |
| M3 压缩实验 | JSON 或 RPC | `compaction_end` 直接给 `tokensBefore` / `estimatedTokensAfter` / `usage` |
| M2 故障注入 | JSON | 要在"测试完成但未推进阶段"瞬间杀进程 |

## 六、三个会坑死人的实现细节

1. **必须持续读 stdout。** 管道缓冲满了 pi 会阻塞（`docs/rpc.md`：*a client that stops reading can stall the process*）。
   读循环要独立线程 / async task 常驻。
2. **只按 `\n` 切分。** 用二进制读 + `strip(b"\r")`。文档特意警告 Node 的 `readline`
   会误切 `U+2028 / U+2029`；Python 二进制 `readline` 只按 `\n` 切，是安全的。
   文本模式 + 通用换行不安全。
3. **stdout 是协议专用。** 解析器遇到非 JSON 行应当报错，而不是静默跳过。

## 七、一句话定义

> 从 Python 驱动 pi = 把 pi 当**外部可执行程序**：
> JSON 模式是一次性单向事件流，RPC 模式是长驻双向 JSONL 协议。
> 平台用 `cwd` 隔离工作区、用 `abort` + `agent_settled` 做取消收敛。
