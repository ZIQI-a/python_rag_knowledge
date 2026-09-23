# AGENTS.md — 项目总索引与全局约束

AI 代理在本仓库工作前必读。本文件是**总索引**：全局约束在此；前后端细节约束按需读取对应子文档，不要全量读取无关内容。

## 行为准则（最高优先级）

1. **只改明确让改的文件**：未被提及的文件一律不碰。
2. **不做多余操作**：不自行新增文件、不自行修改代码、不自行执行重构或"优化"。
3. **Git 只在明确要求时提交**：未明确让提交，改完即停，不执行 `git add` / `git commit`。
4. 拿不准时先问，不要自行假设需求。

## 项目定位

AI 企业 RAG 知识库「问津」：`backend/` FastAPI 异步后端，`frontend/` React + Ant Design 前端，PostgreSQL + pgvector 向量检索，腾讯云 COS 存原始文档。核心链路（采集 → 切分 → 向量化 → 检索 → 问答）建设中。

## 分层约束索引

| 工作范围 | 需读取的约束文档 |
| --- | --- |
| 跨端 / 基础设施 / 文档 | 仅本文件 |
| 后端开发 | [backend/AGENTS.md](backend/AGENTS.md) |
| 前端开发 | [frontend/AGENTS.md](frontend/AGENTS.md) |

## 全局工程约定

- 注释、提交信息、文档统一使用**简体中文**。
- **文档实时同步（强制）**：模块增删改须在同一变更中更新 `docs/INDEX.md` 对应条目；结构/命令/约定变化时同步各级 README 与 AGENTS 文档。禁止文档滞后于代码。
- **安全红线**：`.env` 及任何凭据不得进入 Git 历史或接口/日志输出；不提交 `.idea/`、`.venv/`、`node_modules/`、`.workbuddy/` 等本地产物；`frontend/package-lock.json` 必须提交。

## 仓库结构速查

```
backend/            # FastAPI 后端（约束见 backend/AGENTS.md）
frontend/           # React 前端（约束见 frontend/AGENTS.md）
docs/               # 项目文档索引（docs/INDEX.md）
docker-compose.yml  # 本地 PostgreSQL 16 + pgvector
.env.example        # 环境变量模板（真实值写入 .env，不入库）
```
