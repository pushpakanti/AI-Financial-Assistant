"""Version 1 API routes."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router


router = APIRouter()
router.include_router(auth_router)


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API is available to serve requests."""
    return {"status": "healthy"}
