""" 检索流程，策划节点 """
from app.core.config import settings
from app.llm.agent_planner import get_agent_planner
from app.llm.query_rewriter import get_query_rewriter
from app.workflows.rag_state import RAGState, QueryRoute

async def plan_retrieval(state: RAGState) -> RAGState:
    steps = list(state.get("agent_steps", []))
    current_route: QueryRoute = state.get("route", "original")
    current_query = state.get("query") or state["question"]

    # 首轮，route_query已经决定好了路由和查询策略，无需再调大模型
    if not steps:
        steps.append(
            {
                "round": 1,
                "action": "initial",
                "reason": "首轮检索沿用route_query决策",
                "route": current_route,
                "query": current_query
            }
        )
        return {"agent_steps": steps}

    # 后续由大模型Planner决定如何重试
    decision = await get_agent_planner().plan(
        question=state["question"],
        current_route=current_route,
        current_query=current_query,
        previous_steps=steps,
    )

    update: RAGState = {}
    new_route = current_route
    new_query = current_query

     # 如果是需要重写提示词
    if decision.action == "rewrite_query" and decision.new_query:
        new_query = decision.new_query
        new_route = "original" # 改query同时把route强制重置为original
        update["query"] = new_query
        update["route"] = new_route
        update["rewritten_query"] = None
        update["hyde_answer"] = None
        update["multi_queries"] = None
    # 如果需要切换路由策略
    elif decision.action == "switch_route" and decision.new_route:
        rewriter = get_query_rewriter()
        result = await rewriter.apply_route(
            question=state["question"],
            route=decision.new_route,
            multi_query_count=settings.multi_query_count
        )
        new_route = result.route
        new_query = result.query
        update["route"] = new_route
        update["query"] = new_query
        update["rewritten_query"] = result.rewritten_query
        update["hyde_answer"] = result.hyde_answer
        update["multi_queries"] = result.multi_queries

    steps.append(
        {
            "round": len(steps) + 1,
            "action": decision.action,
            "reason": decision.reason,
            "route": new_route,
            "query": new_query,
        }
    )
    update["agent_steps"] = steps
    # 走到巨大路由时，直接把节点塞给Refuse节点，统一显示文案
    return update


