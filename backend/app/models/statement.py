"""Statement import audit records; source files are never persisted."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import PrimaryKeyMixin, TimestampMixin, utc_now


class StatementStatus(str, Enum):
    PREVIEWED = "PREVIEWED"
    IMPORTED = "IMPORTED"
    FAILED = "FAILED"


class Statement(PrimaryKeyMixin, TimestampMixin, Base):
    """A user-owned, one-time import preview and its import state."""

    __tablename__ = "statements"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    statement_month: Mapped[int] = mapped_column(Integer, nullable=False)
    statement_year: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    total_transactions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_transactions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[StatementStatus] = mapped_column(SqlEnum(StatementStatus, name="statement_status"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    # Retained only until confirmation; it contains normalized values, never the uploaded file.
    preview_data: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
