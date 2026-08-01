"""Create user memories table.

Revision ID: 20260801_0006
Revises: 20260801_0005
Create Date: 2026-08-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260801_0006"
down_revision: str | Sequence[str] | None = "20260801_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user-scoped typed memory records with JSON payloads."""
    memory_type = sa.Enum("PROCEDURAL", "SEMANTIC", "CONVERSATION", "PROFILE", name="memory_type")
    op.create_table(
        "user_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("memory_type", memory_type, nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "memory_type", "key", name="uq_user_memories_scope_key"),
    )
    op.create_index(op.f("ix_user_memories_user_id"), "user_memories", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_memories_memory_type"), "user_memories", ["memory_type"], unique=False)
    op.create_index(
        "ix_user_memories_user_type_active",
        "user_memories",
        ["user_id", "memory_type", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Remove user memory persistence."""
    op.drop_index("ix_user_memories_user_type_active", table_name="user_memories")
    op.drop_index(op.f("ix_user_memories_memory_type"), table_name="user_memories")
    op.drop_index(op.f("ix_user_memories_user_id"), table_name="user_memories")
    op.drop_table("user_memories")
