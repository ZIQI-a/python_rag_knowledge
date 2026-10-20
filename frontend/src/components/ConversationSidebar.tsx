import {PALETTE} from '@/config/theme'
import {Button, List, message, Popconfirm, Spin, Tooltip, Typography} from "antd";
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {conversationsQueryKey} from "@/api/queryKeys.ts";
import {type ConversationListItem, deleteConversation, listConversations} from "@/client";
import {DeleteOutlined, PlusOutlined} from "@ant-design/icons";
import {DataState} from '@/components/PageState';


const { Text } = Typography

interface ConversationSidebarProps {
    currentId: string | null
    onSelect: (id: string) => void
    onDeleted: (deletedId: string) => void // 当前会话被删时回调，
    onCreateNew: () => void
    isCreating?: boolean // 新建按钮的联动
}

export function ConversationSidebar({
    currentId,
    onSelect,
    onDeleted,
    onCreateNew,
    isCreating,
}: ConversationSidebarProps) {
    const queryClient = useQueryClient()
    const conversationsQuery = useQuery({
        queryKey: conversationsQueryKey,
        queryFn: async () => {
            const res = await listConversations({ query: { page: 1, page_size: 100 } })
            return res.data!
        }
    })
    const deleteMutation = useMutation({
        mutationFn: async (id: string) => {
            await deleteConversation({ path: { conversation_id: id } })
            return id
        },
        onSuccess: async (id) => {
            message.success("已删除会话")
            await queryClient.invalidateQueries({ queryKey: conversationsQueryKey })
            if (id === currentId) onDeleted(id)
        }
    })

    const items = conversationsQuery.data?.items ?? []

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ padding: 12, borderBottom: `1px solid ${PALETTE.line}` }}>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    block
                    onClick={onCreateNew}
                    loading={isCreating}>
                    新建对话
                </Button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
                {conversationsQuery.isLoading ? (
                    <div style={{ textAlign: 'center', padding: 24 }}>
                        <Spin />
                    </div>
                ) : conversationsQuery.isError || items.length === 0 ? (
                    <DataState failed={conversationsQuery.isError} description="暂无会话，点击上方新建对话开始"
                        onRetry={() => {void conversationsQuery.refetch()}}/>
                ) : (
                    <List
                        size="small"
                        dataSource={items}
                        renderItem={(item) => (
                            <ConversationItem
                                item={item}
                                isActive={item.id === currentId}
                                isDeleting={
                                    deleteMutation.isPending && deleteMutation.variables === item.id
                                }
                                onSelect={() => onSelect(item.id)}
                                onDelete={() => deleteMutation.mutate(item.id)}
                            />
                        )}
                    />
                )}
            </div>
        </div>
    )

}

/**
 * 每个会话具体的Item子组件
 */

interface ConversationItemProps {
    item: ConversationListItem,
    isActive: boolean,
    isDeleting: boolean,
    onSelect: () => void,
    onDelete: () => void
}

function ConversationItem({
    item,
    isActive,
    isDeleting,
    onSelect,
    onDelete
}: ConversationItemProps) {
    return (
        <List.Item
            style={{
                cursor: 'pointer',
                background: isActive ? PALETTE.primarySoft : 'transparent',
                padding: '8px 12px',
                borderRadius: 4,
                margin: '2px 8px',
                border: 'none'
            }}
            actions={[
                <Popconfirm
                    key="del"
                    title="确认删除该会话"
                    description="将删除会话消息和引用无法恢复"
                    okText="删除"
                    okButtonProps={{ danger: true }}
                    cancelText="取消"
                    onConfirm={(e) => {
                        e?.stopPropagation()
                        onDelete()
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                >
                    <Tooltip title="删除会话">
                        <Button
                            aria-label={`删除会话：${item.title}`}
                            type="text"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            loading={isDeleting}
                            onClick={(e) => e.stopPropagation()}
                        />
                    </Tooltip>
                </Popconfirm>
            ]}
        >
            <Button type="text" onClick={onSelect} aria-pressed={isActive}
                style={{height: 'auto', minWidth: 0, flex: 1, padding: 0, textAlign: 'left', display: 'block'}}>
                <Text
                    strong={isActive}
                    ellipsis={{ tooltip: item.title }}
                    style={{ display: 'block', maxWidth: 150 }}
                >
                    {item.title}
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatRelativeTime(item.updated_at)}
                </Text>
            </Button>
        </List.Item>
    )
}

/**
 * 将ISO时间格式化成" x分钟前|小时前|YYYY-MM-DD
 */
function formatRelativeTime(iso: string): string {
    const date = new Date(iso)
    const diffMs = Date.now() - date.getTime()
    const minute = 60 * 1000
    const hour = 60 * minute
    const day = 24 * hour
    if (diffMs < minute) return '刚刚'
    if (diffMs < hour) return `${Math.floor(diffMs / minute)} 分钟前`
    if (diffMs < day) return `${Math.floor(diffMs / hour)} 小时前`
    if (diffMs < 7 * day) return `${Math.floor(diffMs / day)} 天前`
    return date.toISOString().slice(0, 10)
}
