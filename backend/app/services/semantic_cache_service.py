import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.query.filter import Tag
from redisvl.utils.vectorize import CustomVectorizer

from app.core.config import settings
from app.core.logging import get_logger

_CACHE_NAME = "rag_semantic_cache"
_SCOPE_FIELD = "permission_scope"

def _scope_key(permission_scope: list[str]) -> str:
    """ 权限集合 序列化为可比较的Tag值 """
    # 空字符串拼接，对权限数组排序，防止错位，整合字符串
    canonical = "\x00".join(sorted(permission_scope))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _stub_embed(text: str, **_: object) -> list[float]:
    """ 占位函数，实际使用时替换为实际的向量化函数占位 """
    return [0.0] * settings.embedding_dim

logger = get_logger(__name__)

@dataclass(frozen=True)
class CachedAnswer:
    answer: str
    citations: list[dict]
    cached_question: str

class SemanticCacheService:
    def __init__(self) -> None:
        self._cache = SemanticCache(
            name=_CACHE_NAME,
            redis_url=settings.redis_url,
            distance_threshold=1.0 - settings.semantic_cache_min_similarity,
            ttl=settings.semantic_cache_ttl_seconds,
            vectorizer=CustomVectorizer(_stub_embed),
            filterable_fields=[{"name": _SCOPE_FIELD, "type": "tag"}],
            overwrite=False
        )

    async def lookup(
            self, query_embedding: list[float], permission_scope: list[str]
    ) -> CachedAnswer | None:
        """ Cache内KNN查询: 相似度阈值加权限范围同时满足才返回 """
        scope = _scope_key(permission_scope)
        try:
            hits = await self._cache.acheck(
                vector=query_embedding,
                filter_expression=Tag(_SCOPE_FIELD) == scope,
                num_results=1,
                return_fields=["prompt", "response", "metadata"]
            )
        except Exception:
            logger.exception("Semantic cache lookup field, 没有找到")
            return None

        if not hits:
            return None
        hit = hits[0]
        metadata = hit.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        return CachedAnswer(
            answer=hit.get("response", ""),
            citations=metadata.get("citations", []),
            cached_question=hit.get("prompt", "")
        )

    async def save(
            self, *, question: str, query_embedding: list[float],
            answer: str, citations: list[dict], permission_scope: list[str]
    ) -> None:
        try:
            await self._cache.astore(
                prompt=question,
                response=answer,
                vector=query_embedding,
                metadata={"citations": citations},
                filters={_SCOPE_FIELD: _scope_key(permission_scope)}
            )
        except Exception:
            logger.exception("Semantic cache save field, 跳过")

    async def clear(self) -> None:
        """清空该知识库的语义缓存，保留索引及其他 Redis 数据。"""
        await self._cache.aclear()

@lru_cache(maxsize=1)
def get_semantic_cache() -> SemanticCacheService:
    return SemanticCacheService()


async def invalidate_semantic_cache() -> None:
    """文档变更后使旧答案失效；Redis 故障不回滚已完成的文档操作。"""
    if not settings.semantic_cache_enabled:
        return
    try:
        await get_semantic_cache().clear()
    except Exception:
        logger.exception("语义缓存清理失败，缓存命中仍需实时校验文档权限")
