"""Application-specific exceptions with safe client-facing details."""

from typing import Any


class AppException(Exception):
    """Base exception for expected application failures."""

    status_code = 500
    default_message = "An unexpected application error occurred."

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    status_code = 404
    default_message = "The requested resource was not found."


class BadRequestException(AppException):
    status_code = 400
    default_message = "The request could not be processed."


class ConflictException(AppException):
    status_code = 409
    default_message = "The request conflicts with the current resource state."


class UnauthorizedException(AppException):
    status_code = 401
    default_message = "Authentication is required."


class ForbiddenException(AppException):
    status_code = 403
    default_message = "You do not have permission to perform this action."


class ValidationException(AppException):
    status_code = 422
    default_message = "The request validation failed."
