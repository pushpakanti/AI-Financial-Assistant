"""Set-based SQLAlchemy queries used by the authenticated dashboard."""

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, extract, func, or_, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType


class DashboardRepository:
    """Provide fixed-count aggregate queries without per-record lookups."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def account_totals(self, user_id: int) -> tuple[int, Decimal]:
        statement = select(func.count(Account.id), func.coalesce(func.sum(Account.balance), 0)).where(
            Account.user_id == user_id
        )
        count, balance = self._db.execute(statement).one()
        return int(count), Decimal(balance)

    def transaction_overview(self, user_id: int, month_start: date, month_end: date) -> tuple[int, Decimal, Decimal]:
        statement = select(
            func.count(Transaction.id),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.transaction_type == TransactionType.INCOME,
                                Transaction.transaction_date >= month_start,
                                Transaction.transaction_date <= month_end,
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.transaction_type == TransactionType.EXPENSE,
                                Transaction.transaction_date >= month_start,
                                Transaction.transaction_date <= month_end,
                            ),
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(Transaction.user_id == user_id)
        count, income, expense = self._db.execute(statement).one()
        return int(count), Decimal(income), Decimal(expense)

    def monthly_cash_flow(self, user_id: int, start_date: date) -> list[tuple[int, int, Decimal, Decimal]]:
        year = extract("year", Transaction.transaction_date)
        month = extract("month", Transaction.transaction_date)
        statement = (
            select(
                year.label("year"),
                month.label("month"),
                func.coalesce(
                    func.sum(case((Transaction.transaction_type == TransactionType.INCOME, Transaction.amount), else_=0)),
                    0,
                ).label("income"),
                func.coalesce(
                    func.sum(case((Transaction.transaction_type == TransactionType.EXPENSE, Transaction.amount), else_=0)),
                    0,
                ).label("expense"),
            )
            .where(Transaction.user_id == user_id, Transaction.transaction_date >= start_date)
            .group_by(year, month)
            .order_by(year, month)
        )
        return [(int(year), int(month), Decimal(income), Decimal(expense)) for year, month, income, expense in self._db.execute(statement)]

    def expenses_by_category(self, user_id: int, month_start: date, month_end: date) -> list[tuple[int | None, str, Decimal]]:
        category_name = func.coalesce(Category.name, "Uncategorized")
        statement = (
            select(
                Transaction.category_id,
                category_name.label("category_name"),
                func.coalesce(func.sum(Transaction.amount), 0).label("amount"),
            )
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date <= month_end,
            )
            .group_by(Transaction.category_id, category_name)
            .order_by(func.sum(Transaction.amount).desc(), category_name.asc())
        )
        return [(category_id, name, Decimal(amount)) for category_id, name, amount in self._db.execute(statement)]

    def expenses_by_merchant(self, user_id: int, month_start: date, month_end: date) -> list[tuple[str, Decimal]]:
        merchant = func.coalesce(Transaction.merchant, "Unspecified")
        statement = (
            select(merchant.label("merchant"), func.coalesce(func.sum(Transaction.amount), 0).label("amount"))
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date <= month_end,
            )
            .group_by(merchant)
            .order_by(func.sum(Transaction.amount).desc(), merchant.asc())
            .limit(10)
        )
        return [(merchant_name, Decimal(amount)) for merchant_name, amount in self._db.execute(statement)]

    def daily_spending(self, user_id: int, month_start: date, month_end: date) -> list[tuple[date, Decimal]]:
        statement = (
            select(Transaction.transaction_date, func.coalesce(func.sum(Transaction.amount), 0))
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date <= month_end,
            )
            .group_by(Transaction.transaction_date)
            .order_by(Transaction.transaction_date)
        )
        return [(transaction_date, Decimal(amount)) for transaction_date, amount in self._db.execute(statement)]

    def budget_progress(self, user_id: int) -> list[tuple]:
        spent = func.coalesce(func.sum(Transaction.amount), 0).label("spent")
        statement = (
            select(
                Budget.id,
                Budget.name,
                Budget.category_id,
                Budget.amount,
                Budget.alert_percentage,
                Budget.end_date,
                spent,
            )
            .outerjoin(
                Transaction,
                and_(
                    Transaction.user_id == user_id,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.transaction_date >= Budget.start_date,
                    Transaction.transaction_date <= Budget.end_date,
                    or_(Budget.category_id.is_(None), Transaction.category_id == Budget.category_id),
                ),
            )
            .where(Budget.user_id == user_id)
            .group_by(
                Budget.id,
                Budget.name,
                Budget.category_id,
                Budget.amount,
                Budget.alert_percentage,
                Budget.end_date,
            )
            .order_by(Budget.end_date, Budget.id)
        )
        return list(self._db.execute(statement))

    def recent_transactions(self, user_id: int) -> list[tuple]:
        statement = (
            select(
                Transaction.id,
                Transaction.title,
                Transaction.amount,
                Transaction.transaction_type,
                Transaction.transaction_date,
                Category.name,
                Transaction.merchant,
                Transaction.created_at,
            )
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
            .limit(10)
        )
        return list(self._db.execute(statement))

    def largest_transaction(self, user_id: int, transaction_type: TransactionType) -> tuple | None:
        statement = (
            select(
                Transaction.id,
                Transaction.title,
                Transaction.amount,
                Transaction.transaction_type,
                Transaction.transaction_date,
                Category.name,
                Transaction.merchant,
                Transaction.created_at,
            )
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(Transaction.user_id == user_id, Transaction.transaction_type == transaction_type)
            .order_by(Transaction.amount.desc(), Transaction.transaction_date.desc(), Transaction.id.desc())
            .limit(1)
        )
        return self._db.execute(statement).one_or_none()
