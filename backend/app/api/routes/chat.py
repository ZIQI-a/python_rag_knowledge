""" 支持问答请求路由 """
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Query, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.schemas.chat import ConversationRead, ConversationCreate, ConversationDetail, MessageRead, ChatRequest, \
    ConversationPage, ConversationListItem
from app.db.deps import DbSession
from app.services.chat_service import ChatService

router = APIRouter(prefix="/conversations", tags=["chat"])


# 创建会话接口
@router.post(
    "",
    response_model=ConversationRead,
    status_code=201,
    operation_id="createConversation",
)
async def create_conversation(
        payload: ConversationCreate,
        session: DbSession,
) -> ConversationRead:
    service = ChatService(session)
    conversation = await service.create_conversation(title=payload.title)
    return ConversationRead.model_validate(conversation)


# 获取给定ID的会话和历史消息
@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    operation_id="getConversation",
)
async def get_conversation(
        conversation_id: UUID,
        session: DbSession,
) -> ConversationDetail:
    service = ChatService(session)
    conversation, messages = await service.list_messages(conversation_id)
    return ConversationDetail(conversation=ConversationRead.model_validate(conversation),
                              messages=[MessageRead.from_orm(m) for m in messages])

# 流式回答接口
@router.post(
    "/{conversation_id}/chat",
    operation_id="streamChat",
    response_class=EventSourceResponse
)
async def stream_chat(
        conversation_id: UUID,
        payload: ChatRequest,
        session: DbSession,
) -> AsyncIterator[ServerSentEvent]:
    service = ChatService(session)
    async for sse_event in service.stream_answer(conversation_id, payload.question):
        yield ServerSentEvent(
            data=sse_event["data"],
            event=sse_event["event"]
        )

""" 获取对话列表 """
@router.get(
    "",
    response_model=ConversationPage,
    operation_id="listConversations",
    summary="按更新时间倒序分页列出所有会话"
)
async def list_conversations(
        session: DbSession,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100)
) -> ConversationPage:
    service = ChatService(session)
    items, total = await service.list_conversation(page=page, page_size=page_size)
    return ConversationPage(
        items=[
            ConversationListItem(
                id=conv.id,
                title=conv.title,
                updated_at=conv.updated_at,
                message_count=count
            )
            for conv, count in items
        ],
        total=total,
        page=page,
        page_size=page_size
    )

""" 删除指定对话 """
@router.delete(
    "/{conversation_id}",
    status_code=204,
    operation_id="deleteConversation"
)
async def delete_conversation(
        conversation_id: UUID,
        session: DbSession
) -> Response:
    service = ChatService(session)
    await service.delete_conversation(conversation_id)
    return Response(status_code=204)