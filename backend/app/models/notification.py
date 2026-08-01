"""Notification database model for user-scoped in-app alerts and reminders."""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import PrimaryKeyMixin, TimestampMixin, utc_now


class NotificationType(str, Enum):
    """In-app notification categories supported by the backend."""

    BUDGET_ALERT = "BUDGET_ALERT"
    GOAL_REMINDER = "GOAL_REMINDER"
    SALARY_REMINDER = "SALARY_REMINDER"
    BILL_REMINDER = "BILL_REMINDER"


class NotificationPriority(str, Enum):
    """Relative urgency for notification presentation."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Notification(PrimaryKeyMixin, TimestampMixin, Base):
    """A persistent in-app notification belonging to one user."""

    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        SqlEnum(NotificationType, name="notification_type"), nullable=False
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        SqlEnum(NotificationPriority, name="notification_priority"), nullable=False, default=NotificationPriority.MEDIUM
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
