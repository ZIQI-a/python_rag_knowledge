# DOCS — 文档与模块索引

项目文档总入口。以下内容按截至 2026-10-16 的代码实现整理；运行方式、配置和评测步骤分别见前后端 README。

## 总览

| 文档 | 位置 | 说明 |
| --- | --- | --- |
| 项目 README | [README.md](../README.md) | 功能进度、技术栈、本地启动、评测入门 |
| 代理总索引 | [AGENTS.md](../AGENTS.md) | 全局行为约束、安全红线与分层索引 |
| 后端说明 | [backend/README.md](../backend/README.md) | 模块职责、配置、迁移、接口、评测步骤与指标口径 |
| 后端约束 | [backend/AGENTS.md](../backend/AGENTS.md) | 后端命令、工程约定和模块位置 |
| 前端说明 | [frontend/README.md](../frontend/README.md) | 页面路由、开发命令、API 生成与前端结构 |
| 前端约束 | [frontend/AGENTS.md](../frontend/AGENTS.md) | 前端工程约定与模块位置 |

## 配置与基础设施

| 主题 | 位置 | 说明 |
| --- | --- | --- |
| 环境变量模板 | [.env.example](../.env.example) | 基础配置模板；真实配置写入根目录 `.env`，模型等扩展配置见后端 README |
| 应用配置 | [config.py](../backend/app/core/config.py) | `Settings`：基础设施、模型、查询、Agent、精排、校验与追踪开关 |
| 数据库镜像 | [postgres.Dockerfile](../postgres.Dockerfile) | PostgreSQL 16、pgvector 与 zhparser / SCWS 中文分词依赖 |
| 本地服务 | [docker-compose.yml](../docker-compose.yml) | 构建数据库镜像、端口、持久化卷及健康检查 |
| 数据库迁移 | [alembic/](../backend/alembic/) | 文档、对话、向量索引、中文全文检索及评测表迁移 |
| 后端依赖 | [pyproject.toml](../backend/pyproject.toml) | uv 项目定义与 Python 依赖 |
| 前端依赖与锁文件 | [package.json](../frontend/package.json)、[package-lock.json](../frontend/package-lock.json) | npm 命令与可复现安装；锁文件必须提交 |

## 后端基础与文档管理

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 应用入口 | [main.py](../backend/app/main.py) | 日志、可观测性、CORS、异常处理、四组业务路由装配 |
| 健康检查 | [health.py](../backend/app/api/routes/health.py) | `/api/health`、`/api/health/db`、`/api/health/cos` |
| 异常定义与处理 | [exceptions.py](../backend/app/core/exceptions.py)、[error_handlers.py](../backend/app/api/error_handlers.py) | 业务异常及统一响应转换 |
| 日志 | [logging.py](../backend/app/core/logging.py) | `configure_logging` / `get_logger` |
| 模型与基类 | [models.py](../backend/app/db/models.py)、[base.py](../backend/app/db/base.py) | 文档/切片、会话/消息/引用、评测任务/明细及状态枚举 |
| 会话管理与依赖 | [session.py](../backend/app/db/session.py)、[deps.py](../backend/app/db/deps.py) | 异步引擎、会话工厂与请求会话注入 |
| 仓储 | [repositories/](../backend/app/db/repositories/) | 文档、切片、会话、引用、评测任务和明细数据访问 |
| 文档接口与模型 | [documents.py 路由](../backend/app/api/routes/documents.py)、[documents.py 模型](../backend/app/api/schemas/documents.py) | 上传、状态筛选、详情、删除、重试、文件预览/下载及切片浏览 |
| 文档服务 | [document_service.py](../backend/app/services/document_service.py) | 文件校验、哈希去重、管理操作及后台入库调度 |
| 文件与 COS | [file_service.py](../backend/app/storage/file_service.py)、[cos_client.py](../backend/app/storage/cos_client.py) | 文件上传/下载/删除、存储客户端与连通检查 |
| 入库流水线 | [pipeline.py](../backend/app/ingestion/pipeline.py) | 下载原文、解析、切分、向量化、落库及状态更新 |
| 解析与切分 | [parser.py](../backend/app/ingestion/parser.py)、[splitter.py](../backend/app/ingestion/splitter.py) | Docling 转 Markdown，递归切分并补齐切片索引和哈希 |
| Embedding | [embedder.py](../backend/app/ingestion/embedder.py) | 向量模型实例与配置 |

## 检索、问答与可观测性

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 会话接口与模型 | [chat.py 路由](../backend/app/api/routes/chat.py)、[chat.py 模型](../backend/app/api/schemas/chat.py) | 会话列表/详情/删除、SSE 问答及引用、路由、Agent、校验、Trace 响应 |
| 问答服务 | [chat_service.py](../backend/app/services/chat_service.py) | 流式问答、持久化；内部 `answer_for_evaluation()` 复用链路，不写会话历史 |
| 模型与提示词 | [models.py](../backend/app/llm/models.py)、[prompts.py](../backend/app/llm/prompts.py) | 聊天模型与生成、路由、规划、校验等提示词 |
| 查询优化 | [query_rewriter.py](../backend/app/llm/query_rewriter.py) | Original / Rewrite / HyDE / Multi-query，HyDE 使用假设答案召回 |
| 向量与关键词检索 | [vector_retriever.py](../backend/app/retrieval/vector_retriever.py)、[keyword_retriever.py](../backend/app/retrieval/keyword_retriever.py) | pgvector 相似度与 zhparser 全文检索 |
| 混合检索 | [hybrid_retriever.py](../backend/app/retrieval/hybrid_retriever.py) | 双路并发召回、RRF 融合与单路异常降级 |
| Agent 规划 | [agent_planner.py](../backend/app/llm/agent_planner.py) | 基于当前检索情况决定继续、改写、切换策略或拒答 |
| 重排与答案校验 | [reranker.py](../backend/app/llm/reranker.py)、[answer_verifier.py](../backend/app/llm/answer_verifier.py) | HTTP 精排与生成后的依据校验 |
| 工作流 | [graph.py](../backend/app/workflows/graph.py)、[rag_state.py](../backend/app/workflows/rag_state.py) | 有限轮 Agent 检索图、精排、上下文判断、拒答与状态定义 |
| 节点入口 | [nodes/](../backend/app/workflows/nodes/) | 上下文加载、查询路由、规划、检索、观察、重排、判断、拒答和流式生成 |
| LangSmith | [observbility.py](../backend/app/core/observbility.py) | 追踪开关、SDK 环境变量、Trace ID 和可选详情链接；沿用当前文件名 |

## 评测与归因分析

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 评测接口与模型 | [evaluations.py 路由](../backend/app/api/routes/evaluations.py)、[evaluations.py 模型](../backend/app/api/schemas/evaluations.py) | 数据集、任务、明细筛选与人工归因接口 |
| 评测服务 | [evaluation_service.py](../backend/app/services/evaluation_service.py) | 后台逐条问答、进度、批量评分、规则归因与汇总指标 |
| 评测仓储 | [evaluation_repo.py](../backend/app/db/repositories/evaluation_repo.py) | 评测任务/明细数据访问与筛选 |
| 数据集加载 | [dataset.py](../backend/app/evaluation/dataset.py) | 枚举及解析 JSONL，校验必需字段 |
| RAGAS | [ragas_runner.py](../backend/app/evaluation/ragas_runner.py) | Faithfulness、Answer Relevancy、Context Precision、Context Recall |
| 规则指标与归因 | [scoring.py](../backend/app/evaluation/scoring.py) | 引用命中、拒答正确及 Bad Case 自动分类 |
| 种子样本 | [seed.jsonl](../backend/app/evaluation/datasets/seed.jsonl) | 50 条评测样本，接口名称为 `seed` |
| 冒烟样本 | [smoke.jsonl](../backend/app/evaluation/datasets/smoke.jsonl) | 5 条评测样本，接口名称为 `smoke` |

评测集仅包含问题、预期答案和引用期望，不包含原始知识文档；使用步骤、文档前置条件、空指标含义及后台任务限制见 [后端评测说明](../backend/README.md#评测分析)。

## 前端模块

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 应用入口 | [main.tsx](../frontend/src/main.tsx) | 中文配置、antd App 消息上下文、QueryClient 与路由 |
| 路由与布局 | [routes/index.tsx](../frontend/src/routes/index.tsx)、[BasicLayout.tsx](../frontend/src/layouts/BasicLayout.tsx) | 首页、文档、对话、评测的路由与菜单 |
| 首页 | [HomePage.tsx](../frontend/src/pages/HomePage.tsx) | 欢迎页与功能入口 |
| 文档页面 | [DocumentsPage.tsx](../frontend/src/pages/DocumentsPage.tsx)、[DocumentDetailPage.tsx](../frontend/src/pages/DocumentDetailPage.tsx) | 上传/管理、状态刷新、预览/下载与切片详情 |
| 问答页与会话侧栏 | [ChatPage.tsx](../frontend/src/pages/ChatPage.tsx)、[ConversationSidebar.tsx](../frontend/src/components/ConversationSidebar.tsx) | 会话管理、流式答案及校验状态 |
| 引用 | [CitationList.tsx](../frontend/src/components/CitationList.tsx) | 引用片段、来源文档及检索/精排分数 |
| 调试与追踪 | [QueryRoutePanel.tsx](../frontend/src/components/QueryRoutePanel.tsx)、[AgentStepsPanel.tsx](../frontend/src/components/AgentStepsPanel.tsx)、[TraceIdPanel.tsx](../frontend/src/components/TraceIdPanel.tsx) | 查询策略、Agent 步骤、Trace ID 和可选链接 |
| 评测页面 | [EvaluationListPage.tsx](../frontend/src/pages/EvaluationListPage.tsx)、[EvaluationDetailPage.tsx](../frontend/src/pages/EvaluationDetailPage.tsx) | 任务列表、进度、指标、样本详情、Bad Case 筛选及人工归因 |
| 评测指标与分类 | [MetricsCard.tsx](../frontend/src/components/MetricsCard.tsx)、[BadCaseCategorySelect.tsx](../frontend/src/components/BadCaseCategorySelect.tsx)、[badCaseCategory.ts](../frontend/src/utils/badCaseCategory.ts) | 指标卡片、归因标签和选择组件 |
| 请求封装 | [client.ts](../frontend/src/api/client.ts)、[chatStream.ts](../frontend/src/api/chatStream.ts)、[evaluation.ts](../frontend/src/api/evaluation.ts)、[queryKeys.ts](../frontend/src/api/queryKeys.ts) | SDK 配置、SSE 解析、评测请求与查询键 |
| 生成客户端 | [openapi-ts.config.ts](../frontend/openapi-ts.config.ts)、[src/client/](../frontend/src/client/) | 从后端 8000 端口生成类型与 SDK，禁止手工修改生成文件 |
| 构建与代理 | [vite.config.ts](../frontend/vite.config.ts) | 路径别名、前端 5173 端口、`/api` 到后端 8000 端口的开发代理 |

## 后续可补充文档

- 独立的 RAG 架构设计与策略效果对比（当前流程摘要见后端 README）。
- 评测基线、数据集维护和 Bad Case 调优记录。
- API 规范与鉴权/权限设计；当前评测分类中的权限条目不代表权限模块已落地。
- 生产部署、后台任务恢复、配置与数据备份运维手册。
