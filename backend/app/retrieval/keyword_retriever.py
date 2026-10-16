"""  关键词检索
 检索与Vector Retriever对齐,都暴露search接口
 适用于需要名称精确匹配的场景
"""
from langsmith import traceable
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.chunk_repo import DocumentChunkRepository
from app.retrieval.vector_retriever import RetrievedChunk

class KeywordRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self.chunk_repo = DocumentChunkRepository(session)

    @traceable(name="KeywordRetriever.search", run_type="retriever")
    async def search(self, query: str, top_k: int, permission_tags: list[str] | None = None) -> list[RetrievedChunk]:
        rows = await self.chunk_repo.keyword_search(query, top_k, permission_tags=permission_tags)
        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=chunk.document.name,
                content=chunk.content,
                page_no=chunk.page_no,
                section_path=chunk.section_path,
                score=ts_rank,
                sources=("keyword",),
                keyword_rank=rank,
                keyword_score=ts_rank,
            )
            for rank, (chunk, ts_rank) in enumerate(rows, start=1)
        ]