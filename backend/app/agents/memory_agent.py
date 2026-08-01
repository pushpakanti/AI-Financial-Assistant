"""Memory agent node placeholder; it aggregates graph output but persists nothing."""

from app.agents.state import AgentOutput, GraphState, SUPPORTED_AGENTS
from app.prompts import PromptManager


_prompt_manager = PromptManager()


def memory_agent(state: GraphState) -> dict[str, object]:
    """Aggregate structured agent results without adding memory storage or AI behavior."""
    prompt = _prompt_manager.render_agent_prompt(
        "memory", variables={"request": state.get("request", "")}
    )
    result_keys = {agent: f"{agent}_result" for agent in SUPPORTED_AGENTS}
    completed_agents = [
        agent
        for agent, key in result_keys.items()
        if state.get(key, {}).get("status") == "completed"
    ]
    output = AgentOutput(
        agent="memory",
        status="completed",
        summary="Workflow results aggregated; persistence is intentionally not implemented.",
        data={
            "completed_agents": completed_agents,
            "persistence_enabled": False,
            "prompt": {"version": prompt.version, "locale": prompt.locale},
        },
    )
    return {"memory_result": output.model_dump()}
