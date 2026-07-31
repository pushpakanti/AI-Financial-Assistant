"""Database access operations for users."""

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Encapsulate all persistence operations for the User model."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_user(self, user: User) -> User:
        """Persist and return a new user."""
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        """Return a user by email, if one exists."""
        statement = select(User).where(User.email == email)
        return self._db.scalar(statement)

    def get_by_id(self, user_id: int) -> User | None:
        """Return a user by primary key, if one exists."""
        return self._db.get(User, user_id)

    def exists(self, email: str) -> bool:
        """Return whether a user exists for the supplied email."""
        statement = select(exists().where(User.email == email))
        return bool(self._db.scalar(statement))
