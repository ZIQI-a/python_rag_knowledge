// 路由策略调试面板前端展示


import {Collapse, Tag, Typography} from "antd";
import type {QueryRouteRead} from "@/client";
import React from "react";

const { Paragraph, Text } = Typography

const ROUTE_META: Record<QueryRouteRead['route'], { color: string; label: string; hint: string }> = {
    original: { color: 'default', label: 'Original', hint: '问题清晰，无需改写' },
    rewrite: { color: 'blue', label: 'Rewrite', hint: '问题已改写' },
    hyde: { color: 'purple', label: 'HyDE', hint: '以生成假设答案用于检索' },
    multi_query: { color: 'orange', label: 'Multi_Query', hint: '已扩展为多个子查询' },
}

 // 路由策略调试面板前端展示
interface QueryRoutePanelProps {
    queryRoute: QueryRouteRead
}

/**
 * Query优化调试面板，AI消息上方折叠展示路由结果
 */
export function QueryRoutePanel({ queryRoute }: QueryRoutePanelProps) {
    if(queryRoute.route === 'original') return null

    const meta = ROUTE_META[queryRoute.route]
    return (
        <Collapse
            size="small"
            ghost
            style={{ marginTop: 12, background: '#fafafa', borderRadius: 6 }}
            items={[
                {
                    key: 'route',
                    label: (
                        <span>
                            <Tag color={meta.color} style={{ marginInlineEnd: 8 }}>
                                {meta.label}
                            </Tag>
                            <Text type="secondary">{meta.hint}</Text>
                        </span>
                    ),
                    children: <RouteDetail queryRoute={queryRoute} />
                }
            ]}
            />
    )
}

// 展示详情
function RouteDetail({queryRoute}: { queryRoute: QueryRouteRead }) {
    switch (queryRoute.route) {
        case 'rewrite':
            return (
                <DetailRow label="改写后的查询">
                    <Paragraph style={paragraphStyle}>{queryRoute.rewritten_query}</Paragraph>
                </DetailRow>
            )
        case 'hyde':
            return (
                <DetailRow label="HyDE假设答案">
                    <Paragraph style={paragraphStyle}>{queryRoute.hyde_answer}</Paragraph>
                </DetailRow>
            )
        case 'multi_query':
            return (
                <DetailRow label="子列表查询">
                    <ol style={{ paddingInlineStart: 20, margin: 0, color: '#555' }}>
                        {(queryRoute.multi_queries ?? []).map((q, i) => (
                            <li key={i} style={{ marginBottom: 4 }}>
                                {q}
                            </li>
                        ))}
                    </ol>
                    <Paragraph style={paragraphStyle}>{queryRoute.hyde_answer}</Paragraph>
                </DetailRow>
            )
        default:
            return null
    }
}


function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div>
            <Text strong style={{ fontSize: 12, color: '#888' }}>
                {label}
            </Text>
            <div style={{ marginTop: 4 }} > {children}</div>
        </div>
    )
}
// 段落样式
const paragraphStyle: React.CSSProperties = {
    whiteSpace: 'pre-wrap',
    marginBottom:0,
    color: '#555'
}

