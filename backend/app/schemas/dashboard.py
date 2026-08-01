"""Structured response schemas for the authenticated dashboard."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.budget import BudgetStatus
from app.models.transaction import TransactionType


class UserSummary(BaseModel):
    total_accounts: int
    total_balance: Decimal
    monthly_income: Decimal
    monthly_expense: Decimal
    net_cash_flow: Decimal
    total_transactions: int
    active_budgets: int
    budget_alerts: int


class MonthlyCashFlowPoint(BaseModel):
    month: str
    income: Decimal
    expense: Decimal


class ExpenseByCategoryPoint(BaseModel):
    category_id: int | None
    category_name: str
    amount: Decimal


class ExpenseByMerchantPoint(BaseModel):
    merchant: str
    amount: Decimal


class DailySpendingPoint(BaseModel):
    date: date
    amount: Decimal


class BudgetProgressPoint(BaseModel):
    budget_id: int
    name: str
    category_id: int | None
    amount: Decimal
    spent: Decimal
    remaining: Decimal
    percentage_used: Decimal
    alert_percentage: Decimal
    status: BudgetStatus
    end_date: date


class DashboardCharts(BaseModel):
    monthly_income_vs_expense: list[MonthlyCashFlowPoint]
    expense_by_category: list[ExpenseByCategoryPoint]
    expense_by_merchant: list[ExpenseByMerchantPoint]
    daily_spending: list[DailySpendingPoint]
    budget_progress: list[BudgetProgressPoint]


class RecentTransaction(BaseModel):
    id: int
    title: str
    amount: Decimal
    transaction_type: TransactionType
    transaction_date: date
    category_name: str | None
    merchant: str | None
    created_at: datetime


class DashboardActivity(BaseModel):
    recent_transactions: list[RecentTransaction]
    upcoming_budget_alerts: list[BudgetProgressPoint]
    largest_expense: RecentTransaction | None
    largest_income: RecentTransaction | None


class DashboardStatistics(BaseModel):
    average_daily_expense: Decimal
    average_monthly_expense: Decimal
    highest_spending_category: ExpenseByCategoryPoint | None
    highest_spending_merchant: ExpenseByMerchantPoint | None
    savings_rate: Decimal


class DashboardResponse(BaseModel):
    user_summary: UserSummary
    charts: DashboardCharts
    recent_activity: DashboardActivity
    statistics: DashboardStatistics
