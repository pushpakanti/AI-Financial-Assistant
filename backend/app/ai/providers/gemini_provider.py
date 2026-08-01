"""Google Gemini REST adapter for the provider-neutral gateway contract."""

import json
import time
from collections.abc import Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.ai.providers.base import BaseLLMProvider, LLMProviderError, LLMResponse, LLMStreamChunk


class GeminiProvider(BaseLLMProvider):
    """Use Gemini's REST API without requiring an additional SDK dependency."""

    name = "gemini"
    _base_url = "https://generativelanguage.googleapis.com/v1beta/models"

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
            f"{self._model_url(selected_model)}:generateContent",
            self._payload(prompt, system_prompt, temperature, max_tokens),
        )
        content = self._content_from_response(payload)
        usage = payload.get("usageMetadata", {})
        return LLMResponse(
            content=content,
            provider=self.name,
            model=selected_model,
            latency_ms=(time.perf_counter() - started) * 1000,
            usage=self._usage(
                input_tokens=usage.get("promptTokenCount"),
                output_tokens=usage.get("candidatesTokenCount"),
                total_tokens=usage.get("totalTokenCount"),
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
        request = Request(
            f"{self._model_url(selected_model)}:streamGenerateContent?alt=sse&key={quote(self._require_api_key())}",
            data=json.dumps(self._payload(prompt, system_prompt, temperature, max_tokens)).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310 - provider URL is constant
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = json.loads(line.removeprefix("data:").strip())
                    content = self._content_from_response(payload, allow_empty=True)
                    if content:
                        yield LLMStreamChunk(content=content, provider=self.name, model=selected_model)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise self._provider_error(error) from error

    def health_check(self) -> bool:
        """Verify the configured key can retrieve the selected Gemini model metadata."""
        if not self.is_configured:
            return False
        request = Request(f"{self._model_url(self._default_model)}?key={quote(self._require_api_key())}")
        try:
            with urlopen(request, timeout=self._timeout_seconds):  # noqa: S310 - provider URL is constant
                return True
        except (HTTPError, URLError, TimeoutError):
            return False

    def _model_url(self, model: str) -> str:
        return f"{self._base_url}/{quote(model, safe='-._')}"

    def _request_json(self, url: str, payload: dict) -> dict:
        request = Request(
            f"{url}?key={quote(self._require_api_key())}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310 - provider URL is constant
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise self._provider_error(error) from error

    @staticmethod
    def _payload(
        prompt: str, system_prompt: str | None, temperature: float | None, max_tokens: int | None
    ) -> dict:
        payload: dict = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        generation_config = {
            key: value
            for key, value in {"temperature": temperature, "maxOutputTokens": max_tokens}.items()
            if value is not None
        }
        if generation_config:
            payload["generationConfig"] = generation_config
        return payload

    @staticmethod
    def _content_from_response(payload: dict, allow_empty: bool = False) -> str:
        candidates = payload.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        content = "".join(part.get("text", "") for part in parts)
        if not content and not allow_empty:
            raise LLMProviderError("Gemini returned no generated content.", retryable=True)
        return content

    @staticmethod
    def _provider_error(error: Exception) -> LLMProviderError:
        if isinstance(error, HTTPError):
            return LLMProviderError(
                f"Gemini request failed with HTTP {error.code}.", retryable=error.code >= 500 or error.code == 429
            )
        return LLMProviderError("Gemini request failed.", retryable=True)
