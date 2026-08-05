"""Memory node that retrieves and persists user-scoped workflow context."""

import hashlib
import json
import logging
import re
from typing import Any

from app.agents.state import AgentOutput, GraphState, SUPPORTED_AGENTS
from app.memory.memory_models import MemoryType, ProfileMemory, RiskProfile
from app.prompts import PromptManager


logger = logging.getLogger(__name__)
_prompt_manager = PromptManager()
_MEMORY_QUERY_LIMIT = 100


def memory_agent(state: GraphState) -> dict[str, object]:
    """Retrieve relevant memories and persist the completed workflow without blocking chat."""
    prompt_manager = state.get("prompt_manager") or _prompt_manager
    prompt = prompt_manager.render_agent_prompt(
        "memory", variables={"request": state.get("request", "")}
    )
    manager = state.get("memory_manager")
    retrieved_memories: list[dict[str, Any]] = []
    profile: ProfileMemory | None = None
    persistence_status: dict[str, str] = {"retrieval": "unavailable", "conversation": "unavailable", "profile": "not_applicable"}
    newly_stored: list[dict[str, Any]] = []

    if manager is not None:
        retrieved_memories, profile, retrieval_status = _retrieve_memories(
            manager, state["user_id"], state.get("request", "")
        )
        persistence_status["retrieval"] = retrieval_status
        conversation, summaries, routing = _conversation_record(state)
        stored_conversation, conversation_status = _store_conversation(
            manager, state["user_id"], conversation
        )
        persistence_status["conversation"] = conversation_status
        if stored_conversation is not None:
            newly_stored.append(_memory_payload(manager, stored_conversation))

        stored_profile, profile_status = _store_profile_preference(
            manager, state["user_id"], state.get("request", ""), profile
        )
        persistence_status["profile"] = profile_status
        if stored_profile is not None:
            newly_stored.append(_memory_payload(manager, stored_profile))
    else:
        summaries, routing = _agent_summaries(state), _planner_routing(state)

    completed_agents = [agent for agent in SUPPORTED_AGENTS if agent in summaries]
    summary = _retrieved_profile_summary(state.get("request", ""), retrieved_memories) or _summary(
        persistence_status, len(retrieved_memories), len(newly_stored)
    )
    result = AgentOutput(
        agent="memory",
        status="completed",
        summary=summary,
        data={
            "retrieved_memories": retrieved_memories,
            "newly_stored_memories": newly_stored,
            "memory_metadata": {
                "user_scoped": True,
                "completed_agents": completed_agents,
                "planner_routing": routing,
                "persistence_status": persistence_status,
            },
            "persistence_enabled": manager is not None,
            "prompt": {"version": prompt.version, "locale": prompt.locale},
        },
    )
    return {
        "retrieved_memories": retrieved_memories,
        "memory_result": result.model_dump(),
    }


def _retrieve_memories(
    manager: Any, user_id: int, request: str
) -> tuple[list[dict[str, Any]], ProfileMemory | None, str]:
    """Search only the caller's relevant memories and include their canonical profile."""
    try:
        memories = manager.search_memory(user_id, request[:_MEMORY_QUERY_LIMIT], limit=10)
        retrieved = [_memory_payload(manager, memory) for memory in memories]
        profile = manager.load_profile(user_id)
        profile_already_retrieved = any(
            memory.get("memory_type") == MemoryType.PROFILE.value and memory.get("key") == "profile"
            for memory in retrieved
        )
        if profile is not None and not profile_already_retrieved:
            retrieved.append(
                {
                    "memory_type": MemoryType.PROFILE.value,
                    "key": "profile",
                    "value": profile.model_dump(mode="json", exclude_none=True),
                }
            )
        return retrieved, profile, "completed"
    except Exception:  # pragma: no cover - persistence failures must not break chat
        logger.exception("Memory retrieval failed for user_id=%s", user_id)
        return [], None, "failed"


def _conversation_record(state: GraphState) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Create the durable, deterministic record for this completed workflow."""
    summaries = _agent_summaries(state)
    routing = _planner_routing(state)
    return (
        {
            "user_message": state.get("request", ""),
            "planner_routing": routing,
            "agent_summaries": summaries,
        },
        summaries,
        routing,
    )


def _agent_summaries(state: GraphState) -> dict[str, str]:
    """Collect final summaries without persisting implementation-level agent data."""
    summaries: dict[str, str] = {}
    for agent in SUPPORTED_AGENTS:
        result = state.get(f"{agent}_result", {})
        if isinstance(result, dict) and result.get("status") == "completed" and isinstance(result.get("summary"), str):
            summaries[agent] = result["summary"]
    return summaries


def _planner_routing(state: GraphState) -> list[str]:
    """Return the planner's selected agents in a JSON-safe form."""
    planned_agents = state.get("planned_agents", [])
    return [agent for agent in planned_agents if agent in SUPPORTED_AGENTS]


def _store_conversation(manager: Any, user_id: int, conversation: dict[str, Any]) -> tuple[Any | None, str]:
    """Persist one idempotently keyed conversation record for the authenticated user."""
    identity = {
        "user_id": user_id,
        "user_message": _normalize_message(conversation["user_message"]),
        "planner_routing": sorted(conversation["planner_routing"]),
    }
    key = f"conversation:{_digest(identity)}"
    try:
        if manager.load_memory(user_id, MemoryType.CONVERSATION, key):
            return None, "duplicate_skipped"
        memory = manager.save_memory(user_id, MemoryType.CONVERSATION, key, conversation)
        return memory, "stored"
    except Exception:  # pragma: no cover - persistence failures must not break chat
        logger.exception("Conversation memory persistence failed for user_id=%s", user_id)
        return None, "failed"


def _store_profile_preference(
    manager: Any, user_id: int, request: str, profile: ProfileMemory | None
) -> tuple[Any | None, str]:
    """Update the canonical profile only for explicit, long-lived preference signals."""
    updates = _profile_updates(request)
    if not updates:
        return None, "not_applicable"
    try:
        existing = profile or manager.load_profile(user_id) or ProfileMemory()
        profile_data = existing.model_dump()
        profile_data.update(updates)
        updated = ProfileMemory.model_validate(profile_data)
        if updated == existing:
            return None, "duplicate_skipped"
        return manager.save_profile(user_id, updated), "stored"
    except Exception:  # pragma: no cover - persistence failures must not break chat
        logger.exception("Profile memory persistence failed for user_id=%s", user_id)
        return None, "failed"


def _profile_updates(request: str) -> dict[str, Any]:
    """Extract only clear preference statements; transactional requests are not profiled."""
    normalized = request.casefold()
    updates: dict[str, Any] = {}
    if "risk" in normalized:
        for risk in RiskProfile:
            if risk.value.casefold() in normalized:
                updates["risk_profile"] = risk.value
                break
    if "prefer" in normalized and any(term in normalized for term in ("invest", "investment", "portfolio")):
        updates["investment_preference"] = request[:255]
    salary_day = re.search(
        r"\b(?:salary day|(?:get )?paid)(?: is| on)?\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\b",
        normalized,
    )
    if salary_day and 1 <= int(salary_day.group(1)) <= 31:
        updates["salary_day"] = int(salary_day.group(1))
    if "prefer" in normalized and "budget" in normalized:
        updates["budget_preferences"] = {"stated_preference": request[:255]}
    return updates


def _digest(value: dict[str, Any]) -> str:
    """Produce a compact stable key that avoids duplicate conversation records."""
    serialized = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:64]


def _normalize_message(message: str) -> str:
    """Normalize user input used solely for conversation identity."""
    return " ".join(message.casefold().split())


def _memory_payload(manager: Any, memory: Any) -> dict[str, Any]:
    """Serialize only public memory fields for graph state and API output."""
    try:
        return manager.to_response(memory).model_dump(mode="json")
    except Exception:
        if isinstance(memory, dict):
            return memory
        return {
            "memory_type": getattr(getattr(memory, "memory_type", None), "value", getattr(memory, "memory_type", None)),
            "key": getattr(memory, "key", None),
            "value": getattr(memory, "value", None),
        }


def _summary(status: dict[str, str], retrieved_count: int, stored_count: int) -> str:
    """Return a compact status sentence without exposing persistence failures to the chat flow."""
    if status["retrieval"] == "failed":
        return "Workflow completed; memory retrieval was unavailable."
    if status["conversation"] == "failed" or status["profile"] == "failed":
        return "Workflow completed; memory persistence was partially unavailable."
    return f"Workflow completed with {retrieved_count} retrieved and {stored_count} newly stored memory record(s)."


def _retrieved_profile_summary(request: str, memories: list[dict[str, Any]]) -> str | None:
    """Answer direct profile lookups from already retrieved, user-scoped memory."""
    if "risk profile" not in request.casefold():
        return None
    for memory in memories:
        value = memory.get("value")
        if memory.get("key") == "profile" and isinstance(value, dict) and value.get("risk_profile"):
            return f"Your risk profile is {str(value['risk_profile']).casefold()}."
    return None
