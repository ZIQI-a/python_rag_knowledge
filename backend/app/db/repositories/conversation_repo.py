""" 会话存储 """
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from watchfiles import awatch

from app.db.models import Conversation, Message, MessageRole

class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # 创建新对话
    async def create(self, title: str = "新对话") -> Conversation:
        conversation = Conversation(title=title)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    # 获取对话
    async def get(self, conversation_id: UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    # 按时间正序返回所有消息(历史消息)
    async def list_message(self, conversation_id: UUID) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .options(selectinload(Message.citations))
        )
        return list((await self.session.execute(stmt)).scalars().all())

    # 取N条消息按时间顺序和返回
    async def recent_messages(self, conversation_id: UUID, limit: int) -> list[Message]:
        if limit <= 0:
            return []
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return list(reversed(rows))

    # 添加新消息
    async def add_message(self, message: Sequence[Message]) -> None:
        if not message:
            return
        self.session.add_all(message)
        await self.session.flush()

    # 创建用户消息
    @staticmethod
    def make_user_message(conversation_id: UUID, content: str) -> Message:
        return Message(conversation_id=conversation_id, role=MessageRole.USER, content=content)

    # 创建AI消息
    @staticmethod
    def make_assistant_message(
            conversation_id: UUID,
            content: str,
            *,
            extra_metadata: dict | None = None
    ) -> Message:
        return Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            extra_metadata=extra_metadata or {}
        )