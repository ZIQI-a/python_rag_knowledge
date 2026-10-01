""" 支持问答请求路由 """
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.schemas.chat import ConversationRead, ConversationCreate, ConversationDetail, MessageRead, ChatRequest
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

