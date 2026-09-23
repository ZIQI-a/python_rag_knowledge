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
```

## 前端约定

1. **布局与路由**：所有页面挂在 `src/layouts/BasicLayout.tsx` 的 `Outlet` 下；新增页面 = 在 `src/pages/` 建组件 + 在 `src/router.tsx` 的 children 加路由 + 在 BasicLayout 菜单加条目。
2. **UI 组件**：统一使用 antd 组件与 `@ant-design/icons`，不引入第二个组件库；全局中文语言包已在 `main.tsx` 的 `ConfigProvider` 配置。
3. **全局样式**：`src/index.css` 仅保留全局重置，页面样式优先用 antd 组件属性与内联 style，不新增全局 CSS。
4. **完成标准**：改动须通过 `npm run lint` 与 `npm run build` 验证。
5. **接口联调**：后端 API 前缀为 `/api`，健康检查为 `/api/health*`。

## 目录速查

| 要做什么 | 去哪里 |
| --- | --- |
| 新增页面 | `src/pages/` + `src/router.tsx` + BasicLayout 菜单 |
| 修改主布局/菜单 | `src/layouts/BasicLayout.tsx` |
| 应用入口（挂载/语言包） | `src/main.tsx` |
| 构建配置 | `vite.config.ts` |
