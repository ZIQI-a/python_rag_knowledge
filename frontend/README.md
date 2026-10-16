# frontend — 问津前端

React 19 + TypeScript + Vite + Ant Design 6 + React Router 7 + TanStack Query。已实现文档管理、知识库对话、查询/检索调试、Trace 展示和评测分析。项目总览见 [根目录 README](../README.md)，开发约束见 [AGENTS.md](AGENTS.md)。

## 页面与功能

| 路由 | 页面 | 功能 |
| --- | --- | --- |
| `/` | `HomePage.tsx` | 首页与功能入口 |
| `/documents` | `DocumentsPage.tsx` | 上传、分页/状态筛选、状态刷新、重试与删除 |
| `/documents/:id` | `DocumentDetailPage.tsx` | 原文预览/下载、切片列表与内容查看 |
| `/chat` | `ChatPage.tsx` | 会话侧栏、历史消息、SSE 流式回答、引用、查询路由、Agent 步骤、答案校验及 Trace 信息 |
| `/evaluation` | `EvaluationListPage.tsx` | 新建/删除评测任务、任务列表、进度与汇总指标 |
| `/evaluation/runs/:id` | `EvaluationDetailPage.tsx` | 指标、Bad Case 筛选、样本详情、引用/追踪信息、人工归因与备注 |

评测任务列表及任务详情在 `running` 状态下每 5 秒轮询。评测集与后端配置、指标定义见 [后端评测说明](../backend/README.md#评测分析)。

## 开发

在 `frontend/` 执行，后端使用 `8000` 端口：

```bash
npm ci
npm run dev       # 默认 localhost:5173；/api 代理到 localhost:8000
npm run lint      # ESLint 检查
npm run build     # TypeScript 检查与生产构建
npm run preview   # 预览构建产物；不等同于生产部署
```

新增依赖使用 `npm install <包名>` 并同步 `package-lock.json`。开发代理在 `vite.config.ts` 配置；生产环境需自行将 `/api` 转发到后端，Vite 开发代理不会进入构建产物。

## API 与目录

- `src/client/`：OpenAPI 生成的类型及 SDK，禁止手工修改。
- `src/api/client.ts`：生成客户端的基础配置与错误处理；请求使用同源 `/api`。
- `src/api/chatStream.ts`：SSE 事件解析，包括路由、Agent 步骤、引用、校验结果和 Trace 字段。
- `src/api/evaluation.ts`：评测数据集、任务、样本及归因操作的 TanStack Query 封装。
- `src/api/queryKeys.ts`：会话与评测查询键。
- `src/components/`：会话侧栏、引用、查询路由、Agent 步骤、Trace、评测指标与归因选择组件。
- `src/routes/index.tsx`：全部页面路由；`src/layouts/BasicLayout.tsx` 提供布局与菜单。
- `src/main.tsx`：中文 `ConfigProvider`、antd `App` 上下文、QueryClient 和路由挂载。

后端接口变化后，先启动后端，再执行：

```bash
npm run gen-api
```

`openapi-ts.config.ts` 当前从 `http://localhost:8000/openapi.json` 生成客户端，与开发代理端口一致。后端端口变更时需同时调整这两个配置。
