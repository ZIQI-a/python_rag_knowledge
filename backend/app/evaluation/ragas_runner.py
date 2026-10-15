""" RAGAS自动指标封装 """
import asyncio
from dataclasses import dataclass

from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)

from app.core.logging import get_logger
from app.ingestion.embedder import get_embeddings
from app.llm.models import get_chat_model

logger = get_logger(__name__)

@dataclass(frozen=True)
class RagasMetrics:
    """ 单条case的RAGAS四项指标结果: [0, 1] """
    faithfulness: float | None
    answer_relevancy: float | None
    context_precision: float | None
    context_recall: float | None


@dataclass(frozen=True)
class RagasSample:
    """ 未给Evaluate的单条样本，评测的单条样本 """
    question: str
    answer: str
    retrieved_contexts: list[str]
    reference_answer: str

_METRICS = [faithfulness, answer_relevancy, context_precision, context_recall]


""" 批量计算RAGAS指标(基于样本) """
async def evaluate_batch(samples: list[RagasSample]) -> list[RagasMetrics]:
    if not samples:
        return []

    # 拿到数据集
    dataset = EvaluationDataset(
        samples=[
            SingleTurnSample(
                user_input=s.question,
                response=s.answer or " ",
                retrieved_contexts=s.retrieved_contexts or [" "],
                reference=s.reference_answer or " "
            )
            for s in samples
        ]
    )

    try:
        result = await asyncio.to_thread(
            evaluate,
            dataset=dataset,
            metrics=_METRICS,
            llm=get_chat_model(),
            embeddings=get_embeddings(),
            raise_exceptions=False,
            show_progress=False
        )
    except Exception:
        logger.exception("RAGAS 批量评测失败，返回空")
        return [_empty_metrics() for _ in samples]

    return _extract_metrics(result, expected=len(samples))

# 整合成返回的RagasMetrics格式
def _extract_metrics(result, expected: int) -> list[RagasMetrics]:
    rows = getattr(result, "scores", None) or []
    if len(rows) != expected:
        logger.warning(
            "RAGAS返回行数 %d 与样本数 %d 不一致，按可用值对齐", len(rows), expected
        )

    metrics: list[RagasMetrics] = []
    for i in range(expected):
        row = rows[i] if i < len(rows) else {}

        metrics.append(
            RagasMetrics(
                faithfulness=_pick(row, "faithfulness"),
                answer_relevancy=_pick(row, "answer_relevancy"),
                context_precision=_pick(row, "context_precision"),
                context_recall=_pick(row, "context_recall")
            )
        )
    return metrics

# 从结果行里取分数，如果缺失即为None
def _pick(row: dict, key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return None
    return as_float

# 评测失败或出现异常，为每个case返回空对象
def _empty_metrics() -> RagasMetrics:
    return RagasMetrics(
        faithfulness=None, answer_relevancy=None,
        context_precision=None, context_recall=None
    )