"""Finance reasoning node backed by existing tools, prompts, and LLM gateway."""

import json
import logging
from typing import Any

from app.agents.state import AgentOutput, GraphState, skipped_output
from app.ai.providers.base import LLMProviderError
from app.prompts import PromptManager


logger = logging.getLogger(__name__)
_prompt_manager = PromptManager()
_FINANCE_TOOL_ACTIONS: tuple[tuple[str, str], ...] = (
    ("transaction", "list"),
    ("account", "list"),
    ("budget", "summary"),
    ("dashboard", "get"),
)


def finance_agent(state: GraphState) -> dict[str, object]:
    """Analyze user-scoped financial data and return a stable structured result."""
    if "finance" not in state.get("planned_agents", []):
        return {"finance_result": skipped_output("finance")}

    tool_results = _finance_tool_results(state)
    context = _finance_context(tool_results)
    prompt_manager = state.get("prompt_manager") or _prompt_manager
    rendered_prompt = prompt_manager.render_agent_prompt(
        "finance", variables={"request": state.get("request", "")}
    )
    analysis_prompt = _analysis_prompt(rendered_prompt.content, context)

    output_data: dict[str, Any] = {
        "raw_tool_data": tool_results,
        "finance_context": context,
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
                    "finance_result": AgentOutput(
                        agent="finance",
                        status="completed",
                        summary=response.content.strip(),
                        data=output_data,
                    ).model_dump()
                }
        except (LLMProviderError, ValueError) as error:
            logger.warning("Finance LLM generation unavailable; using deterministic fallback: %s", error)
        except Exception:  # pragma: no cover - final agent boundary protection
            logger.exception("Finance LLM generation failed; using deterministic fallback")

    output_data["llm"] = {"used": False, "fallback": "deterministic"}
    return {
        "finance_result": AgentOutput(
            agent="finance",
            status="completed",
            summary=_deterministic_summary(context),
            data=output_data,
        ).model_dump()
    }


def _finance_tool_results(state: GraphState) -> list[dict[str, Any]]:
    """Reuse planner output and request only finance inputs it did not provide."""
    results = [result for result in state.get("tool_results", []) if isinstance(result, dict)]
    present_tools = {result.get("tool") for result in results}
    registry = state.get("tool_registry")
    if registry is None:
        return results

    for tool_name, action in _FINANCE_TOOL_ACTIONS:
        if tool_name not in present_tools:
            results.append(registry.execute(tool_name, state["user_id"], action, {}))
    return results


def _finance_context(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract one structured, model-safe financial context from raw tool envelopes."""
    context: dict[str, Any] = {
        "transactions": None,
        "accounts": None,
        "budgets": None,
        "dashboard": None,
    }
    context_key_by_tool = {
        "transaction": "transactions",
        "account": "accounts",
        "budget": "budgets",
        "dashboard": "dashboard",
    }
    for result in tool_results:
        context_key = context_key_by_tool.get(result.get("tool"))
        if context_key is not None and result.get("success") and context[context_key] is None:
            context[context_key] = result.get("data")
    return context


def _analysis_prompt(rendered_prompt: str, context: dict[str, Any]) -> str:
    """Append trusted tool data and concise output instructions to the managed prompt."""
    serialized_context = json.dumps(context, ensure_ascii=False, default=str)
    return (
        f"{rendered_prompt}\n\n"
        "Use only the following user-scoped financial context. Do not invent values. "
        "Give a concise, practical answer and clearly note when data is unavailable.\n\n"
        f"Financial context:\n{serialized_context}"
    )


def _deterministic_summary(context: dict[str, Any]) -> str:
    """Provide a useful answer when no configured LLM can return one."""
    dashboard = context.get("dashboard") or {}
    dashboard_summary = dashboard.get("user_summary", {}) if isinstance(dashboard, dict) else {}
    transactions = context.get("transactions") or {}
    accounts = context.get("accounts") or []
    budgets = context.get("budgets") or {}

    parts = ["Here is your financial overview from the available data."]
    if dashboard_summary:
        parts.append(
            "Current balance: {balance}; monthly income: {income}; monthly expenses: {expense}; "
            "net cash flow: {cash_flow}.".format(
                balance=dashboard_summary.get("total_balance", "unavailable"),
                income=dashboard_summary.get("monthly_income", "unavailable"),
                expense=dashboard_summary.get("monthly_expense", "unavailable"),
                cash_flow=dashboard_summary.get("net_cash_flow", "unavailable"),
            )
        )
    if isinstance(transactions, dict):
        parts.append(f"Transactions available for review: {transactions.get('total', 'unavailable')}.")
    if isinstance(accounts, list):
        parts.append(f"Accounts available for review: {len(accounts)}.")
    if isinstance(budgets, dict):
        parts.append(
            "Active budgets: {count}; total remaining: {remaining}.".format(
                count=budgets.get("active_budget_count", "unavailable"),
                remaining=budgets.get("total_remaining", "unavailable"),
            )
        )
    if len(parts) == 1:
        parts.append("No financial records were available to analyze yet.")
    return " ".join(parts)
