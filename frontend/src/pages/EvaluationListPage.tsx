import {PageHeader} from '@/components/PageHeader'
import {DataState} from '@/components/PageState'
import {useState} from "react";
import {
    useCreateEvaluationRun,
    useDeleteEvaluationRun,
    useEvaluationDatasets,
    useEvaluationRuns
} from "@/api/evaluation.ts";
import type {ColumnsType} from "antd/lib/table";
import type {EvaluationRunListItem} from "@/client";
import {Link} from "react-router-dom";
import {App, Button, Form, Input, Modal, Popconfirm, Select, Table, Tag} from "antd";
import {DeleteOutlined, PlusOutlined} from "@ant-design/icons";


const STATUS_TAG: Record<string, { color: string; label: string }> = {
    running: { color: 'processing', label: '执行中' },
    completed: { color: 'success', label: '已完成' },
    failed: { color: 'error', label: '失败' },
}

/** 格式化百分比 */
function pct(v: number | null | undefined) {
    if (v === null || v === undefined) return '-'
    return `${(v * 100).toFixed(1)}%`
}

function CreateRunModal({open, onClose}: { open: boolean; onClose: () => void }) {
    const { message } = App.useApp()
    const datasets = useEvaluationDatasets()
    const mutation = useCreateEvaluationRun()
    const [form] = Form.useForm<{ name: string; dataset_name: string }>()

    return (
        <Modal
            title="新建评测"
            open={open}
            onCancel={onClose}
            destroyOnHidden
            onOk={async () => {
                const values = await form.validateFields()
                await mutation.mutateAsync(values)
                message.success('评测已创建，后台开始执行')
                form.resetFields()
                onClose()
            }}
            confirmLoading={mutation.isPending}
            okText="开始评测"
            >
                <Form form={form} layout="vertical" initialValues={{ name: '', dataset_name: 'seed' }}>
                    <Form.Item
                        name="name"
                        label="评测名称"
                        rules={[{ required: true, message: '请输入测评项' }, {max: 256}]}
                        >
                        <Input placeholder="如：接入rerank后" />
                    </Form.Item>
                    <Form.Item
                        name="dataset_name"
                        label="评测集"
                        rules={[{ required: true, message: '请选择评测集' }, {max: 256}]}
                    >
                        <Select
                            loading={datasets.isLoading}
                            options={(datasets.data?.items ?? []).map((d) => ({
                                value: d.name,
                                label: `${d.name} (${d.size}条)`
                            }))}
                            placeholder="请选择评测集"
                            />
                    </Form.Item>
                </Form>
        </Modal>
    )
}

function DeleteRunButton({ runId, runName }: { runId: string, runName: string }) {
    const { message } = App.useApp()
    const mutation = useDeleteEvaluationRun()
    return (
        <Popconfirm
            title={`删除评测 "${runName}"?`}
            description="该run及全部case都会被删除"
            okType="danger"
            onConfirm={async () => {
                await mutation.mutateAsync(runId)
                message.success('已删除')
            }}
        >
            <Button type="text" danger icon={<DeleteOutlined />} aria-label={`删除评测：${runName}`} />
        </Popconfirm>
    )
}

export function EvaluationListPage() {
    const [page, setPage] = useState(1)
    const  pageSize = 20
    const { data, isLoading, isError, refetch } = useEvaluationRuns(page, pageSize)
    const [modalOpen, setModalOpen] = useState(false)

    const columns: ColumnsType<EvaluationRunListItem> = [
        {
            title: '名称',
            dataIndex: 'name',
            render: (text, record) => <Link to={`/evaluation/runs/${record.id}`}>{text}</Link>
        },
        {
            title: '测评集',
            dataIndex: 'dataset_name',
            width: 120,
            render: (text, r) => (
                <span>
                    {text} <Tag>{r.dataset_size}</Tag>
                </span>
            )
        },
        {
            title: '状态',
            dataIndex: 'status',
            width: 120,
            render: (status: string, r) => {
                const tag = STATUS_TAG[status] ?? { color: 'default', label: status }
                if (status === 'running') {
                    return (
                        <Tag color={tag.color}>
                            {tag.label} {r.progress_completed}/{r.progress_total}
                        </Tag>
                    )
                }
                return <Tag color={tag.color}>{tag.label}</Tag>
            }
        },
        { title: 'Faithfulness', dataIndex: 'faithfulness', width: 110, render: pct },
        { title: 'AnswerRel', dataIndex: 'answer_relevancy', width: 110, render: pct },
        { title: 'Ctx Prec', dataIndex: 'context_precision', width: 110, render: pct },
        { title: 'Ctx Recall', dataIndex: 'context_recall', width: 110, render: pct },
        { title: '引用命中', dataIndex: 'citation_hit_rate', width: 100, render: pct },
        { title: '拒答正确', dataIndex: 'refusal_accuracy', width: 100, render: pct },
        {
            title: '平均耗时',
            dataIndex: 'avg_latency_ms',
            width: 110,
            render: (v: number | null) => (v === null || v === undefined ? '-' : `${Math.round(v)}`)
        },
        {
            title: '首Token延迟',
            dataIndex: 'avg_first_token_latency_ms',
            width: 120,
            render: (v: number | null) => (v === null || v === undefined ? '-' : `${Math.round(v)}`)
        },
        {
            title: '操作',
            width: 80,
            render: (_, record) => <DeleteRunButton runId={record.id} runName={record.name} />
        },
    ]

    return (
        <div>
            <PageHeader title="试津 · 评测分析" description="查看问答质量指标、评测样本与问题归因。" actions={<>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                    新建评测
                </Button>
            </>}/>
            {!isLoading && (isError || !data?.items.length) ? (
                <DataState failed={isError} description="暂无评测任务"
                    onRetry={() => {void refetch()}}
                    action={page > 1 ? <Button onClick={() => setPage(1)}>返回第一页</Button> : <Button type="primary" onClick={() => setModalOpen(true)}>创建首次评测</Button>}/>
            ) : (
            <Table
                rowKey="id"
                loading={isLoading}
                columns={columns}
                dataSource={data?.items ?? []}
                pagination={{
                    current: page,
                    pageSize,
                    total: data?.total ?? 0,
                    onChange: (p) => setPage(p),
                    showSizeChanger: false
                }}
                scroll={{ x: 1400 }}
            />
            )}
            <CreateRunModal open={modalOpen} onClose={() => setModalOpen(false)} />
        </div>
    )
}
