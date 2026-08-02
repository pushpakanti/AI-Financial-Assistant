"""Request and response contracts for the authenticated AI chat API."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.agents.state import AgentOutput, AgentName


class ChatRequest(BaseModel):
    """One user message for the financial assistant workflow."""

    message: str = Field(..., min_length=1, max_length=4_000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        """Normalize the message and reject whitespace-only requests."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message must not be blank.")
        return normalized


class ChatResponse(BaseModel):
    """Structured result produced by one LangGraph execution."""

    message: str
    planned_agents: list[AgentName]
    planner: AgentOutput
    finance: AgentOutput
    budget: AgentOutput
    goal: AgentOutput
    report: AgentOutput
    memory: AgentOutput
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
