"""Report agent node placeholder."""

from app.agents.state import GraphState, placeholder_output, skipped_output
from app.prompts import PromptManager


_prompt_manager = PromptManager()


def report_agent(state: GraphState) -> dict[str, object]:
    """Return a structured placeholder for future reporting behavior."""
    prompt = _prompt_manager.render_agent_prompt(
        "report", variables={"request": state.get("request", "")}
    )
    output = placeholder_output("report") if "report" in state.get("planned_agents", []) else skipped_output("report")
    output["data"]["prompt"] = {"version": prompt.version, "locale": prompt.locale}
    return {"report_result": output}
