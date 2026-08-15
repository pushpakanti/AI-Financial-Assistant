"""Finance reasoning node backed by existing tools, prompts, and LLM gateway."""

import json
import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.agents.state import AgentOutput, GraphState, skipped_output
from app.ai.providers.base import LLMProviderError
from app.memory.memory_models import MemoryType
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

    mutation = state.get("mutation")
    if isinstance(mutation, dict):
        return _handle_mutation(state, mutation)

    tool_results = _finance_tool_results(state)
    context = _finance_context(tool_results)
    
    request = state.get("request", "")
    is_affordability = _is_affordability_question(request)
    if is_affordability:
        analysis = _calculate_affordability(request, context)
        context["affordability_analysis"] = analysis

    prompt_manager = state.get("prompt_manager") or _prompt_manager
    rendered_prompt = prompt_manager.render_agent_prompt(
        "finance", variables={"request": request}
    )

    if is_affordability and not context["affordability_analysis"].get("has_amount"):
        output_data = {
            "raw_tool_data": tool_results,
            "finance_context": context,
            "prompt": {"version": rendered_prompt.version, "locale": rendered_prompt.locale},
        }
        return {
            "finance_result": AgentOutput(
                agent="finance",
                status="completed",
                summary="To check if you can afford this purchase, please tell me the amount you're planning to spend.",
                data=output_data,
            ).model_dump()
        }

    llm_context = _minimal_finance_context(context, request)
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


_PENDING_OPERATION_KEY = "pending_financial_operation"


def _handle_mutation(state: GraphState, mutation: dict[str, Any]) -> dict[str, object]:
    """Persist, cancel, or execute only a planner-validated mutation intent."""
    status = mutation.get("status")
    if status == "confirmation_required":
        _save_pending(state, mutation)
        account = mutation["account"]
        amount = _money(mutation["amount"])
        balance = Decimal(str(account["balance"]))
        action = "withdraw" if mutation.get("operation") == "withdrawal" else "record"
        summary = (
            f"You want to {action} {amount} "
            f"{'from' if action == 'withdraw' else 'as an expense from'} {account['name']}.\n\n"
            f"Current balance: {_money(balance)}\n"
            f"Balance after {'withdrawal' if action == 'withdraw' else 'recording'}: {_money(balance - Decimal(str(mutation['amount'])))}\n\n"
            "Should I proceed?"
        )
        logger.info("chat_mutation_confirmation_requested operation=%s account_id=%s", mutation.get("operation"), account.get("id"))
    elif status == "confirmed":
        pending = mutation.get("pending", {})
        summary = _execute_pending_withdrawal(state, pending)
    elif status == "cancelled":
        pending = mutation.get("pending", {})
        _clear_pending(state)
        summary = f"Okay, I cancelled the {pending.get('operation', 'financial operation')}. No changes were made."
        logger.info("chat_mutation_cancelled operation=%s", pending.get("operation"))
    elif status == "clarification_required":
        _save_pending(state, mutation)
        summary = _clarification(mutation)
    elif status == "rejected":
        summary = "That withdrawal cannot be completed because the available account balance is insufficient."
    else:
        summary = "I need a clear withdrawal amount and account before I can prepare that operation."
    return {"finance_result": AgentOutput(agent="finance", status="completed", summary=summary, data={"mutation": mutation}).model_dump()}


def _execute_pending_withdrawal(state: GraphState, pending: dict[str, Any]) -> str:
    if pending.get("user_id") != state["user_id"]:
        return "That pending operation is not available for this user, so no changes were made."
    account = pending.get("account") if isinstance(pending.get("account"), dict) else {}
    try:
        amount = Decimal(str(pending["amount"]))
        account_id = int(account["id"])
    except (KeyError, TypeError, ValueError, InvalidOperation):
        _clear_pending(state)
        return "That pending operation is no longer valid, so no changes were made."
    payload = {
        "account_id": account_id,
        "transaction_type": "EXPENSE",
        "title": pending.get("title") or f"Withdrawal from {account.get('name', 'account')}",
        "description": pending.get("description") or "Confirmed through AI chat",
        "amount": str(amount),
        "transaction_date": date.today().isoformat(),
        "tags": ["ai-chat", "withdrawal"],
    }
    if pending.get("merchant"):
        payload["merchant"] = pending["merchant"]
    registry = state.get("tool_registry")
    result = registry.execute("transaction", state["user_id"], "withdraw", payload) if registry else None
    if isinstance(result, dict) and result.get("success"):
        _clear_pending(state)
        balance = Decimal(str(account.get("balance", 0))) - amount
        logger.info("chat_mutation_executed operation=%s account_id=%s", pending.get("operation"), account_id)
        if pending.get("operation") == "expense":
            return f"Recorded {_money(amount)} expense from {account.get('name', 'your account')}. New balance: {_money(balance)}."
        return f"Withdrawal complete: {_money(amount)} was debited from {account.get('name', 'your account')}. New balance: {_money(balance)}."
    error = result.get("error", {}).get("message") if isinstance(result, dict) else None
    logger.warning("chat_mutation_execution_failed operation=withdrawal account_id=%s", account_id)
    return f"I couldn’t complete that withdrawal. {error or 'No changes were made.'}"


def _save_pending(state: GraphState, mutation: dict[str, Any]) -> None:
    manager = state.get("memory_manager")
    if manager is None:
        raise ValueError("Conversation memory is required before a financial mutation can be confirmed.")
    records = manager.load_memory(state["user_id"], MemoryType.CONVERSATION, _PENDING_OPERATION_KEY)
    if records:
        manager.update_memory(state["user_id"], records[0].id, value=mutation)
    else:
        manager.save_memory(state["user_id"], MemoryType.CONVERSATION, _PENDING_OPERATION_KEY, mutation)


def _clear_pending(state: GraphState) -> None:
    manager = state.get("memory_manager")
    if manager is None:
        return
    records = manager.load_memory(state["user_id"], MemoryType.CONVERSATION, _PENDING_OPERATION_KEY)
    if records:
        manager.delete_memory(state["user_id"], records[0].id)


def _clarification(mutation: dict[str, Any]) -> str:
    reason = mutation.get("reason")
    if reason == "account":
        if mutation.get("operation") == "expense":
            amount = _money(mutation["amount"])
            return f"I haven't recorded the transaction yet because I need to know which account to use for this {amount} expense."
        return "Which account should I use for this withdrawal?"
    if reason == "amount":
        return "What amount would you like to withdraw?"
    if reason == "destination":
        return "Which account should receive the transfer?"
    return "Please clarify the financial operation you want to make."


def _money(value: Any) -> str:
    return f"₹{Decimal(str(value)):,.2f}"


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
    if _is_affordability_question(normalized_request):
        selected = tuple(dict.fromkeys((*selected, ("account", "list"), ("dashboard", "get"))))
        return selected
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
    if "affordability_analysis" in context:
        result["affordability_analysis"] = context["affordability_analysis"]
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
    
    affordability_instruction = ""
    if "affordability_analysis" in context:
        affordability_instruction = (
            "\nFor affordability questions, clearly explain:\n"
            "- The requested amount.\n"
            "- The user's available/current financial position (such as total balance across accounts, monthly income, and monthly expenses).\n"
            "- Whether the purchase appears affordable and why (being conservative, and warning the user if their balance is barely enough or if monthly expenses are high/negative cash flow).\n"
            "- The remaining balance after the purchase when it can be calculated reliably.\n"
            "If there is not enough reliable information (e.g. no accounts or no balance information), state that clearly and explain what is missing rather than guessing.\n"
        )
        
    return (
        f"{rendered_prompt}\n\n"
        f"{affordability_instruction}"
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
    if "affordability_analysis" in context:
        return _deterministic_affordability_summary(context["affordability_analysis"])
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


def _is_affordability_question(request: str) -> bool:
    """Identify affordability questions."""
    normalized = request.casefold()
    if "afford" in normalized or "affordable" in normalized:
        return True
    if "enough money" in normalized or "enough balance" in normalized or "have enough" in normalized:
        return True
    if "can i spend" in normalized:
        return True
    return False


def _parse_amount(request: str) -> Decimal | None:
    """Parse a valid non-zero Decimal amount from user input."""
    match = re.search(r"(?:₹|â‚¹|inr\s*)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", request, re.IGNORECASE)
    if not match:
        return None
    try:
        amount = Decimal(match.group(1).replace(",", ""))
        return amount if amount > 0 else None
    except (InvalidOperation, ValueError):
        return None


def _calculate_affordability(request: str, context: dict[str, Any]) -> dict[str, Any]:
    """Calculate affordability analysis based on request and current context."""
    amount = _parse_amount(request)
    if amount is None:
        return {
            "has_amount": False,
            "has_reliable_info": False,
            "missing_info": ["requested amount"],
        }

    accounts = context.get("accounts")
    dashboard = context.get("dashboard") or {}
    user_summary = dashboard.get("user_summary") or {}

    missing = []
    if accounts is None:
        missing.append("account balance details")
    if not user_summary:
        missing.append("monthly financial summary")

    if missing:
        return {
            "has_amount": True,
            "requested_amount": str(amount),
            "has_reliable_info": False,
            "missing_info": missing,
        }

    total_balance = Decimal("0.00")
    for acc in accounts:
        if isinstance(acc, dict):
            bal = acc.get("balance")
            if bal is not None:
                try:
                    total_balance += Decimal(str(bal))
                except (InvalidOperation, ValueError, TypeError):
                    pass

    remaining = total_balance - amount

    monthly_income = None
    monthly_expense = None
    mi = user_summary.get("monthly_income")
    me = user_summary.get("monthly_expense")
    if mi is not None:
        try:
            monthly_income = Decimal(str(mi))
        except (InvalidOperation, ValueError, TypeError):
            pass
    if me is not None:
        try:
            monthly_expense = Decimal(str(me))
        except (InvalidOperation, ValueError, TypeError):
            pass

    is_affordable = remaining >= 0

    return {
        "has_amount": True,
        "requested_amount": str(amount),
        "has_reliable_info": True,
        "total_balance": str(total_balance),
        "remaining_balance": str(remaining),
        "monthly_income": str(monthly_income) if monthly_income is not None else None,
        "monthly_expense": str(monthly_expense) if monthly_expense is not None else None,
        "is_affordable": is_affordable,
    }


def _deterministic_affordability_summary(analysis: dict[str, Any]) -> str:
    """Provide a deterministic summary for affordability checks."""
    if not analysis.get("has_amount"):
        return "To check if you can afford this purchase, please tell me the amount you're planning to spend."

    if not analysis.get("has_reliable_info"):
        return (
            "I don't have enough reliable financial information to determine affordability. "
            f"Missing: {', '.join(analysis.get('missing_info', []))}."
        )

    amount = Decimal(str(analysis["requested_amount"]))
    total_balance = Decimal(str(analysis["total_balance"]))
    remaining = Decimal(str(analysis["remaining_balance"]))

    formatted_amount = f"₹{amount:,.2f}"
    formatted_balance = f"₹{total_balance:,.2f}"
    formatted_remaining = f"₹{remaining:,.2f}"

    parts = []
    parts.append(f"Requested amount: {formatted_amount}.")
    parts.append(f"Current total balance: {formatted_balance}.")

    monthly_income = analysis.get("monthly_income")
    monthly_expense = analysis.get("monthly_expense")
    if monthly_income is not None and monthly_expense is not None:
        parts.append(
            f"Monthly income: ₹{Decimal(str(monthly_income)):,.2f}; "
            f"Monthly expenses: ₹{Decimal(str(monthly_expense)):,.2f}."
        )

    if total_balance < amount:
        parts.append(
            f"This purchase does not appear affordable because the requested amount exceeds your total balance by ₹{(amount - total_balance):,.2f}."
        )
    else:
        parts.append(f"This purchase appears affordable. Your remaining balance after this purchase would be {formatted_remaining}.")
        if monthly_expense is not None and remaining < Decimal(str(monthly_expense)):
            parts.append(
                f"Warning: Your remaining balance ({formatted_remaining}) would be less than your current monthly expenses (₹{Decimal(str(monthly_expense)):,.2f}). Proceed with caution."
            )
        elif monthly_income is not None and monthly_expense is not None and Decimal(str(monthly_income)) < Decimal(str(monthly_expense)):
            parts.append("Warning: Your monthly net cash flow is currently negative. Proceed with caution.")

    return " ".join(parts)
