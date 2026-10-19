# backend — 问津后端

基于 FastAPI 的异步服务，负责文档入库、知识库问答、认证权限、评测分析及 MCP 工具。项目概览见 [根目录 README](../README.md)。

## 模块结构

| 目录 | 职责 |
| --- | --- |
| `app/api/` | HTTP 路由、请求/响应模型与用户依赖 |
| `app/core/` | 配置、认证、日志、异常、Redis、限流与 LangSmith |
| `app/db/` | SQLAlchemy 模型、会话工厂、仓储与初始管理员 |
| `app/storage/` | COS 客户端与文件操作 |
| `app/ingestion/` | Docling 解析、切分、Embedding 与 Celery 入库/重建 |
| `app/retrieval/` | 向量、中文关键词检索与 RRF 融合 |
| `app/llm/`、`app/workflows/` | 查询策略、Agent 规划、LangGraph 检索图、精排与答案校验 |
| `app/services/` | 文档、会话、用户、角色、权限、缓存与评测业务 |
| `app/evaluation/` | JSONL 数据集、RAGAS 评分与 Bad Case 规则 |
| `app/mcp_server/` | Streamable HTTP 服务、工具、鉴权与数据模型 |
| `alembic/` | 数据库迁移 |

## 配置

配置统一写入根目录 `.env`，字段与默认值以 [Settings](app/core/config.py) 为准；[`.env.example`](../.env.example) 提供基础模板。

| 功能 | 主要配置项 |
| --- | --- |
| 数据库与文件 | `DATABASE_URL`、`COS_SECRET_ID`、`COS_SECRET_KEY`、`COS_REGION`、`COS_BUCKET`、`CORS_ORIGINS` |
| 模型 | `AI_BASE_URL`、`AI_API_KEY`、`CHAT_MODEL_NAME`、`EMBEDDING_MODEL`、`EMBEDDING_DIM` |
| 认证 | `JWT_SECRET`、`JWT_EXPIRE_MINUTES`、`DEFAULT_ADMIN_USERNAME`、`DEFAULT_ADMIN_PASSWORD`、`DEFAULT_ADMIN_DISPLAY_NAME` |
| Redis / 队列 | `REDIS_URL`、`CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND` |
| 查询与质量 | `QUERY_ROUTE_ENABLED`、`AGENT_LOOP_ENABLED`、`AGENT_MAX_ROUNDS`、`RERANK_ENABLED`、`RERANK_BASE_URL`、`RERANK_MODEL`、`RERANK_API_KEY`、`VERIFY_ANSWER_ENABLED` |
| 缓存与限流 | `SEMANTIC_CACHE_ENABLED`、`SEMANTIC_CACHE_TTL_SECONDS`、`SEMANTIC_CACHE_MIN_SIMILARITY`、`RATE_LIMIT_ENABLED`、`RATE_LIMIT_PER_MINUTE` |
| 追踪 | `LANGSMITH_TRACING`、`LANGSMITH_API_KEY`、`LANGSMITH_PROJECT`、`LANGSMITH_ENDPOINT`、`LANGSMITH_RUN_URL_PREFIX` |

使用默认 Compose 宿主 Redis 端口 `6380` 时，配置如下；API 与 worker 使用同一份配置：

```dotenv
REDIS_URL=redis://localhost:6380/0
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2
```

`JWT_SECRET` 用于令牌签名；首次启动且用户表为空时初始化管理员。重排密钥未配置时复用 `AI_API_KEY`；追踪需开关和密钥同时配置，详情链接由 URL 前缀控制。Embedding 维度须与数据库向量列一致。数据库需要 pgvector 和 zhparser，缓存使用具备向量搜索能力的 Redis Stack。

## 运行

先在根目录启动 Compose，再在 `backend/` 执行：

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

另开终端，在 `backend/` 启动文档入库 worker：

```bash
uv run celery -A app.celery_app worker -l info
```

默认 prefork worker 的每个子进程独立复用事件循环与异步连接；正常退出时先释放数据库、Embedding 和语义缓存连接，再关闭循环。单进程运行可使用 `--pool=solo`。

## 接口与核心流程

| 入口 | 用途 |
| --- | --- |
| `/api/health` | 应用健康状态；`/db`、`/cos` 检查依赖 |
| `/api/auth` | 登录与当前用户 |
| `/api/users`、`/api/roles` | 管理员用户、角色与权限标签管理 |
| `/api/documents` | 上传、筛选、详情、下载、切片、权限标签、重试与增量重建 |
| `/api/conversations` | 当前用户的会话与历史；`POST /{id}/chat` 为 SSE 问答 |
| `/api/evaluations` | 管理员评测数据集、任务、样本与人工归因 |
| `/mcp/` | Bearer JWT 鉴权的 MCP Streamable HTTP 工具 |

文档经 COS、Docling、文本切分和 Embedding 入库；Celery 维护任务进度，增量重建按切片哈希复用内容，成功后更新版本。问答使用查询路由、混合检索、Agent 循环、精排和上下文判断生成带引用的回答，并执行答案校验。语义缓存按问题向量和权限范围查询，并校验引用文档可见性。

角色标签取并集；文档标签为空时向已登录用户公开，标签有交集时可见，`*` 为通配。文档写操作、评测及用户/角色管理需要管理员；会话按用户归属隔离。

## MCP 工具

| 工具 | 用途 |
| --- | --- |
| `ask_knowledge_base` | 按调用者权限问答，返回答案、引用及 Trace ID |
| `upload_document` | 管理员以文件名和 Base64 内容上传，可指定 MIME 与权限标签 |
| `list_documents` | 按可见性与状态分页查看文档 |
| `get_document_status` | 查询文档状态、版本与入库任务进度 |
| `get_knowledge_base_stats` | 查询可见文档数、切片数与最近入库时间 |

## 评测分析

评测数据集位于 `app/evaluation/datasets/`：`smoke` 为 5 条，`seed` 为 50 条。JSONL 每行包含必需的 `id`、`question`，以及参考答案、预期文档名、关键词、拒答标记与标签。样本不包含原始知识文档，运行前需上传相应文档并等待就绪。

管理员在评测页选择数据集创建任务，后台逐条执行问答、批量评分并保存明细。指标包括 RAGAS 的忠实度、答案相关性、上下文精度/召回，以及引用命中率、拒答正确率和耗时；支持 Bad Case 筛选、分类与备注。评测由 FastAPI `BackgroundTasks` 执行，文档入库由 Celery 执行。

开发约束见 [AGENTS.md](AGENTS.md)，模块导航见 [文档索引](../docs/INDEX.md)。
