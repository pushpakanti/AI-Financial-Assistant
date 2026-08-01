"""Finance agent node placeholder."""

from app.agents.state import GraphState, placeholder_output, skipped_output
from app.prompts import PromptManager


_prompt_manager = PromptManager()


def finance_agent(state: GraphState) -> dict[str, object]:
    """Return a structured placeholder for future finance-domain behavior."""
    prompt = _prompt_manager.render_agent_prompt(
        "finance", variables={"request": state.get("request", "")}
    )
    output = placeholder_output("finance") if "finance" in state.get("planned_agents", []) else skipped_output("finance")
    output["data"]["prompt"] = {"version": prompt.version, "locale": prompt.locale}
    return {"finance_result": output}
