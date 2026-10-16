""" 评测相关API接口定义 """
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Query, Response, Depends

from app.api.deps import get_current_admin
from app.api.schemas.evaluations import DatasetListResponse, DatasetInfo, EvaluationRunRead, EvaluationRunCreate, \
    EvaluationRunPage, EvaluationRunListItem, EvaluationItemPage, BadCaseCategoryValue, EvaluationItemRead, \
    EvaluationItemUpdate
from app.db.deps import DbSession
from app.services.evaluation_service import EvaluationService, execute_evaluation_run

router = APIRouter(prefix="/evaluations", tags=["evaluations"], dependencies=[Depends(get_current_admin)])


@router.get(
    "/datasets", response_model=DatasetListResponse,
    operation_id="listEvaluationDatasets", summary="列出可用评测集(jsonl文件名+条数）"
)
async def list_evaluation_datasets(session: DbSession) -> DatasetListResponse:
    service = EvaluationService(session)
    items = service.list_datasets()
    return DatasetListResponse(
        items=[DatasetInfo(name=name, size=size) for name, size in items]
    )


@router.post(
    "/runs", response_model=EvaluationRunRead, status_code=201,
    operation_id="createEvaluationRun", summary="创建评测Run并通过BackgroundTask异步执行"
)
async def create_evaluation_run(
        payload: EvaluationRunCreate,
        session: DbSession,
        background_tasks: BackgroundTasks
) -> EvaluationRunRead:
    """ 创建评测任务，通过BackgroundTask异步执行 """
    service = EvaluationService(session)
    run = await service.run(name=payload.name, dataset_name=payload.dataset_name)
    background_tasks.add_task(execute_evaluation_run, run.id)
    return EvaluationRunRead.model_validate(run)


""" run 的列表 / 详情 / 删除 """


@router.get(
    "/runs", response_model=EvaluationRunPage,
    operation_id="listEvaluationRuns", summary="按创建时间倒序分页列出评测Run"
)
async def list_evaluation_runs(
        session: DbSession,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100)
) -> EvaluationRunPage:
    """ 按创建时间倒序分页列出评测列表 """
    service = EvaluationService(session)
    items, total = await service.list_runs(page=page, page_size=page_size)
    return EvaluationRunPage(
        items=[EvaluationRunListItem.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/runs/{run_id}", response_model=EvaluationRunRead, operation_id="getEvaluationRun"
)
async def get_evaluation_run(run_id: UUID, session: DbSession) -> EvaluationRunRead:
    """ 根据Run ID获取单个评测任务详情 """
    service = EvaluationService(session)
    run = await service.get_run(run_id)
    return EvaluationRunRead.model_validate(run)


@router.delete(
    "/runs/{run_id}", status_code=204, operation_id="deleteEvaluationRun"
)
async def delete_evaluation_run(run_id: UUID, session: DbSession) -> Response:
    """ 删除指定ID的评测 """
    service = EvaluationService(session)
    await service.delete_run(run_id)
    return Response(status_code=204)


"""  items 的列表 / 详情 / 归因更新 """


@router.get(
    "/runs/{run_id}/items", response_model=EvaluationItemPage,
    operation_id="listEvaluationItems", summary="分页列出Run下的Case"
)
async def list_evaluation_items(
        run_id: UUID, session: DbSession, page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100), bad_case_only: bool = Query(False),
        category: BadCaseCategoryValue | None = Query(None)
) -> EvaluationItemPage:
    service = EvaluationService(session)
    items, total = await service.list_items(
        run_id, page=page, page_size=page_size,
        bad_case_only=bad_case_only, category=category
    )
    return EvaluationItemPage(
        items=[EvaluationItemRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get(
    "/items/{item_id}", response_model=EvaluationItemRead, operation_id="getEvaluationItem"
)
async def get_evaluation_item(item_id: UUID, session: DbSession) -> EvaluationItemRead:
    """ 根据给定的Item ID获取详情 """
    service = EvaluationService(session)
    item = await service.get_item(item_id)
    return EvaluationItemRead.model_validate(item)

@router.patch(
    "/items/{item_id}", response_model=EvaluationItemRead, operation_id="updateEvaluationItem",
    summary="人工覆盖Badcase归因/备注"
)
async def update_evaluation_item(
        item_id: UUID,
        payload: EvaluationItemUpdate,
        session: DbSession
) -> EvaluationItemRead:
    service = EvaluationService(session)
    item = await service.update_item_bad_case(
        item_id, bad_case_category=payload.bad_case_category,
        bad_case_note=payload.bad_case_note,
        is_bad_case=payload.is_bad_case
    )
    return EvaluationItemRead.model_validate(item)