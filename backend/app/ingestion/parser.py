"""
第一步：文档解析
使用Docling开源插件对文档进行解析
"""
import asyncio
import io

from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document

from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)

class DocumentParseError(AppException):
    code = "document_parse_error"
    message = "文档解析失败"
    http_status = 400

_converter: DocumentConverter | None = None

def _get_converter() -> DocumentConverter:
    # 单例模式
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter

# 执行转换函数，将获得的文档转为Markdown
def _convert_sync(filename: str, content: bytes) -> str:
    source = DocumentStream(name=filename, stream=io.BytesIO(content))
    result = _get_converter().convert(source)
    return result.document.export_to_markdown()

async def parse(filename: str, content: bytes) -> list[Document]:
    """ 解析并转换成Langchain Document列表 """
    try:
        mardown = await asyncio.to_thread(_convert_sync, filename, content)
    except Exception as e:
        logger.exception("文档解析失败: %s", filename)
        raise DocumentParseError(f"Docling解析失败; {e}") from e

    if not mardown.strip():
        raise DocumentParseError("解析结果为空，文档可能损坏或不支持")

    return [
        Document(
            page_content=mardown,
            metadata={"source": filename},
        )
    ]


