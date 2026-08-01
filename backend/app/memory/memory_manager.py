"""High-level, validated memory operations for application services and future agents."""

from typing import Any

from app.core.exceptions import ConflictException, NotFoundException
from app.memory.memory_models import MemoryResponse, MemoryType, ProfileMemory, UserMemory
from app.memory.memory_store import MemoryStore


class MemoryManager:
    """Manage typed user memory without vector search, agents, or cross-user access."""

    def __init__(self, memory_store: MemoryStore) -> None:
        self._memory_store = memory_store

    def save_memory(
        self, user_id: int, memory_type: MemoryType | str, key: str, value: dict[str, Any]
    ) -> UserMemory:
        """Create one uniquely keyed memory after validating its supported payload."""
        normalized_type = self._memory_type(memory_type)
        normalized_key = self._key(key)
        normalized_value = self._value(normalized_type, normalized_key, value)
        existing = self._memory_store.get_any_by_scope_and_key(user_id, normalized_type, normalized_key)
        if existing is not None and existing.is_active:
            raise ConflictException("A memory with this type and key already exists.")
        if existing is not None:
            existing.value = normalized_value
            existing.is_active = True
            return self._memory_store.update(existing)
        return self._memory_store.create(
            UserMemory(
                user_id=user_id,
                memory_type=normalized_type,
                key=normalized_key,
                value=normalized_value,
            )
        )

    def load_memory(
        self,
        user_id: int,
        memory_type: MemoryType | str | None = None,
        key: str | None = None,
    ) -> list[UserMemory]:
        """Load active memories belonging only to the authenticated user."""
        normalized_type = self._memory_type(memory_type) if memory_type is not None else None
        normalized_key = self._key(key) if key is not None else None
        return self._memory_store.list_by_user_id(user_id, normalized_type, normalized_key)

    def update_memory(
        self,
        user_id: int,
        memory_id: int,
        *,
        value: dict[str, Any] | None = None,
        key: str | None = None,
    ) -> UserMemory:
        """Update a caller-owned memory; changes preserve its type and user scope."""
        memory = self._get_owned_memory(memory_id, user_id)
        if key is not None:
            normalized_key = self._key(key)
            existing = self._memory_store.get_by_scope_and_key(user_id, memory.memory_type, normalized_key)
            if existing is not None and existing.id != memory.id:
                raise ConflictException("A memory with this type and key already exists.")
            memory.key = normalized_key
        if value is not None:
            memory.value = self._value(memory.memory_type, memory.key, value)
        if value is None and key is None:
            raise ValueError("At least one of value or key must be provided.")
        return self._memory_store.update(memory)

    def delete_memory(self, user_id: int, memory_id: int) -> None:
        """Soft-delete a caller-owned memory record."""
        self._memory_store.soft_delete(self._get_owned_memory(memory_id, user_id))

    def search_memory(
        self,
        user_id: int,
        query: str,
        memory_type: MemoryType | str | None = None,
        limit: int = 20,
    ) -> list[UserMemory]:
        """Search a caller's active memories by key or JSON content."""
        normalized_query = self._key(query)
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100.")
        normalized_type = self._memory_type(memory_type) if memory_type is not None else None
        return self._memory_store.search(user_id, normalized_query, normalized_type, limit)

    def save_profile(self, user_id: int, profile: ProfileMemory) -> UserMemory:
        """Create or replace the canonical structured PROFILE memory for a user."""
        existing = self._memory_store.get_by_scope_and_key(user_id, MemoryType.PROFILE, "profile")
        value = profile.model_dump(mode="json", exclude_none=True)
        if existing is None:
            return self.save_memory(user_id, MemoryType.PROFILE, "profile", value)
        existing.value = value
        return self._memory_store.update(existing)

    def load_profile(self, user_id: int) -> ProfileMemory | None:
        """Load and validate a user's canonical profile memory, if present."""
        memory = self._memory_store.get_by_scope_and_key(user_id, MemoryType.PROFILE, "profile")
        return ProfileMemory.model_validate(memory.value) if memory is not None else None

    def to_response(self, memory: UserMemory) -> MemoryResponse:
        """Serialize a database memory record for a future API boundary."""
        return MemoryResponse.model_validate(memory)

    def _get_owned_memory(self, memory_id: int, user_id: int) -> UserMemory:
        memory = self._memory_store.get_by_id_and_user_id(memory_id, user_id)
        if memory is None:
            raise NotFoundException("Memory not found.")
        return memory

    @staticmethod
    def _memory_type(memory_type: MemoryType | str) -> MemoryType:
        try:
            return memory_type if isinstance(memory_type, MemoryType) else MemoryType(memory_type.upper())
        except (AttributeError, ValueError) as error:
            raise ValueError("Unsupported memory type.") from error

    @staticmethod
    def _key(value: str) -> str:
        if not isinstance(value, str) or not (normalized := value.strip()):
            raise ValueError("Memory key and search query must be non-empty strings.")
        if len(normalized) > 100:
            raise ValueError("Memory key must not exceed 100 characters.")
        return normalized

    @staticmethod
    def _value(memory_type: MemoryType, key: str, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("Memory value must be a JSON object.")
        if memory_type == MemoryType.PROFILE and key == "profile":
            return ProfileMemory.model_validate(value).model_dump(mode="json", exclude_none=True)
        return value
