# backend — 问津后端

FastAPI 异步后端，已实现文档入库、知识库问答、Agent 检索循环、LangSmith 追踪、评测分析、JWT / RBAC、Redis 缓存/限流、Celery 入库及 MCP 工具。项目总览见 [根目录 README](../README.md)，开发约束见 [AGENTS.md](AGENTS.md)。

## 技术栈与目录

Python 3.14（uv）· FastAPI · SQLAlchemy async / asyncpg · Alembic · PostgreSQL 16 / pgvector / zhparser · COS SDK · Docling · LangChain / LangGraph · LangSmith · RAGAS · PyJWT / bcrypt · Redis Stack / RedisVL · Celery · MCP。

| 目录 / 文件 | 职责 |
| --- | --- |
| `app/api/routes/`、`app/api/schemas/` | 文档、会话、评测、健康检查接口及输入输出模型 |
| `app/core/config.py` | `Settings` 单例，读取根目录 `.env` |
| `app/core/observbility.py` | 配置 LangSmith SDK 环境变量、获取 Trace ID、构造详情链接；文件名以当前实现为准 |
| `app/db/models.py`、`app/db/repositories/` | 文档/切片、会话/消息/引用、评测任务/明细模型与数据访问 |
| `app/db/session.py`、`app/db/deps.py` | 异步引擎、会话工厂与请求会话依赖 |
| `app/storage/` | COS 客户端与文件操作 |
| `app/ingestion/` | Docling 解析、递归切分、Embedding、后台入库流水线 |
| `app/retrieval/` | 向量和中文关键词检索、双路并发召回、RRF 融合 |
| `app/llm/` | 模型封装、查询优化、Agent 规划、精排、答案校验与提示词 |
| `app/workflows/` | LangGraph 图、RAG 状态、检索与判断节点 |
| `app/services/` | 文档管理、会话问答、评测调度与持久化 |
| `app/evaluation/` | JSONL 加载、RAGAS 评分、规则指标与 Bad Case 归因 |
| `app/api/deps.py`、`app/core/security.py` | 当前用户/管理员依赖、JWT 与密码哈希 |
| `app/db/seed.py` | 首次无用户时初始化角色和管理员 |
| `app/services/permission_service.py` | 角色标签合并与管理员判断 |
| `app/core/redis.py`、`app/core/rate_limiter.py` | Redis 客户端与滑动窗口限流 |
| `app/services/semantic_cache_service.py` | RedisVL 语义缓存、相似度阈值与权限范围 |
| `app/celery_app.py`、`app/ingestion/tasks.py` | Celery 应用、首次入库与增量重建任务 |
| `app/mcp_server/` | FastMCP 服务、JWT 解析、工具注册及响应模型 |
| `alembic/` | 数据库版本迁移，包含全文检索配置与评测表 |

## 启动与迁移

先在根目录准备 `.env` 并运行 `docker compose up -d --build`，再在 `backend/` 执行：

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

另开终端，在 `backend/` 启动文档入库 worker：

```bash
uv run celery -A app.celery_app worker -l info
```

Compose 的 Redis Stack 默认宿主端口为 `6380`，应用默认 URL 则是 `6379`；使用默认 Compose 时，在根目录 `.env` 配置：

```dotenv
REDIS_URL=redis://localhost:6380/0
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2
```

限流和 Celery 需要 Redis；语义缓存还依赖 Redis Stack 的向量搜索能力，不能仅用无搜索模块的普通 Redis 替代。Compose 只启动基础设施，不自动启动 API 或 worker。

新增依赖使用 `uv add <包名>`；模型变更使用 `uv run alembic revision --autogenerate -m "<中文说明>"` 生成迁移。混合检索迁移要求数据库具备 `zhparser`，向量检索要求 `vector` 扩展；项目自定义镜像提供所需扩展。升级现有库也要应用全部迁移，评测表由 `5c0db4229ffc`、认证与权限字段由 `30a994ef6a36`、入库任务与文档版本由 `c2eb56a7edf6` 迁移管理。

## 配置

全部配置写入根目录 `.env`，字段定义以 [config.py](app/core/config.py) 为准。基础模板 [`.env.example`](../.env.example) 当前未包含模型、查询优化、重排与追踪配置；使用这些功能时需补充对应环境变量。

| 功能 | 环境变量与说明 |
| --- | --- |
| 基础设施 | `DATABASE_URL`、`COS_SECRET_ID`、`COS_SECRET_KEY`、`COS_REGION`、`COS_BUCKET`；跨域来源用 `CORS_ORIGINS` |
| 模型 | `AI_BASE_URL`、`AI_API_KEY`、`CHAT_MODEL_NAME`、`EMBEDDING_MODEL`；`EMBEDDING_DIM` 默认 1024，须与数据库向量列维度一致 |
| 入库 | `UPLOAD_MAX_SIZE_MB` 默认 50；`CHUNK_SIZE` 默认 600、`CHUNK_OVERLAP` 默认 60；`EMBEDDING_BATCH_SIZE` 默认 10 |
| 查询与召回 | `QUERY_ROUTE_ENABLED` 默认 true、`MULTI_QUERY_COUNT` 默认 3；`RETRIEVAL_RECALL_TOP_K` 默认 20、`RETRIEVAL_TOP_K` 默认 5、`RRF_K` 默认 60 |
| Agent 循环 | `AGENT_LOOP_ENABLED` 默认 true、`AGENT_MAX_ROUNDS` 默认 3；`CHAT_HISTORY_WINDOW` 默认 5 |
| 精排与判断 | `RERANK_ENABLED` 默认 true；启用时配置 `RERANK_BASE_URL`（完整 HTTP 接口地址）、`RERANK_MODEL`；`RERANK_API_KEY` 未配置时回退 `AI_API_KEY`；`RERANK_TIMEOUT` 默认 0.8 秒；`RERANK_MIN_SCORE` 默认 0.3、`RETRIEVAL_MIN_SCORE` 默认 0.6 |
| 答案校验 | `VERIFY_ANSWER_ENABLED` 默认 true，生成后使用模型校验，未通过时替换为拒答 |
| 追踪 | `LANGSMITH_TRACING` 默认 false，开启且配置 `LANGSMITH_API_KEY` 才生效；可设 `LANGSMITH_PROJECT`、`LANGSMITH_ENDPOINT`；`LANGSMITH_RUN_URL_PREFIX` 配置后才下发追踪详情链接 |

仅启动健康检查无需配置全部模型；实际上传、问答和评测前，应配置所需 COS、Embedding、聊天与重排服务。若暂不使用精排，将 `RERANK_ENABLED=false`；关闭追踪不影响主问答功能。凭据不得写入文档、提交记录或接口输出。

其他配置：

| 功能 | 环境变量与说明 |
| --- | --- |
| 登录 | `JWT_SECRET` 必须非空；`JWT_ALGORITHM` 默认 HS256，`JWT_EXPIRE_MINUTES` 默认 1440；首次管理员由 `DEFAULT_ADMIN_USERNAME`、`DEFAULT_ADMIN_PASSWORD`、`DEFAULT_ADMIN_DISPLAY_NAME` 配置 |
| Redis / 队列 | `REDIS_URL`、`CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND`，默认分别使用本地 6379 的 DB 0、1、2；按实际宿主端口覆盖 |
| 语义缓存 | `SEMANTIC_CACHE_ENABLED` 默认 true，`SEMANTIC_CACHE_TTL_SECONDS` 默认 3600，`SEMANTIC_CACHE_MIN_SIMILARITY` 默认 0.92 |
| 限流 | `RATE_LIMIT_ENABLED` 默认 true，`RATE_LIMIT_PER_MINUTE` 默认 60；HTTP 上传、重建与流式问答使用用户限流依赖 |

## 认证与权限

- `POST /api/auth/login` 获取访问令牌，`GET /api/auth/me` 获取用户、角色标签及管理员标识。业务 API 使用 `Authorization: Bearer <访问令牌>`。
- 应用启动且用户表为空时初始化 `admin`、`user` 角色及配置的管理员账号。后续修改初始化配置不会覆盖已有账号，需通过用户管理更新密码。
- 角色标签取并集；文档标签为空表示公开给已登录用户，标签有交集时可见，持有 `*` 时不限制。管理员身份按角色名 `admin` 判断。
- 文档上传、删除、重试、重建、权限标签调整，以及用户、角色、评测接口由管理员访问；文档读取、下载、切片及检索使用权限标签过滤。会话列表与详情按用户归属隔离。
- 文件接口还接受查询参数 `token` 以支持 iframe / 新窗口；它是访问令牌，不是 Basic Auth。前端构造文件链接时直接追加 `&token=`，不在查询值后添加路径分隔符。
- 流式问答的语义缓存按问题向量及权限范围查询；命中时直接发送缓存答案与引用，并持久化缓存命中标志。命中及写入时通过单次数据库查询检查全部引用文档是否存在、就绪且对当前权限可见；无引用、无效文档 ID、部分文档不可见或校验异常时不使用缓存。文档权限修改、删除、开始重建以及首次入库/重建成功后清空该知识库缓存，保留 Redis 索引及其他数据；清理失败只记录日志，数据库可见性检查仍会执行。当前仍未实现多轮上下文隔离。

## 核心流程与接口

- **入库**：文件类型及大小校验、哈希去重 → COS 上传 → 数据库记录 `IngestionTask` → Celery worker 解析、切分、向量化及入库。状态为 `uploading / parsing / indexing / ready / failed`；失败任务支持重试。
- **问答**：加载历史 → 按问题与权限范围尝试语义缓存 → 未命中时进入查询路由 → Agent 规划、混合检索、观察与有限轮重试 → 精排及上下文判断 → 拒答或流式生成 → 答案校验 → 消息、引用与调试信息落库。HyDE 使用假设答案召回，最终生成与答案校验使用用户原问题。
- **评测**：`ChatService.answer_for_evaluation()` 复用问答流程并收集结果，不写入会话历史；它是内部服务方法，不是独立 HTTP 端点。

| 前缀 | 接口能力 |
| --- | --- |
| `/api/health` | 应用健康状态；`/db` 和 `/cos` 检查依赖连通性 |
| `/api/documents` | 上传、筛选、详情、删除、重试、预览/下载、切片、`/{id}/permission-tags`、`/{id}/reindex`；响应含版本及最新任务进度 |
| `/api/conversations` | 新建、分页列表、详情及历史、删除；`POST /{id}/chat` 为 SSE 问答 |
| `/api/evaluations` | 管理员评测数据集、任务、样本筛选及归因 |
| `/api/auth` | 登录及当前用户信息 |
| `/api/users`、`/api/roles` | 管理员用户、角色、权限标签维护 |
| `/mcp/` | 同进程挂载的 MCP Streamable HTTP 服务，不使用 `/api` 前缀 |

接口参数与响应以运行时 `/docs`、`/openapi.json` 以及 `app/api/schemas/` 为准。SSE 事件包含 `message_start`、`query_route`、`agent_steps`、`citations`、`token`、可选 `verify_result`、`message_end`；异常通过 `error` 事件返回。`message_start` 携带 `trace_id` 和可选 `trace_url`；缓存命中时还携带 `cache_hit=true`，跳过路由、Agent 及答案校验事件。

## Celery 入库与增量重建

首次上传和失败重试创建 `ingest` 任务；`POST /api/documents/{id}/reindex` 接收同类型的新文件并创建 `reindex` 任务。重建按 `chunk_hash` 比对，保留未变化切片，仅对新增/变化部分计算向量；新切片哈希重复时回退全量重建。成功后文档 `version` 加一。

文档详情携带 `latest_task`，包含任务类型、`pending / running / success / failed`、进度与错误。进度总数代表本次需向量化的切片数，不是整个流水线的百分比。未启动 worker 时任务留在队列；当前没有自动重试或断点续跑保证，同进程连续任务的连接池与事件循环生命周期仍需修复，见根目录审查状态。

## MCP 工具

服务随 FastAPI 启动，使用父应用 lifespan 维护 MCP session manager；配置为无状态 HTTP 和 JSON 响应。客户端使用 `http://localhost:8000/mcp/`、Streamable HTTP，并在每次调用中传入 `Authorization: Bearer <访问令牌>`；不支持无 HTTP 请求上下文的 stdio 鉴权。

| 工具 | 权限与作用 |
| --- | --- |
| `ask_knowledge_base` | 已登录用户；使用权限过滤后的 RAG 非流式回答，返回拒答标志、引用和 Trace ID；当前入口不走网页语义缓存分支 |
| `upload_document` | 管理员；`filename`、`content_base64`，可选 MIME 和权限标签；预期复用 Celery 入库，当前适配器存在读取参数不兼容错误 |
| `list_documents` | 已登录用户；按可见性、状态分页，`page_size` 为 1–100；当前仓储按创建时间倒序 |
| `get_document_status` | 已登录且文档可见；返回文档状态、版本与最新入库任务进度 |
| `get_knowledge_base_stats` | 已登录用户；按可见性统计文档数、切片数与最近就绪文档的更新时间 |

工具的 JWT、用户状态和管理员鉴权复用业务规则；HTTP 的 `RateLimited` 依赖不会自动应用到 MCP 工具。MCP 工具不在 FastAPI OpenAPI 中生成 SDK，参数定义见 `app/mcp_server/schemas.py` 与工具函数。

## 评测分析

数据集位于 `app/evaluation/datasets/`，每行一个 JSON 对象。内置 `smoke.jsonl` 为 5 条，`seed.jsonl` 为 50 条；调用接口时使用不带扩展名的 `smoke` 或 `seed`。

| 字段 | 用途 |
| --- | --- |
| `id`、`question` | 必需，样本编号与输入问题 |
| `expected_answer` | 参考答案，供 RAGAS 评分 |
| `expected_document_names` | 期望引用的文档名，需与上传名称一致 |
| `expected_keywords` | 引用片段中的预期关键词 |
| `should_refuse` | 是否应拒答，默认 false |
| `tags` | 样本分类标签 |

**运行步骤：**

1. 准备并上传对应知识文档，等待状态为 `ready`。冒烟集引用《差旅管理制度.md》《考勤与请假制度.md》《员工福利手册.md》《产品技术规格-A100.md》；原文未随仓库交付，种子集还引用其他文档，具体以 JSONL 为准。
2. 以管理员身份登录，前端进入「评测分析」新建任务，或调用 `POST /api/evaluations/runs`，请求体示例：`{"name":"冒烟评测","dataset_name":"smoke"}`。
3. 后端通过 FastAPI `BackgroundTasks` 逐条运行问答并保存明细，再批量计算 RAGAS、规则归因和汇总指标。通过 `GET /api/evaluations/runs/{run_id}` 查看进度，状态为 `running / completed / failed`。
4. 通过 `GET /api/evaluations/runs/{run_id}/items` 查看明细，支持 `bad_case_only` 与 `category` 筛选；通过 `PATCH /api/evaluations/items/{item_id}` 更新归因和备注。

**指标口径：**

- RAGAS：Faithfulness（忠实度）、Answer Relevancy（答案相关性）、Context Precision（上下文精度）、Context Recall（上下文召回）。应拒答、执行异常或无检索片段的样本不参与本批 RAGAS；评分异常时可能返回空指标，空值不等于零分。
- 引用命中：引用文档名命中任一期望文档，或引用正文包含任一期望关键词。应拒答样本不计算该指标，汇总只统计非空值。
- 拒答正确：实际拒答状态与 `should_refuse` 是否相同；汇总统计全部样本。
- 耗时：记录每条问答的端到端耗时、可用时的首 token 延迟，单位毫秒；不包含后续批量 RAGAS 评分时间。指标均值仅统计对应的非空值。
- Bad Case：按异常、拒答错误、引用命中及低分指标等规则自动归因；支持人工修改分类、标记和备注。分类选项包括解析、切分、召回、融合、精排、上下文判断、生成、引用与权限过滤等，权限过滤已实现；该分类仍是评测归因标签，不自动证明过滤逻辑正确。

评测后台任务仍在 API 进程内执行，未接入 Celery，也没有断点续跑；重启 API 会中断评测。文档入库与重建已使用独立 Celery worker。完整评测会调用聊天、Embedding 和 RAGAS 评分服务，建议先跑 `smoke`，再跑 `seed`。可观测性需配置启用后才能产生 Trace ID。
