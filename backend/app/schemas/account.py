"""Pydantic schemas for account data validation and serialization."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


AccountName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
AccountType = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
CurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=3),
]
Balance = Annotated[Decimal, Field(max_digits=15, decimal_places=2)]


class AccountBase(BaseModel):
    """Shared validation behavior for account payloads."""

    @field_validator("currency", mode="before", check_fields=False)
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        """Normalize ISO currency codes before validation and persistence."""
        return value.strip().upper() if isinstance(value, str) else value


class AccountCreate(AccountBase):
    """Validated payload for creating an account."""

    name: AccountName
    account_type: AccountType
    balance: Balance = Decimal("0.00")
    currency: CurrencyCode = "USD"


class AccountUpdate(AccountBase):
    """Validated payload for updating selected account fields."""

    name: AccountName | None = None
    account_type: AccountType | None = None
    balance: Balance | None = None
    currency: CurrencyCode | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "AccountUpdate":
        """Reject accidental empty update requests."""
        if not self.model_fields_set:
            raise ValueError("At least one account field must be provided.")
        return self


class AccountResponse(AccountBase):
    """Public account representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    account_type: str
    balance: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
