// 对话页面

import {Input, Typography, Alert, Avatar, Button, Empty, Space, Spin, message as antdMessage} from "antd";
import {type CitationRead, createConversation, getConversation, type MessageRead} from "@/client";
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import React, {useEffect, useMemo, useRef, useState} from "react";
import type {ChatStreamEvent} from "@/api/chatStream.ts";
import {streamChat} from "@/api/chatStream.ts";
import {formatApiError} from "@/utils/errors.ts";
import {PlusOutlined, RobotOutlined, SendOutlined, UserOutlined} from "@ant-design/icons";
import {gfmComponents} from "@/components/markdownComponents.tsx";
import {CitationList, type CitationListHandle} from "@/components/CitationList.tsx";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

const {Title, Paragraph, Text} = Typography
const {TextArea} = Input
// 本地存储的key
const STORAGE_KEY = 'rag.chat.conversation_id'
const CITATION_HASH_PREFIX = '#cite-'

type AssistantStatus = 'streaming' | 'done' | 'error'

interface UiMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    citations: CitationRead[]
    status?: AssistantStatus
    error?: string | null
}

// 从服务端消息转换为UI消息
function fromServerMessage(m: MessageRead): UiMessage {
    return {
        id: m.id,
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content,
        citations: m.citations ?? [],
        status: 'done',
    }
}

// 主要的页面聊天
export function ChatPage() {
    const queryClient = useQueryClient()
    // 对话id，从本地存储获取，如果没有则生成一个新的
    const [conversationId, setConversationId] = useState<string | null>(
        () => localStorage.getItem(STORAGE_KEY) || null
    )
    const [draft, setDraft] = useState('') // 用户输入的草稿
    // 待发送的消息（只放在前端state结束后，由历史接口返回正式ID）
    const [pendingMessages, setPendingMessages] = useState<UiMessage[]>([])
    const [isStreaming, setIsStreaming] = useState(false)
    // 中断控制器
    const abortRef = useRef<AbortController | null>(null)
    // 滚动容器
    const scrollRef = useRef<HTMLDivElement>(null)

    // 创建会话
    const createMutation = useMutation({
        mutationFn: async () => {
            const res = await createConversation({ body: {title: '新会话'} });
            return res.data!
        },
        onSuccess: (conversation) => {
            setConversationId(conversation.id)
            localStorage.setItem(STORAGE_KEY, conversation.id)
            setPendingMessages([])
            queryClient.removeQueries({ queryKey: ['conversation'] })
        }
    })
    // 没有Conversation ID时创建一个
    useEffect(() => {
        if(!conversationId && !createMutation.isPending) {
            createMutation.mutate()
        }
    }, [conversationId])

    // 拉取历史消息
    const historyQuery = useQuery({
        queryKey: ['conversation', conversationId],
        queryFn: async () => {
            const res = await getConversation({ path: { conversation_id: conversationId! } })
            return res.data!
        },
        enabled: Boolean(conversationId)
    })

    // 历史消息变化
    useEffect(() => {
        if(historyQuery.data) {
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
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
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
    /**
     * 发送消息的核心逻辑
     */
    // 更新assistant消息
    const updateAssistant = (updater: (prev: UiMessage) => UiMessage) => {
        setPendingMessages((prev) => {
            if (prev.length === 0) return prev;
            const lastIdx = prev.length - 1;
            const last = prev[lastIdx];
            if(!last) return prev;
            const next = prev.slice()
            next[lastIdx] = updater(last)
            return next
        })
    }
    // 发送消息
    const handleSend = async () => {
        // 用户输入的草稿内容读出，然后将对话框设置为空
        const question = draft.trim();
        if(!question || !conversationId || isStreaming) return;
        setDraft('')
        const userMsg: UiMessage = {
            id: `local-user-${Date.now()}`,
            role: 'user',
            content: question,
            citations: [],
            status: 'done'
        }
        const assistantMsg: UiMessage = {
            id: `local-assistant-${Date.now()}`,
            role: 'assistant',
            content: '',
            citations: [],
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
                            break
                        case 'citations':
                            updateAssistant((prev) => ({ ...prev, citations: event.citations}))
                            break
                        case 'token':
                            updateAssistant((prev) => ({ ...prev, content: prev.content + event.delta }))
                            break
                        case 'end':
                            updateAssistant((prev) => ({ ...prev, status: 'done' }))
                            break
                        case 'error':
                            updateAssistant((prev) => ({ ...prev, status: 'error', error: event.message }))
                            break
                    }
                },
            })

            await queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] })
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
        if(e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault()
            handleSend()
        }
    }

    /**
     * 最终渲染UI
     */
    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 160px)' }}>
            {/*顶部标题和操作按钮*/}
            <Space style={{ marginBottom: 12, justifyContent: 'space-between', display: 'flex' }}>
                <div>
                    <Title level={3} style={{ marginBottom: 0 }}>知识库问答</Title>
                    <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                        对已经上传的文档进行检索增强问答，引用来源可点击跳转原文档
                    </Paragraph>
                </div>
                <Button icon={<PlusOutlined />} onClick={handleNewConversation} disabled={isStreaming}>
                    新对话
                </Button>
            </Space>
            {/*问题展示框*/}
            <div
                ref={scrollRef}
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    background: '#fff',
                    padding: 24,
                    borderRadius: 8,
                    border: '1px solid #e8e8e8'
                }}
            >
                {historyQuery.isLoading ? (
                    <Spin />
                ) : allMessages.length === 0 ? (
                    <Empty description="还没有问题，请在下方输入问题" />
                ) : (
                    allMessages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
                )}
            </div>
            {/*发送消息框和发送按钮*/}
            <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                <TextArea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="请输入问题，按Enter发送，Shift+Enter换行"
                    autoSize={{ minRows: 2, maxRows: 6 }}
                    disabled={!conversationId || isStreaming}
                />
                <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    loading={isStreaming}
                    disabled={!conversationId || !draft.trim()}
                    >
                    发送
                </Button>
            </div>
        </div>
    )
}

/**
 * 处理MessageBubble和Markdown的引用展示
 */

// 将回答的引用编号改写成Markdown Hash链接
function linkifyCitations(content: string, maxIndex: number, messageId: string): string{
    if(maxIndex <= 0) return content;
    return content.replace(/[(\d+)]/g, (raw, num: string) => {
        const n = Number(num)
        if(n < 1 || n > maxIndex) return raw
        return `[[${n}]](${CITATION_HASH_PREFIX}${messageId}-${n}}`
    })
}
// 创建Markdown组件，处理引用点击事件
function createMarkdownComponents(onCitationClick: (n: number) => void) {
    return {
        a: (props: React.ComponentProps<'a'>) => {
            const href = props.href ?? ''
            if(href.startsWith(CITATION_HASH_PREFIX)) {
                const n = Number(href.split('-').pop())
                return (
                    <a
                        {...props}
                        href={href}
                        onClick={(e) => {
                            e.preventDefault()
                            if(Number.isFinite(n)) onCitationClick(n)
                        }}
                        />
                )
            }
            return <a {...props} target="_blank" rel="noreferrer" />
        },
        ...gfmComponents,
    }
}

// 消息二次重构时处理组件，包括引用链接跳转、样式修复
interface MessageBubbleProps {
    message: UiMessage
}
function MessageBubble({message}: MessageBubbleProps) {
    const isUser = message.role === 'user'
    const citationRef = useRef<CitationListHandle>(null)
    const components = useMemo(
        () => createMarkdownComponents((n) => citationRef.current?.expandAndScroll(n)),
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
                icon={isUser ? <UserOutlined /> : <RobotOutlined />}
                style={{ background: isUser ? '#1890ff' : '#f56a00', flexShrink: 0 }}
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
                    <Alert type="error" message={message.error} style={{ marginBottom: 8 }} />
                ) : null}
                {message.content ? (
                    isUser ? (
                        <Text style={{ whiteSpace: 'pre-wrap' }}>{message.content}</Text>
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
                {!isUser && message.citations.length > 0 ? (
                    <CitationList ref={citationRef} citations={message.citations} messageId={message.id} />
                ) : null}
            </div>
        </div>
    )
}
