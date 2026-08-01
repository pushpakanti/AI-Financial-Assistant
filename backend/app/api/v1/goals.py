"""Authenticated financial goal endpoints for version 1 of the API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories.goal_repository import GoalRepository
from app.schemas.goal import GoalCreate, GoalPrediction, GoalProgress, GoalRecommendation, GoalResponse, GoalSummary, GoalUpdate
from app.services.goal_service import GoalService


router = APIRouter(prefix="/goals", tags=["goals"])


def get_goal_service(db: Annotated[Session, Depends(get_db)]) -> GoalService:
    """Build the request-scoped goal service."""
    return GoalService(GoalRepository(db))


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    goal_data: GoalCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> GoalResponse:
    return goal_service.create_goal(current_user.id, goal_data)


@router.get("", response_model=list[GoalResponse])
def list_goals(
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> list[GoalResponse]:
    return goal_service.list_goals(current_user.id)


@router.get("/summary", response_model=GoalSummary)
def goal_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> GoalSummary:
    return goal_service.summary(current_user.id)


@router.get("/progress", response_model=list[GoalProgress])
def goal_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> list[GoalProgress]:
    return goal_service.progress(current_user.id)


@router.get("/prediction", response_model=list[GoalPrediction])
def goal_prediction(
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> list[GoalPrediction]:
    return goal_service.predictions(current_user.id)


@router.get("/recommendations", response_model=list[GoalRecommendation])
def goal_recommendations(
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> list[GoalRecommendation]:
    return goal_service.recommendations(current_user.id)


@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> GoalResponse:
    return goal_service.get_goal(goal_id, current_user.id)


@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    goal_data: GoalUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> GoalResponse:
    return goal_service.update_goal(goal_id, current_user.id, goal_data)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> Response:
    goal_service.delete_goal(goal_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
