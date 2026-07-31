"""Authenticated account management endpoints for version 1 of the API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories.account_repository import AccountRepository
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.services.account_service import AccountService


router = APIRouter(prefix="/accounts", tags=["accounts"])


def get_account_service(db: Annotated[Session, Depends(get_db)]) -> AccountService:
    """Build the request-scoped account service."""
    return AccountService(AccountRepository(db))


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    account_data: AccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    """Create an account for the authenticated user."""
    return account_service.create_account(current_user.id, account_data)


@router.get("", response_model=list[AccountResponse])
def list_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> list[AccountResponse]:
    """List accounts owned by the authenticated user."""
    return account_service.list_accounts(current_user.id)


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    """Get one account owned by the authenticated user."""
    return account_service.get_account(account_id, current_user.id)


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: int,
    account_data: AccountUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    """Update one account owned by the authenticated user."""
    return account_service.update_account(account_id, current_user.id, account_data)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> Response:
    """Delete one account owned by the authenticated user."""
    account_service.delete_account(account_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
