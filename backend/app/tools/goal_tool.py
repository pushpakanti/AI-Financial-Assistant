"""Goal tool adapter backed by the goal service."""

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.goal_repository import GoalRepository
from app.schemas.goal import GoalCreate, GoalResponse, GoalUpdate
from app.services.goal_service import GoalService
from app.tools.base import BaseTool


class GoalTool(BaseTool):
    """Expose user-scoped goal operations through a JSON tool contract."""

    name = "goal"
    description = "Manage financial goals and return their progress, predictions, and recommendations."

    def __init__(self, db: Session) -> None:
        self._service = GoalService(GoalRepository(db))

    def _execute(self, user_id: int, action: str, payload: dict[str, Any]) -> Any:
        if action == "create":
            return GoalResponse.model_validate(self._service.create_goal(user_id, GoalCreate(**payload)))
        if action == "list":
            return [GoalResponse.model_validate(item) for item in self._service.list_goals(user_id)]
        if action == "summary":
            return self._service.summary(user_id)
        if action == "progress":
            return self._service.progress(user_id)
        if action == "prediction":
            return self._service.predictions(user_id)
        if action == "recommendations":
            return self._service.recommendations(user_id)
        if action == "get":
            return GoalResponse.model_validate(self._service.get_goal(self._id(payload), user_id))
        if action == "update":
            goal_id = self._id(payload)
            data = {key: value for key, value in payload.items() if key != "id"}
            return GoalResponse.model_validate(self._service.update_goal(goal_id, user_id, GoalUpdate(**data)))
        if action == "delete":
            self._service.delete_goal(self._id(payload), user_id)
            return {"deleted": True}
        raise ValueError("Unsupported goal tool action.")
