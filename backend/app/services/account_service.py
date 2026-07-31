"""Business logic for user-owned financial accounts."""

from app.core.exceptions import NotFoundException
from app.models.account import Account
from app.repositories.account_repository import AccountRepository
from app.schemas.account import AccountCreate, AccountUpdate


class AccountService:
    """Coordinate account operations while enforcing ownership boundaries."""

    def __init__(self, account_repository: AccountRepository) -> None:
        self._account_repository = account_repository

    def create_account(self, user_id: int, account_data: AccountCreate) -> Account:
        """Create an account owned by the authenticated user."""
        account = Account(user_id=user_id, **account_data.model_dump())
        return self._account_repository.create(account)

    def list_accounts(self, user_id: int) -> list[Account]:
        """List only the authenticated user's accounts."""
        return self._account_repository.list_by_user_id(user_id)

    def get_account(self, account_id: int, user_id: int) -> Account:
        """Get a user-owned account without disclosing foreign accounts."""
        return self._get_owned_account(account_id, user_id)

    def update_account(self, account_id: int, user_id: int, account_data: AccountUpdate) -> Account:
        """Update an account only after confirming user ownership."""
        account = self._get_owned_account(account_id, user_id)
        for field, value in account_data.model_dump(exclude_unset=True).items():
            setattr(account, field, value)
        return self._account_repository.update(account)

    def delete_account(self, account_id: int, user_id: int) -> None:
        """Delete an account only after confirming user ownership."""
        self._account_repository.delete(self._get_owned_account(account_id, user_id))

    def _get_owned_account(self, account_id: int, user_id: int) -> Account:
        account = self._account_repository.get_by_id_and_user_id(account_id, user_id)
        if account is None:
            raise NotFoundException("Account not found.")
        return account
