"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.config import LLMSettings
from app.ai.providers.groq_provider import GroqProvider
from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging


configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def log_groq_startup_diagnostic() -> None:
    """Log safe Groq configuration and connectivity details without exposing credentials."""
    llm_settings = LLMSettings()
    provider = GroqProvider(
        llm_settings.GROQ_API_KEY, llm_settings.GROQ_MODEL, llm_settings.LLM_TIMEOUT_SECONDS
    )
    try:
        health_check = provider.health_check()
    except Exception:  # pragma: no cover - diagnostics must not block application startup
        logger.exception("Groq startup health check failed unexpectedly")
        health_check = False
    logger.info(
        "Groq startup diagnostic api_key_configured=%s model=%s health_check=%s",
        provider.is_configured,
        llm_settings.GROQ_MODEL,
        health_check,
    )


@app.get("/", tags=["health"])
def read_root() -> dict[str, str]:
    """Return a minimal service status response."""
    return {"message": f"{settings.APP_NAME} is running"}
