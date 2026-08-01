"""Pydantic schemas for category validation and serialization."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


CategoryName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
Icon = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Color = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]


class CategoryBase(BaseModel):
    """Shared validation behavior for category payloads."""

    @field_validator("color", mode="before", check_fields=False)
    @classmethod
    def normalize_color(cls, value: object) -> object:
        """Normalize valid hexadecimal color values for stable storage."""
        return value.strip().upper() if isinstance(value, str) else value


class CategoryCreate(CategoryBase):
    """Validated payload for a caller-owned custom category."""

    name: CategoryName
    icon: Icon | None = None
    color: Color | None = None


class CategoryUpdate(CategoryBase):
    """Validated fields that can be updated on a custom category."""

    name: CategoryName | None = None
    icon: Icon | None = None
    color: Color | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "CategoryUpdate":
        """Reject empty update requests."""
        if not self.model_fields_set:
            raise ValueError("At least one category field must be provided.")
        return self


class CategoryResponse(CategoryBase):
    """Public category representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    icon: str | None
    color: str | None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CategoryUsageResponse(CategoryResponse):
    """Category metadata enriched with the caller's transaction usage count."""

    transaction_count: Annotated[int, Field(ge=0)]
