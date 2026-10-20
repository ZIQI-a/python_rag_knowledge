import {PageHeader} from '@/components/PageHeader'
import {DataState} from '@/components/PageState'
import {
    App as AntdApp,
    Button, Form,
    Modal,
    Popconfirm, Select,
    Space, Table,
    type TableProps,
    Tag,
    Tooltip,
    Upload,
    type UploadFile,
    type UploadProps
} from "antd";
import {deleteDocument, type DocumentRead, listDocuments, retryDocument, updateDocumentPermissionTags, uploadDocument} from "@/client";
import {useState} from "react";
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {getStatusColor, getStatusLabel, isTerminalStatus} from "@/utils/documentStatus.ts";
import {Link} from "react-router-dom";
import {DeleteOutlined, InboxOutlined, ReadOutlined, ReloadOutlined, TagOutlined} from "@ant-design/icons";
import {useAuthStore} from "@/stores/authStore.ts";



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

// 上传表单的字段：files 是 antd Upload 的文件列表，permission_tags 是权限标签
interface UploadFormValues {
    files?: UploadFile[]
    permission_tags?: string[]
}

/** 上传文档弹窗 */
function UploadModal({ open, onClose, onUpload }: {
    open: boolean
    onClose: () => void
    onUpload: (file: File, tags: string[]) => void
}) {
    const {message} = AntdApp.useApp()
    const [form] = Form.useForm<UploadFormValues>()

    const uploadProps: UploadProps = {
        multiple: false,
        accept: ACCEPTED,
        maxCount: 1,
        beforeUpload: () => false, // 用 form 控制提交
    }

    const handleOk = async () => {
        try {
            const values = await form.validateFields()
            const file = values.files?.[0]?.originFileObj as File | undefined
            if (!file) {
                message.error('请先选择文件')
                return
            }
            onUpload(file, values.permission_tags ?? [])
            form.resetFields()
            onClose()
        } catch {}
    }

    return (
        <Modal title="上传文档" open={open} onCancel={onClose} onOk={handleOk} destroyOnHidden>
            <Form<UploadFormValues> form={form} layout="vertical">
                <Form.Item
                    name="files" label="选择文件"
                    valuePropName="fileList"
                    getValueFromEvent={(e) => (Array.isArray(e) ? e : e?.fileList)}
                    rules={[{ required: true, message: '请选择文件' }]}
                >
                    <Upload {...uploadProps}>
                        <Button icon={<InboxOutlined />}>点击选择文件</Button>
                    </Upload>
                </Form.Item>
                <Form.Item
                    name="permission_tags" label="权限标签"
                    extra="留空视为公开（所有登录用户可见）；填入后仅拥有匹配标签的角色可见"
                >
                    <Select
                        mode="tags"
                        tokenSeparators={[',']}
                        open={false}
                        placeholder="例如：合同、财务；* 表示全部文档"
                        options={[{label: '*（全部文档）', value: '*'}]}
                    />
                </Form.Item>
            </Form>
        </Modal>
    )
}

// 文档轮训展示
export function DocumentsPage() {
    const {message} = AntdApp.useApp()
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
    // 上传弹窗开关
    const [uploadOpen, setUploadOpen] = useState(false)
    // 标签编辑弹窗：对象兼做开关和数据源
    const [tagEditing, setTagEditing] = useState<DocumentRead | null>(null)
    const [tagForm] = Form.useForm<{ permission_tags?: string[] }>()
    const queryClient = useQueryClient()
    // 标签编辑只有 admin 能用
    const isAdmin = useAuthStore((s) => Boolean(s.user?.isAdmin))

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
            const hasInflight = data.items.some((d) => !isTerminalStatus(d.status))
            return hasInflight ? 3000 : false
        }
    })

    const invalidateList = () =>
        queryClient.invalidateQueries({queryKey: ['documents']})

    /**
     * 上传文件方法
     */
    const uploadMutation = useMutation({
        mutationFn: async ({ file, tags }: {file: File; tags: string[]}) => {
            const res = await uploadDocument({ body: {
                    file, permission_tags: tags.length > 0 ? JSON.stringify(tags) : null,
                } })
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

    /**
     * 修改权限标签（仅 admin）
     */
    const updateTagsMutation = useMutation({
        mutationFn: async (params: { documentId: string; tags: string[] }) => {
            await updateDocumentPermissionTags({
                path: { document_id: params.documentId },
                body: { permission_tags: params.tags },
            })
        },
        onSuccess: () => {
            message.success('权限标签已更新')
            invalidateList()
        },
    })

    /** 打开标签编辑弹窗并回填 */
    function openTagEdit(record: DocumentRead) {
        setTagEditing(record)
        tagForm.setFieldsValue({ permission_tags: record.permission_tags ?? [] })
    }

    /** 提交标签修改 */
    async function submitTags() {
        if (!tagEditing) return
        try {
            const values = await tagForm.validateFields()
            await updateTagsMutation.mutateAsync({
                documentId: tagEditing.id,
                tags: values.permission_tags ?? [],
            })
            setTagEditing(null)
        } catch {
            // 校验失败 / 请求失败都保持弹窗打开
        }
    }

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
            title: '权限标签',
            dataIndex: 'permission_tags',
            width: 200,
            render: (tags: string[]) =>
                tags.length === 0 ? (
                    <Tag>公开</Tag>
                ) : (
                    <Space size={4} wrap>
                        {tags.map((t) => (
                            <Tag color={t === '*' ? 'warning' : 'default'} key={t}>
                                {t}
                            </Tag>
                        ))}
                    </Space>
                ),
        },
        {
            title: '版本',
            dataIndex: 'version',
            width: 80,
            render: (version: number) => <Tag color="default">v{version}</Tag>,
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
                        {isAdmin ? (
                            <Button type="link" size="small" icon={<TagOutlined />}
                                    onClick={() => openTagEdit(record)}>
                                标签
                            </Button>
                        ) : null}
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
            <PageHeader title="藏书阁 · 文档管理" description="支持PDF、 Word、 HTML、Markdown。上传后会进行文档解析、拆分、向量化，状态自动刷新" actions={<>
                <Button type="primary" icon={<InboxOutlined />}
                        onClick={() => setUploadOpen(true)}>
                    上传文档
                </Button>
                <Button icon={<ReloadOutlined />}
                        onClick={() => listQuery.refetch()}
                        loading={listQuery.isFetching}>
                    刷新
                </Button>
                <Select<StatusFilter>
                    aria-label="文档状态筛选"
                    value={statusFilter}
                    onChange={(v) => {
                        setStatusFilter(v)
                        setPage(1)
                    }}
                    options={STATUS_OPTIONS}
                    style={{width: 140}}
                    />
            </>}/>
            {!listQuery.isLoading && (listQuery.isError || !listQuery.data?.items.length) ? (
                <DataState failed={listQuery.isError} description={statusFilter === 'all' ? '暂无文档，可上传文件建立知识库' : '当前筛选条件下没有文档'}
                    onRetry={() => {void listQuery.refetch()}} action={page > 1 ? <Button onClick={() => setPage(1)}>返回第一页</Button> : statusFilter === 'all' ? <Button type="primary" onClick={() => setUploadOpen(true)}>上传第一份文档</Button> : <Button onClick={() => {setStatusFilter('all'); setPage(1)}}>清除筛选</Button>}/>
            ) : (
            <Table<DocumentRead>
                scroll={{x: 'max-content'}}
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
            )}
            {/*上传文档弹窗*/}
            <UploadModal
                open={uploadOpen}
                onClose={() => setUploadOpen(false)}
                onUpload={(file, tags) => uploadMutation.mutate({ file, tags })}
            />
            {/*编辑权限标签弹窗（仅 admin 入口可达）*/}
            <Modal
                title={`权限标签 · ${tagEditing?.name ?? ''}`}
                open={tagEditing !== null}
                forceRender
                confirmLoading={updateTagsMutation.isPending}
                okText="保存"
                cancelText="取消"
                onOk={submitTags}
                onCancel={() => setTagEditing(null)}
            >
                <Form form={tagForm} layout="vertical">
                    <Form.Item
                        name="permission_tags"
                        label="权限标签"
                        extra="留空视为公开（所有登录用户可见）；* 表示全部文档"
                    >
                        <Select
                            mode="tags"
                            tokenSeparators={[',']}
                            open={false}
                            placeholder="输入标签后回车"
                            options={[{label: '*（全部文档）', value: '*'}]}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )

}


