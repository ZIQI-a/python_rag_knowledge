# 文档与模块索引

## 文档

| 文档 | 内容 |
| --- | --- |
| [项目 README](../README.md) | 项目用途、功能、技术栈与目录 |
| [后端 README](../backend/README.md) | 配置、运行、接口、MCP 与评测 |
| [前端 README](../frontend/README.md) | 页面、目录与开发命令 |
| [全局 AGENTS](../AGENTS.md) | 全局约束与按范围读取入口 |
| [后端 AGENTS](../backend/AGENTS.md) | 后端约束与快速索引 |
| [前端 AGENTS](../frontend/AGENTS.md) | 前端约束与快速索引 |

## 基础设施

| 入口 | 内容 |
| --- | --- |
| [docker-compose.yml](../docker-compose.yml)、[postgres.Dockerfile](../postgres.Dockerfile) | PostgreSQL、pgvector、zhparser 与 Redis Stack |
| [.env.example](../.env.example)、[config.py](../backend/app/core/config.py) | 配置模板与 Settings 定义 |
| [pyproject.toml](../backend/pyproject.toml)、[package.json](../frontend/package.json) | 依赖与命令；前端锁文件为 [package-lock.json](../frontend/package-lock.json) |
| [alembic/](../backend/alembic/) | 数据库迁移 |

## 后端

| 模块 | 入口 |
| --- | --- |
| 应用装配 | [main.py](../backend/app/main.py) |
| 配置、异常、日志、Redis、认证与追踪 | [core/](../backend/app/core/) |
| HTTP 路由、鉴权依赖与响应模型 | [api/](../backend/app/api/) |
| 模型、会话、仓储与管理员初始化 | [db/](../backend/app/db/) |
| 文档管理与统计 | [document_service.py](../backend/app/services/document_service.py) |
| COS 文件服务 | [storage/](../backend/app/storage/) |
| 解析、切分、向量化与增量入库 | [ingestion/](../backend/app/ingestion/) |
| Celery、worker 事件循环与资源生命周期 | [celery_app.py](../backend/app/celery_app.py)、[tasks.py](../backend/app/ingestion/tasks.py) |
| 向量、关键词与 RRF 检索 | [retrieval/](../backend/app/retrieval/) |
| 模型、提示词、查询策略、Agent、精排与校验 | [llm/](../backend/app/llm/) |
| LangGraph 图、状态与节点 | [workflows/](../backend/app/workflows/) |
| 会话与问答 | [chat_service.py](../backend/app/services/chat_service.py) |
| 语义缓存 | [semantic_cache_service.py](../backend/app/services/semantic_cache_service.py) |
| 用户与角色 | [auth_service.py](../backend/app/services/auth_service.py)、[user_service.py](../backend/app/services/user_service.py)、[role_service.py](../backend/app/services/role_service.py) |
| 权限标签 | [permission_service.py](../backend/app/services/permission_service.py) |
| 评测调度、数据集、指标与归因 | [evaluation_service.py](../backend/app/services/evaluation_service.py)、[evaluation/](../backend/app/evaluation/) |
| 评测样本 | [smoke.jsonl](../backend/app/evaluation/datasets/smoke.jsonl)、[seed.jsonl](../backend/app/evaluation/datasets/seed.jsonl) |
| MCP 服务、工具、认证与模型 | [mcp_server/](../backend/app/mcp_server/) |

## 前端

| 模块 | 入口 |
| --- | --- |
| 应用装配 | [main.tsx](../frontend/src/main.tsx) |
| 主题配色与组件令牌 | [theme.ts](../frontend/src/config/theme.ts) |
| 路由与布局 | [routes/](../frontend/src/routes/)、[layouts/](../frontend/src/layouts/) |
| 品牌、图标、页面元信息与收录 | [brand.ts](../frontend/src/config/brand.ts)、[BrandLogo.tsx](../frontend/src/components/BrandLogo.tsx)、[PageTitleLayout.tsx](../frontend/src/components/PageTitleLayout.tsx)、[public/](../frontend/public/)、[robots.txt](../frontend/public/robots.txt)、[index.html](../frontend/index.html) |
| 首页、登录、文档、对话、评测、用户与角色 | [pages/](../frontend/src/pages/) |
| 鉴权、会话、引用、追踪、指标与归因组件 | [components/](../frontend/src/components/) |
| 请求、SSE 与查询键 | [api/](../frontend/src/api/) |
| 生成客户端 | [client/](../frontend/src/client/)、[openapi-ts.config.ts](../frontend/openapi-ts.config.ts) |
| 认证状态 | [authStore.ts](../frontend/src/stores/authStore.ts) |
| 文件链接、状态与辅助函数 | [utils/](../frontend/src/utils/) |
| 构建与开发代理 | [vite.config.ts](../frontend/vite.config.ts) |
