"""Create goals table.

Revision ID: 20260801_0007
Revises: 20260801_0006
Create Date: 2026-08-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260801_0007"
down_revision: str | Sequence[str] | None = "20260801_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user-owned financial goals with derived contribution fields."""
    goal_priority = sa.Enum("LOW", "MEDIUM", "HIGH", name="goal_priority")
    goal_status = sa.Enum("ACTIVE", "COMPLETED", "OVERDUE", name="goal_status")
    op.create_table(
        "goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("target_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("current_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("priority", goal_priority, nullable=False),
        sa.Column("status", goal_status, nullable=False),
        sa.Column("monthly_required", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("target_amount > 0", name="ck_goals_target_amount_positive"),
        sa.CheckConstraint("current_amount >= 0", name="ck_goals_current_amount_nonnegative"),
        sa.CheckConstraint("monthly_required >= 0", name="ck_goals_monthly_required_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_goals_user_id"), "goals", ["user_id"], unique=False)
    op.create_index(op.f("ix_goals_deadline"), "goals", ["deadline"], unique=False)
    op.create_index("ix_goals_user_status_deadline", "goals", ["user_id", "status", "deadline"], unique=False)


def downgrade() -> None:
    """Remove user-owned financial goals."""
    op.drop_index("ix_goals_user_status_deadline", table_name="goals")
    op.drop_index(op.f("ix_goals_deadline"), table_name="goals")
    op.drop_index(op.f("ix_goals_user_id"), table_name="goals")
    op.drop_table("goals")
