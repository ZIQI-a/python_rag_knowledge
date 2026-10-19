# 问津 — AI RAG 知识库

面向企业文档的检索增强问答系统，提供文档管理、知识库对话、评测分析和权限管理，并通过 MCP 向外部 Agent 提供知识库工具。

## 主要功能

| 模块 | 功能 |
| --- | --- |
| 文档管理 | PDF、DOCX、Markdown、HTML 上传、去重、预览/下载、切片查看、任务进度与版本管理 |
| 文档入库 | COS 存储、Docling 解析、文本切分、向量化及 Celery 异步入库，支持增量重建 |
| 知识库对话 | 多会话、历史消息、流式回答、引用来源、查询路由、混合检索、Agent 检索循环、精排和答案校验 |
| 评测分析 | JSONL 数据集、RAGAS 指标、引用与拒答指标、耗时统计、Bad Case 筛选和人工归因 |
| 认证授权 | JWT 登录、用户/角色管理、权限标签、文档可见性和会话归属隔离 |
| 缓存与追踪 | Redis 语义缓存、滑动窗口限流、LangSmith 链路追踪 |
| MCP 工具 | 知识库问答、文档上传、列表、状态和统计查询 |

## 技术栈

- 后端：Python 3.14、FastAPI、SQLAlchemy async、Alembic、uv。
- RAG：Docling、LangChain、LangGraph、LangSmith、RAGAS。
- 数据与存储：PostgreSQL 16、pgvector、zhparser、腾讯云 COS、Redis Stack、Celery。
- 前端：React 19、TypeScript、Vite、Ant Design 6、React Router 7、TanStack Query、npm。

## 项目结构

```text
backend/
  app/
    api/           # HTTP 接口与请求/响应模型
    core/          # 配置、认证、日志、Redis、限流与追踪
    db/            # 模型、会话、仓储与管理员初始化
    storage/       # COS 文件存储
    ingestion/     # 解析、切分、向量化及入库任务
    retrieval/     # 向量、关键词与 RRF 混合检索
    llm/           # 模型、提示词、查询优化、规划、精排与校验
    workflows/     # LangGraph 工作流与状态
    services/      # 文档、会话、权限、缓存与评测服务
    evaluation/    # 评测样本、评分与归因
    mcp_server/    # MCP 服务、工具与认证
    celery_app.py  # Celery 应用
  alembic/         # 数据库迁移
frontend/src/      # 页面、组件、路由、API 与状态管理
docs/INDEX.md      # 文档与模块索引
docker-compose.yml # PostgreSQL 与 Redis Stack
postgres.Dockerfile # pgvector + zhparser 数据库镜像
.env.example       # 基础配置模板
```

## 本地运行

1. 复制 `.env.example` 为 `.env`，按 [后端说明](backend/README.md#配置) 配置数据库、Redis、JWT、COS 和模型。
2. 在根目录运行 `docker compose up -d --build` 启动 PostgreSQL 与 Redis Stack。
3. 在 `backend/` 安装依赖、应用迁移并启动 API；另开终端启动 Celery worker，命令见 [后端说明](backend/README.md#运行)。
4. 在 `frontend/` 运行 `npm ci` 和 `npm run dev`。

前端默认地址为 `http://localhost:5173`，后端为 `http://localhost:8000`，接口文档为 `http://localhost:8000/docs`。前端开发代理和 API 客户端生成均使用后端 `8000` 端口。

登录入口为 `/login`；首次管理员由环境变量配置，在用户表为空时初始化。MCP 使用 Streamable HTTP，连接地址为 `http://localhost:8000/mcp/`，调用携带 Bearer 访问令牌。

## 文档

- [后端说明](backend/README.md)：配置、运行、接口、入库与评测。
- [前端说明](frontend/README.md)：页面、开发命令与 API 客户端。
- [文档与模块索引](docs/INDEX.md)。
- [AI 代理约束](AGENTS.md)。
