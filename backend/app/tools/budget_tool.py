"""Budget tool adapter backed by the budget service."""

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.budget import BudgetCreate, BudgetProgress, BudgetResponse, BudgetSummary, BudgetUpdate
from app.services.budget_service import BudgetService
from app.tools.base import BaseTool


class BudgetTool(BaseTool):
    """Expose user-scoped budget operations through a JSON tool contract."""

    name = "budget"
    description = "Manage budgets and return their progress, alerts, and summaries."

    def __init__(self, db: Session) -> None:
        self._service = BudgetService(BudgetRepository(db), CategoryRepository(db))

    def _execute(self, user_id: int, action: str, payload: dict[str, Any]) -> Any:
        if action == "create":
            return BudgetResponse.model_validate(self._service.create_budget(user_id, BudgetCreate(**payload)))
        if action == "list":
            return [BudgetResponse.model_validate(item) for item in self._service.list_budgets(user_id)]
        if action == "progress":
            return [self._progress(item) for item in self._service.list_progress(user_id)]
        if action == "alerts":
            return [self._progress(item) for item in self._service.list_alerts(user_id)]
        if action == "summary":
            return BudgetSummary(**self._service.summary(user_id))
        if action == "get":
            return BudgetResponse.model_validate(self._service.get_budget(self._id(payload), user_id))
        if action == "update":
            budget_id = self._id(payload)
            data = {key: value for key, value in payload.items() if key != "id"}
            return BudgetResponse.model_validate(
                self._service.update_budget(budget_id, user_id, BudgetUpdate(**data))
            )
        if action == "delete":
            self._service.delete_budget(self._id(payload), user_id)
            return {"deleted": True}
        raise ValueError("Unsupported budget tool action.")

    def _progress(self, budget) -> BudgetProgress:
        response = BudgetResponse.model_validate(budget)
        return BudgetProgress(
            **response.model_dump(), percentage_used=self._service.percentage_used(budget)
        )
