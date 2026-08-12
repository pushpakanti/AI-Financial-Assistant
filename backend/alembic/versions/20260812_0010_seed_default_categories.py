"""seed_default_categories

Revision ID: 20260812_0010
Revises: 20260805_0009
Create Date: 2026-08-12 20:55:18.269996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import datetime


# revision identifiers, used by Alembic.
revision: str = '20260812_0010'
down_revision: Union[str, Sequence[str], None] = '20260805_0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use connection to check for existing categories
    bind = op.get_bind()
    
    categories_to_seed = [
        "Food",
        "Shopping",
        "Transport",
        "Bills",
        "Entertainment",
        "Healthcare",
        "Education",
        "Travel",
        "Salary",
        "Investment",
        "Miscellaneous",
        "Uncategorized",
    ]
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    for name in categories_to_seed:
        # Check if default category exists
        res = bind.execute(
            sa.text("SELECT id FROM categories WHERE user_id IS NULL AND name = :name AND is_default = 1"),
            {"name": name}
        ).fetchone()
        
        if not res:
            bind.execute(
                sa.text("INSERT INTO categories (name, is_default, is_active, user_id, created_at, updated_at) VALUES (:name, 1, 1, NULL, :now, :now)"),
                {"name": name, "now": now}
            )


def downgrade() -> None:
    bind = op.get_bind()
    categories_to_delete = [
        "Food",
        "Shopping",
        "Transport",
        "Bills",
        "Entertainment",
        "Healthcare",
        "Education",
        "Travel",
        "Salary",
        "Investment",
        "Miscellaneous",
        "Uncategorized",
    ]
    for name in categories_to_delete:
        bind.execute(
            sa.text("DELETE FROM categories WHERE user_id IS NULL AND name = :name AND is_default = 1"),
            {"name": name}
        )
