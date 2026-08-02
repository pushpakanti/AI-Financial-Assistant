"""Financial report node backed by existing tools, prompts, and LLM gateway."""

import json
import logging
from typing import Any

from app.agents.state import AgentOutput, GraphState, skipped_output
from app.ai.providers.base import LLMProviderError
from app.prompts import PromptManager


logger = logging.getLogger(__name__)
_prompt_manager = PromptManager()
_REPORT_TOOL_ACTIONS: tuple[tuple[str, str], ...] = (("dashboard", "get"), ("budget", "summary"))


def report_agent(state: GraphState) -> dict[str, object]:
    """Create a user-scoped financial report with an LLM or deterministic fallback."""
    if "report" not in state.get("planned_agents", []):
        return {"report_result": skipped_output("report")}

    tool_results = _report_tool_results(state)
    context = _report_context(tool_results)
    prompt_manager = state.get("prompt_manager") or _prompt_manager
    rendered_prompt = prompt_manager.render_agent_prompt(
        "report", variables={"request": state.get("request", "")}
    )
    analysis_prompt = _analysis_prompt(rendered_prompt.content, context)
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

    for tool_name, action in _REPORT_TOOL_ACTIONS:
        if (tool_name, action) not in available_results:
            results.append(registry.execute(tool_name, state["user_id"], action, {}))
    return results


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
        "budget_overview": budget_overview,
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


def _analysis_prompt(rendered_prompt: str, context: dict[str, Any]) -> str:
    """Append trusted reporting data and explicit analysis boundaries to the prompt."""
    serialized_context = json.dumps(context, ensure_ascii=False, default=str)
    return (
        f"{rendered_prompt}\n\n"
        "Use only the following user-scoped financial report context. Do not invent values. "
        "Write a concise report with practical insights and clearly note unavailable data.\n\n"
        f"Report context:\n{serialized_context}"
    )


def _deterministic_summary(context: dict[str, Any]) -> str:
    """Create a useful report when no configured LLM can return one."""
    dashboard_summary = context.get("dashboard_summary") or {}
    cash_flow = context.get("income_vs_expense") or {}
    savings = context.get("savings_metrics") or {}
    recent_activity = context.get("recent_activity")
    largest_expense = context.get("largest_expense")
    largest_income = context.get("largest_income")
    budget = context.get("budget_overview") or {}

    parts = ["Here is your financial report from the available data."]
    if isinstance(cash_flow, dict) and any(value is not None for value in cash_flow.values()):
        parts.append(
            "Monthly income: {income}; expenses: {expense}; net cash flow: {cash_flow}.".format(
                income=cash_flow.get("monthly_income", "unavailable"),
                expense=cash_flow.get("monthly_expense", "unavailable"),
                cash_flow=cash_flow.get("net_cash_flow", "unavailable"),
            )
        )
    if isinstance(dashboard_summary, dict):
        parts.append(f"Total account balance: {dashboard_summary.get('total_balance', 'unavailable')}.")
    if isinstance(savings, dict):
        parts.append(f"Savings rate: {savings.get('savings_rate', 'unavailable')}%.")
    if isinstance(recent_activity, list):
        parts.append(f"Recent transactions available: {len(recent_activity)}.")
    if isinstance(largest_income, dict):
        parts.append(f"Largest income: {largest_income.get('title', 'unavailable')} ({largest_income.get('amount', 'unavailable')}).")
    if isinstance(largest_expense, dict):
        parts.append(f"Largest expense: {largest_expense.get('title', 'unavailable')} ({largest_expense.get('amount', 'unavailable')}).")
    if isinstance(budget, dict):
        parts.append(
            "Budget overview: {active} active, {remaining} remaining.".format(
                active=budget.get("active_budget_count", "unavailable"),
                remaining=budget.get("total_remaining", "unavailable"),
            )
        )
    if len(parts) == 1:
        parts.append("No dashboard or budget records were available to analyze yet.")
    return " ".join(parts)
