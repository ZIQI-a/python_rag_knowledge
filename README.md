# 问津 — AI RAG 知识库

基于 Python、React 的企业知识库，已实现文档管理、知识库对话和评测分析。以下进度依据截至 2026-10-16 的仓库实现整理，不代表所有外部服务均已完成运行验证。

## 当前功能

| 模块 | 已实现能力 |
| --- | --- |
| 文档管理 | PDF、DOCX、Markdown、HTML 上传；内容哈希去重、状态筛选、失败重试、删除、原文件预览/下载与切片查看 |
| 文档入库 | COS 存储 → Docling 解析 → 递归文本切分 → Embedding → PostgreSQL / pgvector |
| 知识库对话 | 会话列表、自动标题、历史消息、删除会话、SSE 流式回答与引用来源展示 |
| 查询与检索 | Original / Rewrite / HyDE / Multi-query；向量与中文关键词双路召回、RRF 融合、LangGraph Agent 检索循环 |
| 答案质量 | Rerank 精排、上下文充分性判断、拒答及答案生成后校验 |
| 可观测性 | LangSmith 链路追踪、Trace ID、可配置的追踪详情链接 |
| 评测分析 | JSONL 评测集、后台批量问答、RAGAS 四项指标、引用命中率、拒答正确率、耗时统计及 Bad Case 筛选与人工归因 |

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.14 · FastAPI · SQLAlchemy 2.0 async · Alembic |
| RAG | Docling · LangChain · LangGraph · OpenAI 兼容模型接口 · HTTP 重排接口 |
| 数据库 | PostgreSQL 16 · pgvector · zhparser 中文全文检索 |
| 存储 / 追踪 / 评测 | 腾讯云 COS · LangSmith · RAGAS |
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
  alembic/         # 数据库迁移
frontend/src/      # 页面、路由、组件、API 封装与生成客户端
docs/INDEX.md      # 文档与模块索引
postgres.Dockerfile # pgvector + zhparser 自定义数据库镜像
docker-compose.yml # 本地数据库服务
.env.example       # 基础环境变量模板，真实配置写入 .env
```

## 本地启动

在仓库根目录准备配置并启动数据库：

```bash
cp .env.example .env
# 编辑 .env，填写数据库、COS 和模型配置，详见 backend/README.md。
docker compose up -d --build
```

数据库使用自定义镜像，包含 `pgvector` 和 `zhparser`；外部数据库也必须安装这两个扩展。首次构建需要下载和编译中文分词依赖。

在第一个终端启动后端：

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

在另一个终端启动前端：

```bash
cd frontend
npm ci
npm run dev
```

前端默认地址为 `http://localhost:5173`；开发代理 `/api` 和 OpenAPI 客户端生成均指向 `http://localhost:8000`。若更换后端端口，需同时对齐 `frontend/vite.config.ts` 与 `frontend/openapi-ts.config.ts`。

后端接口文档位于 `http://localhost:8000/docs`；健康检查为 `/api/health`、`/api/health/db` 和 `/api/health/cos`。模型、重排及 LangSmith 的配置要求见 [后端说明](backend/README.md)。`.env.example` 当前只覆盖基础配置，模型及后续功能配置需按后端说明补充到本地 `.env`。

## 评测入门

1. 上传评测对应的知识文档，等待状态变为 `ready`。
2. 打开前端「评测分析」(`/evaluation`)，新建任务并选择评测集：`smoke` 为 5 条冒烟样本，`seed` 为 50 条种子样本。
3. 查看任务详情中的进度、指标、问题、引用与追踪信息；按 Bad Case 或归因筛选，并保存人工分类和备注。

评测集位于 `backend/app/evaluation/datasets/`。这些文件提供问题与预期答案，**不会自动导入知识文档**；仓库未附带样本引用的原始知识文档，需自行准备或调整样本。完整流程及指标口径见 [后端评测说明](backend/README.md#评测分析)。评测会调用问答、向量及评分模型，耗时与费用随样本数及检索轮数变化。

## 文档与约束

- [文档索引](docs/INDEX.md)
- [后端开发说明](backend/README.md) / [前端开发说明](frontend/README.md)
- [AGENTS 总索引与全局约束](AGENTS.md)
