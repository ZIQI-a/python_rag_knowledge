import {PALETTE} from '@/config/theme'
import {Collapse, Tag, Typography} from "antd";
import type {AgentStep} from "@/client";
import React from "react";


const { Text, Paragraph } = Typography
// 影射5种Action
const ACTION_META: Record<AgentStep['action'], { color: string; label: string }> = {
    initial: { color: 'default', label: '初始检索' },
    proceed: { color: 'success', label: '继续生成' },
    rewrite_query: { color: 'blue', label: '改写Query' },
    switch_route: { color: 'purple', label: '切换策略' },
    refuse: { color: 'error', label: '拒绝' }
}

interface AgentStepsPanelProps {
    steps: AgentStep[]
}

/**
 * AgenticRAG调试面板展示每一轮的决策与观察
 */
export function AgentStepsPanel({ steps }: AgentStepsPanelProps) {
    if (steps.length === 0) return null
    if (steps.length === 1 && steps[0]?.action === 'initial') return null

    const rounds = steps.length
    const finalStep = steps[steps.length - 1]

    return (
        <Collapse
            size="small"
            ghost
            style={{ marginTop: 12, background: PALETTE.sunken, borderRadius: 6 }}
            items={[
                {
                    key: 'agent',
                    label: (
                        <span>
                            <Tag color="geekblue" style={{ marginInlineEnd: 8 }}>
                                Agent · {rounds} 轮
                            </Tag>
                            <Text type="secondary">
                                最终动作：{finalStep ? ACTION_META[finalStep.action].label : '-'}
                            </Text>
                        </span>
                    ),
                    children: (
                        <ol style={{ paddingInlineStart:20, margin: 0 }}>
                            {steps.map((step) => (
                                <li key={step.round} style={{ marginBottom: 10 }}>
                                    <StepRow step={step}/>
                                </li>
                            ))}
                        </ol>
                    )
                }
            ]}
        />
    )
}


function StepRow({ step }: {step: AgentStep}) {
    const meta = ACTION_META[step.action]
    return (
        <div>
            <div style={{ marginBottom: 4 }}>
                <Tag color={meta.color} style={{ marginInlineEnd: 6 }}>
                    Round {step.round} · {meta.label}
                </Tag>
                <Tag style={{ marginInlineEnd: 6 }}>{step.route}</Tag>
                {step.sufficient != null ? (
                    <Tag color={step.sufficient ? 'success' : 'warning'}>
                        {step.sufficient ? '上下文充足' : '上下文不足'}
                    </Tag>
                ): null}
            </div>
            <Paragraph style={paragraphStyle}>
                <Text type="secondary" style={smallLabel}>
                    query:
                </Text>
                {step.query}
            </Paragraph>
            <Paragraph style={paragraphStyle}>
                <Text type="secondary" style={smallLabel}>
                    reason:
                </Text>
                {step.reason}
            </Paragraph>
            {step.retrieved_count != null || step.top_score != null ? (
                <Text type="secondary" style={{ fontSize: 12 }}>
                    检索 {step.retrieved_count ?? '-'} 条
                    {step.top_score != null ? ` · Top score ${step.top_score}` : ''}
                </Text>
            ): null}
        </div>
    )
}

const paragraphStyle: React.CSSProperties = {
    whiteSpace: 'pre-wrap',
    marginBottom: 4,
    color: PALETTE.secondary,
    fontSize: 13
}
const smallLabel: React.CSSProperties = {
    fontSize: 12,
    marginInlineEnd: 4
}
