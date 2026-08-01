"""Financial goal database model owned by an application user."""

from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, Date, Enum as SqlEnum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import PrimaryKeyMixin, TimestampMixin


class GoalPriority(str, Enum):
    """Priority levels used to order financial goals."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class GoalStatus(str, Enum):
    """Lifecycle states derived from progress and the deadline."""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"


class Goal(PrimaryKeyMixin, TimestampMixin, Base):
    """A user-owned financial target with derived monthly contribution guidance."""

    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_goals_target_amount_positive"),
        CheckConstraint("current_amount >= 0", name="ck_goals_current_amount_nonnegative"),
        CheckConstraint("monthly_required >= 0", name="ck_goals_monthly_required_nonnegative"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    deadline: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    priority: Mapped[GoalPriority] = mapped_column(
        SqlEnum(GoalPriority, name="goal_priority"), nullable=False, default=GoalPriority.MEDIUM
    )
    status: Mapped[GoalStatus] = mapped_column(
        SqlEnum(GoalStatus, name="goal_status"), nullable=False, default=GoalStatus.ACTIVE
    )
    monthly_required: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
