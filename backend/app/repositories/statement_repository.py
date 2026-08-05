"""Persistence operations for statement import previews."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.statement import Statement
from app.models.transaction import Transaction, TransactionType


class StatementRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, statement: Statement) -> Statement:
        self._db.add(statement)
        self._db.commit()
        self._db.refresh(statement)
        return statement

    def get_by_id_and_user_id(self, statement_id: int, user_id: int) -> Statement | None:
        return self._db.scalar(select(Statement).where(Statement.id == statement_id, Statement.user_id == user_id))

    def save(self, statement: Statement) -> Statement:
        self._db.commit()
        self._db.refresh(statement)
        return statement

    def transaction_duplicate_exists(
        self, user_id: int, transaction_date: date, amount: Decimal, merchant: str, transaction_type: TransactionType
    ) -> bool:
        """Check the deterministic import identity without changing transaction repository APIs."""
        statement = select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date == transaction_date,
            Transaction.amount == amount,
            Transaction.transaction_type == transaction_type,
            func.lower(func.coalesce(Transaction.merchant, Transaction.description, Transaction.title)) == merchant.casefold(),
        ).limit(1)
        return self._db.scalar(statement) is not None
