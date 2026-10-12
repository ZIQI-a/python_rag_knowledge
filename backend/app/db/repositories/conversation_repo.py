""" 会话存储 """
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Conversation, Message, MessageRole

DEFAULT_CONVERSATION_TITLE = "新会话"

class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    # 首次提问后，把新对话改成问题前几个字
    async def update_title_if_default(
            self, conversation_id: UUID, title: str
    ) -> None:
        new_title = title.strip()
        if not new_title:
            return
        conversation = await self.get(conversation_id)
        if conversation is None or conversation.title != DEFAULT_CONVERSATION_TITLE:
            return
        conversation.title = new_title[:30]
        await self.session.flush()


    # 创建新对话
    async def create(self, title: str = DEFAULT_CONVERSATION_TITLE) -> Conversation:
        conversation = Conversation(title=title)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    # 计算当前会话是否有消息,用于判断是否是新对话
    async def count_messages(self, conversation_id: UUID) -> int:
        stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
        return int ((await self.session.execute(stmt)).scalar_one())

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


    async def list_page(
            self, page: int, page_size: int
    ) -> tuple[list[tuple[Conversation, int]], int]:
        """ 按照 update倒序分页返回(会话，消息数)列表 + 总数 """
        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)
        offset = (page - 1) * page_size

        msg_count = func.count(Message.id).label("message_count")
        stmt = (
            select(Conversation, msg_count)
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).all()
        items = [(row[0], int(row[1])) for row in rows]
        total  =int(
            (await self.session.execute(select(func.count(Conversation.id)))).scalar_one()
        )
        return items, total


    # 添加新消息
    async def add_message(self, message: Sequence[Message]) -> None:
        if not message:
            return
        self.session.add_all(message)
        await self.session.flush()

    # 删除会话
    async def delete(self, conversation_id: UUID) -> bool:
        conversation  = await self.get(conversation_id)
        if conversation is None:
            return False
        await self.session.delete(conversation)
        await self.session.flush()
        return True

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