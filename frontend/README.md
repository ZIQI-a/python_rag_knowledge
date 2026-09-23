# frontend — 问津前端

React + TypeScript + Vite + Ant Design 6。当前提供首页和基础布局；文档管理、知识问答页面仍在建设中。项目总览见 [根目录 README](../README.md)，开发约束见 [AGENTS.md](AGENTS.md)。

## 开发

```bash
npm install
npm run dev       # 启动开发服务，/api 代理到 localhost:8080
npm run lint      # ESLint 检查
npm run build     # TypeScript 检查与生产构建
```

API 客户端由 `npm run gen-api` 根据后端 OpenAPI 生成到 `src/client/`。生成前先启动后端，并核对 `openapi-ts.config.ts` 中的 OpenAPI 地址与后端端口；当前配置为 `8000`，与开发代理的 `8080` 不同。不要手工修改生成文件。

页面位于 `src/pages/`，路由在 `src/router.tsx`，主布局和菜单在 `src/layouts/BasicLayout.tsx`。
