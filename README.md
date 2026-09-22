# RAG Knowledge — AI 企业 RAG 知识库

面向企业场景的检索增强生成（RAG）知识库系统：将企业文档统一采集、切分、向量化后存入向量数据库，为员工/业务系统提供基于私有知识的智能问答与检索能力。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.14 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · Pydantic Settings |
| 数据库 | PostgreSQL 16 + pgvector（向量检索） |
| 对象存储 | 腾讯云 COS（原始文档存储） |
| 前端 | React 19 · TypeScript · Vite |
| 包管理 | 后端 uv · 前端 npm |

## 项目结构

```
python-rag-knowledge/
├── backend/                # FastAPI 后端服务
│   ├── app/
│   │   ├── api/            # 路由与全局异常处理
│   │   │   ├── routes/     # 业务路由（health 等）
│   │   │   └── error_handlers.py
│   │   ├── core/           # 配置 / 日志 / 异常定义
│   │   ├── db/             # SQLAlchemy 引擎、会话依赖、模型基类
│   │   ├── storage/        # 腾讯云 COS 客户端封装
│   │   └── main.py         # 应用入口（create_app）
│   ├── alembic/            # 数据库迁移
│   └── pyproject.toml      # uv 项目定义
├── frontend/               # React + Vite 前端（暂未纳入版本管理）
├── docker-compose.yml      # 本地 PostgreSQL + pgvector
├── .env.example            # 环境变量模板
└── docs/                   # 项目文档（见 docs/INDEX.md）
```

## 快速开始

### 1. 准备环境变量

```bash
cp .env.example .env
# 按需填写：数据库连接、腾讯云 COS 凭据、CORS 来源等
```

### 2. 启动数据库

```bash
docker compose up -d
```

### 3. 启动后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

启动后可访问：

- 应用健康检查：`GET /api/health`
- 数据库连通性：`GET /api/health/db`
- COS 连通性：`GET /api/health/cos`

### 4. 数据库迁移

```bash
cd backend
uv run alembic upgrade head
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 文档索引

完整的文档导航见 [docs/INDEX.md](docs/INDEX.md)；面向 AI 编码代理的工程约定见 [AGENTS.md](AGENTS.md)。
