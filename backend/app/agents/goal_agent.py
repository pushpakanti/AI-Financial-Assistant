"""Goal agent node placeholder."""

from app.agents.state import GraphState, placeholder_output, skipped_output
from app.prompts import PromptManager


_prompt_manager = PromptManager()


def goal_agent(state: GraphState) -> dict[str, object]:
    """Return a structured placeholder for future goal-domain behavior."""
    prompt = _prompt_manager.render_agent_prompt(
        "goal", variables={"request": state.get("request", "")}
    )
    output = placeholder_output("goal") if "goal" in state.get("planned_agents", []) else skipped_output("goal")
    output["data"]["prompt"] = {"version": prompt.version, "locale": prompt.locale}
    return {"goal_result": output}
