# 问津 — AI RAG 知识库

基于 Python、React 的企业知识库，已实现文档管理、知识库对话、评测分析、认证授权、后台入库与 MCP 工具。以下进度依据截至 2026-10-19 的仓库实现整理，不代表所有外部服务均已完成运行验证。

## 当前功能

| 模块 | 已实现能力 |
| --- | --- |
| 文档管理 | PDF、DOCX、Markdown、HTML 上传；内容哈希去重、状态筛选、失败重试、删除、原文件预览/下载与切片查看 |
| 文档入库 | Celery 异步任务、进度记录、版本与按切片哈希增量重建；COS → Docling → 切分 → Embedding → pgvector |
| 知识库对话 | 会话列表、自动标题、历史消息、删除会话、SSE 流式回答与引用来源展示 |
| 查询与检索 | Original / Rewrite / HyDE / Multi-query；向量与中文关键词双路召回、RRF 融合、LangGraph Agent 检索循环 |
| 答案质量 | Rerank 精排、上下文充分性判断、拒答及答案生成后校验 |
| 可观测性 | LangSmith 链路追踪、Trace ID、可配置的追踪详情链接 |
| 评测分析 | JSONL 评测集、后台批量问答、RAGAS 四项指标、引用命中率、拒答正确率、耗时统计及 Bad Case 筛选与人工归因 |
| 认证授权 | JWT 登录、用户/角色管理、角色权限标签、文档可见性过滤、会话按用户隔离 |
| 缓存与限流 | RedisVL 语义缓存、按权限范围隔离缓存、Redis 滑动窗口限流 |
| MCP | Streamable HTTP 工具：问答、上传、文档列表、状态及知识库统计；上传仍有待修复项，见下文 |

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.14 · FastAPI · SQLAlchemy 2.0 async · Alembic |
| RAG | Docling · LangChain · LangGraph · OpenAI 兼容模型接口 · HTTP 重排接口 |
| 数据库 | PostgreSQL 16 · pgvector · zhparser 中文全文检索 |
| 存储 / 追踪 / 评测 | 腾讯云 COS · LangSmith · RAGAS |
| 认证 / 队列 / 缓存 | JWT / bcrypt · Celery · Redis Stack / RedisVL |
| 前端 | React 19 · TypeScript · Vite · Ant Design 6 · React Router 7 · TanStack Query |
| 包管理 | 后端 uv · 前端 npm |

## 项目结构

```text
backend/
  app/
    api/           # 文档、会话、评测、健康检查路由与响应模型
    core/          # 配置、日志、异常、可观测性
    db/            # 模型、异步会话与仓储
    storage/       # COS 与文件服务
    ingestion/     # 解析、切分、向量化与入库
    retrieval/     # 向量、关键词与 RRF 混合检索
    llm/           # 模型、查询策略、Agent 决策、重排、答案校验
    workflows/     # LangGraph 图、状态与节点
    services/      # 文档、对话、评测业务服务
    evaluation/    # 数据集加载、指标计算、归因规则与 JSONL 样本
    mcp_server/    # MCP 认证、工具与 Streamable HTTP 服务
    celery_app.py  # Celery 应用与入库任务发现
  alembic/         # 数据库迁移
frontend/src/      # 页面、路由、组件、API 封装与生成客户端
docs/INDEX.md      # 文档与模块索引
postgres.Dockerfile # pgvector + zhparser 自定义数据库镜像
docker-compose.yml # 本地 PostgreSQL 与 Redis Stack 服务
.env.example       # 基础环境变量模板，真实配置写入 .env
```

## 本地启动

在仓库根目录准备配置并启动数据库：

```bash
cp .env.example .env
# 编辑 .env，填写数据库、JWT、COS、模型和 Redis 配置，详见 backend/README.md。
docker compose up -d --build
```

Compose 同时启动 PostgreSQL 与 Redis Stack；Redis 默认映射到宿主 `6380` 端口，而应用默认 URL 使用 `6379`。按默认 Compose 启动时，需在 `.env` 设置 `REDIS_URL=redis://localhost:6380/0`、`CELERY_BROKER_URL=redis://localhost:6380/1`、`CELERY_RESULT_BACKEND=redis://localhost:6380/2`。

数据库使用自定义镜像，包含 `pgvector` 和 `zhparser`；外部数据库也必须安装这两个扩展。首次构建需要下载和编译中文分词依赖。

在第一个终端启动后端：

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

在另一个终端启动文档入库 worker（同样进入 `backend/`）：

```bash
uv run celery -A app.celery_app worker -l info
```

前台 API 与 worker 必须读取同一份数据库、Redis、COS 和模型配置。文档上传、重试及重建会投递 Celery 任务，未启动 worker 时任务不会自动执行；评测任务仍使用 API 进程内的 `BackgroundTasks`。

在第三个终端启动前端：

```bash
cd frontend
npm ci
npm run dev
```

前端默认地址为 `http://localhost:5173`；开发代理 `/api` 和 OpenAPI 客户端生成均指向 `http://localhost:8000`。若更换后端端口，需同时对齐 `frontend/vite.config.ts` 与 `frontend/openapi-ts.config.ts`。

后端接口文档位于 `http://localhost:8000/docs`；健康检查为 `/api/health`、`/api/health/db` 和 `/api/health/cos`。模型、重排及 LangSmith 的配置要求见 [后端说明](backend/README.md)。`.env.example` 当前只覆盖基础配置，模型及后续功能配置需按后端说明补充到本地 `.env`。

## 登录与 MCP

本地 `.env` 必须配置非空 `JWT_SECRET` 才能登录。数据库迁移完成后，API 首次启动且库内无用户时，会创建内置角色与管理员；账号信息由 `DEFAULT_ADMIN_USERNAME`、`DEFAULT_ADMIN_PASSWORD`、`DEFAULT_ADMIN_DISPLAY_NAME` 配置，应在首次启动前设置。已有用户时不会自动重置账号。

前端登录入口为 `/login`。普通用户可查看有权限的文档并对话；文档写操作、评测、用户及角色管理需要管理员。MCP 连接地址为 `http://localhost:8000/mcp/`，传输为 Streamable HTTP，每次工具调用携带 `Authorization: Bearer <访问令牌>`，与网页使用相同 JWT 和权限标签；工具说明见 [后端 MCP 说明](backend/README.md#mcp-工具)。

## 评测入门

1. 上传评测对应的知识文档，等待状态变为 `ready`。
2. 以管理员身份登录，打开前端「评测分析」(`/evaluation`)，新建任务并选择评测集：`smoke` 为 5 条冒烟样本，`seed` 为 50 条种子样本。
3. 查看任务详情中的进度、指标、问题、引用与追踪信息；按 Bad Case 或归因筛选，并保存人工分类和备注。

评测集位于 `backend/app/evaluation/datasets/`。这些文件提供问题与预期答案，**不会自动导入知识文档**；仓库未附带样本引用的原始知识文档，需自行准备或调整样本。完整流程及指标口径见 [后端评测说明](backend/README.md#评测分析)。评测会调用问答、向量及评分模型，耗时与费用随样本数及检索轮数变化。

## 审查状态（2026-10-19）

已修复缓存撤权检查和带令牌的文件链接拼接：缓存读写时批量核对全部引用文档的就绪状态与当前可见性，权限修改、删除、开始重建及入库/重建就绪后清空知识库语义缓存；Redis 清理失败不阻断文档操作，缓存返回前仍需通过数据库校验。剩余待修复项：MCP 上传适配器不兼容限长读取；语义缓存未区分多轮上下文；Celery 同一进程连续任务的异步资源生命周期需要调整。验证范围为模拟依赖与构建检查，尚未做真实模型、数据库、Redis 或 MCP 客户端联调；全量 lint 的其他既有错误仍保留。

## 文档与约束

- [文档索引](docs/INDEX.md)
- [后端开发说明](backend/README.md) / [前端开发说明](frontend/README.md)
- [AGENTS 总索引与全局约束](AGENTS.md)
