"""Category database model for shared defaults and user customizations."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class Category(PrimaryKeyMixin, TimestampMixin, Base):
    """A shared default category or a custom category owned by one user."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_categories_user_id_name"),
        CheckConstraint(
            "(is_default = 1 AND user_id IS NULL) OR (is_default = 0 AND user_id IS NOT NULL)",
            name="ck_categories_default_ownership",
        ),
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="category", passive_deletes=True
    )
