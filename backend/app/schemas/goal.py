"""Pydantic schemas for financial goals, progress, predictions, and recommendations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.goal import GoalPriority, GoalStatus


GoalTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
GoalAmount = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]
CurrentAmount = Annotated[Decimal, Field(ge=0, max_digits=15, decimal_places=2)]


class GoalCreate(BaseModel):
    """Validated payload for creating a financial goal."""

    title: GoalTitle
    target_amount: GoalAmount
    current_amount: CurrentAmount = Decimal("0.00")
    deadline: date
    priority: GoalPriority = GoalPriority.MEDIUM


class GoalUpdate(BaseModel):
    """Validated fields that may be updated on a financial goal."""

    title: GoalTitle | None = None
    target_amount: GoalAmount | None = None
    current_amount: CurrentAmount | None = None
    deadline: date | None = None
    priority: GoalPriority | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "GoalUpdate":
        """Reject empty updates and nulls for non-nullable goal fields."""
        if not self.model_fields_set:
            raise ValueError("At least one goal field must be provided.")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Goal fields cannot be null.")
        return self


class GoalResponse(BaseModel):
    """Public financial goal representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: date
    priority: GoalPriority
    status: GoalStatus
    monthly_required: Decimal
    created_at: datetime
    updated_at: datetime


class GoalProgress(GoalResponse):
    """Goal with current remaining amount and completion percentage."""

    remaining_amount: Decimal
    percentage_complete: Decimal
    days_remaining: int


class GoalPrediction(BaseModel):
    """Rule-based forecast that describes what is required to hit a goal deadline."""

    goal_id: int
    projected_completion_date: date | None
    required_monthly_contribution: Decimal
    remaining_amount: Decimal
    status: GoalStatus
    prediction_basis: str


class GoalRecommendation(BaseModel):
    """Rule-based next actions for one financial goal."""

    goal_id: int
    priority: GoalPriority
    status: GoalStatus
    recommendations: list[str]


class GoalSummary(BaseModel):
    """Aggregate current goal metrics for a user."""

    total_goals: int
    active_goals: int
    completed_goals: int
    overdue_goals: int
    total_target_amount: Decimal
    total_current_amount: Decimal
    total_remaining_amount: Decimal
    overall_completion_percentage: Decimal
