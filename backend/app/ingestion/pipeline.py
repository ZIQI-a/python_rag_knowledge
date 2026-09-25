""" 将整个流程串起来 """
from uuid import UUID

from app.core.logging import get_logger
from app.db.models import DocumentChunk, DocumentStatus
from app.db.repositories.chunk_repo import DocumentChunkRepository
from app.db.repositories.document_repo import DocumentRepository
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
        chunks = await splitter.split(documents)
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


