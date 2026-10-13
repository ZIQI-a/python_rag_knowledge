from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.core.config import settings
from app.core.logging import get_logger
from app.workflows.nodes import normalize_query, route_query, plan_retrieval, retrieve, observe_context, judge_context, refuse, rerank
from app.workflows.rag_state import RAGState

logger = get_logger(__name__)

""" 如果决策为refuse直接结束避免再做无意义的检索 """
def _after_plan(state: RAGState) -> str:
    if state.get("agent_steps"):
        last_action = state["agent_steps"][-1].get("action")
        if last_action == "refuse":
            return "refuse"
    return "retrieve"

""" 执行observer context之后，决定继续循环还是结束 """
def _after_observe(state: RAGState) -> str:
    # 关闭Agent Loop结束
    if not settings.agent_loop_enabled:
        return "rerank"
    # 本轮信息已足够，结束
    if state.get("context_sufficient"):
        return "rerank"
    # 达到上限结束
    if state.get("retrieval_round", 0) >= settings.agent_max_rounds:
        return "rerank"
    return "plan"

def _after_judge(state: RAGState) -> str:
    if state.get("context_is_enough"):
        return "end"
    return "refuse"

def _build_graph():
    builder = StateGraph(RAGState)
    # 构建节点
    builder.add_node("normalize_query", normalize_query)
    builder.add_node("route_query", route_query)
    builder.add_node("plan_retrieval", plan_retrieval)
    builder.add_node("retrieve", retrieve)
    builder.add_node("observe_context", observe_context)
    builder.add_node("rerank", rerank)
    builder.add_node("judge_context", judge_context)
    builder.add_node("refuse", refuse)
    # 添加边连接起来
    builder.add_edge(START, "normalize_query")
    builder.add_edge("normalize_query", "route_query")
    builder.add_edge("route_query", "plan_retrieval")
    # Planner 决定拒答时进入统一拒答节点，避免条件路由找不到目标。
    builder.add_conditional_edges(
        "plan_retrieval", _after_plan, {"retrieve": "retrieve", "refuse": "refuse"}
    )
    builder.add_edge("retrieve", "observe_context")
    builder.add_conditional_edges(
        "observe_context",
        _after_observe,
        {"plan": "plan_retrieval", "rerank": "rerank"},
    )
    builder.add_edge("rerank", "judge_context")
    builder.add_conditional_edges(
        "judge_context", _after_judge, {"end": END, "refuse": "refuse"}
    )
    builder.add_edge("refuse", END)

    return builder.compile()

_rag_graph = _build_graph()

""" 对外暴露子图函数调用节点和边(全局单例，模块加载时构建一次) """
def get_rag_graph():
    return _rag_graph
