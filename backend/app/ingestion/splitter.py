"""
第二步，文档切分
使用Langchain将文档切分为每一个chunk的小块
"""
import hashlib

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

# 创建文本的切分器
def _build_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", "。", "？", "；", "，", " ", ""],
        length_function=len,
        is_separator_regex=False
    )

# 切分并补齐chunk级的meta data
def split(documents: list[Document]) -> list[Document]:
    splitter = _build_splitter()
    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks):
        # Chunk index用于排序与定位，Chunk hash给后续增量索引比对
        chunk.metadata["chunk_index"] = index
        chunk.metadata["chunk_hash"] = hashlib.md5(
            chunk.page_content.encode("utf-8")
        ).hexdigest()


    return chunks
