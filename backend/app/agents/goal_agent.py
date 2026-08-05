"""Goal reasoning node backed by existing tools, prompts, and LLM gateway."""

import json
import logging
from typing import Any

from app.agents.state import AgentOutput, GraphState, skipped_output
from app.ai.providers.base import LLMProviderError
from app.prompts import PromptManager


logger = logging.getLogger(__name__)
_prompt_manager = PromptManager()


def goal_agent(state: GraphState) -> dict[str, object]:
    """Analyze a user's financial goals and return a stable structured result."""
    if "goal" not in state.get("planned_agents", []):
        return {"goal_result": skipped_output("goal")}

    tool_results = _goal_tool_results(state)
    context = _goal_context(tool_results)
    llm_context = _minimal_goal_context(context, state.get("request", ""))
    prompt_manager = state.get("prompt_manager") or _prompt_manager
    rendered_prompt = prompt_manager.render_agent_prompt(
        "goal", variables={"request": state.get("request", "")}
    )
    analysis_prompt = _analysis_prompt(rendered_prompt.content, llm_context)
    output_data: dict[str, Any] = {
        "raw_tool_data": tool_results,
        "goal_context": context,
        "prompt": {"version": rendered_prompt.version, "locale": rendered_prompt.locale},
    }

    gateway = state.get("llm_gateway")
    if gateway is not None:
        try:
            response = gateway.generate(analysis_prompt)
            if response.content.strip():
                output_data["llm"] = {
                    "provider": response.provider,
                    "model": response.model,
                    "latency_ms": response.latency_ms,
                    "usage": response.usage,
                }
                return {
                    "goal_result": AgentOutput(
                        agent="goal",
                        status="completed",
                        summary=response.content.strip(),
                        data=output_data,
                    ).model_dump()
                }
        except (LLMProviderError, ValueError) as error:
            logger.warning("Goal LLM generation unavailable; using deterministic fallback: %s", error)
        except Exception:  # pragma: no cover - final agent boundary protection
            logger.exception("Goal LLM generation failed; using deterministic fallback")

    output_data["llm"] = {"used": False, "fallback": "deterministic"}
    return {
        "goal_result": AgentOutput(
            agent="goal",
            status="completed",
            summary=_deterministic_summary(context),
            data=output_data,
        ).model_dump()
    }


def _goal_tool_results(state: GraphState) -> list[dict[str, Any]]:
    """Reuse successful planner results and request only missing goal actions."""
    results = [result for result in state.get("tool_results", []) if isinstance(result, dict)]
    available_actions = {
        result.get("action")
        for result in results
        if result.get("tool") == "goal" and result.get("success")
    }
    registry = state.get("tool_registry")
    if registry is None:
        return results

    for action in _goal_actions(state.get("request", "")):
        if action not in available_actions:
            results.append(registry.execute("goal", state["user_id"], action, {}))
    return results


def _goal_actions(request: str) -> tuple[str, ...]:
    """Select only the goal views necessary for the user's request."""
    normalized_request = request.casefold()
    if "overview" in normalized_request or "analysis" in normalized_request:
        return ("list", "summary", "progress", "prediction", "recommendations")
    selected: list[str] = []
    if any(keyword in normalized_request for keyword in ("show", "list", "active", "completed")):
        selected.append("list")
    if any(keyword in normalized_request for keyword in ("progress", "on track", "remaining")):
        selected.append("progress")
    if any(keyword in normalized_request for keyword in ("predict", "prediction", "when", "deadline")):
        selected.append("prediction")
    if any(keyword in normalized_request for keyword in ("recommend", "advice", "prioritize")):
        selected.append("recommendations")
    if "summary" in normalized_request:
        selected.append("summary")
    return tuple(dict.fromkeys(selected)) or ("summary",)


def _goal_context(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build model-safe goal data, including status-specific goal lists."""
    results_by_action = {
        result.get("action"): result.get("data")
        for result in tool_results
        if result.get("tool") == "goal" and result.get("success")
    }
    goals = results_by_action.get("list")
    goal_list = goals if isinstance(goals, list) else None
    return {
        "active_goals": _goals_with_status(goal_list, "active"),
        "completed_goals": _goals_with_status(goal_list, "completed"),
        "goal_progress": results_by_action.get("progress"),
        "prediction": results_by_action.get("prediction"),
        "recommendations": results_by_action.get("recommendations"),
        "summary": results_by_action.get("summary"),
    }


def _goals_with_status(goals: list[Any] | None, status: str) -> list[dict[str, Any]] | None:
    """Select a status subset while retaining every public goal field from the tool."""
    if goals is None:
        return None
    return [
        goal
        for goal in goals
        if isinstance(goal, dict) and str(goal.get("status", "")).casefold() == status
    ]


def _minimal_goal_context(context: dict[str, Any], request: str) -> dict[str, Any]:
    """Remove goal audit fields while retaining goal facts used for advice."""
    normalized_request = request.casefold()
    result = {
        "goal_progress": _minimal_goals(context.get("goal_progress")),
        "prediction": _without_metadata(context.get("prediction")),
        "recommendations": _without_metadata(context.get("recommendations")),
        "summary": context.get("summary"),
    }
    if "completed" not in normalized_request or "active" in normalized_request:
        result["active_goals"] = _minimal_goals(context.get("active_goals"))
    if "active" not in normalized_request or "completed" in normalized_request:
        result["completed_goals"] = _minimal_goals(context.get("completed_goals"))
    return result


def _minimal_goals(goals: Any) -> list[dict[str, Any]] | None:
    """Keep only the goal identifiers, state, and contribution facts."""
    if not isinstance(goals, list):
        return None
    fields = (
        "title", "target_amount", "current_amount", "deadline", "priority", "status",
        "monthly_required", "remaining_amount", "percentage_complete", "days_remaining",
    )
    return [{field: goal.get(field) for field in fields if field in goal} for goal in goals if isinstance(goal, dict)]


def _without_metadata(value: Any) -> Any:
    """Remove internal identifiers and audit fields from goal prompt context."""
    excluded = {"id", "user_id", "goal_id", "created_at", "updated_at"}
    if isinstance(value, dict):
        return {key: _without_metadata(item) for key, item in value.items() if key not in excluded}
    if isinstance(value, list):
        return [_without_metadata(item) for item in value]
    return value


def _analysis_prompt(rendered_prompt: str, context: dict[str, Any]) -> str:
    """Append user-scoped goal context and explicit response boundaries to the prompt."""
    serialized_context = json.dumps(context, ensure_ascii=False, default=str)
    return (
        f"{rendered_prompt}\n\n"
        "Use only the following user-scoped goal data. Do not invent values. "
        "Be concise: use bullets where helpful, avoid introductions and generic education, and never repeat tool data. "
        "Keep under 150 words unless the user asks to explain, detail, why, analyze, report, or recommend. "
        "For on-track questions, state on track or not, summarize progress, then give 2-3 actionable next steps.\n\n"
        "All monetary values in the provided context are denominated in INR. Never change the currency "
        "or invent another symbol. Always present monetary amounts using ₹ or INR.\n\n"
        f"Goal context:\n{serialized_context}"
    )


def _deterministic_summary(context: dict[str, Any]) -> str:
    """Provide useful rule-based feedback when LLM generation is unavailable."""
    summary = context.get("summary") or {}
    active_goals = context.get("active_goals")
    completed_goals = context.get("completed_goals")
    predictions = context.get("prediction")
    recommendations = context.get("recommendations")

    parts = ["Here is your goal overview from the available data."]
    if isinstance(summary, dict):
        parts.append(
            "Goals: {total}; active: {active}; completed: {completed}; remaining: {remaining}; "
            "overall completion: {percentage}%.".format(
                total=summary.get("total_goals", "unavailable"),
                active=summary.get("active_goals", "unavailable"),
                completed=summary.get("completed_goals", "unavailable"),
                remaining=summary.get("total_remaining_amount", "unavailable"),
                percentage=summary.get("overall_completion_percentage", "unavailable"),
            )
        )
    elif isinstance(active_goals, list) or isinstance(completed_goals, list):
        parts.append(
            f"Active goals: {len(active_goals or [])}; completed goals: {len(completed_goals or [])}."
        )
    if isinstance(predictions, list):
        parts.append(f"Deadline predictions are available for {len(predictions)} goal(s).")
    if isinstance(recommendations, list):
        parts.append(f"Personalized recommendations are available for {len(recommendations)} goal(s).")
    if len(parts) == 1:
        parts.append("No goal records were available to analyze yet.")
    return " ".join(parts)
