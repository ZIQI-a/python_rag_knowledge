""" 将整个流程串起来 """
import asyncio
from uuid import UUID
from langchain_core.documents import Document as LangChainDocument

from app.core.logging import get_logger
from app.db.models import DocumentChunk, DocumentStatus
from app.db.repositories.chunk_repo import DocumentChunkRepository
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.ingestion_task_repo import IngestionTaskRepository
from app.db.session import AsyncSessionLocal
from app.ingestion import embedder, parser, splitter
from app.storage.file_service import get_file_service


logger = get_logger(__name__)

# 状态变更辅助函数
async def _set_status(document_id: UUID, status: DocumentStatus, * , error_message:str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        repo = DocumentRepository(session)
        await repo.update_status(document_id, status, error_message=error_message)
        await session.commit()
""" 任务状态管理的辅助方法 """

async def _mark_task(task_id: UUID, *, running: bool = False) -> None:
    """ 标记任务为运行中 """
    async with AsyncSessionLocal() as session:
        repo = IngestionTaskRepository(session)
        if running:
            await repo.mark_running(task_id)
        await session.commit()

async def _mark_task_failed(task_id: UUID, error_message: str) -> None:
    """ 标记任务为失败 """
    async with AsyncSessionLocal() as session:
        repo = IngestionTaskRepository(session)
        await repo.mark_failed(task_id, error_message)
        await session.commit()

async def _mark_task_success(task_id: UUID) -> None:
    """ 标记任务为成功 """
    async with AsyncSessionLocal() as session:
        repo = IngestionTaskRepository(session)
        await repo.mark_success(task_id)
        await session.commit()

def _make_chunk(
    document_id: UUID, chunk: LangChainDocument, embedding: list[float]
) -> DocumentChunk:
    return DocumentChunk(
        document_id=document_id,
        content=chunk.page_content,
        embedding=embedding,
        page_no=chunk.metadata.get("page_no"),
        section_path=chunk.metadata.get("section_path"),
        chunk_index=chunk.metadata["chunk_index"],
        chunk_hash=chunk.metadata["chunk_hash"],
        extra_metadata=chunk.metadata,
    )

async def _embed_with_progress(
        texts: list[str], task_id: UUID
) -> list[list[float]]:
    """ 按设定的Embedding大小分批嵌入，逐批写入任务记录 """
    from app.core.config import settings  # 避免循环引用

    if not texts:
        return []
    embeddings_client = embedder.get_embeddings()
    batch_size = max(1, settings.embedding_batch_size)
    results: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        vectors = await embeddings_client.aembed_documents(batch)
        results.extend(vectors)
        await _increment_task_progress(task_id, len(batch))
    return results
""" 首次入库相关内容 """
async def _run_ingest(document_id: UUID, task_id: UUID) -> None:
    """ 首次入库的主流程: 全量解析->切分->向量化->写入数据库 """
    logger.info("首次入库开始: document_id=%s task_id=%s", document_id, task_id)
    await _mark_task(task_id, running=True)

    try:
        async with AsyncSessionLocal() as session:
            # 获取文档信息
            document = await DocumentRepository(session).get_by_id(document_id)
            if document is None:
                logger.warning("文档不存在，跳过入库: %s", document_id)
                await _mark_task_failed(task_id, "文档不存在")
                return
            object_key = document.cos_object_key
            filename = document.name
        # 开始执行第一步，从COS上下载文档
        await _set_status(document_id, DocumentStatus.PARSING)
        content = await get_file_service().download(object_key)
        parsed = await parser.parse(filename, content)

        # 开始执行第二步，切分文档
        await _set_status(document_id, DocumentStatus.INDEXING)
        chunks = splitter.split(parsed)
        if not chunks:
            raise ValueError("切分后文档为空,请检查文档内容")

        # 开始执行第三步，使用向量模型将文档向量化
        await _set_task_total(task_id, len(chunks))
        embeddings = await _embed_with_progress(
            [c.page_content for c in chunks], task_id
        )

        # 开始执行第四步，将切分后的文档和向量化后的文件写入数据库
        async with AsyncSessionLocal() as session:
            chunk_repo = DocumentChunkRepository(session)
            await chunk_repo.bulk_add(
                [_make_chunk(document_id, c, vec) for c, vec in zip(chunks, embeddings, strict=True)]
            )
            await session.commit()

        await _set_status(document_id, DocumentStatus.READY, error_message=None)
        await _mark_task_success(task_id)
        logger.info("首次入库完成: document_id=%s, chunks=%s", document_id, len(chunks))
    except Exception as exc:
        logger.exception("首次入库失败: document_id=%s, error=%s", document_id, exc)
        message = str(exc).strip() or exc.__class__.__name__
        await _set_status(document_id, DocumentStatus.FAILED, error_message=message[:500])
        await _mark_task_failed(task_id, message)

""" 增量重建相关内容 """
def _has_duplicate_hash(chunks: list[LangChainDocument]) -> bool:
    seen: set[str] = set()
    for c in chunks:
        h = c.metadata["chunk_hash"]
        if h in seen:
            return True
        seen.add(h)
    return False

async def _run_incremental(
        document_id: UUID, task_id: UUID, old_chunks: list[DocumentChunk], new_chunks: list[LangChainDocument]
) -> None:
    """ 按创哈希对其增删改 """
    old_by_hash = {c.chunk_hash: c for c in old_chunks}
    new_hashes = {c.metadata["chunk_hash"] for c in new_chunks}

    to_delete_ids: list[UUID] = [
        c.id for c in old_chunks if c.chunk_hash not in new_hashes
    ]
    to_insert: list[LangChainDocument] = []
    to_update: list[tuple[DocumentChunk, LangChainDocument]] = []
    # 遍历新增的chunk, 如果存在则更新，不存在则插入
    for nc in new_chunks:
        h = nc.metadata["chunk_hash"]
        existing = old_by_hash.get(h)
        if existing is None:
            to_insert.append(nc)
        else:
            to_update.append((existing, nc))

    await _set_task_total(task_id, len(to_insert))
    new_embeddings = await _embed_with_progress(
        [c.page_content for c in to_insert], task_id
    )

    async with AsyncSessionLocal() as session:
        chunk_repo = DocumentChunkRepository(session)
        await chunk_repo.delete_by_ids(to_delete_ids)
        # 更新命中Chunk的位置
        for old, nc in to_update:
            old.chunk_index = nc.metadata["chunk_index"]
            old.page_no = nc.metadata["page_no"]
            old.section_path = nc.metadata.get("section_path")
            old.extra_metadata = nc.metadata
        # 插入新Chunk
        await chunk_repo.bulk_add(
            [
                _make_chunk(document_id, nc, vec)
                for nc, vec in zip(to_insert, new_embeddings, strict=True)
            ]
        )
        await session.commit()

async def _run_full_rebuild(
    document_id: UUID,
    task_id: UUID,
    new_chunks: list[LangChainDocument],
) -> None:
    """hash 冲突场景的兜底：清空旧 chunks，全量 embedding 后写入。"""
    await _set_task_total(task_id, len(new_chunks))
    embeddings = await _embed_with_progress(
        [c.page_content for c in new_chunks], task_id
    )

    async with AsyncSessionLocal() as session:
        chunk_repo = DocumentChunkRepository(session)
        await chunk_repo.delete_by_document(document_id)
        await chunk_repo.bulk_add(
            [
                _make_chunk(document_id, c, vec)
                for c, vec in zip(new_chunks, embeddings, strict=True)
            ]
        )
        await session.commit()

async def _set_task_total(task_id: UUID, total: int) -> None:
    """ 设置任务总进度 """
    async with AsyncSessionLocal() as session:
        repo = IngestionTaskRepository(session)
        await repo.set_progress_total(task_id, total)
        await session.commit()

async def _increment_task_progress(task_id: UUID, delta: int) -> None:
    """ 增量更新任务进度 """
    async with AsyncSessionLocal() as session:
        repo = IngestionTaskRepository(session)
        await repo.increment_progress(task_id, delta)
        await session.commit()

async def _run_reindex(document_id: UUID, task_id: UUID) -> None:
    """ 增量重建:按chunk cache对齐，仅对变化部分重新向量化 """
    logger.info("增量重建开始: document_id=%s task_id=%s", document_id, task_id)
    await _mark_task(task_id, running=True)

    try:
        async with AsyncSessionLocal() as session:
            # 获取文档信息
            document = await DocumentRepository(session).get_by_id(document_id)
            if document is None:
                logger.warning("文档不存在，跳过重建: %s", document_id)
                await _mark_task_failed(task_id, "文档不存在")
                return
            object_key = document.cos_object_key
            filename = document.name
        # 开始执行第一步，从COS上下载文档
        await _set_status(document_id, DocumentStatus.PARSING)
        content = await get_file_service().download(object_key)
        parsed = await parser.parse(filename, content)

        # 开始执行第二步，切分文档
        await _set_status(document_id, DocumentStatus.INDEXING)
        new_chunks = splitter.split(parsed)
        if not new_chunks:
            raise ValueError("切分后文档为空,请检查文档内容")
        # 获取旧的chunk
        async with AsyncSessionLocal() as session:
            old_chunks = await DocumentChunkRepository(session).list_all_by_document(
                document_id
            )
        if _has_duplicate_hash(new_chunks):
            logger.warning(
                "切分后文档存在重复的chunk_hash,请检查文档内容: %s", document_id
            )
            await _run_full_rebuild(document_id, task_id, new_chunks)
        else:
            await _run_incremental(document_id, task_id, old_chunks, new_chunks)
        # 内容已成功重建：版本号 +1
        async with AsyncSessionLocal() as session:
            doc_repo = DocumentRepository(session)
            doc = await doc_repo.get_by_id(document_id)
            if doc is not None:
                doc.version += 1
            await session.commit()

        await _set_status(document_id, DocumentStatus.READY, error_message=None)
        await _mark_task_success(task_id)

    except Exception as exc:
        logger.exception("reindex failed: document_id=%s", document_id)
        message = str(exc).strip() or exc.__class__.__name__
        await _set_status(document_id, DocumentStatus.FAILED, error_message=message[:500])
        await _mark_task_failed(task_id, message)

""" 对外给的首次入库和增量入库的worker同步接口 """
def run_ingest_sync(document_id: UUID, task_id: UUID) -> None:
    """ 首次入库的同步接口 """
    asyncio.run(_run_ingest(document_id, task_id))

def run_reindex_sync(document_id: UUID, task_id: UUID) -> None:
    """ 增量入库的同步接口 """
    asyncio.run(_run_reindex(document_id, task_id))

# 整体执行的流程连接
async def ingest_document(document_id: UUID) -> None:
    logger.info("开始执行流程: document_id=%s", document_id)

    try:
        # 获取文档信息
        async with AsyncSessionLocal() as session:
            doc_repo = DocumentRepository(session)
            doc = await doc_repo.get_by_id(document_id)
            if doc is None:
                logger.warning("文档不存在，跳过执行: %s", document_id)
                return
            object_key = doc.cos_object_key
            filename = doc.name

        # 开始执行第一步，从COS上下载文档
        await _set_status(document_id, DocumentStatus.PARSING)
        content = await get_file_service().download(object_key)
        documents = await parser.parse(filename, content)

        # 开始执行第二步，切分文档
        await _set_status(document_id, DocumentStatus.INDEXING)
        chunks = splitter.split(documents)
        if not chunks:
            raise ValueError("切分后文档为空")

        # 开始执行第三步，使用向量模型将文档向量化
        embeddings = await embedder.get_embeddings().aembed_documents(
            [c.page_content for c in chunks]
        )

        # 开始执行第四步，将切分后的文档和向量化后的文件写入数据库
        async with AsyncSessionLocal() as session:
            chunk_repo = DocumentChunkRepository(session)
            await chunk_repo.bulk_add(
                [
                    DocumentChunk(
                        document_id=document_id,
                        content=c.page_content,
                        embedding=vec,
                        page_no=c.metadata.get("page_no"),
                        section_path=c.metadata.get("section_path"),
                        chunk_index=c.metadata.get("chunk_index"),
                        chunk_hash=c.metadata.get("chunk_hash"),
                        extra_metadata=c.metadata,
                    )
                    for c, vec in zip(chunks, embeddings, strict=True)
                ]
            )
            await session.commit()

        # 设置最后状态为完成，并清空错误信息
        await _set_status(document_id, DocumentStatus.READY, error_message=None)
        logger.info("文档处理完成: document_id=%s, chunks=%s", document_id, len(chunks))

    except Exception as exc:
        logger.exception("文档处理失败: document_id=%s, error=%s", document_id, exc)
        message = str(exc).strip() or exc.__class__.__name__
        await _set_status(document_id, DocumentStatus.FAILED, error_message=message[:500])


