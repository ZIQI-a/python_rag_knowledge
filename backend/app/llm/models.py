from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.exceptions import ConfigurationError

_chat_model: BaseChatModel | None = None

""" 返回流式ChatOpenAI实例;单例缓存 """
def get_chat_model() -> BaseChatModel | None:
    global _chat_model
    # 检查是否存在，避免多次创建
    if _chat_model is not None:
        return _chat_model
    if not settings.ai_api_key:
        raise ConfigurationError("API key未配置，请先配置")

    _chat_model = ChatOpenAI(
        model=settings.chat_model_name,
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        temperature=0,
        streaming=True,
    )
    return _chat_model