"""Groq OpenAI-compatible REST adapter for the gateway contract."""

import json
import time
from collections.abc import Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.ai.providers.base import BaseLLMProvider, LLMProviderError, LLMResponse, LLMStreamChunk


class GroqProvider(BaseLLMProvider):
    """Use Groq's OpenAI-compatible REST API without an SDK dependency."""

    name = "groq"
    _base_url = "https://api.groq.com/openai/v1"

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        selected_model = model or self._default_model
        started = time.perf_counter()
        payload = self._request_json(
            f"{self._base_url}/chat/completions",
            self._payload(prompt, system_prompt, selected_model, temperature, max_tokens),
        )
        content = payload.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise LLMProviderError("Groq returned no generated content.", retryable=True)
        usage = payload.get("usage", {})
        return LLMResponse(
            content=content,
            provider=self.name,
            model=payload.get("model", selected_model),
            latency_ms=(time.perf_counter() - started) * 1000,
            usage=self._usage(
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
            ),
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
        selected_model = model or self._default_model
        payload = self._payload(prompt, system_prompt, selected_model, temperature, max_tokens)
        payload["stream"] = True
        request = Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310 - provider URL is constant
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        return
                    event = json.loads(data)
                    choice = (event.get("choices") or [{}])[0]
                    content = choice.get("delta", {}).get("content", "")
                    if content:
                        yield LLMStreamChunk(
                            content=content,
                            provider=self.name,
                            model=event.get("model", selected_model),
                            finish_reason=choice.get("finish_reason"),
                        )
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise self._provider_error(error) from error

    def health_check(self) -> bool:
        """Verify the configured key can access Groq's model listing."""
        if not self.is_configured:
            return False
        request = Request(f"{self._base_url}/models", headers=self._headers())
        try:
            with urlopen(request, timeout=self._timeout_seconds):  # noqa: S310 - provider URL is constant
                return True
        except (HTTPError, URLError, TimeoutError):
            return False

    def _request_json(self, url: str, payload: dict) -> dict:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310 - provider URL is constant
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise self._provider_error(error) from error

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._require_api_key()}", "Content-Type": "application/json"}

    @staticmethod
    def _payload(
        prompt: str, system_prompt: str | None, model: str, temperature: float | None, max_tokens: int | None
    ) -> dict:
        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        return {
            "model": model,
            "messages": messages,
            **({"temperature": temperature} if temperature is not None else {}),
            **({"max_tokens": max_tokens} if max_tokens is not None else {}),
        }

    @staticmethod
    def _provider_error(error: Exception) -> LLMProviderError:
        if isinstance(error, HTTPError):
            return LLMProviderError(
                f"Groq request failed with HTTP {error.code}.", retryable=error.code >= 500 or error.code == 429
            )
        return LLMProviderError("Groq request failed.", retryable=True)
