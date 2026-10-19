"""
第三步，调用大模型向量化处理
"""
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from openai import DefaultAsyncHttpxClient

from app.core.config import settings
from app.core.exceptions import ConfigurationError

_embeddings: Embeddings | None = None
_http_async_client: DefaultAsyncHttpxClient | None = None

def get_embeddings() -> Embeddings:
    global _embeddings, _http_async_client
    if _embeddings is not None:
        return _embeddings

    if not settings.ai_api_key:
        raise ConfigurationError("向量化API KV配置，请先配置后继续操作")

    # 显式持有客户端以便退出时关闭，同时保留 OpenAI SDK 默认连接参数。
    _http_async_client = DefaultAsyncHttpxClient()
    _embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        dimensions=settings.embedding_dim,
        chunk_size=settings.embedding_batch_size,
        check_embedding_ctx_length=False,
        http_async_client=_http_async_client,
    )
    return _embeddings


async def close_embeddings() -> None:
    """释放已创建的 Embedding 异步连接，不为清理而创建模型。"""
    global _embeddings, _http_async_client
    try:
        if _http_async_client is not None:
            await _http_async_client.aclose()
    finally:
        _embeddings = None
        _http_async_client = None
