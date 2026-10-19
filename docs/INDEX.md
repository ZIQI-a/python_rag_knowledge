# DOCS — 文档与模块索引

项目文档总入口。以下内容按截至 2026-10-19 的代码实现整理；运行方式、配置和评测步骤分别见前后端 README。

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
| 本地服务 | [docker-compose.yml](../docker-compose.yml) | 构建 PostgreSQL 镜像与 Redis Stack，宿主 Redis 默认 6380；端口、卷及健康检查 |
| 数据库迁移 | [alembic/](../backend/alembic/) | 文档、对话、检索、评测、用户/角色/权限及入库任务/版本迁移 |
| 后端依赖 | [pyproject.toml](../backend/pyproject.toml) | uv 项目定义与 Python 依赖 |
| 前端依赖与锁文件 | [package.json](../frontend/package.json)、[package-lock.json](../frontend/package-lock.json) | npm 命令与可复现安装；锁文件必须提交 |

## 后端基础与文档管理

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 应用入口 | [main.py](../backend/app/main.py) | 日志、追踪、CORS、异常、认证/业务路由、默认管理员初始化及 MCP lifespan/挂载 |
| 健康检查 | [health.py](../backend/app/api/routes/health.py) | `/api/health`、`/api/health/db`、`/api/health/cos` |
| 异常定义与处理 | [exceptions.py](../backend/app/core/exceptions.py)、[error_handlers.py](../backend/app/api/error_handlers.py) | 业务异常及统一响应转换 |
| 日志 | [logging.py](../backend/app/core/logging.py) | `configure_logging` / `get_logger` |
| 模型与基类 | [models.py](../backend/app/db/models.py)、[base.py](../backend/app/db/base.py) | 文档/切片、会话/消息/引用、评测、用户/角色、入库任务与状态枚举 |
| 会话管理与依赖 | [session.py](../backend/app/db/session.py)、[deps.py](../backend/app/db/deps.py) | 异步引擎、会话工厂与请求会话注入 |
| 仓储 | [repositories/](../backend/app/db/repositories/) | 文档、切片、会话、引用、评测任务和明细数据访问 |
| 文档接口与模型 | [documents.py 路由](../backend/app/api/routes/documents.py)、[documents.py 模型](../backend/app/api/schemas/documents.py) | 上传、状态筛选、详情、删除、重试、文件预览/下载及切片浏览 |
| 文档服务 | [document_service.py](../backend/app/services/document_service.py) | 文件校验、去重、权限、版本/重建、Celery 调度与统计；权限/删除/重建变更后使缓存失效 |
| 文件与 COS | [file_service.py](../backend/app/storage/file_service.py)、[cos_client.py](../backend/app/storage/cos_client.py) | 文件上传/下载/删除、存储客户端与连通检查 |
| 入库流水线 | [pipeline.py](../backend/app/ingestion/pipeline.py) | Celery 首次入库及增量重建：解析、哈希对齐、向量化、版本与任务进度 |
| 解析与切分 | [parser.py](../backend/app/ingestion/parser.py)、[splitter.py](../backend/app/ingestion/splitter.py) | Docling 转 Markdown，递归切分并补齐切片索引和哈希 |
| Embedding | [embedder.py](../backend/app/ingestion/embedder.py) | 向量模型实例与配置 |

## 检索、问答与可观测性

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 会话接口与模型 | [chat.py 路由](../backend/app/api/routes/chat.py)、[chat.py 模型](../backend/app/api/schemas/chat.py) | 会话列表/详情/删除、SSE 问答及引用、路由、Agent、校验、Trace 响应 |
| 问答服务 | [chat_service.py](../backend/app/services/chat_service.py) | 流式问答、持久化；语义缓存命中/写入前批量校验引用权限；内部 `answer_for_evaluation()`、`answer_for_mcp()` 复用问答，不写会话历史 |
| 模型与提示词 | [models.py](../backend/app/llm/models.py)、[prompts.py](../backend/app/llm/prompts.py) | 聊天模型与生成、路由、规划、校验等提示词 |
| 查询优化 | [query_rewriter.py](../backend/app/llm/query_rewriter.py) | Original / Rewrite / HyDE / Multi-query，HyDE 使用假设答案召回 |
| 向量与关键词检索 | [vector_retriever.py](../backend/app/retrieval/vector_retriever.py)、[keyword_retriever.py](../backend/app/retrieval/keyword_retriever.py) | pgvector 相似度与 zhparser 全文检索 |
| 混合检索 | [hybrid_retriever.py](../backend/app/retrieval/hybrid_retriever.py) | 双路并发召回、RRF 融合与单路异常降级 |
| Agent 规划 | [agent_planner.py](../backend/app/llm/agent_planner.py) | 基于当前检索情况决定继续、改写、切换策略或拒答 |
| 重排与答案校验 | [reranker.py](../backend/app/llm/reranker.py)、[answer_verifier.py](../backend/app/llm/answer_verifier.py) | HTTP 精排与生成后的依据校验 |
| 工作流 | [graph.py](../backend/app/workflows/graph.py)、[rag_state.py](../backend/app/workflows/rag_state.py) | 有限轮 Agent 检索图、精排、上下文判断、拒答与状态定义 |
| 节点入口 | [nodes/](../backend/app/workflows/nodes/) | 上下文加载、查询路由、规划、检索、观察、重排、判断、拒答和流式生成 |
| LangSmith | [observbility.py](../backend/app/core/observbility.py) | 追踪开关、SDK 环境变量、Trace ID 和可选详情链接；沿用当前文件名 |

## 认证、缓存、后台任务与 MCP

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 认证依赖 | [deps.py](../backend/app/api/deps.py)、[security.py](../backend/app/core/security.py) | JWT 签发/校验、当前用户、管理员与 HTTP 限流依赖 |
| 认证接口 | [auth.py](../backend/app/api/routes/auth.py)、[auth_service.py](../backend/app/services/auth_service.py) | 登录与当前用户信息 |
| 用户/角色接口 | [users.py](../backend/app/api/routes/users.py)、[roles.py](../backend/app/api/routes/roles.py) | 管理员用户、角色和标签维护 |
| 权限与初始化 | [permission_service.py](../backend/app/services/permission_service.py)、[seed.py](../backend/app/db/seed.py) | 标签合并、管理员判断及首次管理员创建 |
| 用户/角色服务 | [user_service.py](../backend/app/services/user_service.py)、[role_service.py](../backend/app/services/role_service.py) | 创建、更新、角色分配与内置角色保护 |
| Redis 与限流 | [redis.py](../backend/app/core/redis.py)、[rate_limiter.py](../backend/app/core/rate_limiter.py) | Redis 客户端、每用户滑动窗口限流 |
| 语义缓存 | [semantic_cache_service.py](../backend/app/services/semantic_cache_service.py) | RedisVL 问题向量与权限范围过滤；文档变更后清空缓存，命中及写入前核对引用文档可见性；多轮隔离待修复 |
| Celery 应用与任务 | [celery_app.py](../backend/app/celery_app.py)、[tasks.py](../backend/app/ingestion/tasks.py) | 独立 worker 的 ingest / reindex 入口 |
| 入库任务仓储 | [ingestion_task_repo.py](../backend/app/db/repositories/ingestion_task_repo.py) | 状态、进度及错误记录 |
| MCP 服务 | [server.py](../backend/app/mcp_server/server.py)、[tools.py](../backend/app/mcp_server/tools.py) | `/mcp/` Streamable HTTP、JSON 响应、五个知识库工具 |
| MCP 认证与模型 | [auth.py](../backend/app/mcp_server/auth.py)、[schemas.py](../backend/app/mcp_server/schemas.py) | 请求头 Bearer JWT、用户状态、管理员校验及工具响应 |

启动要求与 MCP 工具参数见 [后端说明](../backend/README.md)；已发现问题见 [根目录审查状态](../README.md#审查状态2026-10-19)。

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
| 路由与布局 | [routes/index.tsx](../frontend/src/routes/index.tsx)、[BasicLayout.tsx](../frontend/src/layouts/BasicLayout.tsx) | 独立登录页、登录业务布局、管理员路由与权限菜单 |
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

## 前端认证与新增功能索引

| 模块 | 位置 | 说明 |
| --- | --- | --- |
| 登录与认证 API | [LoginPage.tsx](../frontend/src/pages/LoginPage.tsx)、[auth.ts](../frontend/src/api/auth.ts) | 登录、当前用户与返回原页面 |
| 用户与角色页面 | [UserPage.tsx](../frontend/src/pages/UserPage.tsx)、[RolesPage.tsx](../frontend/src/pages/RolesPage.tsx) | 管理员维护用户、角色、状态与权限标签 |
| 认证状态与守卫 | [authStore.ts](../frontend/src/stores/authStore.ts)、[RequireAuth.tsx](../frontend/src/components/RequireAuth.tsx)、[RequireAdmin.tsx](../frontend/src/components/RequireAdmin.tsx) | 认证持久化、登录保护与管理员页面控制 |
| 用户菜单 | [UserMenu.tsx](../frontend/src/components/UserMenu.tsx) | 展示当前用户、退出登录及清理查询缓存 |
| 用户/角色请求 | [users.ts](../frontend/src/api/users.ts)、[roles.ts](../frontend/src/api/roles.ts) | 用户和角色 SDK 查询封装 |
| 文件链接 | [documentFile.ts](../frontend/src/utils/documentFile.ts) | 原文件预览/下载链接、查询令牌与 MIME 判断，正确追加 `&token=` |

## 后续可补充文档

- 独立的 RAG 架构设计与策略效果对比（当前流程摘要见后端 README）。
- 评测基线、数据集维护和 Bad Case 调优记录。
- 已实现 JWT / 角色标签权限；可补充独立的 API 权限矩阵、缓存撤权策略与安全验证记录。
- 生产部署、后台任务恢复、配置与数据备份运维手册。
