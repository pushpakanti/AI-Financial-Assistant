"""Authenticated budget management endpoints for version 1 of the API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.budget import BudgetCreate, BudgetProgress, BudgetResponse, BudgetSummary, BudgetUpdate
from app.services.budget_service import BudgetService


router = APIRouter(prefix="/budgets", tags=["budgets"])


def get_budget_service(db: Annotated[Session, Depends(get_db)]) -> BudgetService:
    """Build the request-scoped budget service."""
    return BudgetService(BudgetRepository(db), CategoryRepository(db))


def _progress_response(budget) -> BudgetProgress:
    response = BudgetResponse.model_validate(budget)
    return BudgetProgress(
        **response.model_dump(), percentage_used=BudgetService.percentage_used(budget)
    )


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget_data: BudgetCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> BudgetResponse:
    """Create a budget for the authenticated user."""
    return budget_service.create_budget(current_user.id, budget_data)


@router.get("", response_model=list[BudgetResponse])
def list_budgets(
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> list[BudgetResponse]:
    """List budgets owned by the authenticated user."""
    return budget_service.list_budgets(current_user.id)


@router.get("/progress", response_model=list[BudgetProgress])
def list_budget_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> list[BudgetProgress]:
    """Return current spent, remaining, and percentage-used data for each budget."""
    return [_progress_response(budget) for budget in budget_service.list_progress(current_user.id)]


@router.get("/summary", response_model=BudgetSummary)
def budget_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> BudgetSummary:
    """Return aggregate budget totals for the authenticated user."""
    return budget_service.summary(current_user.id)


@router.get("/alerts", response_model=list[BudgetProgress])
def list_budget_alerts(
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> list[BudgetProgress]:
    """Return active budgets at or above their alert thresholds."""
    return [_progress_response(budget) for budget in budget_service.list_alerts(current_user.id)]


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(
    budget_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> BudgetResponse:
    """Get one budget owned by the authenticated user."""
    return budget_service.get_budget(budget_id, current_user.id)


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    budget_data: BudgetUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> BudgetResponse:
    """Update one budget owned by the authenticated user."""
    return budget_service.update_budget(budget_id, current_user.id, budget_data)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> Response:
    """Delete one budget owned by the authenticated user."""
    budget_service.delete_budget(budget_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
