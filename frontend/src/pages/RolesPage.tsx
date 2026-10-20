/** 角色管理页 */
import {App as AntdApp, Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, Tooltip, Typography} from "antd";
import type {TableProps} from "antd";
import {DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined} from "@ant-design/icons";
import {useState} from "react";
import type {RoleRead} from "@/client";
import {useCreateRole, useDeleteRole, useRoles, useUpdateRole} from "@/api/roles.ts";

const {Title, Paragraph} = Typography

// 默认的两个角色不能修改或删除
const PROTECTED_ROLE_NAMES = new Set(['admin', 'user'])

/** 新建/编辑共用的表单字段（name 只在新建时可填） */
interface RoleFormValues {
    name?: string
    description?: string
    permission_tags?: string[]
}

export function RolesPage() {
    const {message} = AntdApp.useApp()

    const [createOpen, setCreateOpen] = useState(false)
    const [editing, setEditing] = useState<RoleRead | null>(null)

    const [createForm] = Form.useForm<RoleFormValues>()
    const [editForm] = Form.useForm<RoleFormValues>()

    const listQuery = useRoles()
    const createMutation = useCreateRole()
    const updateMutation = useUpdateRole()
    const deleteMutation = useDeleteRole()

    /** 打开编辑弹窗并回填 */
    function openEdit(role: RoleRead) {
        setEditing(role)
        editForm.setFieldsValue({
            description: role.description,
            permission_tags: role.permission_tags ?? [],
        })
    }

    /** 删除 */
    function handleDelete(role: RoleRead) {
        deleteMutation.mutate(role.id, {
            onSuccess: () => message.success(`角色 ${role.name} 已删除`),
        })
    }

    const columns: TableProps<RoleRead>['columns'] = [
        {
            title: '角色名',
            dataIndex: 'name',
            width: 180,
            render: (name: string) => (
                PROTECTED_ROLE_NAMES.has(name)
                    ? <Tag>{name}（内置）</Tag>
                    : <Tag>{name}</Tag>
            ),
        },
        {title: '描述', dataIndex: 'description', ellipsis: true},
        {
            title: '权限标签',
            dataIndex: 'permission_tags',
            render: (_, record) => (
                record.permission_tags && record.permission_tags.length > 0 ? (
                    <Space size={4} wrap>
                        {record.permission_tags.map((t) => (
                            <Tag key={t} color={t === '*' ? 'warning' : 'default'}>{t}</Tag>
                        ))}
                    </Space>
                ) : <Tag>公开文档</Tag>
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
            width: 200,
            render: (_, record) => {
                const isProtected = PROTECTED_ROLE_NAMES.has(record.name)
                return (
                    <Space size={0}>
                        <Button type="link" size="small" icon={<EditOutlined/>}
                                onClick={() => openEdit(record)}>
                            编辑
                        </Button>
                        <Tooltip title={isProtected ? '内置角色不允许删除' : ''}>
                            <Popconfirm
                                title="确认删除该角色?"
                                description="挂着该角色的用户将立即失去对应权限"
                                okText="删除"
                                cancelText="取消"
                                okButtonProps={{danger: true}}
                                disabled={isProtected}
                                onConfirm={() => handleDelete(record)}
                            >
                                <Button type="link" size="small" danger icon={<DeleteOutlined/>}
                                        disabled={isProtected}
                                        loading={deleteMutation.isPending && deleteMutation.variables === record.id}>
                                    删除
                                </Button>
                            </Popconfirm>
                        </Tooltip>
                    </Space>
                )
            },
        },
    ]

    /** 提交新建 */
    async function submitCreate() {
        try {
            const values = await createForm.validateFields()
            await createMutation.mutateAsync({
                name: values.name!.trim(),
                description: values.description?.trim() ?? '',
                permission_tags: values.permission_tags ?? [],
            })
            message.success(`角色 ${values.name} 已创建`)
            setCreateOpen(false)
        } catch {
            // 校验失败 / 请求失败都保持弹窗打开
        }
    }
    /** 提交编辑（不含 name） */
    async function submitEdit() {
        if (!editing) return
        try {
            const values = await editForm.validateFields()
            await updateMutation.mutateAsync({
                roleId: editing.id,
                body: {
                    description: values.description?.trim() ?? '',
                    permission_tags: values.permission_tags ?? [],
                },
            })
            message.success('已保存')
            setEditing(null)
        } catch {
            // 同上
        }
    }

    return (
        <div>
            <Title level={3}>司津 · 角色管理</Title>
            <Paragraph type="secondary">
                角色承载权限标签，决定该角色下的用户能检索到哪些文档。admin 与 user 为内置角色，不可删除、不可改名。
            </Paragraph>
            <Space style={{marginBottom: 16}} wrap>
                <Button type="primary" icon={<PlusOutlined/>} onClick={() => setCreateOpen(true)}>
                    新建角色
                </Button>
                <Button icon={<ReloadOutlined/>} loading={listQuery.isFetching}
                        onClick={() => listQuery.refetch()}>
                    刷新
                </Button>
            </Space>
            <Table<RoleRead>
                rowKey="id"
                loading={listQuery.isLoading}
                columns={columns}
                dataSource={listQuery.data ?? []}
                pagination={false}
            />
            {/*新建角色弹窗*/}
            <Modal
                title="新建角色"
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
                        name="name"
                        label="角色"
                        rules={[
                            {required: true, whitespace: true, message: '请输入角色'},
                            {max: 64, message: '最长 64 字'},
                        ]}
                    >
                        <Input placeholder="赋予角色" autoComplete="off"/>
                    </Form.Item>
                    <Form.Item
                        name="description"
                        label="描述"
                        rules={[{max: 256, message: '最长 256 字'}]}
                    >
                        <Input.TextArea rows={2} placeholder="这个角色是干什么的"/>
                    </Form.Item>
                    <Form.Item
                        name="permission_tags"
                        label="权限标签"
                        extra="标签需与文档上传时填的权限标签一致；* 表示全部文档；留空表示只能检索公开文档"
                    >
                        <Select
                            mode="tags"
                            tokenSeparators={[',']}
                            placeholder="输入标签后回车，可输多个"
                            options={[{label: '*（全部文档）', value: '*'}]}
                            open={false}
                        />
                    </Form.Item>
                </Form>
            </Modal>
            {/*编辑角色弹窗*/}
            <Modal
                title={`编辑角色 · ${editing?.name ?? ''}`}
                open={editing !== null}
                forceRender
                confirmLoading={updateMutation.isPending}
                okText="保存"
                cancelText="取消"
                onOk={submitEdit}
                onCancel={() => setEditing(null)}
            >
                <Form form={editForm} layout="vertical">
                    <Form.Item label="角色名" extra="角色名不允许修改">
                        <Input value={editing?.name ?? ''} disabled/>
                    </Form.Item>
                    <Form.Item
                        name="description"
                        label="描述"
                        rules={[{max: 256, message: '最长 256 字'}]}
                    >
                        <Input.TextArea rows={2}/>
                    </Form.Item>
                    <Form.Item
                        name="permission_tags"
                        label="权限标签"
                        extra="标签需与文档上传时填的权限标签一致；* 表示全部文档；留空表示只能检索公开文档"
                    >
                        <Select
                            mode="tags"
                            tokenSeparators={[',']}
                            placeholder="输入标签后回车，可输多个"
                            options={[{label: '*（全部文档）', value: '*'}]}
                            open={false}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )

}
