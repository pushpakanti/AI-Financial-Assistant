"""SQLAlchemy and validation models for persistent user memory."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Enum as SqlEnum, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class MemoryType(str, Enum):
    """Persistent memory domains supported by the application."""

    PROCEDURAL = "PROCEDURAL"
    SEMANTIC = "SEMANTIC"
    CONVERSATION = "CONVERSATION"
    PROFILE = "PROFILE"


class RiskProfile(str, Enum):
    """Supported investment risk preferences."""

    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"


class UserMemory(PrimaryKeyMixin, TimestampMixin, Base):
    """One user-scoped typed memory record with a JSON payload."""

    __tablename__ = "user_memories"
    __table_args__ = (UniqueConstraint("user_id", "memory_type", "key", name="uq_user_memories_scope_key"),)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        SqlEnum(MemoryType, name="memory_type"), index=True, nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProfileMemory(BaseModel):
    """Validated optional user profile details stored as PROFILE memory."""

    model_config = ConfigDict(extra="forbid")

    user_preferences: dict[str, Any] = Field(default_factory=dict)
    salary_day: int | None = Field(default=None, ge=1, le=31)
    budget_preferences: dict[str, Any] = Field(default_factory=dict)
    investment_preference: str | None = Field(default=None, max_length=255)
    risk_profile: RiskProfile | None = None
    recurring_expenses: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    favorite_categories: list[str] = Field(default_factory=list, max_length=100)


class MemoryResponse(BaseModel):
    """Serializable memory representation for future API or agent consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    memory_type: MemoryType
    key: str
    value: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
