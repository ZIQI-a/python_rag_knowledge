# AGENTS.md — AI 编码代理工作指南

本文件为在本仓库中工作的 AI 代理（Harness 工程约定）提供上下文与规则。动手改代码前请先读完。

## 项目定位

AI 企业 RAG 知识库：`backend/` 为 FastAPI 异步后端，`frontend/` 为 React 前端，PostgreSQL + pgvector 承担向量检索，腾讯云 COS 存储原始文档。核心链路（采集 → 切分 → 向量化 → 检索 → 问答）仍在建设中，当前已完成应用骨架、配置体系、健康检查、数据库会话与 COS 封装。

## 运行与验证命令

```bash
# 基础设施（仓库根目录）
docker compose up -d                 # 启动 PostgreSQL + pgvector

# 后端（backend/ 目录下）
uv sync                              # 安装/同步依赖
uv run uvicorn app.main:app --reload # 开发模式启动
uv run alembic upgrade head          # 应用迁移
uv run alembic revision --autogenerate -m "<说明>"  # 生成迁移

# 前端（frontend/ 目录下）
npm install && npm run dev           # 开发模式
npm run build && npm run lint        # 构建与检查
```

## 必须遵守的工程约定

1. **环境变量**：所有配置走仓库根目录 `.env`，由 `backend/app/core/config.py` 的 `Settings` 单例读取。**严禁提交 `.env`**，新增配置项时同步更新 `.env.example` 并在 `Settings` 中声明。
2. **异步优先**：数据库访问使用 `sqlalchemy[asyncio]` + `asyncpg`；路由内需要同步阻塞调用（如 COS SDK）时，用 `asyncio.to_thread` 包装，参考 `app/storage/cos_client.py`。
3. **依赖注入**：数据库会话通过 `app/db/deps.py` 的 `DbSession` 注入，不要在路由里自建引擎/会话。
4. **模型变更必须走 Alembic**：修改 `app/db/base.py` 中的模型后，生成并提交迁移脚本，禁止手工改库。
5. **异常处理**：业务异常继承 `app/core/exceptions.py` 中的基类，由 `app/api/error_handlers.py` 统一转换为响应；不要在路由里裸 `try/except` 后吞掉异常。
6. **日志**：统一使用 `app/core/logging.py` 的 `get_logger(__name__)`，禁止 `print`。
7. **注释与提交信息**：使用简体中文，说明"为什么"而不仅是"做了什么"。
8. **接口风格**：REST 路由统一挂载在 `/api` 前缀下，为每个端点显式声明 `operation_id` 与 `response_model`。

## 安全红线

- `.env`、任何云凭据（COS SecretId/SecretKey、数据库密码）不得进入 Git 历史。
- 不要提交 `.idea/`、`.venv/`、`__pycache__/`、`node_modules/` 等本地产物。
- `.workbuddy/` 目录（WorkBuddy 对话日志与本地工作区数据）已被 `.gitignore` 排除，严禁提交。
- 健康检查接口可以返回连通状态，但不得在响应或日志中回显凭据内容。

## 文档实时同步约束（强制）

**代码变更与文档更新是同一个提交的一部分，不允许"先改代码、后补文档"。**

1. 新增、删除或重构任何模块（后端包/路由/模型、前端页面/组件、基础设施配置）时，必须在同一提交中同步更新：
   - `docs/INDEX.md` —— 文档索引中对应的条目、导航表；
   - 根 `README.md` 与 `backend/README.md` / `frontend/README.md` —— 目录结构、技术栈或命令发生变化时；
   - 本文件 `AGENTS.md` —— 工程约定、命令或目录导航发生变化时。
2. 新增配置项时，同步更新 `.env.example` 与 `docs/INDEX.md` 的配置章节。
3. 提交前自查：`git diff --name-only` 中每出现一个新增/删除的代码模块，确认对应文档条目已更新；做不到"文档与代码同提交"时，先在提交信息中注明原因。
4. 文档中的描述必须与代码现状一致——禁止保留指向已删除模块的链接或已失效的命令。

## 目录导航速查

| 你要做什么 | 去哪里 |
| --- | --- |
| 新增 API 端点 | `backend/app/api/routes/` |
| 新增/修改数据模型 | `backend/app/db/base.py` + `backend/alembic/` |
| 新增配置项 | `backend/app/core/config.py` + `.env.example` |
| 文档/文件存储 | `backend/app/storage/cos_client.py` |
| 本地数据库 | 根目录 `docker-compose.yml` |
| 文档索引 | `docs/INDEX.md` |
