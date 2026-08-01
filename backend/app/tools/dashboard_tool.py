"""Dashboard tool adapter backed by the analytics service."""

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import DashboardRepository
from app.services.dashboard_service import DashboardService
from app.tools.base import BaseTool


class DashboardTool(BaseTool):
    """Expose the authenticated user's dashboard as a JSON tool result."""

    name = "dashboard"
    description = "Retrieve the caller's aggregated financial dashboard analytics."

    def __init__(self, db: Session) -> None:
        self._service = DashboardService(DashboardRepository(db))

    def _execute(self, user_id: int, action: str, payload: dict[str, Any]) -> Any:
        if action != "get":
            raise ValueError("Unsupported dashboard tool action.")
        return self._service.get_dashboard(user_id)
