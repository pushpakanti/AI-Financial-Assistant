"""Business logic for user-owned financial goals and rule-based guidance."""

from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from app.core.exceptions import NotFoundException
from app.models.goal import Goal, GoalPriority, GoalStatus
from app.repositories.goal_repository import GoalRepository
from app.schemas.goal import GoalCreate, GoalPrediction, GoalProgress, GoalRecommendation, GoalSummary, GoalUpdate


class GoalService:
    """Coordinate user-scoped goal CRUD, derived progress, and non-AI guidance."""

    def __init__(self, goal_repository: GoalRepository) -> None:
        self._goal_repository = goal_repository

    def create_goal(self, user_id: int, goal_data: GoalCreate) -> Goal:
        """Create a goal with current status and required monthly contribution."""
        goal = Goal(user_id=user_id, **goal_data.model_dump())
        self._refresh_goal(goal)
        return self._goal_repository.create(goal)

    def list_goals(self, user_id: int) -> list[Goal]:
        """List caller-owned goals after synchronizing derived fields."""
        goals = self._goal_repository.list_by_user_id(user_id)
        self._synchronize(goals)
        return goals

    def get_goal(self, goal_id: int, user_id: int) -> Goal:
        """Get one caller-owned goal after synchronizing derived fields."""
        goal = self._get_owned_goal(goal_id, user_id)
        self._refresh_goal(goal)
        return self._goal_repository.save(goal)

    def update_goal(self, goal_id: int, user_id: int, goal_data: GoalUpdate) -> Goal:
        """Update a caller-owned goal and recalculate its status and monthly requirement."""
        goal = self._get_owned_goal(goal_id, user_id)
        for field, value in goal_data.model_dump(exclude_unset=True).items():
            setattr(goal, field, value)
        self._refresh_goal(goal)
        return self._goal_repository.save(goal)

    def delete_goal(self, goal_id: int, user_id: int) -> None:
        """Delete a caller-owned goal."""
        self._goal_repository.delete(self._get_owned_goal(goal_id, user_id))

    def progress(self, user_id: int) -> list[GoalProgress]:
        """Return progress metrics for all caller-owned goals."""
        return [self._progress(goal) for goal in self.list_goals(user_id)]

    def predictions(self, user_id: int) -> list[GoalPrediction]:
        """Return transparent deadline-based predictions for all caller-owned goals."""
        return [self._prediction(goal) for goal in self.list_goals(user_id)]

    def recommendations(self, user_id: int) -> list[GoalRecommendation]:
        """Return deterministic action recommendations for all caller-owned goals."""
        return [self._recommendation(goal) for goal in self.list_goals(user_id)]

    def summary(self, user_id: int) -> GoalSummary:
        """Aggregate current goal totals and completion status counts for a user."""
        goals = self.list_goals(user_id)
        total_target = sum((goal.target_amount for goal in goals), Decimal("0.00"))
        total_current = sum((goal.current_amount for goal in goals), Decimal("0.00"))
        return GoalSummary(
            total_goals=len(goals),
            active_goals=sum(goal.status == GoalStatus.ACTIVE for goal in goals),
            completed_goals=sum(goal.status == GoalStatus.COMPLETED for goal in goals),
            overdue_goals=sum(goal.status == GoalStatus.OVERDUE for goal in goals),
            total_target_amount=total_target,
            total_current_amount=total_current,
            total_remaining_amount=sum((self._remaining(goal) for goal in goals), Decimal("0.00")),
            overall_completion_percentage=self._percentage(total_current, total_target) if total_target else Decimal("0.00"),
        )

    def _synchronize(self, goals: list[Goal]) -> None:
        for goal in goals:
            self._refresh_goal(goal)
        self._goal_repository.save_all(goals)

    def _get_owned_goal(self, goal_id: int, user_id: int) -> Goal:
        goal = self._goal_repository.get_by_id_and_user_id(goal_id, user_id)
        if goal is None:
            raise NotFoundException("Goal not found.")
        return goal

    def _refresh_goal(self, goal: Goal) -> None:
        remaining = self._remaining(goal)
        goal.status = self._status(goal, remaining)
        goal.monthly_required = self._monthly_required(remaining, goal.deadline, goal.status)

    def _progress(self, goal: Goal) -> GoalProgress:
        return GoalProgress(
            **self._response_data(goal),
            remaining_amount=self._remaining(goal),
            percentage_complete=self._percentage(goal.current_amount, goal.target_amount),
            days_remaining=max(0, (goal.deadline - date.today()).days),
        )

    def _prediction(self, goal: Goal) -> GoalPrediction:
        projected_date = date.today() if goal.status == GoalStatus.COMPLETED else None
        if goal.status == GoalStatus.ACTIVE:
            projected_date = goal.deadline
        return GoalPrediction(
            goal_id=goal.id,
            projected_completion_date=projected_date,
            required_monthly_contribution=goal.monthly_required,
            remaining_amount=self._remaining(goal),
            status=goal.status,
            prediction_basis="Rule-based monthly contribution required to meet the configured deadline.",
        )

    def _recommendation(self, goal: Goal) -> GoalRecommendation:
        if goal.status == GoalStatus.COMPLETED:
            recommendations = ["Goal reached. Consider creating a new target or reallocating contributions."]
        elif goal.status == GoalStatus.OVERDUE:
            recommendations = [
                "Deadline has passed. Extend the deadline or increase the contribution amount.",
                f"Remaining amount: {self._remaining(goal):.2f}.",
            ]
        else:
            recommendations = [
                f"Set aside at least {goal.monthly_required:.2f} each month to meet the deadline.",
            ]
            if goal.priority == GoalPriority.HIGH:
                recommendations.append("Review this high-priority goal before discretionary spending.")
        return GoalRecommendation(
            goal_id=goal.id,
            priority=goal.priority,
            status=goal.status,
            recommendations=recommendations,
        )

    @staticmethod
    def _remaining(goal: Goal) -> Decimal:
        return max(Decimal("0.00"), goal.target_amount - goal.current_amount)

    @staticmethod
    def _status(goal: Goal, remaining: Decimal) -> GoalStatus:
        if remaining == 0:
            return GoalStatus.COMPLETED
        if date.today() > goal.deadline:
            return GoalStatus.OVERDUE
        return GoalStatus.ACTIVE

    @staticmethod
    def _monthly_required(remaining: Decimal, deadline: date, status: GoalStatus) -> Decimal:
        if status == GoalStatus.COMPLETED:
            return Decimal("0.00")
        days_remaining = max(0, (deadline - date.today()).days)
        months_remaining = max(1, (days_remaining + 29) // 30)
        return (remaining / Decimal(months_remaining)).quantize(Decimal("0.01"), rounding=ROUND_CEILING)

    @staticmethod
    def _percentage(current: Decimal, target: Decimal) -> Decimal:
        return (current / target * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _response_data(goal: Goal) -> dict:
        return {
            "id": goal.id,
            "title": goal.title,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
            "deadline": goal.deadline,
            "priority": goal.priority,
            "status": goal.status,
            "monthly_required": goal.monthly_required,
            "created_at": goal.created_at,
            "updated_at": goal.updated_at,
        }
