"""Pydantic schemas for user data validation and serialization."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator


Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
Password = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=8, max_length=128),
]


class UserSchema(BaseModel):
    """Shared validation behavior for user schemas."""

    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def strip_email_whitespace(cls, value: object) -> object:
        """Remove accidental leading and trailing whitespace from email input."""
        return value.strip() if isinstance(value, str) else value


class UserCreate(UserSchema):
    """Validated payload for creating a user."""

    full_name: Name
    email: EmailStr
    password: Password


class UserLogin(UserSchema):
    """Validated credentials payload for a future authentication flow."""

    email: EmailStr
    password: Password


class UserResponse(UserSchema):
    """Public user representation that never exposes password data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(UserSchema):
    """Validated fields that may be updated for an existing user."""

    full_name: Name | None = None
    email: EmailStr | None = None
    password: Password | None = None
    is_active: bool | None = None
