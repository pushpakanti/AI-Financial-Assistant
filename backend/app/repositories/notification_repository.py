"""Database access operations for user-owned in-app notifications."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType


class NotificationRepository:
    """Encapsulate notification persistence and user-scoped filtering."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, notification: Notification) -> Notification:
        self._db.add(notification)
        self._db.commit()
        self._db.refresh(notification)
        return notification

    def get_by_id_and_user_id(self, notification_id: int, user_id: int) -> Notification | None:
        statement = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        return self._db.scalar(statement)

    def list_by_user_id(
        self,
        user_id: int,
        *,
        is_read: bool | None,
        notification_type: NotificationType | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int]:
        statement = select(Notification).where(Notification.user_id == user_id)
        if is_read is not None:
            statement = statement.where(Notification.is_read.is_(is_read))
        if notification_type is not None:
            statement = statement.where(Notification.notification_type == notification_type)
        total = int(self._db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        items = list(
            self._db.scalars(
                statement.order_by(Notification.is_read.asc(), Notification.created_at.desc(), Notification.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return items, total

    def unread_count(self, user_id: int) -> int:
        statement = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        return int(self._db.scalar(statement) or 0)

    def save(self, notification: Notification) -> Notification:
        self._db.commit()
        self._db.refresh(notification)
        return notification

    def delete(self, notification: Notification) -> None:
        self._db.delete(notification)
        self._db.commit()
