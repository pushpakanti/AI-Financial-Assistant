"""Authenticated category management endpoints for version 1 of the API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate, CategoryUsageResponse
from app.services.category_service import CategoryService


router = APIRouter(prefix="/categories", tags=["categories"])


def get_category_service(db: Annotated[Session, Depends(get_db)]) -> CategoryService:
    """Build the request-scoped category service."""
    return CategoryService(CategoryRepository(db), TransactionRepository(db), BudgetRepository(db))


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryResponse:
    """Create a custom category for the authenticated user."""
    return category_service.create_category(current_user.id, category_data)


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> list[CategoryResponse]:
    """List active default and caller-owned custom categories."""
    return category_service.list_categories(current_user.id)


@router.get("/default", response_model=list[CategoryResponse])
def list_default_categories(
    _current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> list[CategoryResponse]:
    """List active system default categories."""
    return category_service.list_default_categories()


@router.get("/custom", response_model=list[CategoryResponse])
def list_custom_categories(
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> list[CategoryResponse]:
    """List the authenticated user's custom categories."""
    return category_service.list_custom_categories(current_user.id)


@router.get("/usage", response_model=list[CategoryUsageResponse])
def list_category_usage(
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> list[CategoryUsageResponse]:
    """List visible categories with transaction counts scoped to the caller."""
    return [
        CategoryUsageResponse(
            **CategoryResponse.model_validate(category).model_dump(),
            transaction_count=transaction_count,
        )
        for category, transaction_count in category_service.list_usage(current_user.id)
    ]


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryResponse:
    """Get a shared default or caller-owned category."""
    return category_service.get_category(category_id, current_user.id)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryResponse:
    """Update a caller-owned custom category."""
    return category_service.update_category(category_id, current_user.id, category_data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> Response:
    """Delete an unused caller-owned custom category."""
    category_service.delete_category(category_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
