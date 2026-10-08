// 引用面板组件
import {Collapse, Tag, Typography} from "antd";
import type {CitationRead} from "@/client";
import {forwardRef, useImperativeHandle, useState} from "react";
import {Link} from "react-router-dom";

const {Paragraph} = Typography
type SourceTagMeta = { color: string; label: string }

// 将source函数映射成tag源信息, 前端展示用了什么搜索方式
function formatSourceTag(sources?: string[]): SourceTagMeta | null {
    if (!sources || sources.length === 0) return null
    const hasVector = sources.includes('vector')
    const hasKeyword = sources.includes('keyword')
    if (hasVector && hasKeyword) return { color: 'purple', label: '混合' }
    if (hasVector) return { color: 'blue', label: '向量' }
    if (hasKeyword) return { color: 'orange', label: '关键词' }
    return null
}

// 引用列表组件的操作句柄
export interface CitationListHandle {
    expandAndScroll: (n: number) => void
}

// 引用列表组件
interface CitationListProps {
    citations: CitationRead[]
    messageId: string
}

// 生成面板的key
function panelKey(c: CitationRead): string {
    return c.id || `ord-${c.ordinal}`
}
// 生成锚点的id
function anchorId(messageId: string, n: number): string {
    return `cite-${messageId}-${n}`
}
// 引用列表组件
export const CitationList = forwardRef<CitationListHandle, CitationListProps>(
    function CitationList({ citations, messageId }, ref) {
        const [activeKey, setActiveKey] = useState<string[]>([]) // 受控active，保持已展开的项目不被点击

        useImperativeHandle(
            ref,
            () => ({
                expandAndScroll: (n: number) => {
                    const target = citations.find((c) => c.ordinal === n)
                    if (!target) return
                    const key = panelKey(target)
                    setActiveKey((prev) => (prev.includes(key) ? prev : [...prev, key]))
                    requestAnimationFrame(() => {
                        document
                            .getElementById(anchorId(messageId, n))
                            ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                    })
                }
            }),
            [citations, messageId]
        )

        if (citations.length === 0) return null;
        const items = citations.map((c) => {
            const sourceTag = formatSourceTag(c.retrieval_meta?.sources)
            return {
                key: panelKey(c),
                label: (
                    <span id={anchorId(messageId, c.ordinal)}>
                    <Tag color="blue" style={{ marginInlineEnd: 8 }}>{`[${c.ordinal}]`}</Tag>
                    {sourceTag ? (
                        <Tag color={sourceTag.color} style={{ marginInlineEnd: 8 }}>
                            {sourceTag.label}
                        </Tag>
                    ) : null}
                    {c.document_id ? (
                        <Link to={`/documents/${c.document_id}`}>{c.document_name}</Link>
                    ) : (
                        <span>{c.document_name}</span>
                    )}
                    {c.page_no != null ? (
                        <span style={{ marginInlineStart: 8, color: '#999' }}>第 {c.page_no} 页</span>
                    ) : null}
                </span>
                ),
                children: (
                    <Paragraph
                        style={{ whiteSpace: 'pre-wrap', marginBottom: 0, color: '#555' }}
                        ellipsis={{ rows: 6, expandable: true, symbol: '展开'}}
                    >
                        {c.quote}
                    </Paragraph>
                )
            }
        })

        return (
            <Collapse
                size="small"
                ghost
                items={items}
                activeKey={activeKey}
                onChange={(keys) => setActiveKey(typeof keys === 'string' ? [keys] : keys)}
                style={{ marginTop: 12, background: '#fafafa', borderRadius: 6 }}
                />
        )
    }
)


