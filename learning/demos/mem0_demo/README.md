# Mem0 独立学习 Demo

这是从零开始的实验，不依赖 DeepTutor 服务，不假设你已经实现 L1/L2/L3，也不接入学生业务数据。
使用 Mem0 Python 开源库、你自行运行的 Milvus 服务和本地 SQLite 历史；不需要 Mem0 云账号。
LLM 和 Embedding 仍需要你自行提供接口，调用可能计费，消息会发送给配置的模型供应商。
只使用虚构学生信息，不输入真实学生隐私。此 Demo 不实现聊天回答，只观察记忆本身。

## 1. 环境准备（PowerShell）

本机默认 `python` 是 Python 2.7，请使用下面明确的解释器命令。开发时已在此目录创建独立环境；
如果环境已存在，跳过创建命令，不影响项目根目录的 `.venv`。

```powershell
cd D:\workfile\deeptutor111self\learning\demos\mem0_demo
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.json config.json
notepad config.json
```

配置中填写两个模型名称、各自的 OpenAI-compatible API 基础地址，以及 Embedding 实际输出维度。
聊天模型需要支持结构化 JSON 输出；Embedding 端点需要支持 embeddings API。
两种模型可以使用不同供应商。`embedding_dims` 是向量库维度，不会作为缩维参数传给接口。
更换 Embedding 模型或维度时使用新的数据目录/集合，不混用已有向量。

密钥读取顺序：对应的环境变量 → `config.json` 中的 `llm_api_key` / `embedding_api_key`
→ 共享字段 `api_key`。如果两个接口使用相同密钥，可以只在本地配置中添加 `api_key`；
只有两个供应商确实接受同一密钥时才能共享。不要把带密钥的配置提交或分享。

也可以设置两个独立环境变量（优先于配置文件）：

```powershell
$env:DEMO_LLM_API_KEY = "你的聊天模型密钥"
$env:DEMO_EMBEDDING_API_KEY = "你的向量模型密钥"
$env:PYTHONIOENCODING = "utf-8"
```

示例赋值可能进入终端历史，请在私人环境操作，或通过 IDE 的受保护环境配置注入。
程序不会加载根目录 `.env`、DeepTutor 设置或任何现有业务密钥。
`config.json`、本地数据、虚拟环境已在此目录 `.gitignore` 中排除。

## 2. 先执行不需要密钥的操作

### Milvus 配置

`demo.py` 默认连接 `http://localhost:19530`，数据库为 `default`，集合为 `mem0_learning_demo`。
已有 config.json 不添加新字段也会使用这些默认值。若 Docker 端口映射不同或服务在其他机器，
在 config.json 添加 `milvus_url`；可选 `milvus_collection`、`milvus_db_name`、`milvus_token`。
认证信息也可通过 `DEMO_MILVUS_TOKEN` 环境变量传入，优先于配置文件。
不要把集合名改成已有教材集合；Mem0 需要自己的字段结构。SDK 初始化可能创建辅助集合。
当前 SDK 的新集合使用 BM25 Function 等能力，需要支持这些能力的 Milvus 服务（2.5+），
仅安装新版 Python 客户端不能替代服务端升级。版本不兼容时保留错误，不自动清空或重建旧集合。

```powershell
docker ps
Test-NetConnection localhost -Port 19530
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

端口可达只说明网络连通，不代表鉴权、服务版本和集合创建一定正常。
2026-09-16 已在用户确认旧库无数据后重建：同一 v3.0.0 镜像改用 Docker 命名卷
`mem0-learning_milvus_data`，不再挂载 System32 数据目录；旧目录保留未删除。
已验证容器 healthy、临时集合写入/查询成功，以及 `demo.py list` 返回空列表。
这证明新实例当前可用，不等于已确定旧实例故障的唯一原因，也未验证真实模型抽取。

在本目录管理服务（端口仅绑定本机）：

```powershell
docker compose up -d
docker compose ps
docker compose logs --tail 50
docker compose stop
```

日常停止使用 stop，不要执行带 `-v` 的 down，以免删除命名卷数据。

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe smoke_sdk.py
.\.venv\Scripts\python.exe demo.py add "这次简单一点" --scope turn
```

最后一条应显示 `persisted: false`，不初始化 Mem0，不调用模型。
`smoke_sdk.py` 特意保留嵌入式 Qdrant 作为离线测试，不连接或验证 Milvus；使用真实 SDK 和临时本地数据库，但模拟向量并禁止联网，验证 CRUD、历史和用户隔离，
不验证模型抽取质量。开发时 7 项单元测试及此 SDK 冒烟测试均已通过，真实供应商调用尚未验证。
这里是你显式指定 `--scope turn` 后由程序拦截，不是模型自动识别“这次”的能力。

## 3. 写入、检索和用户隔离

```powershell
.\.venv\Scripts\python.exe demo.py --user student_a add "以后数学题请先给提示，我不会再讲完整步骤。"
.\.venv\Scripts\python.exe demo.py --user student_a list
.\.venv\Scripts\python.exe demo.py --user student_a search "这个学生喜欢怎样的数学讲解方式？"
.\.venv\Scripts\python.exe demo.py --user student_b list
```

观察 Mem0 实际返回的 `results`、`id`、`memory` 和事件字段，不预设模型一定抽取成功。
student_b 不应看到 student_a 的记录。`--user` 只是本地实验的命名空间，不是登录认证；
生产服务必须由认证状态注入用户身份，不能允许客户端自由声明自己是谁。

## 4. 对比“新增冲突信息”和“明确修改”

先再次新增：

```powershell
.\.venv\Scripts\python.exe demo.py --user student_a add "以后改成先讲完整例题，再给我练习。"
.\.venv\Scripts\python.exe demo.py --user student_a list
.\.venv\Scripts\python.exe demo.py --user student_a search "现在应该怎样给这个学生讲题？"
```

重点看旧记忆是否仍存在、查询是否同时返回两种偏好。不要认为最近一条一定自动覆盖旧偏好，
也不要把搜索排序当作业务事实裁决。这个实验原样暴露 SDK 行为，没有实现生产级冲突策略。

然后从 list 复制你要操作的真实记忆 ID，替换下面占位符：

```powershell
.\.venv\Scripts\python.exe demo.py --user student_a update "替换为记忆ID" "学生长期偏好：数学先讲完整例题，再安排练习。"
.\.venv\Scripts\python.exe demo.py --user student_a history "替换为记忆ID"
.\.venv\Scripts\python.exe demo.py --user student_a delete "替换为记忆ID" --yes
.\.venv\Scripts\python.exe demo.py --user student_a list
```

显式 update 是你选定一条记录进行修订，不是自动找出全部冲突；其他重复/矛盾记录可能仍存在。
本 Demo 在按 ID 更新、删除、读取历史前检查用户归属，但不是并发安全的生产授权服务。
删除命令不等于承诺擦除审计历史或备份，不应把它用作完整隐私删除方案。

## 5. 观察“学生自述”与事实的区别

```powershell
.\.venv\Scripts\python.exe demo.py --user student_a add "我觉得自己已经会分配律了。"
.\.venv\Scripts\python.exe demo.py --user student_a list
```

看看它是否保留“学生自述”的含义，还是过度概括成已掌握。后者说明还需要业务事实类型、
来源和更新规则，不能把抽取结果直接作为学生掌握度。这个 Demo 不声称已经解决这一问题。

## 6. 代码学习顺序

1. `build_config`：模型、Embedding、本地向量库和历史库怎么配置。
2. `execute` 的 add/search：Mem0 如何接收用户消息、如何按用户检索。
3. `require_owner` 与 update/history/delete：显式修改和自动抽取不是同一个入口。
4. `test_demo.py`：用 Mock 验证本地控制逻辑；Mock 测试不证明模型抽取或真实向量检索正确。

向量和记忆内容保存在 Milvus，历史等辅助数据在本目录 `data/` 中。换一个进程执行 list 可观察持久化。
旧 Qdrant 数据不会自动迁移，也不会被删除。学习阶段一次运行一个 Demo 命令，避免混淆并发结果。
报错保留 traceback 便于学习，但分享日志前要检查并去掉供应商地址、密钥和个人内容。

## 7. 常见问题

- 未找到 config.json：复制配置样例并填写，不要保留 YOUR_ 占位符。
- 401/403：检查对应供应商密钥；聊天和向量接口未必共用授权。
- 404：检查模型名、基础地址和该服务是否真的支持对应接口。
- JSON 解析失败：检查聊天模型的结构化输出兼容性，不能靠重试掩盖所有错误。
- 向量维度错误：检查真实返回维度与配置一致；改模型后不要复用原有集合。
- add 返回为空：可能没有提取到记忆，也可能要查 SDK 日志定位异常，不据此宣称系统正常。
- 搜索结果互相矛盾：这是要学习和测量的现象，不把框架当成可靠的事实裁判。
- 提示 spaCy/fastembed 未安装：本例没有安装可选 NLP 和 BM25 能力，不代表记忆 CRUD 必然失败。
- 提示本地 Qdrant 的 payload index 无效：属于本地模式限制，本例不测试服务器索引性能。
- list 最多显示 100 条：仅供小规模实验，不是完整生产导出工具。

## 8. 版本与验证边界

2026-09-16 真实链路验证：配置的 Embedding 实际返回 1024 维，已将本地 config.json 修正为
1024，并切换到新集合 `mem0_learning_demo_1024`，未删除旧集合。测试用户
`demo_check_20260916_fixed` 的偏好已写入，并通过新进程 list 和 search 查到。
模型将中文输入提取为英文记忆，这是实际输出，不是 Demo 翻译。
发现 SDK 在向量插入失败时仍可能返回 ADD，故增加回查；Milvus 写入可见性存在短暂延迟，
回查最多等待约 5 秒，未确认则报错，不盲目重写。当前 9 项单元测试通过。

固定 `mem0ai==2.0.20`；依赖文件不是完整传递依赖锁。代码以安装分发包 API 为准，
不要把 GitHub main 或其他版本教程里的参数直接混用。未配置真实模型密钥前，
只能验证本地逻辑、安装与接口兼容，不能宣称真实抽取/检索已跑通。

参考：[Mem0 源码](https://github.com/mem0ai/mem0)、[固定发布版本](https://pypi.org/project/mem0ai/2.0.20/)。
