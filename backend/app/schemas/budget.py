"""Pydantic schemas for budget validation, progress, and summaries."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.budget import BudgetStatus, BudgetType


BudgetName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Money = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]
Percentage = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]


class BudgetBase(BaseModel):
    """Shared validation for budget date ranges."""

    @model_validator(mode="after")
    def validate_date_range(self) -> "BudgetBase":
        """Ensure budget periods are not inverted."""
        start_date = getattr(self, "start_date", None)
        end_date = getattr(self, "end_date", None)
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError("start_date must be on or before end_date.")
        return self


class BudgetCreate(BudgetBase):
    """Validated payload for creating a budget."""

    category_id: Annotated[int, Field(gt=0)] | None = None
    name: BudgetName
    budget_type: BudgetType
    amount: Money
    start_date: date
    end_date: date
    alert_percentage: Percentage = Decimal("80.00")


class BudgetUpdate(BudgetBase):
    """Validated fields that may be updated on a budget."""

    category_id: Annotated[int, Field(gt=0)] | None = None
    name: BudgetName | None = None
    budget_type: BudgetType | None = None
    amount: Money | None = None
    start_date: date | None = None
    end_date: date | None = None
    alert_percentage: Percentage | None = None

    @model_validator(mode="after")
    def require_valid_update(self) -> "BudgetUpdate":
        """Reject empty updates and nulls for non-nullable budget fields."""
        if not self.model_fields_set:
            raise ValueError("At least one budget field must be provided.")
        non_nullable_fields = ("name", "budget_type", "amount", "start_date", "end_date", "alert_percentage")
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in non_nullable_fields
        ):
            raise ValueError("Required budget fields cannot be null.")
        return self


class BudgetResponse(BudgetBase):
    """Public budget representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int | None
    name: str
    budget_type: BudgetType
    amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    start_date: date
    end_date: date
    alert_percentage: Decimal
    status: BudgetStatus
    created_at: datetime
    updated_at: datetime


class BudgetProgress(BudgetResponse):
    """Budget state enriched with its current consumption percentage."""

    percentage_used: Decimal


class BudgetSummary(BaseModel):
    """Aggregate budget totals for one user."""

    budget_count: int
    active_budget_count: int
    completed_budget_count: int
    expired_budget_count: int
    total_budgeted: Decimal
    total_spent: Decimal
    total_remaining: Decimal
