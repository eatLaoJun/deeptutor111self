# LangGraph 图执行、State、Loop 与工具调度面试讲解

> 本文只讲 LangGraph 的通用运行机制，不绑定任何具体业务项目。
>
> 内容基于 2026-09-09 可访问的 LangGraph Python 官方文档整理。面试时先讲稳定概念，
> 再讲版本敏感的 API。当前文档标明 `langgraph>=1.2` 的 timeout 和 `error_handler`
> 仍属于 alpha 能力，实际编码前应再核对所安装版本。

## 一、先给结论

### 30 秒版本

> LangGraph 本质上是一个有状态的图执行引擎。开发者定义 State、Node 和 Edge，运行时按照
> Pregel 风格的 Superstep 推进：同一 Superstep 内满足条件的节点并行读取同一份状态快照，
> 全部完成后再通过 Reducer 合并更新，然后根据边计算下一批节点。普通 DAG 可以表达固定依赖，
> 条件边和回边可以表达 Agent Loop；ToolNode 则负责执行模型产生的工具调用。重试、持久化和
> 权限不是一回事：RetryPolicy 处理节点异常，Checkpointer 保存执行状态，工具权限仍要由应用
> 在工具可见性、执行入口和具体资源访问处分别校验。

### 一句话版本

> Node 负责工作，Edge 负责路由，State 负责跨节点传递数据，Reducer 负责合并并行写入，
> Checkpointer 负责恢复，Runtime 负责提供本次调用的可信上下文。

## 二、它到底是不是 DAG

DAG 是 Directed Acyclic Graph，即有向无环图。下面这种固定流程是 DAG：

```text
A -> B -> D
 \-> C -/
```

但典型 Agent 会从工具节点回到模型节点：

```text
START -> agent -> tools -> agent -> ... -> END
```

因为存在 `tools -> agent` 回边，所以它在数学上不是 DAG，而是有环有向图。LangGraph 的
`StateGraph` 同时支持无环工作流和有环 Agent 工作流。因此面试中更严谨的说法是：

> LangGraph 是图运行时；其中一部分流程可以是 DAG，加入 Agent Loop 后整张图可能有环。

## 三、核心对象分别负责什么

| 对象 | 核心职责 | 不负责什么 |
| --- | --- | --- |
| `State` | 保存当前线程中的可变工作状态 | 不等于数据库，也不应塞入所有长期数据 |
| Node | 读取 State，执行逻辑，返回局部 State 更新 | 不直接决定所有后续节点 |
| Edge | 描述固定顺序、条件分支、并行分叉和回边 | 不执行具体业务逻辑 |
| Reducer | 决定同一个 State key 的更新如何合并 | 不负责调度节点 |
| Runtime Context | 提供本次运行的用户、租户和配置等可信信息 | 默认不会自动完成业务鉴权 |
| Checkpointer | 按 thread 保存图状态快照和执行位置 | 不等于跨用户长期记忆库 |
| Store | 保存跨 thread 的偏好、事实等长期数据 | 不负责恢复当前图执行位置 |

### Node 为什么返回“局部更新”

节点不需要返回完整 State，只返回它负责修改的字段：

```python
from typing_extensions import TypedDict


class State(TypedDict):
    question: str
    answer: str
    attempts: int


def answer_node(state: State) -> dict:
    return {
        "answer": f"Answer for: {state['question']}",
        "attempts": state["attempts"] + 1,
    }
```

运行时把返回值当作 State update，而不是要求节点原地修改传入对象。这样才能清楚记录每个
节点产生了哪些写入，并在并行执行、Checkpoint 和重放时保持可控。

### Reducer 为什么重要

如果多个并行节点都向同一个列表写结果，需要明确告诉运行时如何合并：

```python
import operator
from typing import Annotated
from typing_extensions import TypedDict


class State(TypedDict):
    query: str
    results: Annotated[list[str], operator.add]
```

此时两个节点分别返回 `{"results": ["B"]}` 和 `{"results": ["C"]}`，Reducer 会追加两批
结果。没有 Reducer 时，普通顺序更新通常采用覆盖语义；同一 Superstep 中多个节点同时写
同一个只允许单值更新的 key，则可能产生并发更新错误。

即使使用列表追加 Reducer，也不要依赖并行分支的完成顺序。如果输出必须稳定排序，应同时写入
任务序号，例如 `(index, result)`，在下游节点显式排序。

## 四、图是怎样一步一步执行的

### 从定义到运行

典型生命周期是：

```text
定义 State
  -> 创建 StateGraph
  -> add_node
  -> add_edge / add_conditional_edges
  -> compile
  -> invoke / ainvoke / stream
```

`compile()` 不会预先执行节点。它主要检查图结构，并绑定 Checkpointer、Store、中断点等
运行能力。真正的计算发生在 `invoke()`、`ainvoke()` 或流式调用阶段。

### Superstep 心智模型

LangGraph 使用受 Pregel 启发的离散 Superstep。可以把运行时近似理解成：

```python
state = initial_input
ready_nodes = entry_nodes

while ready_nodes:
    snapshot = state
    writes = await run_ready_nodes(snapshot)
    state = apply_reducers(state, writes)
    save_checkpoint_if_configured(state)
    ready_nodes = route_by_edges(state)
```

这段代码只是心智模型，不是 LangGraph 源码。最关键的是三个时点：

1. 一个 Superstep 开始时形成状态快照。
2. 本步内的所有活跃节点基于这个快照执行。
3. 本步结束时统一归并写入，再为下一个 Superstep 计算路由。

假设依赖关系是 `A -> [B, C] -> D`，时间线如下：

```text
Superstep 1: A 读取 S0，产生 WA
Barrier:     S1 = reduce(S0, WA)

Superstep 2: B 读取 S1，产生 WB
             C 读取 S1，产生 WC
Barrier:     S2 = reduce(S1, WB, WC)

Superstep 3: D 读取 S2，产生 WD
Barrier:     S3 = reduce(S2, WD)
```

因此 B 和 C 在执行期间看不到彼此本步刚生成的结果。D 必须等到下一步才能看到合并后的结果。

## 五、依赖关系、串行与并行

### 固定串行

```python
builder.add_edge("A", "B")
builder.add_edge("B", "C")
```

这表示 `A -> B -> C`，三个节点位于不同 Superstep。

### 固定并行与严格汇合

```python
builder.add_edge("A", "B")
builder.add_edge("A", "C")
builder.add_edge(["B", "C"], "D")
```

`B` 和 `C` 在同一个 Superstep 并行，列表形式的 edge 表示 D 必须等待二者都实际完成，然后只
执行一次。

列表 edge 与下面两条独立 edge 不是完全相同的语义：

```python
builder.add_edge("B", "D")
builder.add_edge("C", "D")
```

如果 B、C 分支长度相同，它们可能表现得一样；如果分支长度不同，独立 edge 会让 D 在不同
Superstep 中被触发多次。列表 edge 会等待列出的所有前置节点，但如果条件路由根本没有选择
其中一个前置节点，D 也永远不会运行。

### `defer=True` 什么时候用

`defer=True` 会把节点推迟到整张图没有其他 pending task 时再运行，适合“所有实际选中的
分支结束后统一收尾”。它等待的是全图 pending task，而不是只等待某几个局部上游，因此不要把
它简单理解成普通 join。

### 条件分支

```python
from typing import Literal
from langgraph.graph import END


def route(state: State) -> Literal["search", "answer", END]:
    if state.get("done"):
        return END
    if state.get("need_search"):
        return "search"
    return "answer"


builder.add_conditional_edges("plan", route)
```

条件函数读取已经归并完成的当前 State，返回一个或多个目标节点。

### 动态并行：`Send`

静态 edge 适合构图时就知道 B、C 两个分支的情况。如果运行时才知道任务数量，例如检索出
20 篇文档后分别总结，可通过 `Send` 动态创建多份节点任务：

```python
from langgraph.types import Send


def fan_out(state):
    return [
        Send("summarize_one", {"document": document})
        for document in state["documents"]
    ]
```

这些动态任务通常并行执行，再通过带 Reducer 的 State 字段收集结果。这就是典型 Map-Reduce。

### `Command` 与 Edge 的区别

Edge 把控制流固定在图定义中。`Command` 可以让节点在一次返回中同时完成：

```text
更新 State + 指定下一跳 goto
```

它适合路由目标依赖节点内部结果的情况，但也会让控制流分散进节点实现。面试中可以说：固定
拓扑优先用 Edge，需要“计算结果与路由不可分割”时再考虑 Command。

## 六、Agent Loop 怎样执行

下面是一个最小化的“模型节点与工具节点循环”：

```python
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.graph import MessagesState, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


@tool
def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return f"Weather data for {city}"


tools = [get_weather]
model = init_chat_model("provider:model-name").bind_tools(tools)


async def call_model(state: MessagesState) -> dict:
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


builder = StateGraph(MessagesState)
builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

graph = builder.compile()
```

这里的循环按以下顺序运行：

1. `agent` 读取当前 messages 并调用模型。
2. 模型没有返回 `tool_calls` 时，`tools_condition` 路由到 `END`。
3. 模型返回工具调用时，路由到 `tools`。
4. `ToolNode` 执行工具，并产生与每个 `tool_call_id` 对应的 `ToolMessage`。
5. 工具结果通过 messages Reducer 加入 State。
6. `tools -> agent` 回边启动下一轮模型调用。
7. 下一轮模型读取工具结果，决定继续调用工具还是输出最终答案。

一次“用户请求”可能包含多次模型调用。一次 Agent Loop 也不等于一次工具调用。

### Loop 如何结束

常见结束条件包括：

- 最后一条 AIMessage 没有工具调用，路由到 `END`。
- State 中的业务完成标记为真，条件边路由到 `END`。
- 工具设置为直接返回，并由更高层 Agent 语义短路后续模型调用。
- 人工拒绝继续执行，恢复后路由到 `END` 或取消分支。
- 超过 `recursion_limit`，抛出 `GraphRecursionError`。

`recursion_limit` 计算的是 Superstep，不是用户对话轮数，也不是 RetryPolicy 的重试次数。如果
一个循环包含 `agent` 和 `tools` 两个节点，一圈通常就至少占两个 Superstep。

## 七、工具之间怎样并行或串行

需要区分三个层次。

### 第一层：图节点并行

当边把 A 同时连接到 B、C 时，B、C 是两个独立图任务，在同一 Superstep 并行执行。运行图时
可以配置 `max_concurrency` 限制同时运行的图任务数量。

### 第二层：一个 ToolNode 内的多个工具调用

支持并行工具调用的模型，可以在同一条 AIMessage 中返回多项 `tool_calls`：

```text
AIMessage.tool_calls:
  - get_weather(city="Beijing")
  - get_weather(city="Shanghai")
```

`ToolNode` 会处理这一批调用，等待全部工具结束后，把对应的 ToolMessage 一起交给后续步骤。
这属于批次内的 fan-out/fan-in。

部分模型适配器支持在 `bind_tools` 时设置 `parallel_tool_calls=False`，限制模型每次只产生一个
工具调用。但这是模型侧选择约束，不是整个图的并发控制。

### 第三层：工具内部并发

工具本身可能再并发访问数据库、搜索服务或对象存储。这部分不由图拓扑自动管理，仍要在工具或
Service 层设置连接池、Semaphore、速率限制、超时和取消传播。

### 有依赖的工具不能放进同一批盲目并行

假设：

```text
A: 获取订单 ID
B: 根据订单 ID 查询物流
C: 根据物流结果生成补偿方案
```

B 依赖 A，C 又依赖 B，就应该用不同节点或不同 Agent Loop 轮次串行执行。LangGraph 和
ToolNode 不会仅根据工具描述自动推导 `depends_on`。

如果关系是：

```text
A: 解析用户条件
B: 查询库存
C: 查询物流
D: 综合库存和物流
```

合理链路才是：

```text
A -> [B || C] -> D
```

面试中可以概括为：

> 并发来自“同一 Superstep 的多个图任务”或“一条模型消息中的多个独立工具调用”；
> 依赖来自 Edge、条件路由或显式计划数据，框架不会凭空推断工具间的数据依赖。

## 八、失败、重试与恢复

### RetryPolicy 的触发条件

节点配置 `RetryPolicy` 后，只有节点抛出的异常匹配 `retry_on` 时才会重试：

```python
from langgraph.types import RetryPolicy


retry_policy = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    retry_on=(TimeoutError, ConnectionError),
)

builder.add_node(
    "call_remote_api",
    call_remote_api,
    retry_policy=retry_policy,
)
```

当前官方文档中的默认参数是：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `max_attempts` | `3` | 包含第一次执行在内的最大尝试次数 |
| `initial_interval` | `0.5` 秒 | 第一次重试前等待时间 |
| `backoff_factor` | `2.0` | 后续等待时间倍数 |
| `max_interval` | `128.0` 秒 | 单次退避上限 |
| `jitter` | `True` | 加入随机抖动，避免同时重试 |

默认策略不会重试多类确定性或编程错误，例如 `ValueError`、`TypeError`、`SyntaxError`、
`RuntimeError` 和普通 `OSError`。常见 HTTP 客户端异常通常只对 5xx 重试；节点超时产生的
`NodeTimeoutError` 默认可重试。

### 返回失败对象不等于抛异常

下面的节点从 LangGraph 角度看是正常完成，不会触发 RetryPolicy：

```python
def call_api(state):
    try:
        return {"result": remote_call(), "success": True}
    except Exception as exc:
        return {"error": str(exc), "success": False}
```

如果希望 LangGraph 自动重试，就必须让可重试异常抛到节点边界。另一种设计是把错误写入 State，
通过条件边进入自定义重试、换工具或人工处理分支。两者的差别是：前者是 Runtime 级重试，后者
是工作流语义级恢复。

### ToolNode 捕获错误后的影响

当前 ToolNode 默认会把工具参数调用错误转换成可供模型读取的错误消息，而工具执行异常通常继续
向外抛。配置 `handle_tool_errors=True` 或自定义 handler 后，更多异常会被转换成 ToolMessage。

一旦异常被转换为普通 ToolMessage，外层节点 RetryPolicy 就看不到异常。此时下一轮模型可以
调整参数后再次调用工具，但那是模型驱动的语义重试，不是同一次节点尝试的自动重跑。

### 并行 Superstep 的失败语义

同一 Superstep 中 B、C 并行运行，如果 C 抛出未处理异常：

```text
B 成功产生 WB
C 抛异常
```

这一 Superstep 不会把 WB、WC 作为完整的新 State 提交。配置 Checkpointer 后，已经成功的 B
可以保存为 pending write；恢复执行时只重跑失败分支，避免重复调用成功分支。

这里的“事务”只针对图状态归并，不代表外部副作用自动回滚。如果 B 已经发出邮件、扣款或写入
第三方系统，LangGraph 不会替你撤销。带副作用节点应使用幂等键、去重表或 Saga 补偿流程。

### 重试耗尽后怎么办

处理方式可以分成三类：

| 错误类型 | 推荐策略 |
| --- | --- |
| 网络抖动、限流、临时 5xx | RetryPolicy、退避、抖动和总 deadline |
| 参数错误、权限错误、确定性业务错误 | 不自动重试，路由到修正或明确失败分支 |
| 模型可修正的工具错误 | 转成 ToolMessage，让模型调整参数或选择其他工具 |

当前 Python 文档还提供节点级 timeout 和 `error_handler`，执行顺序是“尝试执行、超时或异常、
按策略重试、耗尽后进入 error handler”。这两项要求 `langgraph>=1.2`，当前仍标记为 alpha，
面试中应说明版本边界。

## 九、Checkpointer、Store 与 Interrupt

### Checkpointer 保存什么

编译图时绑定 Checkpointer：

```python
from langgraph.checkpoint.memory import InMemorySaver


checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {
    "configurable": {
        "thread_id": "conversation-001",
    }
}

result = graph.invoke(
    {"messages": [{"role": "user", "content": "Hello"}]},
    config=config,
)
```

Checkpointer 按 `thread_id` 保存状态快照，使同一线程可以继续对话、中断恢复、故障恢复和查看历史
状态。`InMemorySaver` 适合示例和测试，生产环境应使用持久化实现。

### Store 与 Checkpointer 不要混用

```text
Checkpointer: 这一次图执行到了哪里，当前 State 是什么
Store:         这个用户跨会话有哪些偏好、事实或长期资料
```

删除某个 thread 的 Checkpoint 不应自动删除用户长期记忆；长期 Store 也不能单独告诉运行时某个
节点执行到了哪里。

### Interrupt 如何暂停和恢复

节点可以调用 `interrupt()` 暂停图，把审批请求或缺失信息返回调用方。调用方之后通过
`Command(resume=...)` 恢复同一个 thread。

恢复时会从包含 `interrupt()` 的节点开头重新执行，而不是从函数中断语句的下一行继续。因此
中断前执行的日志、写库或外部调用必须幂等，或者移动到恢复后的安全位置。

`interrupt()` 使用专门的运行时控制异常传播，不应被宽泛的 `except Exception` 吞掉；它也不会
进入普通 RetryPolicy 或节点 `error_handler`。

## 十、不同工具的权限怎样设计

### 先分清“可见”与“可执行”

把某个工具绑定给模型，只表示模型能看到它的名称、描述和参数 Schema。隐藏工具 Schema 可以
减少模型误调用，但不是完整安全边界。

可靠权限至少需要四层：

| 层次 | 作用 |
| --- | --- |
| 工具可见性 | 按用户角色、租户和场景，只向模型暴露允许选择的工具 |
| 执行入口校验 | ToolNode 或自定义 dispatcher 再确认工具名属于本轮 allowlist |
| 资源级校验 | 工具内部检查用户是否拥有目标文件、订单或数据库记录 |
| 基础设施隔离 | 文件、命令、网络、凭据、并发和速率采用最小权限控制 |

### ToolRuntime 适合传递可信身份

工具可以声明 `runtime: ToolRuntime`。这个参数由运行时注入，不会出现在发给模型的工具 Schema
中，因此适合读取服务端确定的用户、线程、Store 和执行信息：

```python
from dataclasses import dataclass
from langchain.tools import ToolRuntime, tool


@dataclass(frozen=True)
class UserContext:
    user_id: str
    tenant_id: str
    allowed_tools: frozenset[str]


@tool
def read_private_record(record_id: str, runtime: ToolRuntime) -> str:
    """Read a record that belongs to the current user."""
    context = runtime.context

    if "read_private_record" not in context.allowed_tools:
        raise PermissionError("Tool is not allowed for this run")

    # The service must also verify that record_id belongs to this user and tenant.
    return record_service.read(
        record_id=record_id,
        user_id=context.user_id,
        tenant_id=context.tenant_id,
    )
```

图构建时应声明 `context_schema=UserContext`，调用时再由服务端传入经过认证的 Context：

```python
builder = StateGraph(MessagesState, context_schema=UserContext)
# Add nodes and edges before compiling.
graph = builder.compile()

result = graph.invoke(
    {"...": "..."},
    context=UserContext(
        user_id="authenticated-user-id",
        tenant_id="authenticated-tenant-id",
        allowed_tools=frozenset({"read_private_record"}),
    ),
)
```

模型可以控制 `record_id`，但不能控制可信的 `user_id` 和 `tenant_id`。即使模型在普通参数中
伪造另一个用户 ID，工具也应该忽略它，始终使用 Runtime Context 中的身份。

### 不同风险工具采用不同策略

| 工具类型 | 合理权限策略 |
| --- | --- |
| 只读公开搜索 | 域名白名单、速率限制、结果大小限制 |
| 用户私有数据读取 | 用户身份、租户、资源归属三重校验 |
| 写数据库或发送消息 | 幂等键、审计、细粒度 scope，必要时人工确认 |
| 文件读写 | 限定 workspace，解析规范化路径后再次检查边界 |
| 代码和命令执行 | 独立沙箱、CPU/内存/时间限制、网络和挂载白名单 |
| 管理员操作 | 不向普通用户暴露 Schema，执行入口仍校验角色 |

高风险工具可以结合 Human-in-the-loop，在执行前让用户 approve、edit 或 reject。启用这种暂停恢复
能力需要 Checkpointer，但 Checkpointer 本身并不会替代权限判断。

### 面试中的标准回答

> LangGraph 提供 ToolRuntime、ToolNode 和 Interrupt 等运行机制，但不会自动理解我们的业务权限。
> 我会先根据服务端身份计算本轮工具白名单，让模型和执行层使用同一份不可扩大的 allowlist；
> 再在工具内部校验资源归属，把用户身份通过模型不可控的 Runtime Context 注入。文件和命令工具
> 还要进入沙箱，高风险写操作增加人工审批和审计。因此工具 Schema 过滤是第一层，不是唯一层。

## 十一、常见面试追问

### 1. 同一 Superstep 的节点能读到彼此刚写的数据吗

不能。它们读取同一个步骤开始时的 State 快照，写入在 Barrier 处统一合并。下一个 Superstep
才会读取合并后的新 State。

### 2. LangGraph 怎么判断两个工具是否可以并行

框架不理解业务依赖。图节点是否并行由 Edge 和当前路由决定；同一 AIMessage 中的多个工具调用
通常被 ToolNode 当作同批独立任务。业务上有前后依赖时，开发者必须拆成不同节点、不同轮次，
或者在 State 中显式维护计划和依赖状态。

### 3. 两条 `B -> D`、`C -> D` edge 就一定代表 D 等待二者吗

不一定。分支长度不同时，独立 edge 可能在不同 Superstep 多次触发 D。确定需要严格等待固定的
B、C 时，使用 `add_edge(["B", "C"], "D")`；等待所有实际选择分支收尾时再评估 `defer=True`。

### 4. `recursion_limit=10` 是最多重试十次吗

不是。它限制整张图最多执行多少个 Superstep。节点重试次数由 RetryPolicy 的 `max_attempts`
控制，工具自身的 API 重试又可能是另一层预算。

### 5. 工具返回 `success=False` 会自动触发 RetryPolicy 吗

不会。RetryPolicy 观察异常，不理解业务返回对象。要么抛出可重试异常，要么通过条件边实现业务
重试逻辑。

### 6. Checkpoint 能保证外部操作 Exactly Once 吗

不能。它可以恢复图状态、保留成功节点的 pending writes，但无法自动回滚已发生的外部副作用。
Exactly Once 仍依赖幂等键、去重、事务消息或补偿机制。

### 7. ToolRuntime 是否就是权限系统

不是。它是运行时依赖注入入口，可以提供可信身份和上下文；具体 allowlist、资源归属、Sandbox
和审批规则仍由应用实现。

### 8. 并行是不是一定更快

不是。只有互相独立、以 I/O 等待为主的任务通常适合并行。共享限流、数据库锁、CPU 密集任务、
大上下文归并和外部服务配额都可能让并行收益下降，甚至增加失败率。

## 十二、3 分钟面试口述稿

> LangGraph 可以理解为一个面向 Agent 和长流程的有状态图执行引擎。它的核心抽象是 State、
> Node 和 Edge：State 保存当前执行快照，Node 读取 State 并返回局部更新，Edge 决定下一步运行
> 哪些节点。图在使用前需要 compile，真正调用时按照 Pregel 风格的 Superstep 推进。
>
> Superstep 是理解它执行语义的关键。同一步里满足条件的节点可以并行执行，但它们读取的是同一
> 份旧状态，不能立即看到其他并行节点刚产生的结果。等本步所有节点完成后，运行时才通过每个
> State 字段配置的 Reducer 合并更新，再计算下一批节点。所以像 A 后面同时执行 B、C，再让 D
> 汇总，可以写成 A 分别连接 B、C，再用列表形式的 edge 让 D 严格等待二者。运行时才知道任务
> 数量时，则可以用 Send 做动态 Map-Reduce。
>
> Agent Loop 是在图里增加回边。例如模型节点判断最后一条消息有没有 tool_calls：没有就进入
> END，有就进入 ToolNode。ToolNode 执行工具并把 ToolMessage 写回 State，再通过回边进入模型
> 节点。模型基于工具结果继续决策，直到不再调用工具。因为存在回边，这种图严格来说不再是 DAG。
> recursion_limit 用于限制 Superstep、防止死循环，它和节点重试次数不是一个概念。
>
> 并发也要分层。图里的多个节点可以在同一 Superstep 并行；同一条 AIMessage 里的多个独立工具
> 调用也可以由 ToolNode 批量并发；工具内部还可能有自己的并发。LangGraph 不会根据工具描述
> 自动推导业务依赖，有前后依赖的工具必须拆到不同节点或不同模型轮次。生产中还要分别设置图级
> 并发、工具级 Semaphore、超时和外部服务限流。
>
> 异常方面，RetryPolicy 只对节点抛出的匹配异常生效。网络抖动和临时 5xx 适合指数退避重试，
> 参数错误和权限错误不应盲目重试。如果异常已经被捕获并转换成 ToolMessage 或 success=false，
> RetryPolicy 就不会触发；模型下一轮再次调用属于语义重试。并行 Superstep 在状态提交上是一个
> 事务边界，配置 Checkpointer 后，成功分支的 pending writes 可以保存，恢复时不用全部重跑；
> 但外部写操作仍要靠幂等和补偿保证安全。
>
> 最后是权限。LangGraph 能通过 ToolRuntime 注入用户、线程和 Store 等上下文，也能用 Interrupt
> 做人工审批，但它不是业务权限系统。工程上需要按用户动态过滤工具 Schema，在执行入口重新检查
> 本轮 allowlist，在工具内部校验资源归属，并对文件、命令和网络使用沙箱。这样才能把模型的决策
> 能力和系统的确定性安全边界分开。

## 十三、白板速记

```text
State + Node + Edge
        |
        v
   compile graph
        |
        v
snapshot -> parallel nodes -> barrier/reducer -> route -> next snapshot

静态依赖：A -> [B || C] -> D
动态并发：Send(task, input) * N -> reducer -> aggregate
Agent Loop：agent -> tools -> agent -> ... -> END

自动重试：节点抛异常 + 匹配 RetryPolicy
语义重试：错误写入 State/ToolMessage -> 模型或条件边重新决策
执行恢复：Checkpointer + thread_id
长期数据：Store
人工暂停：interrupt -> Command(resume=...)

权限：Schema 可见性 -> 执行 allowlist -> 资源校验 -> Sandbox/HITL
```

## 十四、官方参考

- [Graph API Overview](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Use the Graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api)
- [Fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance)
- [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [Tools and ToolRuntime](https://docs.langchain.com/oss/python/langchain/tools)
- [Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
- [ToolNode source](https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/langgraph/prebuilt/tool_node.py)
