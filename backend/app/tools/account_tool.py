"""Account tool adapter backed by the account service."""

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.account_repository import AccountRepository
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.services.account_service import AccountService
from app.tools.base import BaseTool


class AccountTool(BaseTool):
    """Expose user-scoped account operations through a JSON tool contract."""

    name = "account"
    description = "Create, list, retrieve, update, and delete the caller's accounts."

    def __init__(self, db: Session) -> None:
        self._service = AccountService(AccountRepository(db))

    def _execute(self, user_id: int, action: str, payload: dict[str, Any]) -> Any:
        if action == "create":
            return AccountResponse.model_validate(self._service.create_account(user_id, AccountCreate(**payload)))
        if action == "list":
            return [AccountResponse.model_validate(item) for item in self._service.list_accounts(user_id)]
        if action == "get":
            return AccountResponse.model_validate(self._service.get_account(self._id(payload), user_id))
        if action == "update":
            account_id = self._id(payload)
            data = {key: value for key, value in payload.items() if key != "id"}
            return AccountResponse.model_validate(
                self._service.update_account(account_id, user_id, AccountUpdate(**data))
            )
        if action == "delete":
            self._service.delete_account(self._id(payload), user_id)
            return {"deleted": True}
        raise ValueError("Unsupported account tool action.")
