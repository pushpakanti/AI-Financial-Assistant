"""Authenticated transaction management endpoints for version 1 of the API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilter,
    TransactionPage,
    TransactionResponse,
    TransactionSearch,
    TransactionSummary,
    TransactionUpdate,
)
from app.services.transaction_service import TransactionService


router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_transaction_service(db: Annotated[Session, Depends(get_db)]) -> TransactionService:
    """Build the request-scoped transaction service."""
    return TransactionService(
        TransactionRepository(db), AccountRepository(db), CategoryRepository(db)
    )


def _page(items, total: int, limit: int, offset: int) -> TransactionPage:
    return TransactionPage(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_data: TransactionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    """Create a transaction for the authenticated user."""
    return transaction_service.create_transaction(current_user.id, transaction_data)


@router.get("", response_model=TransactionPage)
def list_transactions(
    filters: Annotated[TransactionFilter, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionPage:
    """List the authenticated user's transactions with pagination."""
    items, total = transaction_service.list_transactions(current_user.id, filters)
    return _page(items, total, filters.limit, filters.offset)


@router.get("/filter", response_model=TransactionPage)
def filter_transactions(
    filters: Annotated[TransactionFilter, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionPage:
    """Filter the authenticated user's transactions."""
    items, total = transaction_service.list_transactions(current_user.id, filters)
    return _page(items, total, filters.limit, filters.offset)


@router.get("/search", response_model=TransactionPage)
def search_transactions(
    search: Annotated[TransactionSearch, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionPage:
    """Search the authenticated user's transactions."""
    items, total = transaction_service.search_transactions(current_user.id, search)
    return _page(items, total, search.limit, search.offset)


@router.get("/summary", response_model=TransactionSummary)
def summarize_transactions(
    filters: Annotated[TransactionFilter, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionSummary:
    """Summarize the authenticated user's transactions."""
    return transaction_service.summarize_transactions(current_user.id, filters)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    """Get one transaction owned by the authenticated user."""
    return transaction_service.get_transaction(transaction_id, current_user.id)


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    """Update one transaction owned by the authenticated user."""
    return transaction_service.update_transaction(transaction_id, current_user.id, transaction_data)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> Response:
    """Delete one transaction owned by the authenticated user."""
    transaction_service.delete_transaction(transaction_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
