"""Configuration for free-tier LLM providers loaded from environment variables."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]


class LLMSettings(BaseSettings):
    """Gateway settings kept separate from core application configuration."""

    LLM_PRIMARY_PROVIDER: str = "gemini"
    LLM_FALLBACK_PROVIDERS: str = "groq"
    LLM_MAX_RETRIES: int = Field(default=2, ge=0, le=5)
    LLM_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0, le=120)

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("LLM_PRIMARY_PROVIDER", "LLM_FALLBACK_PROVIDERS", mode="before")
    @classmethod
    def normalize_provider_names(cls, value: object) -> object:
        """Keep provider names predictable regardless of environment formatting."""
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @property
    def fallback_provider_names(self) -> list[str]:
        """Return normalized, de-duplicated fallback provider names."""
        names = [name.strip().lower() for name in self.LLM_FALLBACK_PROVIDERS.split(",")]
        return [name for index, name in enumerate(names) if name and name not in names[:index]]

settings = LLMSettings()
