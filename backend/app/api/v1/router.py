"""Version 1 API routes."""

from fastapi import APIRouter

from app.api.v1.accounts import router as accounts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.categories import router as categories_router
from app.api.v1.chat import router as chat_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.goals import router as goals_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.transactions import router as transactions_router


router = APIRouter()
router.include_router(auth_router)
router.include_router(accounts_router)
router.include_router(budgets_router)
router.include_router(categories_router)
router.include_router(chat_router)
router.include_router(dashboard_router)
router.include_router(goals_router)
router.include_router(notifications_router)
router.include_router(transactions_router)


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API is available to serve requests."""
    return {"status": "healthy"}
