# 前端约束与索引

全局约束见 [根 AGENTS.md](../AGENTS.md)；运行命令和页面说明见 [README.md](README.md)。

## 约束

1. `/login` 独立；业务页经 `RequireAuth` 放在 `BasicLayout` 下，管理员页再包 `RequireAdmin`。新增业务页同步路由与菜单。
2. 使用 Ant Design 和 `@ant-design/icons`，不引入第二套组件库；语言包及消息上下文由 `main.tsx` 提供。
3. `src/index.css` 仅保留全局重置，页面样式优先使用组件属性与内联 style，不新增全局 CSS。
4. `src/client/` 为生成代码，接口变化执行 `npm run gen-api`，不手改；开发代理和生成地址与后端端口对齐。
5. 前端改动执行 `npm run lint`、`npm run build`；依赖变更同步 `package-lock.json`。

## 快速索引

| 范围 | 入口 |
| --- | --- |
| 装配 / 路由 / 布局 | `src/main.tsx`、`src/routes/index.tsx`、`src/layouts/BasicLayout.tsx` |
| 业务页面 | `src/pages/` |
| 登录状态与守卫 | `src/stores/authStore.ts`、`src/components/RequireAuth.tsx`、`RequireAdmin.tsx` |
| 共享组件 | `src/components/` |
| 品牌 / 页面元信息 / 收录 | `src/config/brand.ts`、`src/components/BrandLogo.tsx`、`PageTitleLayout.tsx`、`index.html`、`public/robots.txt` |
| 请求 / SSE / 查询键 | `src/api/` |
| 生成客户端 / 代理 | `src/client/`、`openapi-ts.config.ts`、`vite.config.ts` |
| 文件链接与辅助逻辑 | `src/utils/` |
