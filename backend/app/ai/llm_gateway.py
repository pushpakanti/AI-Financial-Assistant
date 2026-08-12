"""Provider-agnostic LLM gateway with retry, fallback, and structured logging."""

import logging
import time
from collections.abc import Callable, Iterator, Mapping

from app.ai.config import LLMSettings
from app.ai.providers.base import BaseLLMProvider, LLMProviderError, LLMResponse, LLMStreamChunk
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.groq_provider import GroqProvider


logger = logging.getLogger(__name__)
ProviderFactory = Callable[[LLMSettings], BaseLLMProvider]


class LLMGateway:
    """Route requests to configured free-tier providers with safe automatic fallback."""

    _provider_factories: dict[str, ProviderFactory] = {
        "gemini": lambda settings: GeminiProvider(
            settings.GEMINI_API_KEY, settings.GEMINI_MODEL, settings.LLM_TIMEOUT_SECONDS
        ),
        "groq": lambda settings: GroqProvider(
            settings.GROQ_API_KEY, settings.GROQ_MODEL, settings.LLM_TIMEOUT_SECONDS
        ),
    }

    def __init__(
        self,
        settings: LLMSettings | None = None,
        providers: Mapping[str, BaseLLMProvider] | None = None,
    ) -> None:
        self._settings = settings or LLMSettings()
        self._providers = dict(providers) if providers is not None else self._build_providers()

    @classmethod
    def register_provider(cls, name: str, factory: ProviderFactory) -> None:
        """Register a provider factory so future adapters need no gateway code changes."""
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise ValueError("Provider name cannot be empty.")
        cls._provider_factories[normalized_name] = factory

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate one unified response with one preferred-provider fallback attempt."""
        self._validate_prompt(prompt)
        errors: list[str] = []
        for attempt, provider in enumerate(self._candidate_providers(prompt), start=1):
            try:
                response = provider.generate(
                    prompt,
                    system_prompt=system_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                logger.info(
                    "LLM generation succeeded provider=%s model=%s latency_ms=%.2f attempt=%s",
                    response.provider,
                    response.model,
                    response.latency_ms,
                    attempt,
                )
                return response
            except LLMProviderError as error:
                errors.append(f"{provider.name}: {error}")
                self._log_failure(provider.name, attempt - 1, error)
                self._log_fallback(prompt, attempt, provider.name)
            except Exception as error:  # pragma: no cover - protects the gateway boundary
                wrapped_error = LLMProviderError("Provider raised an unexpected error.")
                errors.append(f"{provider.name}: {wrapped_error}")
                self._log_failure(provider.name, attempt - 1, wrapped_error)
                self._log_fallback(prompt, attempt, provider.name)
        raise LLMProviderError(
            f"All configured LLM providers failed. {'; '.join(errors)}", retryable=False
        )

    def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[LLMStreamChunk]:
        """Stream unified chunks; fallback only before any content has been emitted."""
        self._validate_prompt(prompt)
        errors: list[str] = []
        for attempt, provider in enumerate(self._candidate_providers(prompt), start=1):
            emitted_content = False
            started = time.perf_counter()
            try:
                for chunk in provider.stream(
                    prompt,
                    system_prompt=system_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    emitted_content = emitted_content or bool(chunk.content)
                    yield chunk
                logger.info(
                    "LLM stream completed provider=%s latency_ms=%.2f attempt=%s",
                    provider.name,
                    (time.perf_counter() - started) * 1000,
                    attempt,
                )
                return
            except LLMProviderError as error:
                errors.append(f"{provider.name}: {error}")
                self._log_failure(provider.name, attempt - 1, error)
                if emitted_content:
                    raise
                self._log_fallback(prompt, attempt, provider.name)
            except Exception as error:  # pragma: no cover - protects the streaming boundary
                wrapped_error = LLMProviderError("Provider stream raised an unexpected error.")
                errors.append(f"{provider.name}: {wrapped_error}")
                self._log_failure(provider.name, attempt - 1, wrapped_error)
                if emitted_content:
                    raise wrapped_error from error
                self._log_fallback(prompt, attempt, provider.name)
        raise LLMProviderError(
            f"All configured LLM providers failed before streaming content. {'; '.join(errors)}",
            retryable=False,
        )

    def health_check(self) -> dict[str, bool]:
        """Return health status for each configured provider without selecting one."""
        return {name: provider.health_check() for name, provider in self._providers.items()}

    def _build_providers(self) -> dict[str, BaseLLMProvider]:
        provider_names = ["gemini", "groq", self._settings.LLM_PRIMARY_PROVIDER, *self._settings.fallback_provider_names]
        providers: dict[str, BaseLLMProvider] = {}
        for name in provider_names:
            factory = self._provider_factories.get(name)
            if factory is None:
                logger.warning("Configured LLM provider is not registered provider=%s", name)
                continue
            providers.setdefault(name, factory(self._settings))
        return providers

    def _candidate_providers(self, prompt: str) -> Iterator[BaseLLMProvider]:
        preferred_name, reason = self._provider_selection(prompt)
        alternate_name = "gemini" if preferred_name == "groq" else "groq"
        logger.info("Selected provider=%s reason=%s", preferred_name, reason)
        ordered_names = [preferred_name, alternate_name]
        yielded_names: set[str] = set()
        for name in ordered_names:
            if name in yielded_names:
                continue
            yielded_names.add(name)
            provider = self._providers.get(name)
            if provider is None:
                continue
            if not provider.is_configured:
                logger.warning("Skipping unconfigured LLM provider provider=%s", name)
                continue
            yield provider
        if not any(provider.is_configured for provider in self._providers.values()):
            logger.warning("No LLM providers were configured for the gateway.")

    @classmethod
    def _preferred_provider_name(cls, prompt: str) -> str:
        """Return the deterministic provider selection without exposing classifier details."""
        return cls._provider_selection(prompt)[0]

    @staticmethod
    def _provider_selection(prompt: str) -> tuple[str, str]:
        """Choose Gemini only for explicit reasoning-heavy user requests."""
        # Safely extract user request or merchant name based on known prompt construction patterns.
        request = ""
        for line in prompt.split("\n"):
            line_lower = line.lower()
            if "requested by the user:" in line_lower:
                request = line.split("requested by the user:", 1)[-1].strip()
                break
            elif "reporting context:" in line_lower:
                request = line.split("reporting context:", 1)[-1].strip()
                break
            elif "transaction:" in line_lower:
                request = line.split("transaction:", 1)[-1].strip()
                break
        if not request:
            # Fallback to the original extraction logic if no specific pattern matches
            request = prompt.split("\n", 1)[0].rsplit(":", 1)[-1].strip()

        request = request.casefold()

        complex_markers = (
            "multi-agent",
            "analysis",
            "analyze",
            "am i on track",
            "on track",
            "predict",
            "recommend",
            "suggest",
            "improve",
            "what should i do",
            "how can i",
            "explain",
            "why",
            "compare",
            "investment",
            "investing",
            "invested",
            "invest",
            "portfolio",
            "sip",
            "stock",
            "equity",
            "shares",
            "mutual fund",
            "cash flow",
            "cashflow",
            "savings",
            "financial health",
            "report",
            "trend",
            "plan",
            "planning",
        )
        if any(marker in request for marker in complex_markers):
            return "gemini", "financial_analysis"
        return "groq", "simple_lookup"

    def _log_fallback(self, prompt: str, attempt: int, failed_provider: str) -> None:
        """Log the one permitted alternate-provider retry without changing control flow."""
        if attempt != 1:
            return
        preferred_name = self._preferred_provider_name(prompt)
        alternate_name = "gemini" if preferred_name == "groq" else "groq"
        alternate = self._providers.get(alternate_name)
        if alternate is not None and alternate.is_configured and failed_provider == preferred_name:
            logger.warning("Primary provider failed. Falling back to %s.", alternate_name.title())

    @staticmethod
    def _validate_prompt(prompt: str) -> None:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string.")

    @staticmethod
    def _backoff(attempt: int) -> None:
        if attempt:
            time.sleep(min(0.25 * (2**attempt), 2.0))

    @staticmethod
    def _log_failure(provider_name: str, attempt: int, error: LLMProviderError) -> None:
        logger.warning(
            "LLM provider request failed provider=%s attempt=%s retryable=%s error=%s",
            provider_name,
            attempt + 1,
            error.retryable,
            error,
        )
