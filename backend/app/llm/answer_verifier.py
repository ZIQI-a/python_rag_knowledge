import json
from dataclasses import dataclass

from app.core.logging import get_logger
from app.llm.models import get_chat_model
from app.llm.prompts import build_verify_answer_messages
from app.retrieval.vector_retriever import RetrievedChunk

logger = get_logger(__name__)

""" 单次校验结果 """
@dataclass(frozen=True)
class VerifyResult:
    verified: bool
    reason: str

""" 答案校验器 """
class AnswerVerifier:
    async def verify(self, question: str, answer: str, chunks: list[RetrievedChunk]) -> VerifyResult:
        if not chunks or not answer.strip():
            return VerifyResult(verified=True, reason="")
        messages = build_verify_answer_messages(
            question=question,
            answer=answer,
            chunks_text=format_context(chunks)
        )
        try:
            response = await get_chat_model().ainvoke(messages)
            raw = _extract_text(response.content).strip()
            return _parse_result(raw)
        except Exception:
            logger.exception(
                "问题校验，调用失败，降级: question=%r", question
            )
            return VerifyResult(verified=True, reason="verifier_exception")

_verifier: AnswerVerifier | None = None
# 单例模式获取答案校验器
def get_answer_verifier() -> AnswerVerifier:
    global _verifier
    if _verifier is None:
        _verifier = AnswerVerifier()
    return _verifier

""" 解析JSON输出任何非法字段降级。 """
def _parse_result(raw: str) -> VerifyResult:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.load(text)
    except json.JSONDecodeError:
        logger.warning("问题，认证JSON解析失败，降级, verified=True: raw=%r", raw)
        return VerifyResult(verified=True, reason="verified_parse_failed")

    if not isinstance(data, dict):
        return VerifyResult(verified=True, reason="verified_parse_failed")

    verified_raw = data.get("verified")
    if not isinstance(verified_raw, bool):
        logger.warning(
            "问题认证返回字段非布尔值降级, raw=%r",raw
        )
        return VerifyResult(verified=True, reason="verifier_invalid_verified")

    reason = str(data.get("reason") or "").strip()
    return VerifyResult(verified=verified_raw, reason=reason)

""" 兼容Langchain ChatModel的Context联合类型 """
def _extract_text(content: str | list[str | dict]) -> str:
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content if isinstance(part, dict))