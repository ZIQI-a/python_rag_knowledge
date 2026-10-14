""" 评测对外暴露接口 """
from app.evaluation.dataset import EvaluationCase, list_datasets, load_dataset
from app.evaluation.ragas_runner import RagasMetrics, evaluate_batch
from app.evaluation.scoring import (
    BadCaseCategory,
    BadCaseRule,
    classify_bad_case,
    compute_citation_hit,
    compute_refusal_correct
)

__all__ = [
    "BadCaseCategory",
    "BadCaseRule",
    "classify_bad_case",
    "compute_citation_hit",
    "compute_refusal_correct",
    "RagasMetrics",
    "evaluate_batch",
    "EvaluationCase",
    "list_datasets",
    "load_dataset"
]