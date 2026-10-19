# 后端约束与索引

全局约束见 [根 AGENTS.md](../AGENTS.md)；运行和配置见 [README.md](README.md)。

## 约束

1. 配置统一经 `app/core/config.py` 读取根 `.env`；新增配置同步 `.env.example`。
2. 数据库使用 SQLAlchemy async / asyncpg；请求会话经 `app/db/deps.py` 注入，后台任务复用 `app/db/session.py` 工厂，不另建引擎。阻塞 SDK 调用使用 `asyncio.to_thread`。
3. 模型变更提供 Alembic 迁移，禁止手工改库。
4. 业务异常使用 `app/core/exceptions.py`，由 `app/api/error_handlers.py` 统一响应；禁止吞异常。日志使用 `get_logger(__name__)`，禁止 `print`。
5. HTTP 业务路由使用 `/api` 前缀，显式声明 `operation_id` 和适用的 `response_model`；MCP 挂载 `/mcp/`。
6. 用户、管理员及限流依赖使用 `app/api/deps.py`；文档可见性使用统一权限过滤逻辑。
7. 新增依赖使用 `uv add`；执行命令的工作目录为 `backend/`。

## 快速索引

| 范围 | 入口 |
| --- | --- |
| 装配 / 配置 / 追踪 | `app/main.py`、`app/core/` |
| HTTP 接口与模型 | `app/api/routes/`、`app/api/schemas/` |
| 数据模型 / 仓储 / 初始化 | `app/db/models.py`、`app/db/repositories/`、`app/db/seed.py`、`alembic/` |
| 文档与入库 | `app/services/document_service.py`、`app/storage/`、`app/ingestion/`、`app/celery_app.py` |
| 检索与工作流 | `app/retrieval/`、`app/llm/`、`app/workflows/` |
| 对话与缓存 | `app/services/chat_service.py`、`semantic_cache_service.py` |
| 用户与权限 | `app/services/auth_service.py`、`user_service.py`、`role_service.py`、`permission_service.py` |
| 评测 | `app/evaluation/`、`app/services/evaluation_service.py` |
| MCP | `app/mcp_server/` |
