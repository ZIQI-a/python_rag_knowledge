/** 用户管理页 */
import {App as AntdApp, Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, Typography} from "antd";
import type {TableProps} from "antd";
import {DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined, TeamOutlined} from "@ant-design/icons";
import {useState} from "react";
import type {UserRead} from "@/client";
import {useAuthStore} from "@/stores/authStore.ts";
import {
    useAssignUserRoles,
    useCreateUser,
    useDeleteUser,
    useUpdateUser,
    useUsers,
} from "@/api/users.ts";
import {useRoles} from "@/api/roles.ts";

const {Title, Paragraph} = Typography

// 创建用户表单的字段
interface CreateFormValues {
    username: string
    password: string
    display_name: string
    role_ids?: string[]
}

// 编辑表单的字段
interface EditFormValues {
    display_name: string
    status: UserRead['status']
    password?: string
}

// 分配角色表单的字段
interface AssignRoleFormValues {
    role_ids: string[]
}

export function UserPage() {
    const {message} = AntdApp.useApp()

    const me = useAuthStore((s) => s.user)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    // 三个弹窗开关
    const [createOpen, setCreateOpen] = useState(false)
    const [editing, setEditing] = useState<UserRead | null>(null)
    const [assigning, setAssigning] = useState<UserRead | null>(null)
    // 3个表单实例
    const [createForm] = Form.useForm<CreateFormValues>()
    const [editForm] = Form.useForm<EditFormValues>()
    const [assignForm] = Form.useForm<AssignRoleFormValues>()
    // 数据列表和操作
    const listQuery = useUsers(page, pageSize)
    const rolesQuery = useRoles()
    const createMutation = useCreateUser()
    const updateMutation = useUpdateUser()
    const deleteMutation = useDeleteUser()
    const assignMutation = useAssignUserRoles()
    // 角色下拉选项
    const roleOptions = (rolesQuery.data ?? []).map(
        (r) => ({ label: r.name, value: r.id })
    )

    const columns: TableProps<UserRead>['columns'] = [
        {title: '用户名', dataIndex: 'username', width: 160},
        {title: '昵称', dataIndex: 'display_name', ellipsis: true},
        {
            title: '角色',
            dataIndex: 'roles',
            width: 240,
            render: (_, record) => (
                record.roles && record.roles.length > 0 ? (
                    <Space size={4} wrap>
                        {record.roles.map((r) => <Tag key={r.id} color="default">{r.name}</Tag>)}
                    </Space>
                ) : <Space>-</Space>
            ),
        },
        {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (status: UserRead['status']) => (
                status === 'active'
                    ? <Tag color="success">正常</Tag>
                    : <Tag color="default">封禁</Tag>
            ),
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            width: 180,
            render: (v: string) => new Date(v).toLocaleString('zh-CN'),
        },
        {
            title: '操作',
            key: 'actions',
            width: 260,
            render: (_, record) => {
                // 后端也挡了（users.py:77），前端同步禁用，避免点了才报错
                const isSelf = record.id === me?.id
                return (
                    <Space size={0}>
                        <Button type="link" size="small" icon={<EditOutlined/>}
                                onClick={() => openEdit(record)}>
                            编辑
                        </Button>
                        <Button type="link" size="small" icon={<TeamOutlined/>}
                                onClick={() => openAssign(record)}>
                            角色
                        </Button>
                        <Popconfirm
                            title="确认删除该用户?"
                            description="删除后无法恢复，该用户将立即注销"
                            okText="删除"
                            cancelText="取消"
                            okButtonProps={{danger: true}}
                            disabled={isSelf}
                            onConfirm={() => handleDelete(record)}
                        >
                            <Button type="link" size="small" danger icon={<DeleteOutlined/>}
                                    disabled={isSelf}
                                    loading={deleteMutation.isPending && deleteMutation.variables === record.id}>
                                删除
                            </Button>
                        </Popconfirm>
                    </Space>
                )
            },
        },
    ]

    /** 打开编辑弹窗并回填 */
    function openEdit(user: UserRead) {
        setEditing(user)
        // Modal 上有 forceRender，表单此时已挂载，可以直接塞值
        editForm.setFieldsValue({
            display_name: user.display_name,
            status: user.status,
            password: undefined,   // 密码不回填，留空表示不改
        })
    }
    /** 打开分配角色弹窗并回填 */
    function openAssign(user: UserRead) {
        setAssigning(user)
        assignForm.setFieldsValue({
            role_ids: user.roles?.map((r) => r.id) ?? [],
        })
    }
    /** 删除 */
    function handleDelete(user: UserRead) {
        deleteMutation.mutate(user.id, {
            onSuccess: () => message.success(`用户 ${user.username} 已删除`),
        })
    }
    /** 提交新建 */
    async function submitCreate() {
        try {
            const values = await createForm.validateFields()
            await createMutation.mutateAsync({
                username: values.username.trim(),
                password: values.password,
                display_name: values.display_name.trim(),
                role_ids: values.role_ids ?? [],
            })
            message.success(`用户 ${values.username} 已创建`)
            setCreateOpen(false)
            createForm.resetFields()
        } catch {
            // validateFields 校验失败 / 请求失败，都保持弹窗打开
            // 表单会把错误字段标红，HTTP 错误已由 client.ts 拦截器弹过提示
        }
    }
    /** 提交编辑 */
    async function submitEdit() {
        if (!editing) return
        try {
            const values = await editForm.validateFields()
            await updateMutation.mutateAsync({
                userId: editing.id,
                body: {
                    display_name: values.display_name.trim(),
                    status: values.status,
                    // 只有填了新密码才带上这个字段
                    ...(values.password ? {password: values.password} : {}),
                },
            })
            message.success('已保存')
            setEditing(null)
        } catch {
            // 同上：校验失败或请求失败都不关弹窗
        }
    }
    /** 提交角色分配 */
    async function submitAssign() {
        if (!assigning) return
        try {
            const values = await assignForm.validateFields()
            await assignMutation.mutateAsync({
                userId: assigning.id,
                roleIds: values.role_ids ?? [],
            })
            message.success('角色已更新')
            setAssigning(null)
        } catch {
            // 同上
        }
    }



    return (
        <div>
            <Title level={3}>名籍管理</Title>
            <Paragraph type="secondary">
                在此可管理其中各项名籍记录
            </Paragraph>
            <Space style={{ marginBottom: 16 }} wrap>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
                    新添籍录
                </Button>
                <Button icon={<ReloadOutlined />} loading={listQuery.isFetching}
                        onClick={() => listQuery.refetch()}>
                    刷新
                </Button>
            </Space>
            <Table<UserRead>
                rowKey="id"
                loading={listQuery.isLoading}
                columns={columns}
                dataSource={listQuery.data?.items ?? []}
                pagination={{
                    current: page,
                    pageSize,
                    total: listQuery.data?.total ?? 0,
                    showSizeChanger: true,
                    onChange: (nextPage, nextSize) => {
                        setPage(nextPage)
                        setPageSize(nextSize)
                    },
                }}
            />
            {/*新建用户弹窗*/}
            <Modal
                title="新建用户"
                open={createOpen}
                forceRender
                confirmLoading={createMutation.isPending}
                okText="创建"
                cancelText="取消"
                onOk={submitCreate}
                onCancel={() => setCreateOpen(false)}
                afterOpenChange={(open) => {
                    if (!open) createForm.resetFields()
                }}
            >
                <Form form={createForm} layout="vertical">
                    <Form.Item
                        name="username"
                        label="用户名"
                        rules={[
                            {required: true, whitespace: true, message: '请输入用户名'},
                            {min: 2, max: 64, message: '长度 2–64 位'},
                        ]}
                    >
                        <Input placeholder="创建后不可修改" autoComplete="off"/>
                    </Form.Item>
                    <Form.Item
                        name="display_name"
                        label="昵称"
                        rules={[{required: true, whitespace: true, message: '请输入昵称'}]}
                    >
                        <Input placeholder="起一个好听的名字吧"/>
                    </Form.Item>
                    <Form.Item
                        name="password"
                        label="密码"
                        rules={[{required: true, min: 4, message: '至少 4 位'}]}
                    >
                        <Input.Password placeholder="至少 4 位" autoComplete="new-password"/>
                    </Form.Item>
                    <Form.Item name="role_ids" label="角色">
                        <Select
                            mode="multiple"
                            allowClear
                            placeholder="选择角色"
                            options={roleOptions}
                            loading={rolesQuery.isLoading}
                        />
                    </Form.Item>
                </Form>
            </Modal>
            {/*编辑用户弹窗*/}
            <Modal
                title={`编辑用户 · ${editing?.username ?? ''}`}
                open={editing !== null}
                forceRender
                confirmLoading={updateMutation.isPending}
                okText="保存"
                cancelText="取消"
                onOk={submitEdit}
                onCancel={() => setEditing(null)}
            >
                <Form form={editForm} layout="vertical">
                    <Form.Item label="用户名" extra="不允许修改">
                        <Input value={editing?.username ?? ''} disabled/>
                    </Form.Item>
                    <Form.Item
                        name="display_name"
                        label="昵称"
                        rules={[{required: true, whitespace: true, message: '请输入昵称'}]}
                    >
                        <Input/>
                    </Form.Item>
                    <Form.Item name="status" label="状态" extra="停用后该用户立即无法登录">
                        <Select
                            options={[
                                {label: '启用', value: 'active'},
                                {label: '停用', value: 'disabled'},
                            ]}
                        />
                    </Form.Item>
                    <Form.Item
                        name="password"
                        label="重置密码"
                        rules={[{min: 4, message: '至少 4 位'}]}
                    >
                        <Input.Password placeholder="留空表示不修改" autoComplete="new-password"/>
                    </Form.Item>
                </Form>
            </Modal>
            {/*分配角色弹窗*/}
            <Modal
                title={`分配角色 · ${assigning?.username ?? ''}`}
                open={assigning !== null}
                forceRender
                confirmLoading={assignMutation.isPending}
                okText="保存"
                cancelText="取消"
                onOk={submitAssign}
                onCancel={() => setAssigning(null)}
            >
                <Form form={assignForm} layout="vertical">
                    <Form.Item
                        name="role_ids"
                        label="角色"
                        extra="可多选"
                    >
                        <Select
                            mode="multiple"
                            allowClear
                            placeholder="选择角色"
                            options={roleOptions}
                            loading={rolesQuery.isLoading}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}
