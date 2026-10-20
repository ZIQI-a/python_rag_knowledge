/** 产品名称、标识及路由标题统一维护。 */
export const BRAND = {
    name: '问津',
    productName: '问津 · AI 知识库',
    logoSrc: '/favicon.svg',
    description: '问津是面向企业文档的 AI 知识库，提供文档管理、带来源引用的智能问答、评测分析与权限管理。',
} as const

interface PageInformation {
    name: string
    description: string
}

const PAGE_INFORMATION: Record<string, PageInformation> = {
    '/': {name: '问津亭', description: '查看问津知识库后端、数据库与文件存储的服务状态。'},
    '/login': {name: '登录', description: BRAND.description},
    '/documents': {name: '藏书阁', description: '管理知识库文档，查看解析进度、内容切片与文档版本。'},
    '/chat': {name: '万事知', description: '基于有权访问的知识库文档提问，获取流式回答与可追溯的来源引用。'},
    '/evaluation': {name: '试津', description: '管理知识库问答评测，查看质量指标、样本结果与问题归因。'},
    '/users': {name: '名籍', description: '管理问津知识库用户及其角色分配。'},
    '/roles': {name: '司津', description: '管理问津知识库角色与文档访问权限标签。'},
}

/** 仅使用模块说明，避免将文档、会话内容或 URL 参数写入页面元信息。 */
export function getPageMetadata(pathname: string): {title: string; description: string} {
    const path = pathname.replace(/\/+$/, '') || '/'
    const information = PAGE_INFORMATION[path]
        ?? (/^\/documents\/[^/]+$/.test(path)
            ? {name: '文档详情', description: '查看知识库文档内容、切片、版本与处理进度。'} : undefined)
        ?? (/^\/evaluation\/runs\/[^/]+$/.test(path)
            ? {name: '评测详情', description: '查看单次评测的指标、样本结果与问题归因。'} : undefined)
    return {
        title: information ? `${information.name} · ${BRAND.name}` : BRAND.productName,
        description: information?.description ?? BRAND.description,
    }
}

/** 保留统一的标签标题入口。 */
export function getPageTitle(pathname: string): string {
    return getPageMetadata(pathname).title
}
