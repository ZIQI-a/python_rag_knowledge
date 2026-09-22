# backend — RAG 知识库后端服务

FastAPI 异步后端，为 RAG 知识库提供 API、数据模型与存储接入。项目级说明见根目录 [README.md](../README.md)。

## 技术栈

Python 3.14（[uv](https://docs.astral.sh/uv/) 管理）· FastAPI + Uvicorn · SQLAlchemy 2.0 (asyncio) + asyncpg · Alembic · pydantic-settings（读根目录 `.env`）· cos-python-sdk-v5

## 目录说明

```
app/
├── api/
│   ├── routes/health.py    # 健康检查：应用 / 数据库 / COS 连通性
│   └── error_handlers.py   # 全局异常处理器
├── core/
│   ├── config.py           # Settings 单例（读取根目录 .env）
│   ├── exceptions.py       # 业务异常基类
│   └── logging.py          # 日志配置
├── db/
│   ├── base.py             # SQLAlchemy Base 与模型
│   ├── session.py          # 异步引擎与会话工厂
│   └── deps.py             # FastAPI DbSession 依赖
├── storage/cos_client.py   # 腾讯云 COS 封装（单例，阻塞调用走 to_thread）
└── main.py                 # create_app 入口
alembic/                    # 迁移环境（读取 Settings 中的 database_url）
```

## 开发

```bash
uv sync                                     # 安装依赖
uv run uvicorn app.main:app --reload        # 启动开发服务
uv run alembic revision --autogenerate -m "<说明>"   # 模型变更后生成迁移
uv run alembic upgrade head                 # 应用迁移
```

注意：`app` 包通过 `uv run` 在项目根（`backend/`）下解析，新增依赖请使用 `uv add <pkg>`。
