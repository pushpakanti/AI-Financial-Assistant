"""Create budgets table.

Revision ID: 20260801_0005
Revises: 20260801_0004
Create Date: 2026-08-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260801_0005"
down_revision: str | Sequence[str] | None = "20260801_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user-owned budgets optionally scoped to categories."""
    budget_type = sa.Enum("MONTHLY", "WEEKLY", "YEARLY", "CUSTOM", name="budget_type")
    budget_status = sa.Enum("ACTIVE", "COMPLETED", "EXPIRED", name="budget_status")
    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("budget_type", budget_type, nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("spent_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("remaining_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("alert_percentage", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("status", budget_status, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("amount > 0", name="ck_budgets_amount_positive"),
        sa.CheckConstraint("spent_amount >= 0", name="ck_budgets_spent_amount_nonnegative"),
        sa.CheckConstraint("remaining_amount >= 0", name="ck_budgets_remaining_amount_nonnegative"),
        sa.CheckConstraint(
            "alert_percentage >= 0 AND alert_percentage <= 100",
            name="ck_budgets_alert_percentage_range",
        ),
        sa.CheckConstraint("start_date <= end_date", name="ck_budgets_valid_date_range"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_budgets_user_id"), "budgets", ["user_id"], unique=False)
    op.create_index(op.f("ix_budgets_category_id"), "budgets", ["category_id"], unique=False)
    op.create_index(
        "ix_budgets_user_category_period",
        "budgets",
        ["user_id", "category_id", "start_date", "end_date"],
        unique=False,
    )


def downgrade() -> None:
    """Remove user-owned budgets."""
    op.drop_index("ix_budgets_user_category_period", table_name="budgets")
    op.drop_index(op.f("ix_budgets_category_id"), table_name="budgets")
    op.drop_index(op.f("ix_budgets_user_id"), table_name="budgets")
    op.drop_table("budgets")
