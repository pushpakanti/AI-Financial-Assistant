"""Application configuration loaded from the backend `.env` file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed runtime configuration for the application."""

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str | None = None
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str | None = None

    APP_NAME: str
    APP_VERSION: str
    PROJECT_NAME: str = "AI Financial Assistant"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_DATABASE: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> URL:
        """Return a safely encoded SQLAlchemy MySQL connection URL."""
        return URL.create(
            drivername="mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_HOST,
            port=self.MYSQL_PORT,
            database=self.MYSQL_DATABASE,
        )


settings = Settings()
