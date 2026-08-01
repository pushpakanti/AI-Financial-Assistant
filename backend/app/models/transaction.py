"""Transaction database model for user-owned financial activity."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum as SqlEnum, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category


class TransactionType(str, Enum):
    """Supported financial transaction classifications."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class Transaction(PrimaryKeyMixin, TimestampMixin, Base):
    """A financial transaction belonging to a user and one of their accounts."""

    __tablename__ = "transactions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        SqlEnum(TransactionType, name="transaction_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    merchant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    receipt_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    category: Mapped["Category | None"] = relationship("Category", back_populates="transactions")
