// SSE流式输出客户端

import type {CitationRead} from "@/client/types.gen";
import {fetchEventSource} from "@microsoft/fetch-event-source";

export interface ChatStartEvent {
    type: 'start'
}

export interface ChatCitationsEvent {
    type: 'citations'
    citations: CitationRead[]
}

export interface ChatTokenEvent {
    type: 'token'
    delta: string
}

export interface ChatEndEvent {
    type: 'end'
    message_id: string
    refused: boolean
}

export interface ChatErrorEvent {
    type: 'error'
    code: string
    message: string
}

export type ChatStreamEvent =
    | ChatStartEvent
    | ChatCitationsEvent
    | ChatEndEvent
    | ChatTokenEvent
    | ChatErrorEvent

interface StreamChatParams {
    conversationId: string
    question: string
    signal?: AbortSignal
    onEvent: (event: ChatStreamEvent) => void
}

class FatalSseError extends Error {}

export async function streamChat({
    conversationId,
    question,
    signal,
    onEvent,
}: StreamChatParams): Promise<void> {
    await fetchEventSource(
        `/api/conversations/${conversationId}/chat`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
            signal,
            openWhenHidden: true,
            async onopen(response) {
                if(response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
                    return
                }
                const text = await response.text().catch(() => '')
                throw new FatalSseError(text || `HTTP ${response.status}`)
            },
            onmessage(msg) {
                if (!msg.event) return
                const data = msg.data ? JSON.parse(msg.data) : {}
                switch (msg.event) {
                    case 'message_start':
                        onEvent({type: 'start'})
                        break
                    case 'citations':
                        onEvent({type: 'citations', citations: data.citations ?? []})
                        break
                    case 'token':
                        onEvent({ type: 'token', delta: data.delta ?? '' })
                        break
                    case 'message_end':
                        onEvent({
                            type: 'end',
                            message_id: data.message_id,
                            refused: Boolean(data.refused)
                        })
                        break
                    case 'error':
                        onEvent({type: 'error', code: data.code ?? 'error', message: data.message ?? '请求失败'})
                        break
                }
            },
            onclose() {},
            onerror(err) {throw err}
        }
    )
}
