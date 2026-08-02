"""Authenticated AI chat endpoint backed by the existing LangGraph workflow."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.graph import build_agent_graph
from app.agents.state import GraphState
from app.ai import LLMGateway
from app.api.deps import get_current_user
from app.database.session import get_db
from app.memory import MemoryManager
from app.memory.memory_store import MemoryStore
from app.models.user import User
from app.prompts import PromptManager
from app.schemas.chat import ChatRequest, ChatResponse
from app.tools import ToolRegistry


router = APIRouter(prefix="/chat", tags=["chat"])


def get_tool_registry(db: Annotated[Session, Depends(get_db)]) -> ToolRegistry:
    """Create request-scoped tools so every tool retains the current database session."""
    return ToolRegistry(db)


def get_memory_manager(db: Annotated[Session, Depends(get_db)]) -> MemoryManager:
    """Create the existing request-scoped memory manager."""
    return MemoryManager(MemoryStore(db))


def get_llm_gateway() -> LLMGateway:
    """Provide the existing configured LLM gateway to graph nodes."""
    return LLMGateway()


def get_prompt_manager() -> PromptManager:
    """Provide the existing prompt manager to graph nodes."""
    return PromptManager()


@router.post("", response_model=ChatResponse)
def create_chat(
    payload: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    tool_registry: Annotated[ToolRegistry, Depends(get_tool_registry)],
    llm_gateway: Annotated[LLMGateway, Depends(get_llm_gateway)],
    prompt_manager: Annotated[PromptManager, Depends(get_prompt_manager)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
) -> ChatResponse:
    """Execute the financial-assistant graph for the authenticated user only."""
    initial_state: GraphState = {
        "request": payload.message,
        "user_id": current_user.id,
        "tool_registry": tool_registry,
        "llm_gateway": llm_gateway,
        "prompt_manager": prompt_manager,
        "memory_manager": memory_manager,
    }
    result: dict[str, Any] = build_agent_graph().invoke(initial_state)

    return ChatResponse(
        message=payload.message,
        planned_agents=result["planned_agents"],
        planner=result["planner_result"],
        finance=result["finance_result"],
        budget=result["budget_result"],
        goal=result["goal_result"],
        report=result["report_result"],
        memory=result["memory_result"],
        tool_results=result.get("tool_results", []),
    )
