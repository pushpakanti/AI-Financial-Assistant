"""Financial report node backed by existing tools, prompts, and LLM gateway."""

import json
import logging
from typing import Any

from app.agents.state import AgentOutput, GraphState, skipped_output
from app.ai.providers.base import LLMProviderError
from app.prompts import PromptManager


logger = logging.getLogger(__name__)
_prompt_manager = PromptManager()


def report_agent(state: GraphState) -> dict[str, object]:
    """Create a user-scoped financial report with an LLM or deterministic fallback."""
    if "report" not in state.get("planned_agents", []):
        return {"report_result": skipped_output("report")}

    tool_results = _report_tool_results(state)
    context = _report_context(tool_results)
    llm_context = _minimal_report_context(context, state.get("request", ""))
    prompt_manager = state.get("prompt_manager") or _prompt_manager
    rendered_prompt = prompt_manager.render_agent_prompt(
        "report", variables={"request": state.get("request", "")}
    )
    analysis_prompt = _analysis_prompt(rendered_prompt.content, llm_context)
    output_data: dict[str, Any] = {
        "raw_tool_data": tool_results,
        "report_context": context,
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
                    "report_result": AgentOutput(
                        agent="report",
                        status="completed",
                        summary=response.content.strip(),
                        data=output_data,
                    ).model_dump()
                }
        except (LLMProviderError, ValueError) as error:
            logger.warning("Report LLM generation unavailable; using deterministic fallback: %s", error)
        except Exception:  # pragma: no cover - final agent boundary protection
            logger.exception("Report LLM generation failed; using deterministic fallback")

    output_data["llm"] = {"used": False, "fallback": "deterministic"}
    return {
        "report_result": AgentOutput(
            agent="report",
            status="completed",
            summary=_deterministic_summary(context),
            data=output_data,
        ).model_dump()
    }


def _report_tool_results(state: GraphState) -> list[dict[str, Any]]:
    """Reuse successful planner data and request only missing report inputs."""
    results = [result for result in state.get("tool_results", []) if isinstance(result, dict)]
    available_results = {
        (result.get("tool"), result.get("action"))
        for result in results
        if result.get("success")
    }
    registry = state.get("tool_registry")
    if registry is None:
        return results

    for tool_name, action in _report_tool_actions(state.get("request", ""), available_results):
        if (tool_name, action) not in available_results:
            results.append(registry.execute(tool_name, state["user_id"], action, {}))
    return results


def _report_tool_actions(
    request: str, available_results: set[tuple[Any, Any]]
) -> tuple[tuple[str, str], ...]:
    """Always obtain the dashboard and include budget totals only when relevant or available."""
    actions: list[tuple[str, str]] = [("dashboard", "get")]
    if "budget" in request.casefold() or ("budget", "summary") in available_results:
        actions.append(("budget", "summary"))
    return tuple(actions)


def _report_context(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract a concise reporting view from dashboard and optional budget data."""
    results_by_tool_action = {
        (result.get("tool"), result.get("action")): result.get("data")
        for result in tool_results
        if result.get("success")
    }
    dashboard = results_by_tool_action.get(("dashboard", "get"))
    budget_overview = results_by_tool_action.get(("budget", "summary"))
    dashboard = dashboard if isinstance(dashboard, dict) else {}
    charts = dashboard.get("charts", {}) if isinstance(dashboard.get("charts"), dict) else {}
    activity = dashboard.get("recent_activity", {}) if isinstance(dashboard.get("recent_activity"), dict) else {}

    return {
        "dashboard_summary": dashboard.get("user_summary"),
        "income_vs_expense": _income_vs_expense(dashboard.get("user_summary")),
        "monthly_trends": charts.get("monthly_income_vs_expense"),
        "spending_by_category": charts.get("expense_by_category"),
        "spending_by_merchant": charts.get("expense_by_merchant"),
        "recent_activity": activity.get("recent_transactions"),
        "savings_metrics": dashboard.get("statistics"),
        "largest_income": activity.get("largest_income"),
        "largest_expense": activity.get("largest_expense"),
        "budget_overview": budget_overview or _dashboard_budget_overview(
            dashboard.get("user_summary"), charts.get("budget_progress"), activity.get("upcoming_budget_alerts")
        ),
    }


def _income_vs_expense(summary: Any) -> dict[str, Any] | None:
    """Expose the current cash-flow comparison without duplicating dashboard logic."""
    if not isinstance(summary, dict):
        return None
    return {
        "monthly_income": summary.get("monthly_income"),
        "monthly_expense": summary.get("monthly_expense"),
        "net_cash_flow": summary.get("net_cash_flow"),
    }


def _dashboard_budget_overview(
    summary: Any, progress: Any, alerts: Any
) -> dict[str, Any] | None:
    """Build a compact budget overview from dashboard data when no budget tool ran."""
    if not isinstance(summary, dict) and not isinstance(progress, list) and not isinstance(alerts, list):
        return None
    progress_items = [item for item in progress if isinstance(item, dict)] if isinstance(progress, list) else []
    result: dict[str, Any] = {
        "active_budget_count": summary.get("active_budgets") if isinstance(summary, dict) else None,
        "budget_alerts": summary.get("budget_alerts") if isinstance(summary, dict) else None,
        "budget_count": len(progress_items) if progress_items else None,
    }
    if result["budget_alerts"] is None and isinstance(alerts, list):
        result["budget_alerts"] = len(alerts)
    return {key: value for key, value in result.items() if value is not None} or None


def _minimal_report_context(context: dict[str, Any], request: str) -> dict[str, Any]:
    """Keep dashboard overviews compact unless a report explicitly needs history."""
    normalized_request = request.casefold()
    result = {
        "dashboard_summary": context.get("dashboard_summary"),
        "recent_activity": _minimal_activity(context.get("recent_activity")),
        "highest_spending_category": _without_metadata(_highest_spending(context.get("spending_by_category"))),
        "highest_spending_merchant": _without_metadata(_highest_spending(context.get("spending_by_merchant"))),
        "largest_income": _minimal_transaction(context.get("largest_income")),
        "largest_expense": _minimal_transaction(context.get("largest_expense")),
        "budget_overview": _minimal_budget_overview(context.get("budget_overview")),
    }
    if any(keyword in normalized_request for keyword in ("chart", "trend", "analytics", "historical", "history")):
        result["income_vs_expense"] = context.get("income_vs_expense")
        result["monthly_trends"] = _without_metadata(context.get("monthly_trends"))
        result["spending_by_category"] = _without_metadata(context.get("spending_by_category"))
        result["spending_by_merchant"] = _without_metadata(context.get("spending_by_merchant"))
        result["savings_metrics"] = context.get("savings_metrics")
    return result


def _minimal_budget_overview(value: Any) -> dict[str, Any] | None:
    """Avoid passing budget-spend aggregates where transaction facts are required."""
    if not isinstance(value, dict):
        return None
    status = {
        "active": value.get("active_budget_count"),
        "completed": value.get("completed_budget_count"),
        "expired": value.get("expired_budget_count"),
    }
    result = {
        "total_budget": value.get("total_budgeted"),
        "remaining_budget": value.get("total_remaining"),
        "budget_count": value.get("budget_count"),
        "budget_status": {key: item for key, item in status.items() if item is not None},
    }
    return {key: item for key, item in result.items() if item is not None} or None


def _highest_spending(items: Any) -> dict[str, Any] | None:
    """Return one leading category or merchant rather than a complete chart series."""
    if not isinstance(items, list):
        return None
    rows = [item for item in items if isinstance(item, dict)]
    if not rows:
        return None
    return max(rows, key=lambda item: _amount_value(item.get("amount")))


def _amount_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")


def _minimal_activity(items: Any) -> list[dict[str, Any]] | None:
    """Exclude activity audit timestamps from the report prompt."""
    if not isinstance(items, list):
        return None
    fields = ("title", "amount", "transaction_type", "transaction_date", "category_name", "merchant")
    return [{field: item.get(field) for field in fields if field in item} for item in items[:5] if isinstance(item, dict)]


def _minimal_transaction(item: Any) -> dict[str, Any] | None:
    """Return a compact transaction while preserving the report context shape."""
    if not isinstance(item, dict):
        return None
    fields = ("title", "amount", "transaction_type", "transaction_date", "category_name", "merchant")
    return {field: item.get(field) for field in fields if field in item}


def _without_metadata(value: Any) -> Any:
    """Remove identifiers and audit fields from report-only prompt context."""
    excluded = {"id", "user_id", "account_id", "category_id", "budget_id", "created_at", "updated_at", "receipt_url"}
    if isinstance(value, dict):
        return {key: _without_metadata(item) for key, item in value.items() if key not in excluded}
    if isinstance(value, list):
        return [_without_metadata(item) for item in value]
    return value


def _analysis_prompt(rendered_prompt: str, context: dict[str, Any]) -> str:
    """Append trusted reporting data and explicit analysis boundaries to the prompt."""
    serialized_context = json.dumps(context, ensure_ascii=False, default=str)
    return (
        f"{rendered_prompt}\n\n"
        "Use only the following user-scoped financial report context. Do not invent values. "
        "Write one short summary and at most two concise bullet insights, including a practical recommendation when supported; do not repeat summary values. "
        "Avoid introductions and generic education; keep under 150 words unless the user asks to explain, detail, why, analyze, report, or recommend. "
        "Treat dashboard budget fields as available budget data and never call them unavailable.\n\n"
        "All monetary values in the provided context are denominated in INR. Never change the currency "
        "or invent another symbol. Always present monetary amounts using ₹ or INR.\n\n"
        f"Report context:\n{serialized_context}"
    )


def _deterministic_summary(context: dict[str, Any]) -> str:
    """Create a useful report when no configured LLM can return one."""
    dashboard_summary = context.get("dashboard_summary") or {}
    cash_flow = context.get("income_vs_expense") or {}
    largest_expense = context.get("largest_expense")
    budget = context.get("budget_overview") or {}

    parts: list[str] = []
    if isinstance(cash_flow, dict) and any(value is not None for value in cash_flow.values()):
        parts.append(
            "Financial summary: balance {balance}; monthly cash flow {cash_flow} "
            "({income} income, {expense} expenses).".format(
                balance=_inr(dashboard_summary.get("total_balance")),
                income=_inr(cash_flow.get("monthly_income")),
                expense=_inr(cash_flow.get("monthly_expense")),
                cash_flow=_inr(cash_flow.get("net_cash_flow")),
            )
        )
    elif isinstance(dashboard_summary, dict):
        parts.append(f"Financial summary: balance {_inr(dashboard_summary.get('total_balance'))}.")
    if isinstance(budget, dict):
        budget_detail = f"{budget.get('active_budget_count', 0)} active"
        if budget.get("total_remaining") is not None:
            budget_detail += f", {_inr(budget['total_remaining'])} remaining"
        if budget.get("budget_alerts") is not None:
            budget_detail += f", {budget['budget_alerts']} alerts"
        parts.append(f"- Budget: {budget_detail}.")
    if isinstance(largest_expense, dict):
        parts.append(f"- Review {largest_expense.get('title', 'your highest expense')} ({_inr(largest_expense.get('amount'))}).")
    if not parts:
        parts.append("No dashboard or budget records were available to analyze yet.")
    return "\n".join(parts[:3])


def _inr(value: Any) -> str:
    """Format available monetary values consistently for deterministic reports."""
    return f"₹{value}" if value is not None else "unavailable"
