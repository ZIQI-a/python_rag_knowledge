# RAG Knowledge — AI 企业 RAG 知识库

面向企业场景的检索增强生成（RAG）知识库：统一采集企业文档，切分、向量化后存入向量数据库，提供基于私有知识的智能问答与检索。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.14 · FastAPI · SQLAlchemy 2.0 (async) · Alembic |
| 数据库 | PostgreSQL 16 + pgvector |
| 对象存储 | 腾讯云 COS |
| 前端 | React 19 · TypeScript · Vite · Ant Design · React Router |
| 包管理 | 后端 uv · 前端 npm |

## 项目结构

```
python-rag-knowledge/
├── backend/                # FastAPI 后端服务
│   ├── app/
│   │   ├── api/routes/     # 业务路由（health 等）
│   │   ├── core/           # 配置 / 日志 / 异常定义
│   │   ├── db/             # 引擎、会话依赖、模型基类
│   │   ├── storage/        # 腾讯云 COS 封装
│   │   └── main.py         # 应用入口（create_app）
│   ├── alembic/            # 数据库迁移
│   └── pyproject.toml      # uv 项目定义
├── frontend/               # React + Vite 前端
├── docker-compose.yml      # 本地 PostgreSQL + pgvector
├── .env.example            # 环境变量模板
└── docs/                   # 项目文档（见 docs/INDEX.md）
```

## 快速开始

```bash
cp .env.example .env          # 按需填写数据库、COS 凭据、CORS 来源
docker compose up -d          # 启动 PostgreSQL + pgvector

cd backend
uv sync
uv run alembic upgrade head   # 应用数据库迁移
uv run uvicorn app.main:app --reload
# 健康检查：GET /api/health 、/api/health/db 、/api/health/cos

cd ../frontend
npm install && npm run dev
```

## 文档

- 文档导航：[docs/INDEX.md](docs/INDEX.md)
- AI 代理约束：[AGENTS.md](AGENTS.md)（总索引与全局约束，前后端细节见各自目录下的 AGENTS.md）
