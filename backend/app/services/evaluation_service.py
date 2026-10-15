""" 评测与归因分析服务类 """
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError, NotFoundError
from app.core.logging import get_logger
from app.db.repositories.evaluation_repo import EvaluationRunRepository, EvaluationItemRepository
from app.db.session import AsyncSessionLocal

from app.evaluation.dataset import list_datasets
from app.db.models import EvaluationRun, EvaluationRunStatus, EvaluationItem
from app.evaluation import load_dataset, compute_citation_hit, compute_refusal_correct, RagasMetrics, evaluate_batch, \
    classify_bad_case
from app.evaluation.ragas_runner import RagasSample
from app.services.chat_service import ChatService, EvaluationAnswer

logger = get_logger(__name__)

""" 评测相关业务操作: CRUD + 列表筛选 + Badcase归因批量操作 """
class EvaluationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.run_repo = EvaluationRunRepository(session)
        self.item_repo = EvaluationItemRepository(session)

    """ 加载评测集校验存在性 """
    async def run(self, *, name: str, dataset_name: str) -> EvaluationRun:
        # 先加载一遍数据集
        cases = load_dataset(dataset_name)
        if not cases:
            raise ValidationError(f"评测集{dataset_name}为空")

        run = EvaluationRun(
            name=name,
            dataset_name=dataset_name,
            dataset_size=len(cases),
            status=EvaluationRunStatus.RUNNING,
            progress_total=len(cases)
        )
        await self.run_repo.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    # """ 获取已经在执行的评测集 """
    async def get_run(self, run_id: UUID) -> EvaluationRun:
        run = await self.run_repo.get(run_id)
        if run is None:
            raise NotFoundError("评测Run不存在")
        return run

    # """ 展示列表运行评测 """
    async def list_runs(self, page: int, page_size: int):
        return await self.run_repo.list_page(page=page, page_size=page_size)

    # """ 删除评测run """
    async def delete_run(self, run_id: UUID) -> None:
        deleted = await self.run_repo.delete(run_id)
        if not deleted:
            raise NotFoundError("指定删除的评测run不存在")
        await self.session.commit()

    """ Item的评测增删改查 """
    # 分页展示给定的run ID的item列表
    async def list_items(
            self, run_id: UUID, page: int, page_size: int,
            *, bad_case_only: bool, category: str | None
    ):
        await self.get_run(run_id)
        return await self.item_repo.list_page(
            run_id, page=page, page_size=page_size,
            bad_case_only=bad_case_only, category=category
        )

    # 根据ID获取item
    async def get_item(self, item_id: UUID) -> EvaluationItem:
        item = await self.item_repo.get(item_id)
        if item is None:
            raise NotFoundError("指定ID的评测case不存在")
        return item

    # 前端覆盖Bad Case归因
    async def update_item_bad_case(
            self, item_id: UUID, *, bad_case_category: str | None, bad_case_note: str | None, is_bad_case: bool | None
    ) -> EvaluationItem:
        item = await self.get_item(item_id)

        if is_bad_case is False:
            item.is_bad_case = False
            item.bad_case_category = None
        else:
            if bad_case_category is not None:
                item.bad_case_category = bad_case_category
                item.is_bad_case = True
            elif is_bad_case:
                item.is_bad_case = True

        if bad_case_note is not None:
            item.bad_case_note = bad_case_note

        await self.session.commit()
        await self.session.refresh(item)
        return item

    def list_datasets(self) -> list[tuple[str, int]]:
        return list_datasets()

""" 评测run异步执行器 """
async def execute_evaluation_run(run_id: UUID) -> None:

    logger.info("evaluation run start: run_id=%s", run_id)
    try:
        async with AsyncSessionLocal() as session:
            run_repo = EvaluationRunRepository(session)
            run = await run_repo.get(run_id)
            if run is None:
                logger.warning("评测执行未找到，跳过: %s", run_id)
                return
            run.started_at = datetime.now(timezone.utc)
            await session.commit()
            dataset_name = run.dataset_name

        cases = load_dataset(dataset_name)

        # 阶段一： 逐条跑RAG，每条独立事务写一行item
        for case in cases:
            await _run_single_case(run_id, case)

        # 阶段二： 批量计算RAGAS加Badcase归因聚合
        await _finalize_run(run_id)

        async with AsyncSessionLocal() as session:
            run = await EvaluationRunRepository(session).get(run_id)
            if run is not None:
                run.status = EvaluationRunStatus.COMPLETED
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()
        logger.info("评测执行完成, run_id=%s", run_id)

    except Exception as e:
        logger.exception("评测执行失败, run_id=%s", run_id)
        async with AsyncSessionLocal() as session:
            run = await EvaluationRunRepository(session).get(run_id)
            if run is not None:
                run.status = EvaluationRunStatus.FAILED
                run.finished_at = datetime.now(timezone.utc)
                run.error_message = (str(e).strip() or e.__class__.__name__)[:500]
                await session.commit()

async def _run_single_case(run_id: UUID, case) -> None:
    """ 每条Case独立写一行（阶段一： 逐条跑RAG） """
    async with AsyncSessionLocal() as session:
        chat_service = ChatService(session)
        answer: EvaluationAnswer = await chat_service.answer_for_evaluation(case.question)

        citation_hit = (
            None if case.should_refuse else compute_citation_hit(
                actual_citations=answer.citations,
                expected_document_names=case.expected_document_names,
                expected_keywords=case.expected_keywords
            )
        )
        refusal_correct = compute_refusal_correct(answer.refused, case.should_refuse)

        item = EvaluationItem(
            run_id=run_id,
            case_id=case.case_id,
            question=case.question,
            expected_answer=case.expected_answer,
            expected_document_names=case.expected_document_names,
            expected_keywords=case.expected_keywords,
            should_refuse=case.should_refuse,
            tags=case.tags,
            actual_answer=answer.answer,
            actual_refused=answer.refused,
            citations=answer.citations,
            retrieved_chunks_meta=[_chunk_meta(c) for c in answer.chunks],
            query_route=answer.query_route or None,
            agent_steps=answer.agent_steps or None,
            verify_result=_verify_payload(answer.verify_result),
            trace_id=answer.trace_id,
            latency_ms=answer.latency_ms,
            first_token_latency_ms=answer.first_token_latency_ms,
            error_message=answer.error_message,
            citation_hit=citation_hit,
            refusal_correct=refusal_correct,
        )
        await EvaluationItemRepository(session).add(item)

        # 更新Run的进度
        run = await EvaluationRunRepository(session).get(run_id)
        if run is not None:
            run.progress_completed += 1
            if answer.error_message:
                run.progress_failed += 1
        await session.commit()


async def _finalize_run(run_id: UUID) -> None:
    """ RAGAS 批量算分 + Bad Case 归因 + 聚合 run 指标 """
    # 借一个数据库连接：整场算分与回填都在同一个事务里完成
    async with AsyncSessionLocal() as session:
        item_repo = EvaluationItemRepository(session)  # 明细仓库
        items = await item_repo.list_by_run(run_id)  # 取出这次 run 的全部明细
        # 一条明细都没有（例如所有 case 提前失败），没有可算的，直接结束
        if not items:
            return

        samples_with_index: list[tuple[int, RagasSample]] = []  # 待算分清单，每项 =（在 items 中的下标, 样本）
        # 逐条筛出“能算 RAGAS”的明细
        for idx, item in enumerate(items):
            # 三种情况跳过：该拒答的（没有检索上下文可评）、本条跑挂的、一条 chunk 都没检索到的
            if item.should_refuse or item.error_message or not item.retrieved_chunks_meta:
                continue
            samples_with_index.append(
                (
                    idx,  # 记下它在 items 里的位置，算完靠它找回原行
                    RagasSample(
                        question=item.question,  # 问题
                        answer=item.actual_answer,  # 实际答案
                        # 检索到的 chunk 正文拼成上下文列表
                        retrieved_contexts=[
                            str(c.get("content", "")) for c in item.retrieved_chunks_meta
                        ],
                        reference_answer=item.expected_answer  # 参考答案
                    )
                )
            )

        metrics_list: list[RagasMetrics | None] = [None] * len(items)  # 与 items 等长的空位表
        # 有样本才真去调算分服务，避免空调用
        if samples_with_index:
            # 一次批量送出去算分，返回顺序与送进去的样本一一对应
            indexed_metrics = await evaluate_batch([s for _, s in samples_with_index])
            # 两个列表并行遍历：左边拆出（下标, 样本），右边同时取一个分数
            for (idx, _), m in zip(samples_with_index, indexed_metrics, strict=True):
                metrics_list[idx] = m  # 按下标填回原位，完成对账

        # 此时 metrics_list 与 items 等长且一一对应，可以配对写回
        for item, metrics in zip(items, metrics_list, strict=True):

            # 被跳过的那些条目是 None，不需要写
            if metrics is not None:
                item.faithfulness = metrics.faithfulness  # 忠实度评分
                item.answer_relevancy = metrics.answer_relevancy  # 答案相关性评分
                item.context_precision = metrics.context_precision  # 上下文精度评分
                item.context_recall = metrics.context_recall  # 上下文召回评分

            rule = classify_bad_case(
                should_refuse=item.should_refuse,
                actual_refused=item.actual_refused,
                refusal_correct=item.refusal_correct,
                citation_hit=item.citation_hit,
                faithfulness=item.faithfulness,
                answer_relevancy=item.answer_relevancy,
                context_precision=item.context_precision,
                context_recall=item.context_recall,
                has_error=bool(item.error_message)
            )
            item.is_bad_case = rule.is_bad_case
            item.bad_case_category = rule.category

        # 全部 item 处理完后，一次性聚合 run 的汇总指标
        run = await EvaluationRunRepository(session).get(run_id)
        if run is not None:
            run.faithfulness = _avg([i.faithfulness for i in items])
            run.answer_relevancy = _avg([i.answer_relevancy for i in items])
            run.context_precision = _avg([i.context_precision for i in items])
            run.context_recall = _avg([i.context_recall for i in items])
            non_refusal_hits = [i.citation_hit for i in items if i.citation_hit is not None]
            run.citation_hit_rate = (
                sum(1 for h in non_refusal_hits if h) / len(non_refusal_hits)
                if non_refusal_hits else None
            )
            run.refusal_accuracy = sum(1 for i in items if i.refusal_correct) / len(items)
            run.avg_latency_ms = sum(i.latency_ms for i in items) / len(items)
            first_token_values = [
                i.first_token_latency_ms for i in items if i.first_token_latency_ms is not None
            ]
            run.avg_first_token_latency_ms = (
                sum(first_token_values) / len(first_token_values)
                if first_token_values else None
            )

        await session.commit()

""" 以下是一些辅助函数 """

def _chunk_meta(chunk):
    """ Retrieved Chunk序列转换成评测的Retrieved Chunk轻量Meta;人话Json好识别 """
    return {
        "chunk_id": str(chunk.chunk_id),
        "document_id": str(chunk.document_id),
        "document_name": chunk.document_name,
        "page_no": chunk.page_no,
        "section_path": chunk.section_path,
        "content": chunk.content,
        "vector_score": chunk.vector_score,
        "rerank_score": chunk.rerank_score,
        "rrf_score": chunk.rrf_score
    }


def _verify_payload(result) -> dict | None:
    if result is None:
        return None
    return {"verified": result.verified, "reason": result.reason or None}

def _avg(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


