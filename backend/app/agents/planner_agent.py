"""Deterministic, safety-first planner for finance chat."""

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.agents.state import AgentOutput, GraphState, SUPPORTED_AGENTS
from app.memory.memory_models import MemoryType
from app.prompts import PromptManager


_ROUTING_KEYWORDS: dict[str, tuple[str, ...]] = {
    "finance": (
        "finance", "transaction", "income", "expense", "cash flow", "account", "balance",
        "spending", "spent", "merchant", "category",
        "invest", "portfolio", "sip", "stock", "equity", "shares", "mutual fund", "plan",
    ),
    "budget": ("budget", "remaining budget", "budget left", "budget is left", "budget summary", "budget alerts", "alert"),
    "goal": ("goal", "savings goal", "prediction", "recommendation", "save", "saving", "target"),
    "report": ("dashboard", "report", "overview", "analytics"),
}
_MEMORY_KEYWORDS: tuple[str, ...] = (
    "remember",
    "risk profile",
    "risk preference",
    "salary",
    "get paid",
    "paid on",
    "prefer",
    "preference",
    "sip",
    "investing",
    "investment",
    "portfolio",
)
_TOOL_ROUTING: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("dashboard", ("dashboard", "analytics", "report", "overview"), "get"),
    ("budget", ("budget", "alert"), "summary"),
    ("transaction", ("transaction", "income", "expense", "spending", "spent", "merchant", "category", "cash flow"), "list"),
    ("account", ("account", "balance"), "list"),
)
_prompt_manager = PromptManager()
logger = logging.getLogger(__name__)
_PENDING_OPERATION_KEY = "pending_financial_operation"
_CONFIRMATIONS = {"yes", "yes do it", "confirm", "go ahead", "proceed", "do it"}
_CANCELLATIONS = {"no", "cancel", "don't do it", "stop", "forget it"}
_MUTATION_PATTERNS = {
    "withdrawal": ("withdraw", "withdrawal", "cut", "take", "debit"),
    "transfer": ("transfer",),
}
_EXPENSE_STATEMENT_PATTERNS = ("spent", "paid", "debited", "debitted")


def planner_agent(state: GraphState) -> dict[str, object]:
    """Select relevant domain agents with transparent keyword routing only."""
    raw_request = state.get("request", "")
    prompt = _prompt_manager.render_agent_prompt("planner", variables={"request": raw_request})
    request = raw_request.casefold()
    if _is_memory_capability_question(request):
        return _general_plan(prompt.version, prompt.locale, raw_request)
    mutation = _plan_mutation(state, raw_request)
    if mutation is not None:
        selected = ["finance"]
        tool_results = mutation.pop("tool_results", [])
        logger.info("chat_mutation_intent status=%s operation=%s", mutation.get("status"), mutation.get("operation"))
        result = AgentOutput(agent="planner", status="planned", summary="Financial mutation routing completed.", data={
            "selected_agents": selected, "routing_mode": "mutation", "mutation": mutation,
            "prompt": {"version": prompt.version, "locale": prompt.locale},
        })
        return {"planned_agents": selected, "planner_result": result.model_dump(), "tool_results": tool_results, "mutation": mutation}

    selected = _select_domain_agents(request)
    if not selected and any(keyword in request for keyword in _MEMORY_KEYWORDS):
        selected = []
    elif not selected:
        selected = []
    tool_results = _invoke_tools(state, request)
    result = AgentOutput(
        agent="planner",
        status="planned",
        summary="Deterministic routing completed; no LLM reasoning was used.",
        data={
            "selected_agents": selected,
            "routing_mode": "keyword" if selected else "general",
            "general_response": _general_response(raw_request) if not selected else None,
            "tool_results": tool_results,
            "prompt": {"version": prompt.version, "locale": prompt.locale},
        },
    )
    return {
        "planned_agents": selected,
        "planner_result": result.model_dump(),
        "tool_results": tool_results,
    }


def _select_domain_agents(request: str) -> list[str]:
    """Accumulate every matching domain in stable graph order."""
    normalized = " ".join(request.casefold().split())
    return [
        agent
        for agent in SUPPORTED_AGENTS
        if _matches_domain(agent, normalized)
    ]


def _matches_domain(agent: str, request: str) -> bool:
    """Match standalone budget words while retaining the established domain keywords."""
    if agent == "budget":
        return bool(re.search(r"\bbudgets?\b", request))
    return any(keyword in request for keyword in _ROUTING_KEYWORDS[agent])


def _general_plan(prompt_version: str, prompt_locale: str, request: str) -> dict[str, object]:
    """Return a capability response without calling domain tools or pending mutation logic."""
    result = AgentOutput(
        agent="planner",
        status="planned",
        summary="General capability routing completed.",
        data={
            "selected_agents": [],
            "routing_mode": "general",
            "general_response": _general_response(request),
            "tool_results": [],
            "prompt": {"version": prompt_version, "locale": prompt_locale},
        },
    )
    return {"planned_agents": [], "planner_result": result.model_dump(), "tool_results": []}


def _is_memory_capability_question(request: str) -> bool:
    """Keep explicit questions about memory outside financial and pending-operation routing."""
    normalized = " ".join(request.split()).strip(" .!?")
    return normalized in {
        "do you have memory",
        "do you remember me",
        "do you remember our conversation",
        "what do you remember",
        "can you remember this",
        "do you remember what i said",
    }


def _plan_mutation(state: GraphState, raw_request: str) -> dict[str, Any] | None:
    """Parse a narrow mutation grammar; execution remains in the finance service layer."""
    request = " ".join(raw_request.casefold().replace("don’t", "don't").split()).strip(" .!?")
    pending = _load_pending(state)
    if pending:
        follow_up = _resolve_pending_follow_up(state, raw_request, request, pending)
        if follow_up is not None:
            return follow_up
    operation = next((name for name, words in _MUTATION_PATTERNS.items() if any(re.search(rf"\b{re.escape(word)}\b", request) for word in words)), None)
    if operation is None and _is_expense_statement(raw_request, request):
        operation = "expense"
    if operation is None:
        return None
    if operation == "transfer":
        return {"status": "clarification_required", "operation": operation, "reason": "destination"}
    amount = _parse_amount(raw_request)
    if amount is None:
        return {"status": "clarification_required", "operation": operation, "reason": "amount"}
    accounts_result, accounts = _user_accounts(state)
    matched = _match_accounts(raw_request, accounts)
    if operation == "expense" and not matched and len(accounts) == 1:
        matched = accounts
    if len(matched) != 1:
        return _pending_clarification(operation, amount, accounts_result, raw_request, state["user_id"])
    account = matched[0]
    if amount > Decimal(str(account.get("balance", 0))):
        return {"status": "rejected", "operation": operation, "amount": str(amount), "account": account, "reason": "insufficient_balance", "tool_results": [accounts_result] if accounts_result else []}
    mutation = _pending_base(operation, amount, raw_request, state["user_id"])
    mutation.update({"status": "confirmation_required", "account": account, "tool_results": [accounts_result] if accounts_result else []})
    return mutation


def _is_expense_statement(raw_request: str, normalized_request: str) -> bool:
    """Recognize recordable past-tense expense statements, not spending questions."""
    if "?" in raw_request or _parse_amount(raw_request) is None:
        return False
    return bool(
        re.search(r"\bi(?:\s+have)?\s+(?:spent|paid|debited|debitted)\b", normalized_request)
    )


def _resolve_pending_follow_up(
    state: GraphState, raw_request: str, normalized_request: str, pending: dict[str, Any]
) -> dict[str, Any] | None:
    """Give an active, user-scoped financial operation priority over generic routing."""
    if normalized_request in _CONFIRMATIONS:
        return {"status": "confirmed", "pending": pending}
    if normalized_request in _CANCELLATIONS:
        return {"status": "cancelled", "pending": pending}
    if pending.get("reason") != "account" and pending.get("account"):
        return None
    accounts_result, accounts = _user_accounts(state)
    matches = _match_accounts(raw_request, accounts)
    if len(matches) == 1:
        updated = {key: value for key, value in pending.items() if key not in {"reason", "tool_results", "status"}}
        updated.update({"status": "confirmation_required", "account": matches[0], "tool_results": [accounts_result] if accounts_result else []})
        return updated
    updated = {key: value for key, value in pending.items() if key not in {"tool_results", "status"}}
    updated.update({"status": "clarification_required", "reason": "account", "account": None, "tool_results": [accounts_result] if accounts_result else []})
    return updated


def _user_accounts(state: GraphState) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    registry = state.get("tool_registry")
    result = registry.execute("account", state["user_id"], "list", {}) if registry else None
    accounts = result.get("data", []) if isinstance(result, dict) and result.get("success") else []
    return result, accounts if isinstance(accounts, list) else []


def _pending_base(operation: str, amount: Decimal, request: str, user_id: int) -> dict[str, Any]:
    mutation: dict[str, Any] = {
        "operation": operation,
        "amount": str(amount),
        "currency": "INR",
        "confirmation_required": True,
        "user_id": user_id,
    }
    if operation == "expense":
        merchant = _merchant_from_statement(request)
        mutation.update({
            "merchant": merchant,
            "title": f"Expense at {merchant}" if merchant else "Recorded expense",
            "description": request[:10_000],
        })
    return mutation


def _pending_clarification(
    operation: str, amount: Decimal, accounts_result: dict[str, Any] | None, request: str, user_id: int
) -> dict[str, Any]:
    mutation = _pending_base(operation, amount, request, user_id)
    mutation.update({
        "status": "clarification_required",
        "reason": "account",
        "account": None,
        "tool_results": [accounts_result] if accounts_result else [],
    })
    return mutation


def _merchant_from_statement(request: str) -> str | None:
    match = re.search(r"\b(?:at|in)\s+(?:the\s+)?([a-z0-9][a-z0-9 .&'-]{1,80}?)(?:[.!?]|$)", request, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _load_pending(state: GraphState) -> dict[str, Any] | None:
    manager = state.get("memory_manager")
    if manager is None:
        return None
    try:
        records = manager.load_memory(state["user_id"], MemoryType.CONVERSATION, _PENDING_OPERATION_KEY)
        return records[0].value if records and isinstance(records[0].value, dict) else None
    except Exception:
        logger.exception("Unable to load pending financial operation")
        return None


def _parse_amount(request: str) -> Decimal | None:
    match = re.search(r"(?:₹|â‚¹|inr\s*)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", request, re.IGNORECASE)
    if not match:
        return None
    try:
        amount = Decimal(match.group(1).replace(",", ""))
        return amount if amount > 0 else None
    except InvalidOperation:
        return None


def _match_accounts(request: str, accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = request.casefold()
    matches = []
    for account in accounts:
        name = str(account.get("name", "")).casefold()
        account_type = str(account.get("account_type", "")).casefold()
        tokens = [token for token in re.split(r"\W+", name) if len(token) >= 3]
        if (name and name in normalized) or (account_type and account_type in normalized) or any(token in normalized for token in tokens):
            matches.append(account)
    return matches


def _general_response(request: str) -> str:
    normalized = request.casefold()
    if "memory" in normalized or "remember" in normalized:
        return "Yes. I retain relevant conversation context and user-scoped memories, which helps with follow-ups such as confirmations and references to recent financial actions."
    if any(word in normalized for word in ("who are you", "what can you do", "help")):
        return "I’m your AI financial assistant. I can help you track spending, manage budgets, monitor goals, analyze your finances, and import statements."
    return "Hello! I’m your AI financial assistant. How can I help with your finances today?"


def _invoke_tools(state: GraphState, request: str) -> list[dict[str, object]]:
    """Invoke only registered tools; the planner never reaches into persistence directly."""
    registry = state.get("tool_registry")
    if registry is None:
        return []
    results: list[dict[str, object]] = []
    for tool_name, keywords, action in _TOOL_ROUTING:
        if _is_budget_spending_comparison(request) and (tool_name, action) == ("transaction", "list"):
            continue
        if any(keyword in request for keyword in keywords):
            results.append(registry.execute(tool_name, state["user_id"], action, {}))
    # A comparison needs an authoritative expense aggregate.  A paginated list
    # cannot safely stand in for total spending.
    if _is_budget_spending_comparison(request):
        results.append(registry.execute("transaction", state["user_id"], "summary", {}))
        results.append(registry.execute("dashboard", state["user_id"], "get", {}))
    return results


def _is_budget_spending_comparison(request: str) -> bool:
    """Identify requests that need transaction-derived spending plus budget totals."""
    return "budget" in request and any(
        term in request for term in ("compare", "compared", "spending", "spent", "actual")
    )
