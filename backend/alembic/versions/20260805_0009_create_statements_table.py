"""Create statement import audit table.

Revision ID: 20260805_0009
Revises: 20260801_0008
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0009"
down_revision: str | Sequence[str] | None = "20260801_0008"
branch_labels = None
depends_on = None

def upgrade() -> None:
    status = sa.Enum("PREVIEWED", "IMPORTED", "FAILED", name="statement_status")
    op.create_table("statements", sa.Column("id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("bank_name", sa.String(255), nullable=True), sa.Column("statement_month", sa.Integer(), nullable=False), sa.Column("statement_year", sa.Integer(), nullable=False), sa.Column("file_type", sa.String(10), nullable=False), sa.Column("total_transactions", sa.Integer(), nullable=False), sa.Column("imported_transactions", sa.Integer(), nullable=False), sa.Column("status", status, nullable=False), sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False), sa.Column("preview_data", sa.JSON(), nullable=False), sa.Column("account_id", sa.Integer(), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_statements_user_id"), "statements", ["user_id"], unique=False)

def downgrade() -> None:
    op.drop_index(op.f("ix_statements_user_id"), table_name="statements")
    op.drop_table("statements")
