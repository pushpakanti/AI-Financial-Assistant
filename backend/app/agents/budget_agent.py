"""Budget reasoning node backed by existing tools, prompts, and LLM gateway."""

import json
import logging
from typing import Any

from app.agents.state import AgentOutput, GraphState, skipped_output
from app.ai.providers.base import LLMProviderError
from app.prompts import PromptManager


logger = logging.getLogger(__name__)
_prompt_manager = PromptManager()


def budget_agent(state: GraphState) -> dict[str, object]:
    """Analyze user-scoped budget data and return a structured recommendation."""
    if "budget" not in state.get("planned_agents", []):
        return {"budget_result": skipped_output("budget")}

    tool_results = _budget_tool_results(state)
    context = _budget_context(tool_results)
    llm_context = _minimal_budget_context(context, state.get("request", ""))
    prompt_manager = state.get("prompt_manager") or _prompt_manager
    rendered_prompt = prompt_manager.render_agent_prompt(
        "budget", variables={"request": state.get("request", "")}
    )
    analysis_prompt = _analysis_prompt(rendered_prompt.content, llm_context)
    output_data: dict[str, Any] = {
        "raw_tool_data": tool_results,
        "budget_context": context,
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
                    "budget_result": AgentOutput(
                        agent="budget",
                        status="completed",
                        summary=response.content.strip(),
                        data=output_data,
                    ).model_dump()
                }
        except (LLMProviderError, ValueError) as error:
            logger.warning("Budget LLM generation unavailable; using deterministic fallback: %s", error)
        except Exception:  # pragma: no cover - final agent boundary protection
            logger.exception("Budget LLM generation failed; using deterministic fallback")

    output_data["llm"] = {"used": False, "fallback": "deterministic"}
    return {
        "budget_result": AgentOutput(
            agent="budget",
            status="completed",
            summary=_deterministic_summary(context),
            data=output_data,
        ).model_dump()
    }


def _budget_tool_results(state: GraphState) -> list[dict[str, Any]]:
    """Reuse successful planner results and request only missing budget actions."""
    results = [result for result in state.get("tool_results", []) if isinstance(result, dict)]
    available_actions = {
        result.get("action")
        for result in results
        if result.get("tool") == "budget" and result.get("success")
    }
    registry = state.get("tool_registry")
    if registry is None:
        return results

    for action in _budget_actions(state.get("request", "")):
        if action not in available_actions:
            results.append(registry.execute("budget", state["user_id"], action, {}))
    return results


def _budget_actions(request: str) -> tuple[str, ...]:
    """Select only the budget views necessary for the user's request."""
    normalized_request = request.casefold()
    if "overview" in normalized_request or "analysis" in normalized_request:
        return ("summary", "progress", "alerts")
    selected: list[str] = []
    if any(keyword in normalized_request for keyword in ("budget", "summary", "remaining")):
        selected.append("summary")
    if any(keyword in normalized_request for keyword in ("progress", "percentage", "spending")):
        selected.append("progress")
    if any(keyword in normalized_request for keyword in ("alert", "warning", "limit")):
        selected.append("alerts")
    return tuple(selected) or ("summary",)


def _budget_context(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build model-safe budget context from summary, progress, and alert data."""
    results_by_action = {
        result.get("action"): result.get("data")
        for result in tool_results
        if result.get("tool") == "budget" and result.get("success")
    }
    summary = results_by_action.get("summary")
    progress = results_by_action.get("progress")
    progress_items = progress if isinstance(progress, list) else None
    spending_percentage = _spending_percentage(progress_items)
    return {
        "budget_summary": summary,
        "budget_progress": progress_items,
        "active_alerts": results_by_action.get("alerts"),
        "remaining_budget": summary.get("total_remaining") if isinstance(summary, dict) else None,
        "spending_percentage": spending_percentage,
        "exceeded_budgets": [item for item in spending_percentage if _is_exceeded(item)],
    }


def _minimal_budget_context(context: dict[str, Any], request: str) -> dict[str, Any]:
    """Send summary data by default; add progress or alerts only when requested."""
    normalized_request = request.casefold()
    result = {
        "budget_summary": _minimal_summary(context.get("budget_summary")),
        "remaining_budget": context.get("remaining_budget"),
    }
    if any(keyword in normalized_request for keyword in ("progress", "percentage", "spending", "overview", "analysis")):
        result["spending_percentage"] = context.get("spending_percentage")
        result["exceeded_budgets"] = context.get("exceeded_budgets")
    if any(keyword in normalized_request for keyword in ("alert", "warning", "limit", "overview", "analysis")):
        result["active_alerts"] = _minimal_budget_items(context.get("active_alerts"))
    return result


def _minimal_summary(summary: Any) -> dict[str, Any] | None:
    """Keep aggregate budget context to the public planning facts only."""
    if not isinstance(summary, dict):
        return None
    status = {
        "active": summary.get("active_budget_count"),
        "completed": summary.get("completed_budget_count"),
        "expired": summary.get("expired_budget_count"),
    }
    return {
        "total_budget": summary.get("total_budgeted"),
        "remaining_budget": summary.get("total_remaining"),
        "budget_count": summary.get("budget_count"),
        "budget_status": {key: value for key, value in status.items() if value is not None},
    }


def _minimal_budget_items(items: Any) -> list[dict[str, Any]] | None:
    """Keep only the budget facts necessary to explain progress or alerts."""
    if not isinstance(items, list):
        return None
    fields = ("name", "amount", "spent_amount", "remaining_amount", "percentage_used", "alert_percentage", "status")
    return [{field: item.get(field) for field in fields if field in item} for item in items if isinstance(item, dict)]


def _spending_percentage(progress: list[Any] | None) -> list[dict[str, Any]]:
    """Expose only the identifiers and spending thresholds needed for recommendations."""
    if progress is None:
        return []
    return [
        {
            "name": item.get("name"),
            "percentage_used": item.get("percentage_used"),
            "alert_percentage": item.get("alert_percentage"),
        }
        for item in progress
        if isinstance(item, dict)
    ]


def _is_exceeded(budget: dict[str, Any]) -> bool:
    """Keep 100%-spent budgets distinct from budgets that have gone over their limit."""
    try:
        return float(budget.get("percentage_used")) > 100
    except (TypeError, ValueError):
        return False


def _analysis_prompt(rendered_prompt: str, context: dict[str, Any]) -> str:
    """Append trusted budget data and recommendation boundaries to the managed prompt."""
    serialized_context = json.dumps(context, ensure_ascii=False, default=str)
    return (
        f"{rendered_prompt}\n\n"
        "Use only the following user-scoped budget data. Do not invent values. "
        "Be concise: use bullets where helpful, avoid introductions and generic education, and never repeat tool data. "
        "Keep under 150 words unless the user asks to explain, detail, why, analyze, report, or recommend.\n\n"
        "All monetary values in the provided context are denominated in INR. Never change the currency "
        "or invent another symbol. Always present monetary amounts using ₹ or INR.\n\n"
        f"Budget context:\n{serialized_context}"
    )


def _deterministic_summary(context: dict[str, Any]) -> str:
    """Provide a useful budget recommendation when LLM generation is unavailable."""
    summary = context.get("budget_summary") or {}
    alerts = context.get("active_alerts")
    exceeded = context.get("exceeded_budgets") or []
    spending = context.get("spending_percentage") or []

    parts = ["Here is your budget overview from the available data."]
    if isinstance(summary, dict):
        parts.append(
            "Budgets: {count}; active: {active}; total spent: {spent}; remaining: {remaining}.".format(
                count=summary.get("budget_count", "unavailable"),
                active=summary.get("active_budget_count", "unavailable"),
                spent=summary.get("total_spent", "unavailable"),
                remaining=summary.get("total_remaining", "unavailable"),
            )
        )
    if isinstance(alerts, list):
        parts.append(f"Active budget alerts: {len(alerts)}.")
    if exceeded:
        names = ", ".join(str(item.get("name") or item.get("budget_id")) for item in exceeded)
        parts.append(f"Over-budget items: {names}. Reduce spending in these categories.")
    elif spending:
        highest = max(spending, key=lambda item: _percentage_value(item.get("percentage_used")))
        parts.append(
            "Highest budget usage: {name} at {percentage}%.".format(
                name=highest.get("name") or highest.get("budget_id") or "unavailable",
                percentage=highest.get("percentage_used", "unavailable"),
            )
        )
    if len(parts) == 1:
        parts.append("No budget records were available to analyze yet.")
    return " ".join(parts)


def _percentage_value(value: Any) -> float:
    """Order percentage values safely when a tool response is incomplete."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")
