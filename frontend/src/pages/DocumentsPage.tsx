import {
    Button,
    message,
    Popconfirm, Select,
    Space, Table,
    type TableProps,
    Tag,
    Tooltip,
    Typography,
    Upload,
    type UploadProps
} from "antd";
import {deleteDocument, type DocumentRead, listDocuments, retryDocument, uploadDocument} from "@/client";
import {useMemo, useState} from "react";
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {getStatusColor, getStatusLabel, isTerminalStatus} from "@/utils/documentStatus.ts";
import {Link} from "react-router-dom";
import {DeleteOutlined, InboxOutlined, ReadOutlined, ReloadOutlined} from "@ant-design/icons";


const { Title, Paragraph} = Typography

const ACCEPTED = '.pdf, .docx, .md, .markdown, .html, .htm'

type StatusFilter = DocumentRead['status'] | 'all'

const STATUS_OPTIONS: { label: string, value: StatusFilter }[] = [
    {label: '全部状态', value: 'all'},
    {label: '上传中', value: 'uploading'},
    {label: '解析中', value: 'parsing'},
    {label: '索引中', value: 'indexing'},
    {label: '已就绪', value: 'ready'},
    {label: '失败', value: 'failed'}
]

const DELETABLE_STATUSES: ReadonlySet<DocumentRead['status']> = new Set([
    'uploading',
    'ready',
    'failed'
])

// 大小前端格式化
function formatSize(size: number): string {
    if (size < 1024) return `${size} B`
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
    return `${(size / 1024 / 1024).toFixed(2)} MB`
}
// 文档轮训展示
export function DocumentsPage() {
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
    const queryClient = useQueryClient()

    // 根据条件获取文档列表（React Query）
    const listQuery = useQuery({
        queryKey: ['documents', page, pageSize, statusFilter],
        queryFn: async () => {
            const res = await listDocuments({
                query: {
                    page,
                    page_size: pageSize,
                    status: statusFilter === 'all' ? undefined : statusFilter,
                }
            })
            return res.data!
        },
        // 设置轮询，只有失败或成功状态返回false停止轮询其他每3秒轮询一次
        refetchInterval: (query) => {
            const data = query.state.data
            if(!data) return false
            const hasInflight = data.items. some((d) => !isTerminalStatus(d.status))
            return hasInflight ? 3000 : false
        }
    })

    const invalidateList = () =>
        queryClient.invalidateQueries({queryKey: ['documents']})

    /**
     * 上传文件方法
     */
    const uploadMutation = useMutation({
        mutationFn: async (file: File) => {
            const res = await uploadDocument({ body: { file } })
            return res.data!
        },
        onSuccess: (doc) => {
            message.success(`${doc.name} 已提交，后台处理中`)
            invalidateList()
        }
    })
    /**
     * 重试解析
     */
    const retryMutation = useMutation({
        mutationFn: async (id: string) => {
            const res = await retryDocument({ path: {document_id: id} })
            return res.data!
        },
        onSuccess: () => {
            message.success("已提交重新解析")
            invalidateList() // 刷新列表，数据已经发生变化
        }
    })
    /**
     * 删除给定ID的文档
     */
    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            await deleteDocument({path: {document_id: id}})
            return id
        },
        onSuccess: () => {
            message.success("文档已删除")
            invalidateList()
        }
    })

    const uploadProps: UploadProps = useMemo(
        () => ({
            multiple: true,
            accept: ACCEPTED,
            showUploadList: false,
            customRequest: ({file}) => {
                uploadMutation.mutate(file as File)
            }
        }),
        [uploadMutation],
    )
    /**
     * 表格的列，属性
     */
    const columns: TableProps<DocumentRead>['columns'] = [
        {
            title: '文档名',
            dataIndex: 'name',
            ellipsis: true,
            render: (name: string, record) => <Link to={`/documents/${record.id}`}>{name}</Link>,
        },
        {
            title: '类型',
            dataIndex: 'mime_type',
            width: 220,
            ellipsis: true
        },
        { title: '大小', dataIndex: 'size', width: 110, render: formatSize },
        {
            title: '状态',
            dataIndex: 'status',
            width: 110,
            render: (status: DocumentRead['status']) => (
                <Tag color={(getStatusColor(status))}>{getStatusLabel(status)}</Tag>
            ),
        },
        {
            title: '上传时间',
            dataIndex: 'created_at',
            width: 200,
            render: (value: string) => new Date(value).toLocaleString('zh-CN')
        },
        {
            title: '操作',
            key: 'actions',
            width: 180,
            render: (_, record) => {
                const canDelete = DELETABLE_STATUSES.has(record.status)
                const canRetry = record.status === 'failed'
                return (
                    <Space>
                        {canRetry ? (
                                <Button
                                    type='link'
                                    size="small"
                                    icon={<ReadOutlined />}
                                    loading={retryMutation.isPending && retryMutation.variables === record.id}
                                    onClick={() => retryMutation.mutate(record.id)}
                                >
                                    重试
                                </Button>
                            ): null }
                        <Tooltip title={canDelete ? '' : '文档当前状态无法删除'}>
                            <Popconfirm title="确认删除该文档?"
                                        description="将同时删除文档内容、切片以及云端文件，无法恢复"
                                        okText="删除"
                                        okButtonProps={{ danger: true }}
                                        cancelText="取消"
                                        disabled={!canDelete}
                                        onConfirm={() => deleteMutation.mutate(record.id)}>
                                <Button
                                    type="link"
                                    size="small"
                                    danger
                                    icon={<DeleteOutlined />}
                                    disabled={!canDelete}
                                    loading={
                                        deleteMutation.isPending && deleteMutation.variables === record.id
                                    }
                                >
                                    删除
                                </Button>
                            </Popconfirm>
                        </Tooltip>
                    </Space>
                )
            }
        }
    ]

    return (
        <div>
            <Title level={3}>文档管理</Title>
            <Paragraph type={"secondary"}>
                支持PDF、 Word、 HTML、Markdown。上传后会进行文档解析、拆分、向量化，状态自动刷新
            </Paragraph>
            <Space style={{marginBottom: 16}} wrap>
                <Upload {...uploadProps}>
                    <Button type="primary" icon={<InboxOutlined />} loading={uploadMutation.isPending}>
                        上传文档
                    </Button>
                </Upload>
                <Button icon={<ReloadOutlined />}
                        onClick={() => listQuery.refetch()}
                        loading={listQuery.isFetching}>
                    刷新
                </Button>
                <Select<StatusFilter>
                    value={statusFilter}
                    onChange={(v) => {
                        setStatusFilter(v)
                        setPage(1)
                    }}
                    options={STATUS_OPTIONS}
                    style={{width: 140}}
                    />
            </Space>
            <Table<DocumentRead>
                rowKey="id"
                loading={listQuery.isLoading}
                columns={columns}
                dataSource={listQuery.data?.items ?? []}
                pagination={{
                    current:page,
                    pageSize,
                    total: listQuery.data?.total ?? 0,
                    showSizeChanger: true,
                    onChange: (nextPage, nextSize) => {
                        setPage(nextPage)
                        setPageSize(nextSize)
                    },
                }}
                />
        </div>
    )

}


