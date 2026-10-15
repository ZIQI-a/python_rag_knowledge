""" 指标计算函数 + Bad Case 归因规则 """
from dataclasses import dataclass
from typing import Literal

# Bad Case 归因类别,与PRD【bad case归因】12类对齐
BadCaseCategory = Literal[
    "document_parse_failed", # 文档解析失败
    "chunk_split_bad", # chunk分割失败
    "embedding_recall_miss", # 向量召回未命中
    "keyword_recall_miss", # 关键词召回未命中
    "rrf_fusion_error", # RRF融合排序错误
    "rerank_order_error", # 精排排序错误
    "context_judge_too_loose", # 上下文判定过松(该拒未拒)
    "context_judge_too_strict", # 上下文判定过严(误拒)
    "prompt_constraint_weak", # prompt约束不足
    "generation_off_context", # 生成偏离上下文
    "citation_parse_failed", # 引用解析失败
    "permission_filter_error", # 权限过滤错误
    "other" # 其他
]

# 低分阈值，低于该分数的Case视为Bad Case;(实际项目对指标类型分别阈值)
_LOW_SCORE_THRESHOLD = 0.5

@dataclass(frozen=True)
class BadCaseRule:
    """ Bad Case 归因规则 """
    is_bad_case: bool
    category: BadCaseCategory | None

""" 引用命中率判定 """
def compute_citation_hit(
        actual_citations: list[dict],
        expected_document_names: list[str],
        expected_keywords: list[str]
) -> bool:
    if not actual_citations:
        return False

    actual_doc_names = {c.get("document_name", "") for c in actual_citations}
    if any(name in actual_doc_names for name in expected_document_names if name):
        return True

    if expected_keywords:
        quote_blob = "\n".join(str(c.get("quote", "")) for c in actual_citations)
        if any(kw in quote_blob for kw in expected_keywords if kw):
            return True

    return False

""" 拒答正确率，实际拒答状态等于期望 """
def compute_refusal_correct(actual_refused: bool, should_refuse: bool) -> bool:
    return actual_refused == should_refuse

""" 归因主函数 """
def classify_bad_case(
        *,
        should_refuse: bool,
        actual_refused: bool,
        refusal_correct: bool,
        citation_hit: bool | None,
        faithfulness: float | None,
        answer_relevancy: float | None,
        context_precision: float | None,
        context_recall: float | None,
        has_error: bool
) -> BadCaseRule:
    """ 归因主函数 """
    if has_error:
        return BadCaseRule(is_bad_case=True, category="other")

    # 拒答错误的两种方向，该拒不拒或不该拒却拒了
    if not refusal_correct:
        if should_refuse and not actual_refused:
            return BadCaseRule(is_bad_case=True, category="context_judge_too_loose")
        return BadCaseRule(is_bad_case=True, category="context_judge_too_strict")

    # 考察引用命中
    if citation_hit is False:
        return BadCaseRule(is_bad_case=True, category="embedding_recall_miss")

    """ RAGAS指标逐个检查 """
    # 1 召回分数
    if _is_low(context_recall):
        return BadCaseRule(is_bad_case=True, category="embedding_recall_miss")
    # 2 排序分数
    if _is_low(context_precision):
        return BadCaseRule(is_bad_case=True, category="rerank_order_error")
    # 3 可信度分数
    if _is_low(faithfulness):
        return BadCaseRule(is_bad_case=True, category="generation_off_context")
    # 4 答案相关性分数
    if _is_low(answer_relevancy):
        return BadCaseRule(is_bad_case=True, category="prompt_constraint_weak")

    return BadCaseRule(is_bad_case=False, category=None)

# 判断分数是否符合制定的要求
def _is_low(score: float | None) -> bool:
    return score is not None and score < _LOW_SCORE_THRESHOLD

