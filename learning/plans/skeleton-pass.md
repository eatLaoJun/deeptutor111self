# 骨架速通计划：过一遍 chat 主链

> 目标：4 个晚上学完后，能脱稿**口头讲完**这张大箭头，每个节点一句话职责 + 一个文件。
>
> 完成线（不达到不算过完）：
>
> ```
> 一条消息 → UnifiedContext → ChatOrchestrator → Capability → AgentLoop → StreamBus → 事件回前端
> ```
>
> 纪律：**前 3 晚只看函数名和职责，不钻函数体**。看到函数体就停——细节是第二阶段的事。
> 钻进 `_call_llm` 那一百行就是掉进细节黑洞，当晚就困。

## 每晚 30 分钟模板

```
0–3 分   复习:翻手册上一节结论,口头讲一遍(讲不出就翻)
3–8 分   定今晚的一个点(从下表挑)
8–23 分  跑/读:启发后端 → 看 [TRACE] 日志 → 在代码里定位那条日志对应的函数
23–28 分 输出:用手册模板写一小节,或口头费曼一遍
28–30 分 收尾:手册更新记录写一行,标明天要看什么
```

## 四晚排表

### 第 1 晚：统一输入 + 事件总线

- 看什么：手册 4、5.1、5.4 + `deeptutor/core/context.py`、`deeptutor/core/stream_bus.py`
- 只看：UnifiedContext 有哪些字段、StreamBus 有哪些方法名
- 产出：能讲这句话——“一条消息进来先被打成一个统一上下文,能力只往总线发事件,不直接碰 UI”
- 完成：`daily-points-queue.md` 第 1 晚打勾
- 状态：✅ 已完成（2026-07-28/29，UnifiedContext=原料筐、StreamBus=不存储只发事件）

### 第 2 晚：编排器选能力

- 看什么：手册 6（前半）+ `deeptutor/runtime/orchestrator.py`、`deeptutor/agents/chat/capability.py`
- 只看：`ChatOrchestrator.handle()` 那 10 步、chat 入口链
- 产出：能讲——“编排器选能力、起 bus、跑 capability、最后发 DONE”
- 完成：打勾
- 状态：✅ 已完成（2026-07-29，10 步细到机制层：并发、close 收尾、SESSION 不走 bus、EventBus≠StreamBus）

> 备注：`EventBus` / `_publish_completion` 这条目前**只用知道「它是一条独立的项目级公告板、非命脉、吞异常」**就行，**第三阶段不用核**。它在骨架里只是第 10 步的一个收尾符号，钻进去属于偏题。等第三阶段啃完后、对项目全貌有兴趣时再回来看 `event_bus` 的订阅者都有谁。


### 第 3 晚：单个循环

- 看什么：手册 6.2、6.5 + `deeptutor/agents/chat/agent_loop.py` 的 `run` / `_run_loop`
- 只看：单循环那张伪代码图（不看 `_call_llm` 函数体）
- 产出：能讲——“一份不断增长的 messages,有 tool_calls 就继续,没有就是最终答案”
- 完成：打勾

### 第 4 晚：用日志把前 3 晚串成事实

- 做什么：启动后端 → 浏览器发一条消息 → 把终端 `[TRACE]` 日志贴一段进手册 13 章变更记录
- 产出：能讲——“我亲眼看到这条链跑了一遍”
- 完成：打勾,骨架速通结束

## 完成判据

四晚打勾 + 能脱稿讲完顶部那张大箭头图（每节点一句话职责 + 一个文件），即为“过一遍”完成。
之后进入第二阶段：按 `daily-points-queue.md` 逐日啃实现细节。
