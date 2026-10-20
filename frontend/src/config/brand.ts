/** 产品名称、标识及路由标题统一维护。 */
export const BRAND = {
    name: '问津',
    productName: '问津 · AI 知识库',
    logoSrc: '/favicon.svg',
} as const

const PAGE_NAMES: Record<string, string> = {
    '/': '问津亭',
    '/login': '登录',
    '/documents': '藏书阁',
    '/chat': '万事知',
    '/evaluation': '试津',
    '/users': '名籍',
    '/roles': '司津',
}

/** 使用固定模块名，不将文档或会话中的私人内容放入浏览器标签。 */
export function getPageTitle(pathname: string): string {
    const path = pathname.replace(/\/+$/, '') || '/'
    const pageName = PAGE_NAMES[path]
        ?? (/^\/documents\/[^/]+$/.test(path) ? '文档详情' : undefined)
        ?? (/^\/evaluation\/runs\/[^/]+$/.test(path) ? '评测详情' : undefined)
    return pageName ? `${pageName} · ${BRAND.name}` : BRAND.productName
}
