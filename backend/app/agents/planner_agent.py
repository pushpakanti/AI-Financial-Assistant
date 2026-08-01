"""Deterministic planner node used until LLM planning is introduced."""

from app.agents.state import AgentOutput, GraphState, SUPPORTED_AGENTS
from app.prompts import PromptManager


_ROUTING_KEYWORDS: dict[str, tuple[str, ...]] = {
    "finance": ("finance", "transaction", "income", "expense", "cash flow", "account"),
    "budget": ("budget", "spend", "spending", "alert"),
    "goal": ("goal", "save", "saving", "target"),
    "report": ("report", "summary", "analytics", "dashboard"),
}
_TOOL_ROUTING: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("dashboard", ("dashboard", "analytics"), "get"),
    ("budget", ("budget", "alert"), "summary"),
    ("transaction", ("transaction", "income", "expense"), "list"),
    ("account", ("account",), "list"),
    ("goal", ("goal",), "get"),
)
_prompt_manager = PromptManager()


def planner_agent(state: GraphState) -> dict[str, object]:
    """Select relevant domain agents with transparent keyword routing only."""
    raw_request = state.get("request", "")
    prompt = _prompt_manager.render_agent_prompt("planner", variables={"request": raw_request})
    request = raw_request.casefold()
    selected = [
        agent
        for agent in SUPPORTED_AGENTS
        if any(keyword in request for keyword in _ROUTING_KEYWORDS[agent])
    ]
    if not selected:
        selected = list(SUPPORTED_AGENTS)
    tool_results = _invoke_tools(state, request)
    result = AgentOutput(
        agent="planner",
        status="planned",
        summary="Deterministic routing completed; no LLM reasoning was used.",
        data={
            "selected_agents": selected,
            "routing_mode": "keyword",
            "tool_results": tool_results,
            "prompt": {"version": prompt.version, "locale": prompt.locale},
        },
    )
    return {
        "planned_agents": selected,
        "planner_result": result.model_dump(),
        "tool_results": tool_results,
    }


def _invoke_tools(state: GraphState, request: str) -> list[dict[str, object]]:
    """Invoke only registered tools; the planner never reaches into persistence directly."""
    registry = state.get("tool_registry")
    if registry is None:
        return []
    results: list[dict[str, object]] = []
    for tool_name, keywords, action in _TOOL_ROUTING:
        if any(keyword in request for keyword in keywords):
            results.append(registry.execute(tool_name, state["user_id"], action, {}))
    return results
