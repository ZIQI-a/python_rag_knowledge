""" 将Agentic RAG提示词和调大模型两种封装 """
import json
from dataclasses import dataclass
from typing import Literal, get_args

from sympy.polys.subresultants_qq_zz import res

from app.core.logging import get_logger
from app.llm.models import get_chat_model
from app.llm.prompts import build_agent_plan_messages
from app.workflows.rag_state import QueryRoute

logger = get_logger(__name__)

AgentAction = Literal["proceed", "rewrite_query", "switch_route", "refuse"]
_VALID_ACTIONS: tuple[str, ...] = get_args(AgentAction) # 验证执行策略
_VALID_ROUTES: tuple[str, ...] = get_args(QueryRoute) # 验证路由策略

""" Agent决策结果模型 """
@dataclass(frozen=True)
class AgentDecision:
    action: AgentAction
    reason: str
    new_query: str | None = None
    new_route: QueryRoute | None = None

""" 大模型LLM决策的薄封装 """
class AgentPlanner:
    async def plan(
            self,
            question: str,
            current_route: QueryRoute,
            current_query: str,
            previous_steps: list[dict],
    ) -> AgentDecision:
        history = _format_history(previous_steps)
        messages = build_agent_plan_messages(
            question=question,
            current_query=current_query,
            current_route=current_route,
            history=history
        )
        # 调用大模型，传入提示词，拿到结果
        try:
            response = await get_chat_model().ainvoke(messages)
            raw = _extract_text(response.content).strip()
            return _parse_decision(raw)
        except Exception as exc:
            logger.warning("Agent planner调用失败, 降级到proceed: question=%r", question)
            return AgentDecision(action="proceed", reason="planner_exception")

_planner: AgentPlanner | None = None
def get_agent_planner() -> AgentPlanner:
    """ 获取AgentPlanner单例 """
    global _planner
    if _planner is None:
        _planner = AgentPlanner()
    return _planner

""" 把历史Agent Step压成一段可读文本给LLM看 """
def _format_history(steps: list[dict]) -> str:
    if not steps:
        return "(无)"
    lines: list[str] = []
    for step in steps:
        lines.append(
            f"- round {step.get('round')}: action={step.get('action')}, "
            f"route={step.get('route')}, query={step.get('query')!r}, "
            f"retrieved_count={step.get('retrieved_count')}, "
            f"top_score={step.get('top_score')}, "
            f"sufficient={step.get('sufficient')}"
        )
    return "\n".join(lines)

""" 解析大模型JSON的决策输出，多种情况提取，不符合要求退回proceed """
def _parse_decision(raw: str) -> AgentDecision:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Agent planner解析JSON失败, 降级到proceed: raw=%r", raw)
        return AgentDecision(action="proceed", reason="planner_parse_failed")
    # data必须是字典
    if not isinstance(data, dict):
        return AgentDecision(action="proceed", reason="planner_parse_failed")
    # 必须有action字段
    action = str(data.get("action", "")).strip().lower()
    if action not in _VALID_ACTIONS:
        logger.warning("Agent planner返回非法Action=%r, 降级到proceed.", action)
        return AgentDecision(action="proceed", reason="planner_invalid_action")

    reason = str(data.get("reason") or "").strip() or "(no reason)"
    #
    new_query_raw = data.get("new_query")
    new_query = (
        str(new_query_raw).strip()
        if isinstance(new_query_raw, str) and new_query_raw.strip() else None
    )

    new_route_raw = data.get("new_route")
    new_route: QueryRoute | None = None
    # 如果new_route_raw是字符串，且是合法的路由策略，则赋值给new_route
    if isinstance(new_route_raw, str) and new_route_raw.strip().lower() in _VALID_ROUTES:
        new_route = new_route_raw.strip().lower()
    # 如果action是rewrite_query，且new_query为空，降级为proceed
    if action == "rewrite_query" and not new_query:
        logger.warning("Agent plan action=rewrite_query缺少new_query,降级为proceed")
        return AgentDecision(action="proceed", reason="planner_missing_query")

    # switch_route必须带new_route
    if action == "switch_route" and new_route is None:
        logger.warning("agent plan action=switch_route缺少new_route,降级为proceed")
        return AgentDecision(action="proceed", reason="planner_missing_route")

    return AgentDecision(
        action=action,
        reason=reason,
        new_query=new_query,
        new_route=new_route
    )

""" 兼容Langchain ChatModel的Content联合类型 """
def _extract_text(content: str | list[str | dict]) -> str:
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content if isinstance(part, dict))

