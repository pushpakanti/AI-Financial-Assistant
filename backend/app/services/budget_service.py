"""Business logic for user-owned budgets and transaction-derived progress."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.core.exceptions import ConflictException, NotFoundException
from app.models.budget import Budget, BudgetStatus
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.budget import BudgetCreate, BudgetUpdate


class BudgetService:
    """Coordinate budget ownership, validation, lifecycle, and progress calculations."""

    def __init__(
        self,
        budget_repository: BudgetRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self._budget_repository = budget_repository
        self._category_repository = category_repository

    def create_budget(self, user_id: int, budget_data: BudgetCreate) -> Budget:
        """Create a budget after validating category ownership and active-period uniqueness."""
        self._require_visible_category(budget_data.category_id, user_id)
        status = self._derive_status(budget_data.amount, Decimal("0"), budget_data.end_date)
        if status == BudgetStatus.ACTIVE and self._budget_repository.active_duplicate_exists(
            user_id,
            budget_data.category_id,
            budget_data.start_date,
            budget_data.end_date,
        ):
            raise ConflictException("An active budget already exists for this category and time period.")
        budget = Budget(
            user_id=user_id,
            spent_amount=Decimal("0.00"),
            remaining_amount=budget_data.amount,
            status=status,
            **budget_data.model_dump(),
        )
        self._apply_progress(budget)
        return self._budget_repository.create(budget)

    def list_budgets(self, user_id: int) -> list[Budget]:
        """List a user's budgets with current transaction-derived values."""
        budgets = self._budget_repository.list_by_user_id(user_id)
        self._synchronize(budgets)
        return budgets

    def get_budget(self, budget_id: int, user_id: int) -> Budget:
        """Get a caller-owned budget with current progress values."""
        budget = self._get_owned_budget(budget_id, user_id)
        self._apply_progress(budget)
        return self._budget_repository.save(budget)

    def update_budget(self, budget_id: int, user_id: int, budget_data: BudgetUpdate) -> Budget:
        """Update a caller-owned budget after re-validating its effective configuration."""
        budget = self._get_owned_budget(budget_id, user_id)
        data = budget_data.model_dump(exclude_unset=True)
        category_id = data.get("category_id", budget.category_id)
        start_date = data.get("start_date", budget.start_date)
        end_date = data.get("end_date", budget.end_date)
        amount = data.get("amount", budget.amount)
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date.")
        self._require_visible_category(category_id, user_id)
        status = self._derive_status(amount, budget.spent_amount, end_date)
        if status == BudgetStatus.ACTIVE and self._budget_repository.active_duplicate_exists(
            user_id, category_id, start_date, end_date, exclude_budget_id=budget.id
        ):
            raise ConflictException("An active budget already exists for this category and time period.")
        for field, value in data.items():
            setattr(budget, field, value)
        self._apply_progress(budget)
        return self._budget_repository.save(budget)

    def delete_budget(self, budget_id: int, user_id: int) -> None:
        """Delete a caller-owned budget."""
        self._budget_repository.delete(self._get_owned_budget(budget_id, user_id))

    def list_progress(self, user_id: int) -> list[Budget]:
        """Return all caller-owned budgets with synchronized progress."""
        return self.list_budgets(user_id)

    def list_alerts(self, user_id: int) -> list[Budget]:
        """Return active budgets whose consumption reaches the configured alert threshold."""
        return [
            budget
            for budget in self.list_budgets(user_id)
            if budget.status == BudgetStatus.ACTIVE
            and self.percentage_used(budget) >= budget.alert_percentage
        ]

    def summary(self, user_id: int) -> dict[str, Decimal | int]:
        """Aggregate all current budget totals and lifecycle counts for a user."""
        budgets = self.list_budgets(user_id)
        return {
            "budget_count": len(budgets),
            "active_budget_count": sum(budget.status == BudgetStatus.ACTIVE for budget in budgets),
            "completed_budget_count": sum(budget.status == BudgetStatus.COMPLETED for budget in budgets),
            "expired_budget_count": sum(budget.status == BudgetStatus.EXPIRED for budget in budgets),
            "total_budgeted": sum((budget.amount for budget in budgets), Decimal("0.00")),
            "total_spent": sum((budget.spent_amount for budget in budgets), Decimal("0.00")),
            "total_remaining": sum((budget.remaining_amount for budget in budgets), Decimal("0.00")),
        }

    @staticmethod
    def percentage_used(budget: Budget) -> Decimal:
        """Return an unbounded percentage so overspending remains visible."""
        return (budget.spent_amount / budget.amount * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def _synchronize(self, budgets: list[Budget]) -> None:
        for budget in budgets:
            self._apply_progress(budget)
        self._budget_repository.save_all(budgets)

    def _apply_progress(self, budget: Budget) -> None:
        spent_amount = self._budget_repository.calculate_spent_amount(
            budget.user_id,
            budget.category_id,
            budget.start_date,
            budget.end_date,
        )
        budget.spent_amount = spent_amount
        budget.remaining_amount = max(Decimal("0.00"), budget.amount - spent_amount)
        budget.status = self._derive_status(budget.amount, spent_amount, budget.end_date)

    @staticmethod
    def _derive_status(amount: Decimal, spent_amount: Decimal, end_date: date) -> BudgetStatus:
        if date.today() > end_date:
            return BudgetStatus.EXPIRED
        if spent_amount >= amount:
            return BudgetStatus.COMPLETED
        return BudgetStatus.ACTIVE

    def _get_owned_budget(self, budget_id: int, user_id: int) -> Budget:
        budget = self._budget_repository.get_by_id_and_user_id(budget_id, user_id)
        if budget is None:
            raise NotFoundException("Budget not found.")
        return budget

    def _require_visible_category(self, category_id: int | None, user_id: int) -> None:
        if category_id is not None and self._category_repository.get_visible_by_id_and_user_id(
            category_id, user_id
        ) is None:
            raise NotFoundException("Category not found.")
