"""Pydantic schemas for in-app notification APIs."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.notification import NotificationPriority, NotificationType


NotificationTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
NotificationMessage = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)]


class NotificationCreate(BaseModel):
    """Validated payload for a user-owned in-app notification."""

    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    title: NotificationTitle
    message: NotificationMessage
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    """Public representation of an in-app notification."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    metadata_json: dict[str, Any]
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationPage(BaseModel):
    """Offset-paginated notifications with read-state metadata."""

    items: list[NotificationResponse]
    total: int
    limit: int
    offset: int


class UnreadCountResponse(BaseModel):
    """Unread notification count for the authenticated user."""

    unread_count: Annotated[int, Field(ge=0)]
