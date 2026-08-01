"""Budget agent node placeholder."""

from app.agents.state import GraphState, placeholder_output, skipped_output
from app.prompts import PromptManager


_prompt_manager = PromptManager()


def budget_agent(state: GraphState) -> dict[str, object]:
    """Return a structured placeholder for future budget-domain behavior."""
    prompt = _prompt_manager.render_agent_prompt(
        "budget", variables={"request": state.get("request", "")}
    )
    output = placeholder_output("budget") if "budget" in state.get("planned_agents", []) else skipped_output("budget")
    output["data"]["prompt"] = {"version": prompt.version, "locale": prompt.locale}
    return {"budget_result": output}
