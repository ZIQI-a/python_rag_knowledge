"""Celery异步 应用实例。

启动 worker：`uv run celery -A app.celery_app worker -l info`
任务定义见 `app.ingestion.tasks`，通过 `include` 让 worker 启动时自动发现。
"""
import asyncio
from collections.abc import Coroutine
from typing import Any

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown, worker_shutdown

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_worker_runner: asyncio.Runner | None = None

celery_app = Celery(
    "rag_knowledge_base",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.ingestion.tasks"]
)

celery_app.conf.update(
    task_acks_late=False,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


def run_async_task(coroutine: Coroutine[Any, Any, None]) -> None:
    """同一 worker 进程串行复用事件循环，保持异步连接的归属一致。"""
    global _worker_runner
    if _worker_runner is None:
        _worker_runner = asyncio.Runner()
    _worker_runner.run(coroutine)


@worker_process_init.connect
def initialize_worker_process(**kwargs: Any) -> None:
    """子进程不继承父进程的事件循环和数据库连接池。"""
    from app.db.session import engine

    global _worker_runner
    _worker_runner = None
    # 丢弃继承的池引用，不在子进程关闭父进程拥有的连接。
    engine.sync_engine.dispose(close=False)


async def _close_worker_resources() -> None:
    """在资源所属循环中释放连接；一个资源失败不阻止其他资源清理。"""
    from app.db.session import engine
    from app.ingestion.embedder import close_embeddings
    from app.services.semantic_cache_service import close_semantic_cache

    for close in (close_embeddings, close_semantic_cache, engine.dispose):
        try:
            await close()
        except Exception:
            logger.exception("关闭 worker 异步资源失败: %s", close.__name__)


@worker_process_shutdown.connect
@worker_shutdown.connect
def shutdown_worker_process(**kwargs: Any) -> None:
    """prefork 子进程和 solo worker 正常退出时，先释放资源再关闭循环。"""
    global _worker_runner
    runner = _worker_runner
    if runner is None:
        return
    try:
        runner.run(_close_worker_resources())
    finally:
        _worker_runner = None
        runner.close()
