# backend — 问津后端

FastAPI 异步后端，已实现文档入库、知识库问答、Agent 检索循环、LangSmith 追踪及评测分析。项目总览见 [根目录 README](../README.md)，开发约束见 [AGENTS.md](AGENTS.md)。

## 技术栈与目录

Python 3.14（uv）· FastAPI · SQLAlchemy async / asyncpg · Alembic · PostgreSQL 16 / pgvector / zhparser · COS SDK · Docling · LangChain / LangGraph · LangSmith · RAGAS。

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
| `alembic/` | 数据库版本迁移，包含全文检索配置与评测表 |

## 启动与迁移

先在根目录准备 `.env` 并运行 `docker compose up -d --build`，再在 `backend/` 执行：

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

新增依赖使用 `uv add <包名>`；模型变更使用 `uv run alembic revision --autogenerate -m "<中文说明>"` 生成迁移。混合检索迁移要求数据库具备 `zhparser`，向量检索要求 `vector` 扩展；项目自定义镜像提供所需扩展。升级现有库也要应用全部迁移，评测表由 `5c0db4229ffc` 迁移创建。

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

## 核心流程与接口

- **入库**：文件类型及大小校验、哈希去重 → COS 上传 → 后台解析、切分、向量化及入库。状态为 `uploading / parsing / indexing / ready / failed`；失败任务支持重试。
- **问答**：加载历史 → 查询路由 → Agent 规划、混合检索、观察与有限轮重试 → 精排及上下文判断 → 拒答或流式生成 → 答案校验 → 消息、引用与调试信息落库。HyDE 使用假设答案召回，最终生成与答案校验使用用户原问题。
- **评测**：`ChatService.answer_for_evaluation()` 复用问答流程并收集结果，不写入会话历史；它是内部服务方法，不是独立 HTTP 端点。

| 前缀 | 接口能力 |
| --- | --- |
| `/api/health` | 应用健康状态；`/db` 和 `/cos` 检查依赖连通性 |
| `/api/documents` | 上传、分页/状态筛选、详情、删除、`/{id}/retry`、`/{id}/file` 预览或下载、切片列表/详情 |
| `/api/conversations` | 新建、分页列表、详情及历史、删除；`POST /{id}/chat` 为 SSE 问答 |
| `/api/evaluations` | 数据集枚举、任务新建/列表/详情/删除、样本明细筛选及人工归因 |

接口参数与响应以运行时 `/docs`、`/openapi.json` 以及 `app/api/schemas/` 为准。SSE 事件包含 `message_start`、`query_route`、`agent_steps`、`citations`、`token`、可选 `verify_result`、`message_end`；异常通过 `error` 事件返回。`message_start` 携带 `trace_id` 和可选 `trace_url`。

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
2. 前端进入「评测分析」新建任务，或调用 `POST /api/evaluations/runs`，请求体示例：`{"name":"冒烟评测","dataset_name":"smoke"}`。
3. 后端通过 FastAPI `BackgroundTasks` 逐条运行问答并保存明细，再批量计算 RAGAS、规则归因和汇总指标。通过 `GET /api/evaluations/runs/{run_id}` 查看进度，状态为 `running / completed / failed`。
4. 通过 `GET /api/evaluations/runs/{run_id}/items` 查看明细，支持 `bad_case_only` 与 `category` 筛选；通过 `PATCH /api/evaluations/items/{item_id}` 更新归因和备注。

**指标口径：**

- RAGAS：Faithfulness（忠实度）、Answer Relevancy（答案相关性）、Context Precision（上下文精度）、Context Recall（上下文召回）。应拒答、执行异常或无检索片段的样本不参与本批 RAGAS；评分异常时可能返回空指标，空值不等于零分。
- 引用命中：引用文档名命中任一期望文档，或引用正文包含任一期望关键词。应拒答样本不计算该指标，汇总只统计非空值。
- 拒答正确：实际拒答状态与 `should_refuse` 是否相同；汇总统计全部样本。
- 耗时：记录每条问答的端到端耗时、可用时的首 token 延迟，单位毫秒；不包含后续批量 RAGAS 评分时间。指标均值仅统计对应的非空值。
- Bad Case：按异常、拒答错误、引用命中及低分指标等规则自动归因；支持人工修改分类、标记和备注。分类选项包括解析、切分、召回、融合、精排、上下文判断、生成、引用与权限过滤等，存在分类选项不表示已实现相应权限模块。

当前后台任务在应用进程内执行，尚无独立任务队列或断点续跑；执行期间重启后端会中断任务。完整评测会调用聊天、Embedding 和 RAGAS 评分服务，建议先跑 `smoke`，再跑 `seed`。可观测性需配置启用后才能产生 Trace ID。
