# AGENTS.md — AI 编码代理工作指南

本仓库中工作的 AI 代理须遵守以下约定，动手改代码前请先读完。

## 项目定位

AI 企业 RAG 知识库：`backend/` 为 FastAPI 异步后端，`frontend/` 为 React 前端，PostgreSQL + pgvector 做向量检索，腾讯云 COS 存原始文档。核心链路（采集 → 切分 → 向量化 → 检索 → 问答）仍在建设中。

## 常用命令

```bash
docker compose up -d                 # 根目录：启动 PostgreSQL + pgvector
# 后端（backend/ 下）
uv sync                              # 安装依赖
uv run uvicorn app.main:app --reload # 开发启动
uv run alembic upgrade head          # 应用迁移；revision --autogenerate 生成迁移
# 前端（frontend/ 下）
npm install && npm run dev           # 开发启动；npm run build / lint 构建与检查
```

## 工程约定

1. **配置**：统一走根目录 `.env`，由 `app/core/config.py` 的 `Settings` 读取；新增配置项同步声明到 `Settings` 和 `.env.example`。
2. **异步**：DB 用 `sqlalchemy[asyncio]` + `asyncpg`；阻塞调用（如 COS SDK）用 `asyncio.to_thread` 包装。
3. **会话**：一律经 `app/db/deps.py` 的 `DbSession` 注入，禁止自建引擎/会话。
4. **模型变更必须走 Alembic**，生成并提交迁移脚本，禁止手工改库。
5. **异常**：业务异常继承 `app/core/exceptions.py` 基类，由 `error_handlers.py` 统一转响应，禁止吞异常。
6. **日志**：统一 `get_logger(__name__)`，禁止 `print`。
7. **注释与提交信息用简体中文**。
8. **接口**：路由挂 `/api` 前缀，显式声明 `operation_id` 与 `response_model`。

## 安全红线

- `.env` 及任何凭据（COS 密钥、数据库密码）不得进入 Git 历史或接口/日志输出。
- 不提交 `.idea/`、`.venv/`、`__pycache__/`、`node_modules/`、`.workbuddy/` 等本地产物。

## 文档实时同步（强制）

**代码变更与文档更新同属一个提交，不允许先改代码后补文档。**

- 增删/重构模块（后端路由、模型、前端页面组件、基础设施）时，同提交更新 `docs/INDEX.md` 对应条目；目录结构、技术栈、命令变化时同步更新各级 `README.md`；约定变化时同步本文件。
- 新增配置项时同步 `.env.example`。
- 提交前自查 `git diff --name-only`：每个增删的模块都应有对应文档更新。
- 文档必须与代码现状一致，禁止保留失效链接或命令。

## 目录速查

| 要做什么 | 去哪里 |
| --- | --- |
| 新增 API 端点 | `backend/app/api/routes/` |
| 新增/修改数据模型 | `backend/app/db/base.py` + `backend/alembic/` |
| 新增配置项 | `backend/app/core/config.py` + `.env.example` |
| 文件存储 | `backend/app/storage/cos_client.py` |
| 文档索引 | `docs/INDEX.md` |
