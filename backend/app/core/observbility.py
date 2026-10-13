""" 可观测性SDK配置 """
import os

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

""" 把settings配置写到LangSmith官方配置变量应用启动时调用 """
def configure_observability() -> None:
    # 由于默认LangSmith不会读自己配置的Settings环境变量，所以这里要显示声明
    if settings.observability_enabled:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
        logger.info(
            "LangSmith tracing enabled: project=%s, endpoint=%s",
            settings.langsmith_project,
            settings.langsmith_endpoint
        )
    else :
        # 没有开启时显示关闭
        os.environ["LANGSMITH_TRACING"] = "false"
        logger.info("LangSmith trace disabled(No LangSmith API key or switch off)")

""" 读取当前Traceable上下文中的Trace ID """
def get_current_trace_id() -> str | None:
    if not settings.observability_enabled:
        return None
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is None:
            return None
        return str(run.trace_id)
    except Exception:
        logger.warning("Get current trace ID异常返回空", exc_info=True)
        return None

""" 将Trace ID拼成longsmith的详情页URL """
def build_trace_url(trace_id: str | None) -> str | None:
    if not trace_id or not settings.langsmith_run_url_prefix:
        return None
    return f"{settings.langsmith_run_url_prefix.rstrip('/')}/r/{trace_id}"


