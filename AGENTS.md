# AGENTS.md — 全局约束与索引

进入仓库先读本文件；仅按任务范围读取前后端约束。项目介绍见 [README.md](README.md)，详细模块导航见 [docs/INDEX.md](docs/INDEX.md)。

## 行为准则

1. **只改明确让改的文件**，未提及的文件不改。
2. **不做多余操作**：不自行新增文件、重构或优化。
3. **仅明确要求时暂存或提交 Git**；否则不执行 `git add` / `git commit`。
4. 需求或修改范围不明确时先确认，不自行假设。

## 工程约定

- 注释、提交信息、文档使用简体中文；函数及重要步骤添加清晰注释。
- 模块变更同步 `docs/INDEX.md`；结构、命令或约定变化同步相关 README / AGENTS。
- README 仅记录项目介绍、功能、结构与使用说明；AGENTS 仅记录约束和快速索引。调试过程、报错、缺陷清单及修复记录不写入这些文档，也不写入模块索引。
- `.env` 与凭据不得进入 Git 历史或接口/日志；不提交 `.idea/`、`.venv/`、`node_modules/`、`.workbuddy/` 等本地产物；`frontend/package-lock.json` 必须提交。

## 按范围读取

| 工作范围 | 文档 |
| --- | --- |
| 跨端、基础设施、文档 | 本文件 |
| 后端 | [backend/AGENTS.md](backend/AGENTS.md) |
| 前端 | [frontend/AGENTS.md](frontend/AGENTS.md) |

## 目录入口

| 位置 | 用途 |
| --- | --- |
| `backend/` | FastAPI、RAG、评测、认证与 MCP |
| `frontend/` | React 页面、组件与请求 |
| `docs/INDEX.md` | 文档与模块索引 |
| `docker-compose.yml`、`postgres.Dockerfile` | PostgreSQL / pgvector / zhparser 与 Redis Stack |
| `.env.example` | 基础配置模板，实际配置写入 `.env` |
