"""Transaction tool adapter backed by the transaction service."""

from typing import Any

from sqlalchemy.orm import Session

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
from app.tools.base import BaseTool


class TransactionTool(BaseTool):
    """Expose user-scoped transaction operations through a JSON tool contract."""

    name = "transaction"
    description = "Manage, search, filter, and summarize the caller's transactions."

    def __init__(self, db: Session) -> None:
        self._service = TransactionService(
            TransactionRepository(db), AccountRepository(db), CategoryRepository(db)
        )

    def _execute(self, user_id: int, action: str, payload: dict[str, Any]) -> Any:
        if action == "create":
            return TransactionResponse.model_validate(
                self._service.create_transaction(user_id, TransactionCreate(**payload))
            )
        if action in {"list", "filter"}:
            filters = TransactionFilter(**payload)
            items, total = self._service.list_transactions(user_id, filters)
            return TransactionPage(
                items=[TransactionResponse.model_validate(item) for item in items],
                total=total,
                limit=filters.limit,
                offset=filters.offset,
            )
        if action == "search":
            search = TransactionSearch(**payload)
            items, total = self._service.search_transactions(user_id, search)
            return TransactionPage(
                items=[TransactionResponse.model_validate(item) for item in items],
                total=total,
                limit=search.limit,
                offset=search.offset,
            )
        if action == "summary":
            return TransactionSummary(**self._service.summarize_transactions(user_id, TransactionFilter(**payload)))
        if action == "get":
            return TransactionResponse.model_validate(self._service.get_transaction(self._id(payload), user_id))
        if action == "update":
            transaction_id = self._id(payload)
            data = {key: value for key, value in payload.items() if key != "id"}
            return TransactionResponse.model_validate(
                self._service.update_transaction(transaction_id, user_id, TransactionUpdate(**data))
            )
        if action == "delete":
            self._service.delete_transaction(self._id(payload), user_id)
            return {"deleted": True}
        raise ValueError("Unsupported transaction tool action.")
