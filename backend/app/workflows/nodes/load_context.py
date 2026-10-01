""" 加载上下文节点 """
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories.conversation_repo import ConversationRepository
from app.workflows.rag_state import RAGState

# 多轮窗口按消息条数截取
async def load_context(state: RAGState, session: AsyncSession) -> RAGState:
    repo = ConversationRepository(session)
    history = await repo.recent_messages(
        # 一次对话两条消息
        state["conversation_id"], limit=settings.chat_history_window * 2
    )
    return {"chat_history": history}

