"""Authenticated statement upload and confirmation endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.statement_repository import StatementRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.statement import StatementImportResponse, StatementUploadPreview
from app.services.statement_service import StatementService
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/statements", tags=["statements"])

def get_statement_service(db: Annotated[Session, Depends(get_db)]) -> StatementService:
    transactions, accounts, categories = TransactionRepository(db), AccountRepository(db), CategoryRepository(db)
    return StatementService(StatementRepository(db), transactions, accounts, categories, TransactionService(transactions, accounts, categories))

@router.post("/upload", response_model=StatementUploadPreview, status_code=status.HTTP_201_CREATED)
async def upload_statement(file: Annotated[UploadFile, File(...)], account_id: Annotated[int, Form(gt=0)], current_user: Annotated[User, Depends(get_current_user)], service: Annotated[StatementService, Depends(get_statement_service)]) -> StatementUploadPreview:
    """Validate and preview a statement; uploaded bytes are discarded after parsing."""
    data = await file.read()
    return service.preview_upload(current_user.id, account_id, file.filename or "upload", file.content_type, data)

@router.post("/{statement_id}/import", response_model=StatementImportResponse)
def import_statement(statement_id: int, current_user: Annotated[User, Depends(get_current_user)], service: Annotated[StatementService, Depends(get_statement_service)]) -> StatementImportResponse:
    return service.import_statement(current_user.id, statement_id)
