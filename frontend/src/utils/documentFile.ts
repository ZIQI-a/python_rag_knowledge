import {getAuthToken} from "@/stores/authStore.ts";

const MARKDOWN_MIMES = new Set([
    'text/markdown',
    'text/x-markdown',
    'text/plain',
])

// 可预览的MIME类型
const PREVIEWABLE_MIMES = new Set([
    'application/pdf',
    'text/html',
    'application/xhtml+xml',
    ...MARKDOWN_MIMES,
])

// 构建文档文件下载链接
export function buildDocumentFileUrl(
    documentId: string,
    options: { download?: boolean } = {},
): string {
    const param = options.download ? '1': '0'
    const token = getAuthToken()
    const base = `/api/documents/${documentId}/file?download=${param}`
    return token ? `${base}/&token=${encodeURIComponent(token)}` : base
}

export function canPreviewInline(mimeType: string): boolean {
    return PREVIEWABLE_MIMES.has(mimeType)
}

export function isMarkdownMime(mimeType: string): boolean {
    return MARKDOWN_MIMES.has(mimeType)
}

export function isPdfMime(mimeType: string): boolean {
    return mimeType === 'application/pdf'
}

export function isHtmlMime(mimeType: string): boolean {
    return mimeType === 'text/html' || mimeType === 'application/xhtml+xml'
}
