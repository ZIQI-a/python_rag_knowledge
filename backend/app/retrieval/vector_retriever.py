from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.chunk_repo import DocumentChunkRepository
from app.ingestion.embedder import get_embeddings

""" 检索结果中单个chunk的展示视图 """
@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID # 文档chunk的ID
    document_id: UUID
    document_name: str
    content: str # 文档内容
    page_no: int | None
    section_path: str | None # 文档章节路径
    score: float # 相似度分数
    sources: tuple[str, ...] = field(default_factory=tuple)
    vector_rank: int | None = None
    vector_score: float | None = None # 原始向量相似度分数
    keyword_rank: int | None = None
    keyword_score: float | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None # 重新排序分数, 0-1

""" Vector检索 """
class VectorRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self.chunk_repo = DocumentChunkRepository(session)

    # 检索文档chunk
    async def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        embedding = await get_embeddings().aembed_query(query) # 获取查询的embedding
        # 查询数据库中相似度最高的chunk
        rows = await self.chunk_repo.vector_search(embedding, top_k)
        return [
            RetrievedChunk(
                # score 是混合检索后的分数越大越相似
                # """ 共两种检索方式:1 向量路 2 关键词路 """
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=chunk.document.name,
                content=chunk.content,
                page_no=chunk.page_no,
                section_path=chunk.section_path,
                score=1.0 - distance,
                sources=("vector",),
                vector_rank=rank,
                vector_score=1.0 - distance
            )
            for rank, (chunk, distance) in enumerate(rows, start=1)
        ]