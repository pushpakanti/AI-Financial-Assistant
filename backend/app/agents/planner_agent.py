"""Deterministic planner node used until LLM planning is introduced."""

from app.agents.state import AgentOutput, GraphState, SUPPORTED_AGENTS
from app.prompts import PromptManager


_ROUTING_KEYWORDS: dict[str, tuple[str, ...]] = {
    "finance": (
        "finance", "transaction", "income", "expense", "cash flow", "account", "balance",
        "spending", "spent", "merchant", "category",
    ),
    "budget": ("budget", "remaining budget", "budget left", "budget summary", "budget alerts", "alert"),
    "goal": ("goal", "savings goal", "prediction", "recommendation", "save", "saving", "target"),
    "report": ("dashboard", "report", "overview", "analytics"),
}
_MEMORY_KEYWORDS: tuple[str, ...] = (
    "remember",
    "risk profile",
    "risk preference",
    "salary",
    "get paid",
    "paid on",
    "prefer",
    "preference",
    "sip",
    "investing",
    "investment",
    "portfolio",
)
_TOOL_ROUTING: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("dashboard", ("dashboard", "analytics", "report", "overview"), "get"),
    ("budget", ("budget", "alert"), "summary"),
    ("transaction", ("transaction", "income", "expense", "spending", "spent", "merchant", "category", "cash flow"), "list"),
    ("account", ("account", "balance"), "list"),
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
    if not selected and any(keyword in request for keyword in _MEMORY_KEYWORDS):
        selected = []
    elif not selected:
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
        if _is_budget_spending_comparison(request) and (tool_name, action) == ("transaction", "list"):
            continue
        if any(keyword in request for keyword in keywords):
            results.append(registry.execute(tool_name, state["user_id"], action, {}))
    # A comparison needs an authoritative expense aggregate.  A paginated list
    # cannot safely stand in for total spending.
    if _is_budget_spending_comparison(request):
        results.append(registry.execute("transaction", state["user_id"], "summary", {}))
        results.append(registry.execute("dashboard", state["user_id"], "get", {}))
    return results


def _is_budget_spending_comparison(request: str) -> bool:
    """Identify requests that need transaction-derived spending plus budget totals."""
    return "budget" in request and any(
        term in request for term in ("compare", "compared", "spending", "spent", "actual")
    )
