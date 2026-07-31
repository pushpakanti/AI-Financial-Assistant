"""Database access operations for user-owned transactions."""

from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import TransactionFilter


class TransactionRepository:
    """Encapsulate transaction persistence and user-scoped queries."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, transaction: Transaction) -> Transaction:
        """Persist and return a new transaction."""
        self._db.add(transaction)
        self._db.commit()
        self._db.refresh(transaction)
        return transaction

    def get_by_id_and_user_id(self, transaction_id: int, user_id: int) -> Transaction | None:
        """Return a transaction only when it is owned by the supplied user."""
        statement = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
        return self._db.scalar(statement)

    def list_by_user_id(self, user_id: int, filters: TransactionFilter) -> tuple[list[Transaction], int]:
        """Return a filtered, paginated page of a user's transactions."""
        statement = self._filtered_statement(user_id, filters)
        total = self._count(statement)
        items = list(
            self._db.scalars(
                statement.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
                .offset(filters.offset)
                .limit(filters.limit)
            )
        )
        return items, total

    def search_by_user_id(
        self, user_id: int, query: str, limit: int, offset: int
    ) -> tuple[list[Transaction], int]:
        """Search title, description, and merchant within a user's transactions."""
        pattern = f"%{query}%"
        statement = select(Transaction).where(
            Transaction.user_id == user_id,
            or_(
                Transaction.title.ilike(pattern),
                Transaction.description.ilike(pattern),
                Transaction.merchant.ilike(pattern),
            ),
        )
        total = self._count(statement)
        items = list(
            self._db.scalars(
                statement.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return items, total

    def summary_by_user_id(self, user_id: int, filters: TransactionFilter) -> dict[str, Decimal | int]:
        """Aggregate user-owned transactions using optional filter criteria."""
        statement = self._filtered_statement(user_id, filters).with_only_columns(
            func.count(Transaction.id).label("transaction_count"),
            func.coalesce(
                func.sum(case((Transaction.transaction_type == TransactionType.INCOME, Transaction.amount), else_=0)),
                0,
            ).label("total_income"),
            func.coalesce(
                func.sum(case((Transaction.transaction_type == TransactionType.EXPENSE, Transaction.amount), else_=0)),
                0,
            ).label("total_expense"),
            func.coalesce(
                func.sum(case((Transaction.transaction_type == TransactionType.TRANSFER, Transaction.amount), else_=0)),
                0,
            ).label("total_transfer"),
        )
        row = self._db.execute(statement).one()
        income = Decimal(row.total_income)
        expense = Decimal(row.total_expense)
        return {
            "transaction_count": row.transaction_count,
            "total_income": income,
            "total_expense": expense,
            "total_transfer": Decimal(row.total_transfer),
            "net_cash_flow": income - expense,
        }

    def update(self, transaction: Transaction) -> Transaction:
        """Commit changes made to a transaction and return its refreshed state."""
        self._db.commit()
        self._db.refresh(transaction)
        return transaction

    def delete(self, transaction: Transaction) -> None:
        """Remove a transaction permanently."""
        self._db.delete(transaction)
        self._db.commit()

    def _filtered_statement(self, user_id: int, filters: TransactionFilter):
        statement = select(Transaction).where(Transaction.user_id == user_id)
        if filters.account_id is not None:
            statement = statement.where(Transaction.account_id == filters.account_id)
        if filters.category_id is not None:
            statement = statement.where(Transaction.category_id == filters.category_id)
        if filters.transaction_type is not None:
            statement = statement.where(Transaction.transaction_type == filters.transaction_type)
        if filters.start_date is not None:
            statement = statement.where(Transaction.transaction_date >= filters.start_date)
        if filters.end_date is not None:
            statement = statement.where(Transaction.transaction_date <= filters.end_date)
        if filters.merchant is not None:
            statement = statement.where(Transaction.merchant.ilike(f"%{filters.merchant}%"))
        return statement

    def _count(self, statement) -> int:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        return int(self._db.scalar(count_statement) or 0)
