"""
第三步，调用大模型向量化处理
"""
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.exceptions import ConfigurationError

_embeddings: Embeddings | None = None

def get_embeddings() -> Embeddings:
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    if not settings.ai_api_key:
        raise ConfigurationError("向量化API KV配置，请先配置后继续操作")

    _embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        dimensions=settings.embedding_dim,
        chunk_size=settings.embedding_batch_size,
        check_embedding_ctx_length=False,
    )
    return _embeddings