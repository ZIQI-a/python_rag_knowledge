# DOCS — 文档索引

项目文档总入口，按主题列出位置与用途。

## 总览

| 文档 | 位置 | 说明 |
| --- | --- | --- |
| 项目 README | [/README.md](../README.md) | 简介、技术栈、目录结构、快速开始 |
| 代理总索引 | [/AGENTS.md](../AGENTS.md) | AI 代理全局约束（行为准则、安全红线）与分层索引 |
| 后端约束 | [/backend/AGENTS.md](../backend/AGENTS.md) | 后端命令与工程约定（仅后端开发时读取） |
| 前端约束 | [/frontend/AGENTS.md](../frontend/AGENTS.md) | 前端命令与工程约定（仅前端开发时读取） |
| 后端 README | [/backend/README.md](../backend/README.md) | 后端模块说明与开发指引 |
| 前端 README | [/frontend/README.md](../frontend/README.md) | 前端开发、API 客户端生成说明 |

## 配置与基础设施

| 主题 | 位置 | 说明 |
| --- | --- | --- |
| 环境变量模板 | [/.env.example](../.env.example) | 本地开发所需环境变量；真实值写入 `.env`（不入库） |
| 应用配置 | [/backend/app/core/config.py](../backend/app/core/config.py) | `Settings` 单例，从根目录 `.env` 读取全部配置 |
| 数据库服务 | [/docker-compose.yml](../docker-compose.yml) | PostgreSQL 16 + pgvector 本地容器 |
| 数据库迁移 | [/backend/alembic/](../backend/alembic/) | Alembic 迁移环境（`alembic.ini`、`env.py`、版本脚本） |

## 后端模块

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 应用入口 | [/backend/app/main.py](../backend/app/main.py) | `create_app`：日志、CORS、异常处理、路由装配 |
| 健康检查 | [/backend/app/api/routes/health.py](../backend/app/api/routes/health.py) | `/api/health`、`/api/health/db`、`/api/health/cos` |
| 全局异常 | [/backend/app/api/error_handlers.py](../backend/app/api/error_handlers.py) | 统一异常到响应的转换 |
| 日志体系 | [/backend/app/core/logging.py](../backend/app/core/logging.py) | `configure_logging` / `get_logger` |
| 异常定义 | [/backend/app/core/exceptions.py](../backend/app/core/exceptions.py) | 业务异常基类（如 `ConfigurationError`） |
| 数据模型基类 | [/backend/app/db/base.py](../backend/app/db/base.py) | SQLAlchemy `Base` |
| 文档模型 | [/backend/app/db/Document.py](../backend/app/db/Document.py) | `Document`、`DocumentChunk` 表模型 |
| 文档状态 | [/backend/app/db/models.py](../backend/app/db/models.py) | `DocumentStatus` 生命周期枚举 |
| 会话管理 | [/backend/app/db/session.py](../backend/app/db/session.py) | 异步引擎与 `AsyncSessionLocal` 工厂 |
| 会话依赖 | [/backend/app/db/deps.py](../backend/app/db/deps.py) | FastAPI `DbSession` 依赖注入 |
| COS 存储 | [/backend/app/storage/cos_client.py](../backend/app/storage/cos_client.py) | 腾讯云 COS 客户端封装与连通检查 |

## 前端模块

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 应用入口 | [/frontend/src/main.tsx](../frontend/src/main.tsx) | React 挂载，接入 antd `ConfigProvider`（zhCN）与路由 |
| 路由定义 | [/frontend/src/routes/index.tsx](../frontend/src/routes/index.tsx) | `createBrowserRouter`，`/` 挂载 BasicLayout |
| 基础布局 | [/frontend/src/layouts/BasicLayout.tsx](../frontend/src/layouts/BasicLayout.tsx) | antd Layout：侧边菜单 + 顶栏 + `Outlet` 内容区 |
| 首页 | [/frontend/src/pages/HomePage.tsx](../frontend/src/pages/HomePage.tsx) | 欢迎页与功能入口卡片 |
| 构建配置 | [/frontend/vite.config.ts](../frontend/vite.config.ts) | Vite + @vitejs/plugin-react |
| API 客户端生成 | [/frontend/openapi-ts.config.ts](../frontend/openapi-ts.config.ts) | OpenAPI 输入与 `src/client/` 生成配置 |
| 依赖锁定 | [/frontend/package-lock.json](../frontend/package-lock.json) | npm 锁文件，**必须提交**以保证可复现安装 |

## 规划中的文档（待补充）

- RAG 核心链路设计：文档采集 → 切分 → Embedding → pgvector 检索 → 问答
- API 接口规范（鉴权、分页、错误码）
- 部署运维手册（生产环境配置、COS 桶策略、备份）
