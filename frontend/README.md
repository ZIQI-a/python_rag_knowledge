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
- `src/config/brand.ts`：品牌名称、标识地址与模块标题、描述。
- `src/api/`：请求封装、SSE、查询键及业务数据请求。
- `src/client/`：OpenAPI 生成的类型和 SDK。
- `src/stores/`、`src/utils/`：认证状态与公共工具。
- `src/main.tsx`：中文配置、antd App、QueryClient 与路由挂载。

## 品牌标识

使用「渡口书页」标识，登录页和侧栏共用 `BrandLogo`，折叠侧栏仅展示图标。`PageTitleLayout` 随路由更新标签标题，名称统一维护在 `src/config/brand.ts`。

`public/favicon.svg` 为矢量标识，`favicon.ico` 提供 16、32、48 像素版本，`apple-touch-icon.png` 为 180 像素触屏图标。更换标识时同步这些资源；HTML 初始标题在 `index.html` 中维护。

## 页面信息与搜索收录

`index.html` 提供初始产品描述、Open Graph 与 Twitter 分享摘要；`PageTitleLayout` 根据 `brand.ts` 同步各模块标题和描述。元信息使用固定模块说明，不包含文档名、问答内容、用户信息及 URL 参数。调整通用产品描述时同步 `brand.ts` 与 HTML 初始值；不执行 JavaScript 的分享服务使用 HTML 初始摘要。

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
