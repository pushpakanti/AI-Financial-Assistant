"""Database access operations for user-owned financial goals."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal


class GoalRepository:
    """Encapsulate persistence operations for goals scoped to a user."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, goal: Goal) -> Goal:
        self._db.add(goal)
        self._db.commit()
        self._db.refresh(goal)
        return goal

    def list_by_user_id(self, user_id: int) -> list[Goal]:
        statement = (
            select(Goal)
            .where(Goal.user_id == user_id)
            .order_by(Goal.deadline.asc(), Goal.priority.desc(), Goal.id.asc())
        )
        return list(self._db.scalars(statement))

    def get_by_id_and_user_id(self, goal_id: int, user_id: int) -> Goal | None:
        statement = select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
        return self._db.scalar(statement)

    def save(self, goal: Goal) -> Goal:
        self._db.commit()
        self._db.refresh(goal)
        return goal

    def save_all(self, goals: list[Goal]) -> None:
        if goals:
            self._db.commit()

    def delete(self, goal: Goal) -> None:
        self._db.delete(goal)
        self._db.commit()
