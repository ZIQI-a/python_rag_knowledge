import {PageHeader} from '@/components/PageHeader'
import {Card, Col, Row, Spin, Tag, Typography} from 'antd'
import {healthApp, healthCos, healthDb, type HealthStatus} from "@/client";
import {useQuery} from "@tanstack/react-query";

const {Paragraph, Text} = Typography

interface CheckCardProps {
    title: string
    description: string
    data: HealthStatus | undefined
    isLoading: boolean
}

// 根据状态选取颜色
function statusColor(status: HealthStatus['status'] | undefined): string {
    if (status === 'ok') return 'success';
    if (status === 'not_configured') return 'warning';
    return 'error';
}

// 获取展示的标签值
function statusLabel(status: HealthStatus['status'] | undefined): string {
    if (status === 'ok') return '正常';
    if (status === 'not_configured') return '未配置';
    if (status === 'error') return '异常';
    return '未知';
}

// 检查状态的卡片从后端获取信息展示
function CheckCard({title, description, data, isLoading}: CheckCardProps) {
    return (
        <Card title={title} variant="outlined">
            <Paragraph type="secondary" style={{marginBottom: 12}}>
                {description}
            </Paragraph>
            {
                isLoading ? (
                    <Spin/>
                ) : (
                    <>
                        <Tag color={statusColor(data?.status)} style={{fontSize: 14}}>
                            {statusLabel(data?.status)}
                        </Tag>
                        {data?.detail ? (
                            <Paragraph style={{marginTop: 12, marginBottom: 0}}>
                                <Text type="secondary">{data.detail}</Text>
                            </Paragraph>
                        ) : null}
                    </>
                )
            }
        </Card>
    )
}

export function HomePage() {
    const appQuery = useQuery({
        queryKey: ["health", "app"],
        queryFn: async () => (await healthApp()).data,
    });

    const dbQuery = useQuery({
        queryKey: ["health", "db"],
        queryFn: async () => (await healthDb()).data
    });
    const cosQuery = useQuery({
        queryKey: ["health", "cos"],
        queryFn: async () => (await healthCos()).data
    });

    return (
        <div>
            <PageHeader title="问津亭 · 服务状态" description="查看后端服务、数据库及文件存储的运行状态。"/>
            <Row gutter={[16, 16]} style={{marginTop: 16}}>
                <Col xs={24} md={8}>
                    <CheckCard title='后端服务'
                               description='GET /api/health'
                               data={appQuery.data}
                               isLoading={appQuery.isLoading}
                    />
                </Col>
                <Col xs={24} md={8}>
                    <CheckCard title='数据库服务'
                               description='GET /api/health/db'
                               data={dbQuery.data}
                               isLoading={dbQuery.isLoading}
                    />
                </Col>
                <Col xs={24} md={8}>
                    <CheckCard title='云存储服务'
                               description='GET /api/health/cos'
                               data={cosQuery.data}
                               isLoading={cosQuery.isLoading}
                    />
                </Col>
            </Row>
        </div>
    )
}
