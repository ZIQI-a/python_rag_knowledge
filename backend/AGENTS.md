# backend/AGENTS.md — 后端开发约束

仅在后端开发时读取本文件。全局行为准则（只改明确让改的文件、Git 仅明确要求时提交等）见根目录 [AGENTS.md](../AGENTS.md)。

## 技术栈

Python 3.14（uv 管理）· FastAPI + Uvicorn · SQLAlchemy 2.0 (asyncio) + asyncpg · Alembic · pydantic-settings · COS SDK · Docling · LangChain / LangGraph · pgvector / zhparser · LangSmith · RAGAS · PyJWT / bcrypt · Redis Stack / RedisVL · Celery · MCP

## 常用命令

```bash
uv sync                              # 安装依赖（新增依赖用 uv add <pkg>）
uv run uvicorn app.main:app --reload --port 8000 # 开发启动，与前端代理保持一致
uv run celery -A app.celery_app worker -l info # 独立终端运行文档入库 worker
uv run alembic upgrade head          # 应用迁移
uv run alembic revision --autogenerate -m "<说明>"  # 生成迁移
```

## 后端约定

1. **配置**：统一走根目录 `.env`，由 `app/core/config.py` 的 `Settings` 读取；新增配置项同步声明到 `Settings` 和根目录 `.env.example`。
2. **异步**：DB 用 `sqlalchemy[asyncio]` + `asyncpg`；阻塞调用（如 COS SDK）用 `asyncio.to_thread` 包装，参考 `app/storage/cos_client.py`。
3. **会话**：一律经 `app/db/deps.py` 的 `DbSession` 注入，禁止自建引擎/会话。
4. **模型变更必须走 Alembic**，生成迁移脚本并随改动交付，禁止手工改库；仅在明确要求时执行 Git 提交。
5. **异常**：业务异常继承 `app/core/exceptions.py` 基类，由 `app/api/error_handlers.py` 统一转响应，禁止吞异常。
6. **日志**：统一 `app/core/logging.py` 的 `get_logger(__name__)`，禁止 `print`。
7. **接口**：路由挂 `/api` 前缀，显式声明 `operation_id` 与 `response_model`。

## 目录速查

| 要做什么 | 去哪里 |
| --- | --- |
| 新增 API 端点 | `app/api/routes/` |
| 新增/修改数据模型 | 继承 `app/db/base.py` 中的 `Base`，并更新 `alembic/` 迁移 |
| 新增配置项 | `app/core/config.py` + 根目录 `.env.example` |
| 文件存储 | `app/storage/cos_client.py` |
| 应用入口装配 | `app/main.py` |
| 文档入库流水线 | `app/ingestion/` + `app/services/document_service.py` |
| 查询策略与混合检索 | `app/llm/query_rewriter.py` + `app/retrieval/` |
| Agent 工作流与答案校验 | `app/workflows/` + `app/llm/agent_planner.py`、`reranker.py`、`answer_verifier.py` |
| 会话问答与评测复用入口 | `app/services/chat_service.py`（流式问答与内部 `answer_for_evaluation` 方法） |
| 可观测性配置 | `app/core/observbility.py`（沿用当前文件名） |
| 评测与 Bad Case 归因 | `app/evaluation/` + `app/services/evaluation_service.py` + `app/api/routes/evaluations.py` |
| 评测数据集 | `app/evaluation/datasets/*.jsonl`，接口参数使用不带扩展名的名称 |
| JWT、用户与管理员依赖 | `app/core/security.py` + `app/api/deps.py` |
| 默认角色与管理员初始化 | `app/db/seed.py` |
| 用户/角色与权限标签 | `app/services/auth_service.py`、`user_service.py`、`role_service.py`、`permission_service.py` |
| 文档任务与增量重建 | `app/celery_app.py` + `app/ingestion/tasks.py`、`pipeline.py` + `app/db/repositories/ingestion_task_repo.py` |
| Redis 缓存与限流 | `app/core/redis.py`、`rate_limiter.py` + `app/services/semantic_cache_service.py` |
| MCP 服务与认证 | `app/mcp_server/server.py`、`tools.py`、`auth.py`、`schemas.py`，由 `app/main.py` 挂载 `/mcp/` |

请求中的用户/管理员依赖以 `app/api/deps.py` 为准；后台任务和并发检索沿用 `app/db/session.py` 的统一会话工厂，不另建业务专用引擎。文档入库使用 Celery，评测仍使用 FastAPI `BackgroundTasks`。Redis 宿主端口、JWT 初始化与 worker 启动要求见后端 README。
