"""Authenticated dashboard analytics endpoint for version 1 of the API."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(db: Annotated[Session, Depends(get_db)]) -> DashboardService:
    """Build the request-scoped dashboard service."""
    return DashboardService(DashboardRepository(db))


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardResponse:
    """Return aggregated dashboard analytics for the authenticated user only."""
    return dashboard_service.get_dashboard(current_user.id)
