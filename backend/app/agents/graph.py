"""LangGraph workflow assembly for the financial assistant's agent architecture."""

from langgraph.graph import END, START, StateGraph

from app.agents.budget_agent import budget_agent
from app.agents.finance_agent import finance_agent
from app.agents.goal_agent import goal_agent
from app.agents.memory_agent import memory_agent
from app.agents.planner_agent import planner_agent
from app.agents.report_agent import report_agent
from app.agents.state import GraphState


def build_agent_graph():
    """Compile the static planner-to-domains-to-memory workflow.

    Domain nodes run in parallel after planning. The list edge creates a fan-in
    barrier, so Memory executes once after every domain node has returned.
    """
    builder = StateGraph(GraphState)
    builder.add_node("planner", planner_agent)
    builder.add_node("finance", finance_agent)
    builder.add_node("budget", budget_agent)
    builder.add_node("goal", goal_agent)
    builder.add_node("report", report_agent)
    builder.add_node("memory", memory_agent)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "finance")
    builder.add_edge("planner", "budget")
    builder.add_edge("planner", "goal")
    builder.add_edge("planner", "report")
    builder.add_edge(["finance", "budget", "goal", "report"], "memory")
    builder.add_edge("memory", END)
    return builder.compile()
