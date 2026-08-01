"""Business logic for user-scoped in-app notifications."""

from app.core.exceptions import NotFoundException
from app.models.mixins import utc_now
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationCreate


class NotificationService:
    """Coordinate notification creation, retrieval, state changes, and ownership checks."""

    def __init__(self, notification_repository: NotificationRepository) -> None:
        self._notification_repository = notification_repository

    def create_notification(self, user_id: int, notification_data: NotificationCreate) -> Notification:
        """Create an unread in-app notification for the authenticated user."""
        return self._notification_repository.create(
            Notification(
                user_id=user_id,
                notification_type=notification_data.notification_type,
                priority=notification_data.priority,
                title=notification_data.title,
                message=notification_data.message,
                metadata_json=notification_data.metadata,
            )
        )

    def list_notifications(self, user_id: int, **filters):
        """List only the authenticated user's notifications."""
        return self._notification_repository.list_by_user_id(user_id, **filters)

    def get_notification(self, notification_id: int, user_id: int) -> Notification:
        """Get one notification without exposing other users' records."""
        return self._get_owned_notification(notification_id, user_id)

    def mark_read(self, notification_id: int, user_id: int) -> Notification:
        """Mark a caller-owned notification read and set its read timestamp once."""
        notification = self._get_owned_notification(notification_id, user_id)
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = utc_now()
        return self._notification_repository.save(notification)

    def mark_unread(self, notification_id: int, user_id: int) -> Notification:
        """Mark a caller-owned notification unread and clear its read timestamp."""
        notification = self._get_owned_notification(notification_id, user_id)
        if notification.is_read:
            notification.is_read = False
            notification.read_at = None
        return self._notification_repository.save(notification)

    def unread_count(self, user_id: int) -> int:
        return self._notification_repository.unread_count(user_id)

    def delete_notification(self, notification_id: int, user_id: int) -> None:
        self._notification_repository.delete(self._get_owned_notification(notification_id, user_id))

    def _get_owned_notification(self, notification_id: int, user_id: int) -> Notification:
        notification = self._notification_repository.get_by_id_and_user_id(notification_id, user_id)
        if notification is None:
            raise NotFoundException("Notification not found.")
        return notification
