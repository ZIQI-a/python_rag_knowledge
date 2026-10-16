""" 向量检索相关符合的文档 """
from app.retrieval.hybrid_retriever import HybridRetriever

"""retrieve：执行向量 Top-K 检索，并判断是否触发拒答。

multi_query 路径下需要多路召回 + 去重；其他路径走单路。
"""

from app.core.config import settings
from app.retrieval.vector_retriever import RetrievedChunk
from app.workflows.rag_state import RAGState

# 混合检索节点，通过向量检索和关键词检索两路进行融合检索
async def retrieve(state: RAGState) -> RAGState:
    retriever = HybridRetriever()
    recall_top_k = settings.retrieval_recall_top_k
    permissions = state.get("permissions")

    # 多角度查询路径，需要多路召回 + 去重
    if state.get("route") == "multi_query" and state.get("multi_queries"):
        bundles: list[list[RetrievedChunk]] = []
        for sub_query in state["multi_queries"] or []:
            bundles.append(await retriever.search(
                sub_query, recall_top_k=recall_top_k, final_top_k=recall_top_k,
                permission_tags=permissions
            ))
        chunks = _merge_chunks(bundles, top_k=recall_top_k)
    else:
        chunks = await retriever.search(
            state["query"],
            recall_top_k=recall_top_k,
            final_top_k=recall_top_k,
            permission_tags=permissions
        )
    return {"retrieved_chunks": chunks}

# 合并检索结果，去重，保留top-k
def _merge_chunks(
        bundles: list[list[RetrievedChunk]], top_k: int
) -> list[RetrievedChunk]:
    best: dict[str, RetrievedChunk] = {}
    for bundle in bundles:
        for chunk in bundle:
            key = str(chunk.chunk_id)
            prev = best.get(key)
            if prev is None or (chunk.rrf_score or 0.0) > (prev.rrf_score or 0.0):
                best[key] = chunk
    ranked = sorted(best.values(), key=lambda c: c.rrf_score or 0.0, reverse=True)
    return ranked[:top_k]
