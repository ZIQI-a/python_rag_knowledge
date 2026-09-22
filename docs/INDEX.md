# DOCS — 文档索引

本文件是项目文档的总入口（索引），按主题列出所有文档的位置与用途。

## 总览

| 文档 | 位置 | 说明 |
| --- | --- | --- |
| 项目 README | [/README.md](../README.md) | 项目简介、技术栈、目录结构、快速开始 |
| 代理工作指南 | [/AGENTS.md](../AGENTS.md) | 面向 AI 编码代理的工程约定、命令与安全红线 |
| 后端 README | [/backend/README.md](../backend/README.md) | 后端服务的模块说明与开发指引 |
| 前端 README | [/frontend/README.md](../frontend/README.md) | 前端工程说明（前端目录暂未纳入版本管理） |
| 本索引 | [/docs/INDEX.md](INDEX.md) | 文档总入口 |

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
| 数据模型 | [/backend/app/db/base.py](../backend/app/db/base.py) | SQLAlchemy `Base` 与模型定义 |
| 会话管理 | [/backend/app/db/session.py](../backend/app/db/session.py) | 异步引擎与 `AsyncSessionLocal` 工厂 |
| 会话依赖 | [/backend/app/db/deps.py](../backend/app/db/deps.py) | FastAPI `DbSession` 依赖注入 |
| COS 存储 | [/backend/app/storage/cos_client.py](../backend/app/storage/cos_client.py) | 腾讯云 COS 客户端封装与连通检查 |

## 规划中的文档（待补充）

- RAG 核心链路设计：文档采集 → 切分 → Embedding → pgvector 检索 → 问答
- API 接口规范（鉴权、分页、错误码）
- 部署运维手册（生产环境配置、COS 桶策略、备份）
