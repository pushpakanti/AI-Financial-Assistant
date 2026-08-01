"""Database access operations for user-owned budgets."""

from datetime import date
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetStatus
from app.models.transaction import Transaction, TransactionType


class BudgetRepository:
    """Encapsulate budget persistence, ownership scopes, and expense aggregation."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, budget: Budget) -> Budget:
        """Persist and return a new budget."""
        self._db.add(budget)
        self._db.commit()
        self._db.refresh(budget)
        return budget

    def list_by_user_id(self, user_id: int) -> list[Budget]:
        """Return all budgets owned by a user, newest periods first."""
        statement = select(Budget).where(Budget.user_id == user_id).order_by(Budget.end_date.desc(), Budget.id.desc())
        return list(self._db.scalars(statement))

    def get_by_id_and_user_id(self, budget_id: int, user_id: int) -> Budget | None:
        """Return a budget only when it belongs to the supplied user."""
        statement = select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
        return self._db.scalar(statement)

    def active_duplicate_exists(
        self,
        user_id: int,
        category_id: int | None,
        start_date: date,
        end_date: date,
        exclude_budget_id: int | None = None,
    ) -> bool:
        """Return whether an identical active budget period already exists for a user/category."""
        conditions = [
            Budget.user_id == user_id,
            Budget.category_id.is_(None) if category_id is None else Budget.category_id == category_id,
            Budget.start_date == start_date,
            Budget.end_date == end_date,
            Budget.status == BudgetStatus.ACTIVE,
        ]
        if exclude_budget_id is not None:
            conditions.append(Budget.id != exclude_budget_id)
        return bool(self._db.scalar(select(exists().where(*conditions))))

    def calculate_spent_amount(
        self, user_id: int, category_id: int | None, start_date: date, end_date: date
    ) -> Decimal:
        """Sum expense transactions in a budget's category scope and date range."""
        statement = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        if category_id is not None:
            statement = statement.where(Transaction.category_id == category_id)
        return Decimal(self._db.scalar(statement) or 0)

    def save(self, budget: Budget) -> Budget:
        """Commit changes made to a budget and return its refreshed state."""
        self._db.commit()
        self._db.refresh(budget)
        return budget

    def has_budgets_for_category(self, category_id: int) -> bool:
        """Return whether any budget currently references a category."""
        statement = select(exists().where(Budget.category_id == category_id))
        return bool(self._db.scalar(statement))

    def save_all(self, budgets: list[Budget]) -> None:
        """Commit synchronized budget values in one transaction."""
        if budgets:
            self._db.commit()

    def delete(self, budget: Budget) -> None:
        """Remove a budget permanently."""
        self._db.delete(budget)
        self._db.commit()
