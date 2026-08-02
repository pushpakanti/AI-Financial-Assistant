"""Shared typed state and structured output contracts for the LangGraph workflow."""

from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, Field


AgentName = Literal["finance", "budget", "goal", "report"]
AgentStatus = Literal["planned", "completed", "skipped"]
SUPPORTED_AGENTS: tuple[AgentName, ...] = ("finance", "budget", "goal", "report")


class AgentOutput(BaseModel):
    """Stable structured result returned by every node in the workflow."""

    agent: str
    status: AgentStatus
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)


class GraphState(TypedDict):
    """State carried across the graph; domain nodes write only their own result key."""

    request: str
    user_id: int
    tool_registry: NotRequired[Any]
    llm_gateway: NotRequired[Any]
    prompt_manager: NotRequired[Any]
    memory_manager: NotRequired[Any]
    retrieved_memories: NotRequired[list[dict[str, Any]]]
    tool_results: NotRequired[list[dict[str, Any]]]
    planned_agents: NotRequired[list[AgentName]]
    planner_result: NotRequired[dict[str, Any]]
    finance_result: NotRequired[dict[str, Any]]
    budget_result: NotRequired[dict[str, Any]]
    goal_result: NotRequired[dict[str, Any]]
    report_result: NotRequired[dict[str, Any]]
    memory_result: NotRequired[dict[str, Any]]


def skipped_output(agent: AgentName) -> dict[str, Any]:
    """Create a consistent no-op result when the planner did not select an agent."""
    return AgentOutput(
        agent=agent,
        status="skipped",
        summary=f"{agent.title()} agent was not selected for this request.",
        data={"implemented": False},
    ).model_dump()


def placeholder_output(agent: AgentName) -> dict[str, Any]:
    """Create a deterministic placeholder pending future domain and LLM implementation."""
    return AgentOutput(
        agent=agent,
        status="completed",
        summary=f"{agent.title()} agent architecture executed; domain reasoning is not implemented.",
        data={"implemented": False},
    ).model_dump()
