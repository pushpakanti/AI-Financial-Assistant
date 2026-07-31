"""FastAPI exception handlers that enforce the public error response contract."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException
from app.core.responses import ErrorResponse


logger = logging.getLogger(__name__)


def _error_response(
    *,
    status_code: int,
    message: str,
    errors: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Serialize a failure using the API's standard envelope."""
    payload = ErrorResponse(message=message, errors=errors or {}).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle expected domain failures."""
    logger.warning("Application exception on %s: %s", request.url.path, exc.message)
    return _error_response(
        status_code=exc.status_code,
        message=exc.message,
        errors=exc.details,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Normalize FastAPI and Starlette HTTP errors."""
    detail = exc.detail
    errors = detail if isinstance(detail, dict) else {"detail": detail}
    message = detail if isinstance(detail, str) else "The request could not be completed."
    logger.warning("HTTP %s on %s: %s", exc.status_code, request.url.path, message)
    return _error_response(
        status_code=exc.status_code,
        message=message,
        errors=errors,
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return request validation failures without exposing implementation state."""
    validation_errors = [
        {
            "location": list(error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    errors = {"validation": validation_errors}
    logger.warning("Request validation failed on %s", request.url.path)
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="The request validation failed.",
        errors=errors,
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Hide database exception details from API clients."""
    logger.exception("Database error on %s", request.url.path)
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="A database error occurred while processing the request.",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Hide all unexpected exception details from API clients."""
    logger.exception("Unhandled exception on %s", request.url.path)
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the application's complete exception handling policy."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
