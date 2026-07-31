"""Pydantic schemas for transaction validation, filtering, and responses."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.transaction import TransactionType


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
PaymentMethod = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)]
Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Amount = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]


class TransactionBase(BaseModel):
    """Shared fields for transaction write payloads."""

    @field_validator("tags", mode="after", check_fields=False)
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        """Remove duplicates while preserving input order."""
        return list(dict.fromkeys(tag.casefold() for tag in tags))


class TransactionCreate(TransactionBase):
    """Validated payload for creating a transaction."""

    account_id: Annotated[int, Field(gt=0)]
    category_id: Annotated[int, Field(gt=0)] | None = None
    transaction_type: TransactionType
    title: Title
    description: Description | None = None
    amount: Amount
    transaction_date: date
    merchant: ShortText | None = None
    payment_method: PaymentMethod | None = None
    location: ShortText | None = None
    tags: Annotated[list[Tag], Field(max_length=50)] = Field(default_factory=list)
    receipt_url: AnyHttpUrl | None = None


class TransactionUpdate(TransactionBase):
    """Validated payload for replacing selected transaction fields."""

    account_id: Annotated[int, Field(gt=0)] | None = None
    category_id: Annotated[int, Field(gt=0)] | None = None
    transaction_type: TransactionType | None = None
    title: Title | None = None
    description: Description | None = None
    amount: Amount | None = None
    transaction_date: date | None = None
    merchant: ShortText | None = None
    payment_method: PaymentMethod | None = None
    location: ShortText | None = None
    tags: Annotated[list[Tag], Field(max_length=50)] | None = None
    receipt_url: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "TransactionUpdate":
        """Reject empty update requests."""
        if not self.model_fields_set:
            raise ValueError("At least one transaction field must be provided.")
        non_nullable_fields = (
            "account_id",
            "transaction_type",
            "title",
            "amount",
            "transaction_date",
        )
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in non_nullable_fields
        ):
            raise ValueError("Required transaction fields cannot be null.")
        return self


class TransactionResponse(TransactionBase):
    """Public transaction representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    category_id: int | None
    transaction_type: TransactionType
    title: str
    description: str | None
    amount: Decimal
    transaction_date: date
    merchant: str | None
    payment_method: str | None
    location: str | None
    tags: list[str]
    receipt_url: AnyHttpUrl | None
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Reusable offset pagination settings."""

    limit: Annotated[int, Field(default=20, ge=1, le=100)] = 20
    offset: Annotated[int, Field(default=0, ge=0)] = 0


class TransactionFilter(PaginationParams):
    """Supported server-side transaction filtering criteria."""

    account_id: Annotated[int, Field(gt=0)] | None = None
    category_id: Annotated[int, Field(gt=0)] | None = None
    transaction_type: TransactionType | None = None
    start_date: date | None = None
    end_date: date | None = None
    merchant: ShortText | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "TransactionFilter":
        """Reject inverted date ranges before querying the database."""
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date.")
        return self


class TransactionSearch(PaginationParams):
    """Search parameters for transaction free-text search."""

    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class TransactionPage(BaseModel):
    """Page of transactions with pagination metadata."""

    items: list[TransactionResponse]
    total: int
    limit: int
    offset: int


class TransactionSummary(BaseModel):
    """Aggregated transaction totals for a user and optional filters."""

    transaction_count: int
    total_income: Decimal
    total_expense: Decimal
    total_transfer: Decimal
    net_cash_flow: Decimal
