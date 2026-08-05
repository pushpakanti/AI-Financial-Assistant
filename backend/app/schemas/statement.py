"""Public contracts for statement upload preview and confirmation."""

from datetime import date as Date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.statement import StatementStatus
from app.models.transaction import TransactionType


class StatementPreviewTransaction(BaseModel):
    row_number: int
    date: Date | None = None
    merchant: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    transaction_type: TransactionType | None = None
    category: str | None = None
    duplicate: bool = False
    valid: bool
    error: str | None = None


class StatementUploadPreview(BaseModel):
    statement_id: int
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    preview_transactions: list[StatementPreviewTransaction]
    warnings: list[str]


class StatementImportResponse(BaseModel):
    statement_id: int
    status: StatementStatus
    imported_transactions: int
    skipped_duplicates: int


class StatementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    bank_name: str | None
    statement_month: int
    statement_year: int
    file_type: str
    total_transactions: int
    imported_transactions: int
    status: StatementStatus
    uploaded_at: datetime
