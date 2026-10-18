// 对话页面

import {Alert, Avatar, Button, Empty, Input, Layout, message as antdMessage, Spin, Tag, Typography} from "antd";
import {
    type AgentStep,
    type CitationRead,
    createConversation,
    getConversation,
    type MessageRead,
    type QueryRouteRead,
    type VerifyResultRead
} from "@/client";
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import React, {useEffect, useMemo, useRef, useState} from "react";
import type {ChatStreamEvent} from "@/api/chatStream.ts";
import {streamChat} from "@/api/chatStream.ts";
import {formatApiError} from "@/utils/errors.ts";
import {RobotOutlined, SendOutlined, UserOutlined} from "@ant-design/icons";
import {gfmComponents} from "@/components/markdownComponents.tsx";
import {CitationList, type CitationListHandle} from "@/components/CitationList.tsx";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {QueryRoutePanel} from "@/components/QueryRoutePanel.tsx";
import {AgentStepsPanel} from "@/components/AgentStepsPanel.tsx";
import {conversationsQueryKey} from "@/api/queryKeys.ts";
import {ConversationSidebar} from "@/components/ConversationSidebar.tsx";
import {TraceIdPanel} from "@/components/TraceIdPanel.tsx";
import {useAuthStore} from "@/stores/authStore.ts";


const {Text} = Typography
const {TextArea} = Input
const {Sider, Content} = Layout
// 本地存储的key
const STORAGE_KEY_PREFIX = 'rag.chat.conversation_id'
const CITATION_HASH_PREFIX = '#cite-'

const REFUSAL_ANSWER = '啊哦，知识库中没有找到与该问题相关的可靠依据'

type AssistantStatus = 'streaming' | 'done' | 'error'

interface UiMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    citations: CitationRead[]
    queryRoute?: QueryRouteRead | null // Query路由策略
    agentSteps?: AgentStep[] | null
    verifyResult?: VerifyResultRead | null
    traceId?: string | null
    traceUrl?: string | null
    cacheHit?: boolean
    refused?: boolean
    status?: AssistantStatus
    error?: string | null
}

// 从服务端消息转换为UI消息
function fromServerMessage(m: MessageRead): UiMessage {
    return {
        id: m.id,
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content,
        queryRoute: m.query_route ?? null,
        agentSteps: m.agent_steps ?? null,
        verifyResult: m.verify_result ?? null,
        traceId: m.trace_id ?? null,
        traceUrl: m.trace_url ?? null,
        cacheHit: Boolean(m.cache_hit),
        refused: m.role === 'assistant' && m.content === REFUSAL_ANSWER,
        citations: m.citations ?? [],
        status: 'done',
    }
}

// 主要的页面聊天
export function ChatPage() {
    const queryClient = useQueryClient()
    const userId = useAuthStore((s) => s.user?.id)
    const storageKey = `${STORAGE_KEY_PREFIX}.${userId}`
    // 对话id，从本地存储获取，如果没有则生成一个新的
    const [conversationId, setConversationId] = useState<string | null>(
        () => localStorage.getItem(storageKey) || null
    )
    const [draft, setDraft] = useState('') // 用户输入的草稿
    // 待发送的消息（只放在前端state结束后，由历史接口返回正式ID）
    const [pendingMessages, setPendingMessages] = useState<UiMessage[]>([])
    const [isStreaming, setIsStreaming] = useState(false)
    const initialConversationRequested = useRef(false)
    // 中断控制器
    const abortRef = useRef<AbortController | null>(null)
    // 滚动容器
    const scrollRef = useRef<HTMLDivElement>(null)

    // 创建会话
    const createMutation = useMutation({
        mutationFn: async () => {
            const res = await createConversation({body: {title: '新会话'}});
            return res.data!
        },
        onSuccess: async (conversation) => {
            setConversationId(conversation.id)
            localStorage.setItem(storageKey, conversation.id)
            setPendingMessages([])
            queryClient.removeQueries({queryKey: ['conversation']})
            await queryClient.invalidateQueries({queryKey: conversationsQueryKey})
        }
    })


    // 没有Conversation ID时创建一个
    const createConversationMutate = createMutation.mutate
    useEffect(() => {
        if (!conversationId && !initialConversationRequested.current) {
            // 严格模式下 effect 可能重复执行，只创建一次初始会话。
            initialConversationRequested.current = true
            createConversationMutate()
        }
    }, [conversationId, createConversationMutate])

    // 拉取历史消息
    const historyQuery = useQuery({
        queryKey: ['conversation', conversationId],
        queryFn: async () => {
            const res = await getConversation({path: {conversation_id: conversationId!}})
            return res.data!
        },
        enabled: Boolean(conversationId)
    })

    // 历史消息变化
    useEffect(() => {
        if (historyQuery.data) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setPendingMessages([])
        }
    }, [historyQuery.data])
    // 合并历史消息和待发送消息
    const allMessages = useMemo<UiMessage[]>(() => {
        const history = (historyQuery.data?.messages ?? []).map(fromServerMessage);
        return [...history, ...pendingMessages]
    }, [historyQuery.data, pendingMessages])

    // 自动滚动到底部
    useEffect(() => {
        scrollRef.current?.scrollTo({top: scrollRef.current.scrollHeight, behavior: 'smooth'});
    }, [allMessages])
    // 组件卸载或先前对话时取消进行中的请求
    useEffect(() => {
        return () => {
            abortRef.current?.abort()
        }
    }, [])
    // 新建对话
    const handleNewConversation = () => {
        abortRef.current?.abort()
        createMutation.mutate()
    }
    // 处理选择对话
    const handleSelectConversation = (id: string) => {
        if (id === conversationId) return
        abortRef.current?.abort()
        setPendingMessages([])
        setIsStreaming(false)
        localStorage.setItem(storageKey, id)
        setConversationId(id)
    }
    // 处理删除对话
    const handleConversationDeleted = (deletedId: string) => {
        if (deletedId !== conversationId) return
        abortRef.current?.abort()
        setPendingMessages([])
        setIsStreaming(false)
        localStorage.removeItem(storageKey)
        setConversationId(null)
        queryClient.removeQueries({queryKey: ['conversation', deletedId]})
    }
    /**
     * 发送消息的核心逻辑
     */
        // 更新assistant消息
    const updateAssistant = (updater: (prev: UiMessage) => UiMessage) => {
            setPendingMessages((prev) => {
                if (prev.length === 0) return prev;
                const lastIdx = prev.length - 1;
                const last = prev[lastIdx];
                if (!last) return prev;
                const next = prev.slice()
                next[lastIdx] = updater(last)
                return next
            })
        }
    // 发送消息
    const handleSend = async () => {
        // 用户输入的草稿内容读出，然后将对话框设置为空
        const question = draft.trim();
        if (!question || !conversationId || isStreaming) return;
        setDraft('')
        const userMsg: UiMessage = {
            id: `local-user-${Date.now()}`,
            role: 'user',
            content: question,
            citations: [],
            queryRoute: null,
            status: 'done'
        }
        const assistantMsg: UiMessage = {
            id: `local-assistant-${Date.now()}`,
            role: 'assistant',
            content: '',
            citations: [],
            // 路由结果在 SSE query_route 事件到达后填充。
            queryRoute: null,
            status: 'streaming'
        }
        setPendingMessages((prev) => [...prev, userMsg, assistantMsg])
        setIsStreaming(true)

        const ctrl = new AbortController()
        abortRef.current = ctrl

        try {
            await streamChat({
                conversationId,
                question,
                signal: ctrl.signal,
                onEvent: (event: ChatStreamEvent) => {
                    switch (event.type) {
                        case "start":
                            updateAssistant((prev) => ({
                                ...prev,
                                traceId: event.traceId,
                                traceUrl: event.traceUrl,
                                cacheHit: event.cacheHit,
                            }))
                            break
                        case 'query_route':
                            updateAssistant((prev) => ({...prev, queryRoute: event.queryRoute}))
                            break
                        case 'agent_steps':
                            updateAssistant((prev) => ({...prev, agentSteps: event.steps}))
                            break
                        case 'citations':
                            updateAssistant((prev) => ({...prev, citations: event.citations}))
                            break
                        case 'token':
                            updateAssistant((prev) => ({...prev, content: prev.content + event.delta}))
                            break
                        case 'verify_result':
                            updateAssistant((prev) => {
                                const verifyResult: VerifyResultRead = {
                                    verified: event.verified,
                                    reason: event.reason
                                }
                                if (!event.verified && event.replacementAnswer) {
                                    return {
                                        ...prev,
                                        content: event.replacementAnswer,
                                        citations: [],
                                        refused: true,
                                        verifyResult,
                                    }
                                }
                                return {...prev, verifyResult}
                            })
                            break
                        case 'end':
                            updateAssistant((prev) => ({
                                ...prev,
                                status: 'done',
                                refused: prev.refused || event.refused
                            }))
                            break
                        case 'error':
                            updateAssistant((prev) => ({...prev, status: 'error', error: event.message}))
                            // 同时弹全局提示：流结束后历史刷新会清空 pending 消息，避免错误被静默吞掉
                            antdMessage.error(event.message)
                            break
                    }
                },
            })
            // 刷新对话数据
            await Promise.all([
                queryClient.invalidateQueries({queryKey: ['conversation', conversationId]}),
                queryClient.invalidateQueries({queryKey: conversationsQueryKey})
            ])
        } catch (err) {
            const fallback = err instanceof Response ? await formatApiError(err) : (err as Error).message
            updateAssistant((prev) => ({
                ...prev,
                status: 'error',
                error: fallback || '请求失败',
            }))
            antdMessage.error(fallback || '问答请求失败')
        } finally {
            setIsStreaming(false)
            abortRef.current = null
        }
    }

    // 按下Enter键发送消息( 绑定快捷键)
    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault()
            handleSend()
        }
    }

    /**
     * 最终渲染UI
     */
    return (

        <Layout style={{
            height: 'calc(100vh - 160px)',
            background: '#fff',
            borderRadius: 8,
            overflow: "hidden",
            border: '1px solid #f0f0f0'
        }}>
            {/*右侧会话列表展示*/}
            <Sider
                width={260}
                theme={"light"}
                style={{borderRight: '1px solid #f0f0f0', background: '#fafafa'}}
            >
                <ConversationSidebar currentId={conversationId} onSelect={handleSelectConversation}
                                     onDeleted={handleConversationDeleted} onCreateNew={handleNewConversation}
                                     isCreating={createMutation.isPending}/>
            </Sider>
            {/*左侧展示会话具体内容*/}
            <Content style={{display: 'flex', flexDirection: 'column'}}>
                <div ref={scrollRef} style={{flex: 1, overflowY: 'auto', padding: 24}}>
                    {historyQuery.isLoading ? (
                        <Spin/>
                    ) : allMessages.length === 0 ? (
                        <Empty description="还没有问题，请在下方输入问题"/>
                    ) : (
                        allMessages.map((msg) => <MessageBubble key={msg.id} message={msg}/>)
                    )}
                </div>
                <div style={{marginTop: 12, display: 'flex', gap: 8}}>
                    <TextArea
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="请输入问题，按Enter发送，Shift+Enter换行"
                        autoSize={{minRows: 2, maxRows: 6}}
                        disabled={!conversationId || isStreaming}
                    />
                    <Button
                        type="primary"
                        icon={<SendOutlined/>}
                        onClick={handleSend}
                        loading={isStreaming}
                        disabled={!conversationId || !draft.trim()}
                    >
                        发送
                    </Button>
                </div>
            </Content>
        </Layout>
    )
}

/**
 * 处理MessageBubble和Markdown的引用展示
 */

// 将回答的引用编号改写成Markdown Hash链接
function linkifyCitations(content: string, maxIndex: number, messageId: string): string {
    if (maxIndex <= 0) return content;
    return content.replace(/\[(\d+)\]/g, (raw, num: string) => {
        const n = Number(num)
        if (n < 1 || n > maxIndex) return raw
        return `[[${n}]](${CITATION_HASH_PREFIX}${messageId}-${n})`
    })
}

// 创建Markdown组件，处理引用点击事件
function createMarkdownComponents(onCitationClick: (n: number) => void) {
    return {
        a: (props: React.ComponentProps<'a'>) => {
            const href = props.href ?? ''
            if (href.startsWith(CITATION_HASH_PREFIX)) {
                const n = Number(href.split('-').pop())
                return (
                    <a
                        {...props}
                        href={href}
                        onClick={(e) => {
                            e.preventDefault()
                            if (Number.isFinite(n)) onCitationClick(n)
                        }}
                    />
                )
            }
            return <a {...props} target="_blank" rel="noreferrer"/>
        },
        ...gfmComponents,
    }
}

/**
 * Assistant气泡顶部状态条用于拒答提示和校验结果
 */
function AssistantHeader({message}: { message: UiMessage }) {
    if (message.refused) {
        return (
            <Alert
                type="warning"
                showIcon
                title="未在知识库中找到可靠依据"
                description={
                    message.verifyResult && message.verifyResult.verified === false
                        ? `答案校验未通过: ${message.verifyResult.reason ?? '缺乏引用'}, 已替换为巨=拒答` : undefined
                }
                style={{marginBottom: 8}}
            />
        )
    }
    const tags: React.ReactNode[] = []
    if (message.cacheHit) {
        tags.push(
            <Tag key="cache" color="cyan">
                缓存命中
            </Tag>
        )
    }
    if (message.verifyResult?.verified === true) {
        tags.push(
            <Tag key="verified" color="green">
                已校验
            </Tag>
        )
    }
    if (tags.length === 0) return null
    return (
        <div style={{marginBottom: 8}}>
            {tags}
        </div>
    )
}

// 消息二次重构时处理组件，包括引用链接跳转、样式修复
interface MessageBubbleProps {
    message: UiMessage
}

function MessageBubble({message}: MessageBubbleProps) {
    const isUser = message.role === 'user'
    const citationRef = useRef<CitationListHandle>(null)
    const [selectedCitation, setSelectedCitation] = useState<{ n: number } | null>(null)
    // 点击时记录引用编号，渲染完成后再操作引用面板。
    useEffect(() => {
        if (selectedCitation) citationRef.current?.expandAndScroll(selectedCitation.n)
    }, [selectedCitation])
    const components = useMemo(
        () => createMarkdownComponents((n) => setSelectedCitation({n})),
        [],
    )
    const renderedContent = useMemo(
        () => linkifyCitations(message.content, message.citations.length, message.id),
        [message.content, message.citations.length, message.id],
    )
    return (
        <div
            style={{
                display: 'flex',
                gap: 12,
                marginBottom: 24,
                flexDirection: isUser ? 'row-reverse' : 'row',
            }}
        >
            <Avatar
                icon={isUser ? <UserOutlined/> : <RobotOutlined/>}
                style={{background: isUser ? '#1890ff' : '#f56a00', flexShrink: 0}}
            />
            <div
                style={{
                    maxWidth: '78%',
                    background: isUser ? '#e6f7ff' : '#f6f6f6',
                    padding: '12px 16px',
                    borderRadius: 8
                }}
            >
                {message.error ? (
                    <Alert type="error" title={message.error} style={{marginBottom: 8}}/>
                ) : null}
                {!isUser ? <AssistantHeader message={message}/> : null}
                {message.content ? (
                    isUser ? (
                        <Text style={{whiteSpace: 'pre-wrap'}}>{message.content}</Text>
                    ) : (
                        <Markdown remarkPlugins={[remarkGfm]} components={components}>
                            {renderedContent}
                        </Markdown>
                    )
                ) : message.status === 'streaming' ? (
                    <Text type="secondary">
                        <Spin size="small"/>正在加速检索...
                    </Text>
                ) : null}
                {!isUser && message.traceId ? (
                    <TraceIdPanel traceId={message.traceId} traceUrl={message.traceUrl ?? null} />
                ) : null}
                {!isUser && message.queryRoute ? (
                    <QueryRoutePanel queryRoute={message.queryRoute}/>
                ) : null}
                {!isUser && message.agentSteps && message.agentSteps.length > 0 ? (
                    <AgentStepsPanel steps={message.agentSteps}/>
                ) : null}
                {!isUser && message.citations.length > 0 ? (
                    <CitationList ref={citationRef} citations={message.citations} messageId={message.id}/>
                ) : null}
            </div>
        </div>
    )
}
