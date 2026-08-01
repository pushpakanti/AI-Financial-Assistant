"""MySQL persistence operations for user-scoped memory records."""

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.memory.memory_models import MemoryType, UserMemory


class MemoryStore:
    """Encapsulate memory storage while ensuring every query is user-scoped."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, memory: UserMemory) -> UserMemory:
        """Persist and return a memory record."""
        self._db.add(memory)
        self._db.commit()
        self._db.refresh(memory)
        return memory

    def get_by_id_and_user_id(self, memory_id: int, user_id: int) -> UserMemory | None:
        """Return an active memory only when it belongs to the supplied user."""
        statement = select(UserMemory).where(
            UserMemory.id == memory_id,
            UserMemory.user_id == user_id,
            UserMemory.is_active.is_(True),
        )
        return self._db.scalar(statement)

    def get_by_scope_and_key(
        self, user_id: int, memory_type: MemoryType, key: str
    ) -> UserMemory | None:
        """Return an active memory by its user/type/key identity."""
        statement = select(UserMemory).where(
            UserMemory.user_id == user_id,
            UserMemory.memory_type == memory_type,
            UserMemory.key == key,
            UserMemory.is_active.is_(True),
        )
        return self._db.scalar(statement)

    def get_any_by_scope_and_key(
        self, user_id: int, memory_type: MemoryType, key: str
    ) -> UserMemory | None:
        """Return a memory by identity regardless of its soft-delete state."""
        statement = select(UserMemory).where(
            UserMemory.user_id == user_id,
            UserMemory.memory_type == memory_type,
            UserMemory.key == key,
        )
        return self._db.scalar(statement)

    def list_by_user_id(
        self, user_id: int, memory_type: MemoryType | None = None, key: str | None = None
    ) -> list[UserMemory]:
        """Return active memories in a user's selected scope."""
        statement = select(UserMemory).where(UserMemory.user_id == user_id, UserMemory.is_active.is_(True))
        if memory_type is not None:
            statement = statement.where(UserMemory.memory_type == memory_type)
        if key is not None:
            statement = statement.where(UserMemory.key == key)
        return list(self._db.scalars(statement.order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())))

    def search(
        self, user_id: int, query: str, memory_type: MemoryType | None, limit: int
    ) -> list[UserMemory]:
        """Search memory keys and JSON payload text within one user's records."""
        pattern = f"%{query.casefold()}%"
        statement = select(UserMemory).where(
            UserMemory.user_id == user_id,
            UserMemory.is_active.is_(True),
            or_(
                func.lower(UserMemory.key).like(pattern),
                func.lower(cast(UserMemory.value, String)).like(pattern),
            ),
        )
        if memory_type is not None:
            statement = statement.where(UserMemory.memory_type == memory_type)
        return list(
            self._db.scalars(statement.order_by(UserMemory.updated_at.desc(), UserMemory.id.desc()).limit(limit))
        )

    def update(self, memory: UserMemory) -> UserMemory:
        """Commit changes made to a memory and return its refreshed state."""
        self._db.commit()
        self._db.refresh(memory)
        return memory

    def soft_delete(self, memory: UserMemory) -> None:
        """Deactivate a memory without losing its audit history."""
        memory.is_active = False
        self._db.commit()
