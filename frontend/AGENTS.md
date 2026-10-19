# frontend/AGENTS.md — 前端开发约束

仅在前端开发时读取本文件。全局行为准则（只改明确让改的文件、Git 仅明确要求时提交等）见根目录 [AGENTS.md](../AGENTS.md)。

## 技术栈

React 19 · TypeScript · Vite · Ant Design 6 · React Router 7 · zustand · @tanstack/react-query

## 常用命令

```bash
npm install        # 安装依赖（package-lock.json 必须提交）
npm run dev        # 开发启动
npm run build      # tsc + vite 构建
npm run lint       # ESLint 检查
npm run gen-api    # 从后端 OpenAPI 生成 API 客户端；当前后端、生成地址及开发代理均使用 8000
```

## 前端约定

1. **布局与路由**：登录页 `/login` 独立；其他业务页面经 `RequireAuth` 挂在 `src/layouts/BasicLayout.tsx` 的 `Outlet` 下，管理员页面再包 `RequireAdmin`；新增业务页面 = 在 `src/pages/` 建组件 + 在 `src/routes/index.tsx` 的 children 加路由 + 在 BasicLayout 菜单加条目。
2. **UI 组件**：统一使用 antd 组件与 `@ant-design/icons`，不引入第二个组件库；全局中文语言包已在 `main.tsx` 的 `ConfigProvider` 配置。
3. **全局样式**：`src/index.css` 仅保留全局重置，页面样式优先用 antd 组件属性与内联 style，不新增全局 CSS。
4. **完成标准**：改动须通过 `npm run lint` 与 `npm run build` 验证。
5. **接口联调**：后端 API 前缀为 `/api`，健康检查为 `/api/health*`。
6. **生成代码**：`src/client/` 由 `openapi-ts.config.ts` 生成，接口变化后重新生成，不手工修改生成文件。

## 目录速查

| 要做什么 | 去哪里 |
| --- | --- |
| 新增页面 | `src/pages/` + `src/routes/index.tsx` + BasicLayout 菜单 |
| 修改主布局/菜单 | `src/layouts/BasicLayout.tsx` |
| 应用入口（挂载/语言包/消息上下文） | `src/main.tsx` 中的 `ConfigProvider`、antd `App`、`QueryClientProvider` |
| 构建配置 | `vite.config.ts` |
| API 客户端生成 | `openapi-ts.config.ts` + `src/client/` |
| 文档管理与详情 | `src/pages/DocumentsPage.tsx`、`DocumentDetailPage.tsx` |
| 知识库问答与会话侧栏 | `src/pages/ChatPage.tsx` + `src/components/ConversationSidebar.tsx` |
| SSE 问答事件 | `src/api/chatStream.ts` |
| 查询/Agent/追踪展示 | `src/components/QueryRoutePanel.tsx`、`AgentStepsPanel.tsx`、`TraceIdPanel.tsx` |
| 评测列表与详情 | `src/pages/EvaluationListPage.tsx`、`EvaluationDetailPage.tsx` |
| 评测数据请求与查询键 | `src/api/evaluation.ts`、`src/api/queryKeys.ts` |
| 评测指标与归因 | `src/components/MetricsCard.tsx`、`BadCaseCategorySelect.tsx` + `src/utils/badCaseCategory.ts` |
| 登录、用户与角色页面 | `src/pages/LoginPage.tsx`、`UserPage.tsx`、`RolesPage.tsx` |
| 认证状态与路由守卫 | `src/stores/authStore.ts` + `src/components/RequireAuth.tsx`、`RequireAdmin.tsx` |
| 登录/用户/角色 API | `src/api/auth.ts`、`users.ts`、`roles.ts` |
| 顶栏用户菜单 | `src/components/UserMenu.tsx` |
| 原文链接与预览类型 | `src/utils/documentFile.ts` |
