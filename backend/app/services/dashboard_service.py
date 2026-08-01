"""Compose authenticated dashboard analytics from set-based repository queries."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.models.budget import BudgetStatus
from app.models.transaction import TransactionType
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    BudgetProgressPoint,
    DashboardActivity,
    DashboardCharts,
    DashboardResponse,
    DashboardStatistics,
    DailySpendingPoint,
    ExpenseByCategoryPoint,
    ExpenseByMerchantPoint,
    MonthlyCashFlowPoint,
    RecentTransaction,
    UserSummary,
)


class DashboardService:
    """Build a complete dashboard without N+1 persistence access patterns."""

    def __init__(self, dashboard_repository: DashboardRepository) -> None:
        self._dashboard_repository = dashboard_repository

    def get_dashboard(self, user_id: int) -> DashboardResponse:
        """Return all dashboard sections scoped exclusively to one authenticated user."""
        today = date.today()
        month_start = today.replace(day=1)
        month_end = self._month_end(today)
        trend_start = self._shift_months(month_start, 11)

        account_count, total_balance = self._dashboard_repository.account_totals(user_id)
        transaction_count, monthly_income, monthly_expense = self._dashboard_repository.transaction_overview(
            user_id, month_start, month_end
        )
        monthly_rows = self._dashboard_repository.monthly_cash_flow(user_id, trend_start)
        category_rows = self._dashboard_repository.expenses_by_category(user_id, month_start, month_end)
        merchant_rows = self._dashboard_repository.expenses_by_merchant(user_id, month_start, month_end)
        daily_rows = self._dashboard_repository.daily_spending(user_id, month_start, month_end)
        budget_rows = self._dashboard_repository.budget_progress(user_id)
        recent_rows = self._dashboard_repository.recent_transactions(user_id)
        largest_expense = self._dashboard_repository.largest_transaction(user_id, TransactionType.EXPENSE)
        largest_income = self._dashboard_repository.largest_transaction(user_id, TransactionType.INCOME)

        monthly_cash_flow = self._fill_monthly_cash_flow(monthly_rows, trend_start)
        categories = [
            ExpenseByCategoryPoint(category_id=category_id, category_name=name, amount=amount)
            for category_id, name, amount in category_rows
        ]
        merchants = [ExpenseByMerchantPoint(merchant=name, amount=amount) for name, amount in merchant_rows]
        budget_progress = [self._budget_progress_point(row, today) for row in budget_rows]
        active_budgets = sum(item.status == BudgetStatus.ACTIVE for item in budget_progress)
        alerts = [
            item
            for item in budget_progress
            if item.status == BudgetStatus.ACTIVE and item.percentage_used >= item.alert_percentage
        ]

        total_trend_expense = sum((point.expense for point in monthly_cash_flow), Decimal("0.00"))
        net_cash_flow = monthly_income - monthly_expense
        savings_rate = self._percentage(net_cash_flow, monthly_income) if monthly_income else Decimal("0.00")
        average_daily_expense = (monthly_expense / Decimal(today.day)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        average_monthly_expense = (total_trend_expense / Decimal("12")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return DashboardResponse(
            user_summary=UserSummary(
                total_accounts=account_count,
                total_balance=total_balance,
                monthly_income=monthly_income,
                monthly_expense=monthly_expense,
                net_cash_flow=net_cash_flow,
                total_transactions=transaction_count,
                active_budgets=active_budgets,
                budget_alerts=len(alerts),
            ),
            charts=DashboardCharts(
                monthly_income_vs_expense=monthly_cash_flow,
                expense_by_category=categories,
                expense_by_merchant=merchants,
                daily_spending=[DailySpendingPoint(date=item_date, amount=amount) for item_date, amount in daily_rows],
                budget_progress=budget_progress,
            ),
            recent_activity=DashboardActivity(
                recent_transactions=[self._transaction_response(row) for row in recent_rows],
                upcoming_budget_alerts=alerts,
                largest_expense=self._transaction_response(largest_expense) if largest_expense else None,
                largest_income=self._transaction_response(largest_income) if largest_income else None,
            ),
            statistics=DashboardStatistics(
                average_daily_expense=average_daily_expense,
                average_monthly_expense=average_monthly_expense,
                highest_spending_category=categories[0] if categories else None,
                highest_spending_merchant=merchants[0] if merchants else None,
                savings_rate=savings_rate,
            ),
        )

    @staticmethod
    def _transaction_response(row: tuple) -> RecentTransaction:
        return RecentTransaction(
            id=row.id,
            title=row.title,
            amount=Decimal(row.amount),
            transaction_type=row.transaction_type,
            transaction_date=row.transaction_date,
            category_name=row.name,
            merchant=row.merchant,
            created_at=row.created_at,
        )

    def _budget_progress_point(self, row: tuple, today: date) -> BudgetProgressPoint:
        spent = Decimal(row.spent)
        amount = Decimal(row.amount)
        percentage_used = self._percentage(spent, amount)
        status = self._budget_status(amount, spent, row.end_date, today)
        return BudgetProgressPoint(
            budget_id=row.id,
            name=row.name,
            category_id=row.category_id,
            amount=amount,
            spent=spent,
            remaining=max(Decimal("0.00"), amount - spent),
            percentage_used=percentage_used,
            alert_percentage=Decimal(row.alert_percentage),
            status=status,
            end_date=row.end_date,
        )

    @staticmethod
    def _budget_status(amount: Decimal, spent: Decimal, end_date: date, today: date) -> BudgetStatus:
        if today > end_date:
            return BudgetStatus.EXPIRED
        if spent >= amount:
            return BudgetStatus.COMPLETED
        return BudgetStatus.ACTIVE

    @staticmethod
    def _percentage(value: Decimal, total: Decimal) -> Decimal:
        return (value / total * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _fill_monthly_cash_flow(
        self, rows: list[tuple[int, int, Decimal, Decimal]], start_month: date
    ) -> list[MonthlyCashFlowPoint]:
        by_month = {(year, month): (income, expense) for year, month, income, expense in rows}
        result: list[MonthlyCashFlowPoint] = []
        month = start_month
        for _ in range(12):
            income, expense = by_month.get((month.year, month.month), (Decimal("0.00"), Decimal("0.00")))
            result.append(MonthlyCashFlowPoint(month=month.strftime("%Y-%m"), income=income, expense=expense))
            month = self._shift_months(month, -1)
        return result

    @staticmethod
    def _month_end(value: date) -> date:
        return DashboardService._shift_months(value.replace(day=1), -1) - timedelta(days=1)

    @staticmethod
    def _shift_months(value: date, months_back: int) -> date:
        month_index = value.year * 12 + value.month - 1 - months_back
        year, month_zero_based = divmod(month_index, 12)
        return date(year, month_zero_based + 1, 1)
