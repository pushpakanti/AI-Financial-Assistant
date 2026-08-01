"""Authenticated in-app notification endpoints for version 1 of the API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.notification import NotificationType
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationCreate, NotificationPage, NotificationResponse, UnreadCountResponse
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(db: Annotated[Session, Depends(get_db)]) -> NotificationService:
    """Build the request-scoped notification service."""
    return NotificationService(NotificationRepository(db))


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    notification_data: NotificationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationResponse:
    """Create an in-app notification for the authenticated user."""
    return notification_service.create_notification(current_user.id, notification_data)


@router.get("", response_model=NotificationPage)
def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
    is_read: bool | None = None,
    notification_type: NotificationType | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationPage:
    """List the caller's notifications with optional read/type filtering."""
    items, total = notification_service.list_notifications(
        current_user.id,
        is_read=is_read,
        notification_type=notification_type,
        limit=limit,
        offset=offset,
    )
    return NotificationPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_notification_count(
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> UnreadCountResponse:
    """Return the unread notification count for the authenticated user."""
    return UnreadCountResponse(unread_count=notification_service.unread_count(current_user.id))


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationResponse:
    """Mark one caller-owned notification as read."""
    return notification_service.mark_read(notification_id, current_user.id)


@router.patch("/{notification_id}/unread", response_model=NotificationResponse)
def mark_notification_unread(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationResponse:
    """Mark one caller-owned notification as unread."""
    return notification_service.mark_unread(notification_id, current_user.id)


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationResponse:
    """Get one notification owned by the authenticated user."""
    return notification_service.get_notification(notification_id, current_user.id)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> Response:
    """Delete one notification owned by the authenticated user."""
    notification_service.delete_notification(notification_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
