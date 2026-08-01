"""Create notifications table.

Revision ID: 20260801_0008
Revises: 20260801_0007
Create Date: 2026-08-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260801_0008"
down_revision: str | Sequence[str] | None = "20260801_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create in-app notifications with read state and user-scoped indexes."""
    notification_type = sa.Enum(
        "BUDGET_ALERT", "GOAL_REMINDER", "SALARY_REMINDER", "BILL_REMINDER", name="notification_type"
    )
    notification_priority = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="notification_priority")
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", notification_type, nullable=False),
        sa.Column("priority", notification_priority, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"], unique=False)
    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove in-app notification persistence."""
    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_index(op.f("ix_notifications_is_read"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
