""" 两路并发+RRF融合,通过混合检索器双路召回 """
import asyncio
from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.retrieval.keyword_retriever import KeywordRetriever
from app.retrieval.vector_retriever import RetrievedChunk, VectorRetriever

logger = get_logger(__name__)

class HybridRetriever:

    # 使用Safe Search调用进行二次兜底,静态方法
    @staticmethod
    async def _safe_search(
            retriever_cls: type[VectorRetriever] | type[KeywordRetriever],  # 类型
            query: str,
            top_k: int,
            label: str  # 标记来源哪一处挂了
    ) -> list[RetrievedChunk]:
        try:
            async with AsyncSessionLocal() as session:
                retriever = retriever_cls(session)
                return await retriever.search(query, top_k)
        except Exception:
            logger.exception("hybrid retrieve %s 路异常，降级为空结果", label)
            return []

    """ 两路独立Session并发返回 """
    async def search(
            self,
            query: str,
            *,
            recall_top_k: int,
            final_top_k: int,
    ) -> list[RetrievedChunk]:
        """ 两路并发返回，任意一路异常都退化为另一路结果,避免阻塞整个回答 """
        vector_hits, keyword_hits = await asyncio.gather(
            self._safe_search(VectorRetriever, query, recall_top_k, "vector"),
            self._safe_search(KeywordRetriever, query, recall_top_k, "keyword"),
        )
        return rrf_fuse(
            vector_hits=vector_hits,
            keyword_hits=keyword_hits,
            k=settings.rrf_k,
            top_k=final_top_k
        )

# RRF融合函数
def rrf_fuse(
        vector_hits: list[RetrievedChunk],
        keyword_hits: list[RetrievedChunk],
        *,
        k: int,
        top_k: int,
) -> list[RetrievedChunk]:
    """RRF融合算法实现
        Rank从一开始，分数 = Sum 1/K+Rank
    """
    by_id: dict[UUID, RetrievedChunk] = {}

    for rank, hit in enumerate(vector_hits, start=1):
        by_id[hit.chunk_id] = _with_vector(hit, rank=rank, k=k)

    for rank, hit in enumerate(keyword_hits, start=1):
        existing = by_id.get(hit.chunk_id)
        if existing is None:
            by_id[hit.chunk_id] = _with_keyword(hit, rank=rank, k=k)
        else:
            # 同创可跨两路命中，合并source累加RRF分数
            by_id[hit.chunk_id] = _merge_keyword_into(existing, hit, rank=rank, k=k)

    fused = sorted(
        by_id.values(),
        key=lambda c: c.rrf_score or 0.0,
        reverse=True
    )
    return fused[:top_k]


# 构造新的Retrieval Chunk的向量查询结果，并填好字段
def _with_vector(hit: RetrievedChunk, *, rank: int, k: int) -> RetrievedChunk:
    rrf_score = 1.0 / (k + rank) # 计算分数
    return RetrievedChunk(
        chunk_id=hit.chunk_id,
        document_id=hit.document_id,
        document_name=hit.document_name,
        content=hit.content,
        page_no=hit.page_no,
        section_path=hit.section_path,
        score=hit.score,
        sources=("vector",),
        vector_rank=rank,
        vector_score=hit.vector_score,
        rrf_score=rrf_score,
    )

# 构造新的Retrieval Chunk的关键词查询结果，并填好字段
def _with_keyword(hit: RetrievedChunk, *, rank: int, k: int) -> RetrievedChunk:
    rrf_score = 1.0 / (k + rank) # 计算分数
    return RetrievedChunk(
        chunk_id=hit.chunk_id,
        document_id=hit.document_id,
        document_name=hit.document_name,
        content=hit.content,
        page_no=hit.page_no,
        section_path=hit.section_path,
        score=rrf_score,
        sources=("keyword",),
        keyword_rank=rank,
        keyword_score=hit.keyword_score,
        rrf_score=rrf_score,
    )

# 构造新的Retrieval Chunk的两路混合查询结果，并填好字段
def _merge_keyword_into(
        existing: RetrievedChunk,
        keyword_hit: RetrievedChunk,
        *,
        rank: int,
        k: int
) -> RetrievedChunk:
    # existing是指带vector信息的条目需要把Keyword的关键词路的叠加上来
    new_rrf = (existing.rrf_score or 0.0) + 1.0 / (k + rank)
    return RetrievedChunk(
        chunk_id=existing.chunk_id,
        document_id=existing.document_id,
        document_name=existing.document_name,
        content=existing.content,
        page_no=existing.page_no,
        section_path=existing.section_path,
        score=new_rrf,
        sources=("vector", "keyword"),
        vector_rank=existing.vector_rank,
        vector_score=existing.vector_score,
        keyword_rank=rank,
        keyword_score=keyword_hit.keyword_score,
        rrf_score=new_rrf
    )