"""Common contracts and errors for pluggable LLM provider adapters."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


class LLMProviderError(RuntimeError):
    """Expected provider failure that can be considered for retry or fallback."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        self.retryable = retryable
        super().__init__(message)


@dataclass
class LLMResponse:
    """Provider-neutral completed generation response."""

    content: str
    provider: str
    model: str
    latency_ms: float
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class LLMStreamChunk:
    """Provider-neutral incremental generation response."""

    content: str
    provider: str
    model: str
    finish_reason: str | None = None


class BaseLLMProvider(ABC):
    """Interface implemented by every LLM provider adapter."""

    name: str

    def __init__(self, api_key: str | None, default_model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        """Return whether this provider has the credentials required to make calls."""
        return bool(self._api_key)

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a complete response using the provider's API."""

    @abstractmethod
    def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[LLMStreamChunk]:
        """Yield incremental provider-neutral response chunks."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return whether the configured provider can be reached and authenticated."""

    def _require_api_key(self) -> str:
        if not self._api_key:
            raise LLMProviderError(f"{self.name} is not configured.", retryable=False)
        return self._api_key

    @staticmethod
    def _usage(*, input_tokens: Any = None, output_tokens: Any = None, total_tokens: Any = None) -> dict[str, int]:
        """Normalize optional provider usage fields without exposing provider payloads."""
        return {
            key: int(value)
            for key, value in {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }.items()
            if value is not None
        }
