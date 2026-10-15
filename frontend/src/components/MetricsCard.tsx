/** 评测指标卡组件一共8个卡片，6张指标，2张耗时 */
import {Card, Statistic, Tooltip} from "antd";
import {QuestionCircleOutlined} from "@ant-design/icons";


interface MetricsCardProps {
    label: string
    value: number | null | undefined
    // false: [0,1] 显示百分比，颜色控制; true: 显示原值 如ms
    passthrough?: boolean // 是否按原值展示？用于精度控制
    hint?: string
    suffix?: string
}

/** 格式化指标值 */
function formatValue(value: number | null | undefined, passthrough: boolean) {
    if (value === null || value === undefined) return '-'
    if (passthrough) return value.toFixed(2)
    return (value * 100).toFixed(1)
}

/** 指标卡颜色 */
function colorOf(value: number | null | undefined, passthrough: boolean) {
    if (value === null || value === undefined) return undefined
    if (passthrough) return undefined
    if (value >= 0.8) return '#52c41a'
    if (value >= 0.6) return '#faad14'
    return '#ff4d4f'
}

/** 指标卡组件 */
export function MetricsCard({ label, value, passthrough = false, hint, suffix }: MetricsCardProps) {
    const display = formatValue(value, passthrough)
    return (
        <Card size="small" variant="outlined">
            <Statistic
                title={
                    <span>
                        {label}
                        {hint && (
                             <Tooltip title={hint}>
                                 <QuestionCircleOutlined style={{ marginLeft: 6, color: '#8c8c8c' }} />
                             </Tooltip>
                            )
                        }
                    </span>
                }
                value={display}
                suffix={value === null || value === undefined ? '' : suffix ?? (passthrough ? '' : '%')}
                valueStyle={{ color: colorOf(value, passthrough) }}
                />
        </Card>
    )
})
