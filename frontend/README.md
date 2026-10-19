# frontend — 问津前端

React 19、TypeScript、Vite、Ant Design 6、React Router 7 与 TanStack Query 构建的知识库界面。

## 页面

| 路由 | 功能 |
| --- | --- |
| `/login` | 登录 |
| `/` | 首页 |
| `/documents`、`/documents/:id` | 文档管理、预览/下载、切片、版本与任务进度 |
| `/chat` | 会话、流式问答、引用、查询策略、Agent 步骤与 Trace |
| `/evaluation`、`/evaluation/runs/:id` | 评测任务、指标、样本与 Bad Case 归因 |
| `/users`、`/roles` | 用户与角色管理 |

业务页需要登录，评测、用户及角色页面需要管理员。文档写操作也受管理员权限控制。

## 目录

- `src/pages/`：业务页面。
- `src/routes/`、`src/layouts/`：路由、布局及菜单。
- `src/components/`：引用、追踪、评测、会话与鉴权组件。
- `src/api/`：请求封装、SSE、查询键及业务数据请求。
- `src/client/`：OpenAPI 生成的类型和 SDK。
- `src/stores/`、`src/utils/`：认证状态与公共工具。
- `src/main.tsx`：中文配置、antd App、QueryClient 与路由挂载。

## 开发

在 `frontend/` 执行：

```bash
npm ci
npm run dev
npm run lint
npm run build
npm run gen-api
```

开发地址为 `http://localhost:5173`；`vite.config.ts` 的 `/api` 代理与 `openapi-ts.config.ts` 均使用后端 `8000` 端口。生成 API 客户端前需启动后端，禁止手工修改 `src/client/`。生产环境需将 `/api` 转发到后端。

项目概览见 [根目录 README](../README.md)，开发约束见 [AGENTS.md](AGENTS.md)。
