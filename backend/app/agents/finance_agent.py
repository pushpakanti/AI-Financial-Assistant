"""Finance reasoning node backed by existing tools, prompts, and LLM gateway."""

import json
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.agents.state import AgentOutput, GraphState, skipped_output
from app.ai.providers.base import LLMProviderError
from app.prompts import PromptManager


logger = logging.getLogger(__name__)
_prompt_manager = PromptManager()
_FINANCE_KEYWORDS: dict[tuple[str, str], tuple[str, ...]] = {
    ("transaction", "list"): (
        "transaction", "income", "expense", "cash flow", "spending", "spent", "merchant", "category",
    ),
    ("account", "list"): ("account", "balance"),
    ("dashboard", "get"): ("overview", "summary", "analytics", "financial status"),
}


def finance_agent(state: GraphState) -> dict[str, object]:
    """Analyze user-scoped financial data and return a stable structured result."""
    if "finance" not in state.get("planned_agents", []):
        return {"finance_result": skipped_output("finance")}

    tool_results = _finance_tool_results(state)
    context = _finance_context(tool_results)
    llm_context = _minimal_finance_context(context, state.get("request", ""))
    prompt_manager = state.get("prompt_manager") or _prompt_manager
    rendered_prompt = prompt_manager.render_agent_prompt(
        "finance", variables={"request": state.get("request", "")}
    )
    analysis_prompt = _analysis_prompt(rendered_prompt.content, llm_context)

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
    """Reuse planner output and request only inputs relevant to this finance request."""
    results = [result for result in state.get("tool_results", []) if isinstance(result, dict)]
    available_results = {
        (result.get("tool"), result.get("action"))
        for result in results
        if result.get("success")
    }
    registry = state.get("tool_registry")
    if registry is None:
        return results

    for tool_name, action in _finance_tool_actions(state.get("request", "")):
        if (tool_name, action) not in available_results:
            results.append(registry.execute(tool_name, state["user_id"], action, {}))
    return results


def _finance_tool_actions(request: str) -> tuple[tuple[str, str], ...]:
    """Select the smallest finance data set that can answer the requested question."""
    normalized_request = request.casefold()
    selected = tuple(
        tool_action
        for tool_action, keywords in _FINANCE_KEYWORDS.items()
        if any(keyword in normalized_request for keyword in keywords)
    )
    if _is_budget_spending_comparison(normalized_request):
        selected = tuple(action for action in selected if action != ("transaction", "list"))
        return tuple(dict.fromkeys((*selected, ("transaction", "summary"), ("dashboard", "get"))))
    return selected or (("dashboard", "get"),)


def _is_budget_spending_comparison(request: str) -> bool:
    return "budget" in request and any(
        term in request for term in ("compare", "compared", "spending", "spent", "actual")
    )


def _finance_context(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract one structured, model-safe financial context from raw tool envelopes."""
    context: dict[str, Any] = {
        "transactions": None,
        "transaction_summary": None,
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
        if result.get("tool") == "transaction" and result.get("action") == "summary":
            if result.get("success") and context["transaction_summary"] is None:
                context["transaction_summary"] = result.get("data")
        elif context_key is not None and result.get("success") and context[context_key] is None:
            context[context_key] = result.get("data")
    return context


def _minimal_finance_context(context: dict[str, Any], request: str) -> dict[str, Any]:
    """Reduce tool payloads to the data needed by Gemini for this request."""
    normalized_request = request.casefold()
    result = {
        "transactions": _minimal_transactions(context.get("transactions"), normalized_request),
        "transaction_summary": _minimal_transaction_summary(context.get("transaction_summary")),
        "accounts": _minimal_accounts(context.get("accounts")),
        "budgets": _minimal_budget_summary(context.get("budgets")),
        "dashboard": _minimal_dashboard(context.get("dashboard"), normalized_request),
    }
    comparison = _budget_spending_comparison(context, normalized_request)
    if comparison is not None:
        # This is the only comparison source supplied to the model: actual
        # spending is always transaction-derived, never a budget aggregate.
        result["budget_spending_comparison"] = comparison
    return result


def _minimal_transactions(data: Any, request: str) -> dict[str, Any] | None:
    """Keep transaction facts, omitting audit and unrelated detail fields by default."""
    if not isinstance(data, dict):
        return None
    fields = ("title", "amount", "transaction_type", "transaction_date", "merchant")
    requested_fields = {
        "description": ("description", "detail", "note"),
        "payment_method": ("payment method", "paid with"),
        "location": ("location", "where"),
        "tags": ("tag",),
    }
    fields += tuple(field for field, keywords in requested_fields.items() if any(keyword in request for keyword in keywords))
    items = data.get("items")
    return {
        "total": data.get("total"),
        "transactions": [
            {field: item.get(field) for field in fields if field in item}
            for item in items[:10]
            if isinstance(item, dict)
        ] if isinstance(items, list) else None,
    }


def _minimal_accounts(data: Any) -> list[dict[str, Any]] | None:
    """Expose only account fields relevant to financial answers."""
    if not isinstance(data, list):
        return None
    fields = ("name", "account_type", "balance", "currency")
    return [{field: account.get(field) for field in fields if field in account} for account in data if isinstance(account, dict)]


def _minimal_budget_summary(data: Any) -> dict[str, Any] | None:
    """Keep budget totals compact when another agent already retrieved them."""
    if not isinstance(data, dict):
        return None
    total_budget = data.get("total_budgeted")
    total_remaining = data.get("total_remaining")
    status = {
        "active": data.get("active_budget_count"),
        "completed": data.get("completed_budget_count"),
        "expired": data.get("expired_budget_count"),
    }
    return {
        "total_budget": total_budget,
        "remaining_budget": total_remaining,
        "budget_count": data.get("budget_count"),
        "budget_status": {key: value for key, value in status.items() if value is not None},
    }


def _minimal_transaction_summary(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    fields = ("transaction_count", "total_income", "total_expense", "total_transfer", "net_cash_flow")
    return {field: data.get(field) for field in fields if field in data}


def _budget_spending_comparison(context: dict[str, Any], request: str) -> dict[str, Any] | None:
    """Construct authoritative comparison facts without deriving spending from budgets."""
    if "budget" not in request or not any(term in request for term in ("compare", "compared", "spending", "spent", "actual")):
        return None
    transactions = context.get("transaction_summary")
    budgets = context.get("budgets")
    if not isinstance(transactions, dict) or not isinstance(budgets, dict):
        return None
    total_budget = _decimal(budgets.get("total_budgeted"))
    actual_spending = _decimal(transactions.get("total_expense"))
    if total_budget is None or actual_spending is None:
        return None
    remaining = _decimal(budgets.get("total_remaining"))
    utilization = (actual_spending / total_budget * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) if total_budget else None
    result: dict[str, Any] = {
        "total_budget": total_budget,
        "actual_spending": actual_spending,
        "remaining_budget": remaining,
        "budget_utilization_percent": utilization,
        "transaction_count": transactions.get("transaction_count"),
        "largest_expense": _largest_expense(context.get("dashboard")),
    }
    # A budget's remaining value is a reconciliation signal only.  It must not
    # be relabelled as actual spending.  A mismatch can be caused by
    # uncategorized transactions or a stale budget calculation.
    if remaining is not None and total_budget - remaining != actual_spending:
        result["consistency_note"] = (
            "Budget totals do not reconcile with transaction-derived spending. "
            "Transactions may be uncategorized for tracked budgets, or budget calculations may be stale."
        )
    return {key: value for key, value in result.items() if value is not None}


def _largest_expense(dashboard: Any) -> dict[str, Any] | None:
    activity = dashboard.get("recent_activity") if isinstance(dashboard, dict) else None
    expense = activity.get("largest_expense") if isinstance(activity, dict) else None
    if not isinstance(expense, dict):
        return None
    return {field: expense.get(field) for field in ("title", "amount", "transaction_date", "merchant", "category_name") if field in expense}


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _minimal_dashboard(data: Any, request: str) -> dict[str, Any] | None:
    """Use dashboard overview fields unless charts or history are explicitly requested."""
    if not isinstance(data, dict):
        return None
    activity = data.get("recent_activity") if isinstance(data.get("recent_activity"), dict) else {}
    statistics = data.get("statistics") if isinstance(data.get("statistics"), dict) else {}
    result: dict[str, Any] = {
        "user_summary": data.get("user_summary"),
        "recent_activity": _minimal_activity(activity.get("recent_transactions")),
        "highest_spending_category": _without_metadata(statistics.get("highest_spending_category")),
        "highest_spending_merchant": _without_metadata(statistics.get("highest_spending_merchant")),
    }
    if any(keyword in request for keyword in ("chart", "trend", "analytics", "historical", "history")):
        result["charts"] = _without_metadata(data.get("charts"))
    return result


def _minimal_activity(items: Any) -> list[dict[str, Any]] | None:
    """Keep recent activity useful without serializing dashboard audit metadata."""
    if not isinstance(items, list):
        return None
    fields = ("title", "amount", "transaction_type", "transaction_date", "category_name", "merchant")
    return [{field: item.get(field) for field in fields if field in item} for item in items[:5] if isinstance(item, dict)]


def _without_metadata(value: Any) -> Any:
    """Remove identifiers, audit fields, and receipts from nested LLM context."""
    excluded = {"id", "user_id", "account_id", "category_id", "budget_id", "goal_id", "created_at", "updated_at", "receipt_url"}
    if isinstance(value, dict):
        return {key: _without_metadata(item) for key, item in value.items() if key not in excluded}
    if isinstance(value, list):
        return [_without_metadata(item) for item in value]
    return value


def _analysis_prompt(rendered_prompt: str, context: dict[str, Any]) -> str:
    """Append trusted tool data and concise output instructions to the managed prompt."""
    serialized_context = json.dumps(context, ensure_ascii=False, default=str)
    return (
        f"{rendered_prompt}\n\n"
        "Use only the following user-scoped financial context. Do not invent values. "
        "For budget-spending comparisons, use budget_spending_comparison exactly: actual_spending is computed only from transactions; never use budget fields as spending. "
        "If it includes a consistency_note, state it plainly without guessing a cause. "
        "Be concise: use bullets where helpful, avoid introductions and generic education, and never repeat tool data. "
        "Keep under 150 words unless the user asks to explain, detail, why, analyze, report, or recommend.\n\n"
        "All monetary values in the provided context are denominated in INR. Never change the currency "
        "or invent another symbol. Always present monetary amounts using ₹ or INR.\n\n"
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
