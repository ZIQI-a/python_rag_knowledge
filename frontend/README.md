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
- `src/config/theme.ts`：沧浪濯缨色板与 Ant Design 主题配置。
- `src/api/`：请求封装、SSE、查询键及业务数据请求。
- `src/client/`：OpenAPI 生成的类型和 SDK。
- `src/stores/`、`src/utils/`：认证状态与公共工具。
- `src/main.tsx`：中文配置、antd App、QueryClient 与路由挂载。

## 品牌标识

使用「渡口书页」标识，登录页和侧栏共用 `BrandLogo`，折叠侧栏仅展示图标。`PageTitleLayout` 随路由更新标签标题，名称统一维护在 `src/config/brand.ts`。

`public/favicon.svg` 为矢量标识，`favicon.ico` 提供 16、32、48 像素版本，`apple-touch-icon.png` 为 180 像素触屏图标。更换标识时同步这些资源；HTML 初始标题在 `index.html` 中维护。

## 页面信息与搜索收录

`index.html` 提供初始产品描述、Open Graph 与 Twitter 分享摘要；`PageTitleLayout` 根据 `brand.ts` 同步各模块标题和描述。元信息使用固定模块说明，不包含文档名、问答内容、用户信息及 URL 参数。调整通用产品描述时同步 `brand.ts` 与 HTML 初始值；不执行 JavaScript 的分享服务使用 HTML 初始摘要。

## 主题配色

默认使用「沧浪濯缨」亮色主题：宣纸 `#F6F4EC` 为页面底色，墨色 `#2B2B30` 为正文，沧浪 `#3E746B` 为主操作与链接，月白 `#E4EEEA` 为选中背景，朱砂 `#BF3B2B` 用于危险操作和失败状态。知识问答的策略、引用来源及缓存标签，以及用户角色标签使用不同颜色区分；状态保留语义色与文字说明。

`src/config/theme.ts` 统一导出 `PALETTE` 和 `wenjinTheme`。标准组件通过 `AppThemeProvider` 接入，自定义容器与 Markdown 样式引用同一色板；静态提示通过 `holderRender` 使用同一主题。保持可读字号，不引入全局样式覆盖或暗色切换。

## 布局与交互

菜单仅展示原有特色名称，业务含义在对应内容页标题和说明中展示。`PageHeader` 统一各业务页的一级标题、说明和操作区，小屏自动换行。工作台占满视口，内容区独立滚动；表格横向滚动限制在表格内部，聊天消息与输入区分开布局。

宽度小于 768 像素时，主菜单和聊天会话列表使用抽屉；支持 Esc 关闭，选择条目后收起。会话选择、用户菜单、图标操作支持键盘访问并提供可访问名称。`AppThemeProvider`、聊天滚动及引用定位响应系统减少动画偏好。

`PageState` 提供加载、空数据、请求失败与重试、404 和渲染异常兜底；空列表显示对应的新建或清除筛选入口。页面渲染失败时保留业务导航，异常内容不直接展示给用户。

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
