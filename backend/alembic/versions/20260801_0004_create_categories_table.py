"""Create categories table and link transactions to categories.

Revision ID: 20260801_0004
Revises: 20260801_0003
Create Date: 2026-08-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260801_0004"
down_revision: str | Sequence[str] | None = "20260801_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create shared/custom categories and enforce their transaction relationship."""
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_categories_user_id_name"),
        sa.CheckConstraint(
            "(is_default = 1 AND user_id IS NULL) OR (is_default = 0 AND user_id IS NOT NULL)",
            name="ck_categories_default_ownership",
        ),
    )
    op.create_index(op.f("ix_categories_user_id"), "categories", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_transactions_category_id_categories",
        "transactions",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Remove category relationship and categories table."""
    op.drop_constraint("fk_transactions_category_id_categories", "transactions", type_="foreignkey")
    op.drop_index(op.f("ix_categories_user_id"), table_name="categories")
    op.drop_table("categories")
