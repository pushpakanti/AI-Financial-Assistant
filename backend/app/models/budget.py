"""Budget database model for user-owned spending plans."""

from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, Date, Enum as SqlEnum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class BudgetType(str, Enum):
    """Supported budget periods."""

    MONTHLY = "MONTHLY"
    WEEKLY = "WEEKLY"
    YEARLY = "YEARLY"
    CUSTOM = "CUSTOM"


class BudgetStatus(str, Enum):
    """Current lifecycle state of a budget."""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class Budget(PrimaryKeyMixin, TimestampMixin, Base):
    """A user-owned spending budget, optionally limited to one category."""

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_budgets_amount_positive"),
        CheckConstraint("spent_amount >= 0", name="ck_budgets_spent_amount_nonnegative"),
        CheckConstraint("remaining_amount >= 0", name="ck_budgets_remaining_amount_nonnegative"),
        CheckConstraint(
            "alert_percentage >= 0 AND alert_percentage <= 100",
            name="ck_budgets_alert_percentage_range",
        ),
        CheckConstraint("start_date <= end_date", name="ck_budgets_valid_date_range"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    budget_type: Mapped[BudgetType] = mapped_column(
        SqlEnum(BudgetType, name="budget_type"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    spent_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    alert_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=80)
    status: Mapped[BudgetStatus] = mapped_column(
        SqlEnum(BudgetStatus, name="budget_status"), nullable=False, default=BudgetStatus.ACTIVE
    )
