"""Business logic for authenticated users' transactions."""

from app.core.exceptions import NotFoundException
from app.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilter,
    TransactionSearch,
    TransactionUpdate,
)


class TransactionService:
    """Coordinate transactions while enforcing account and transaction ownership."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
    ) -> None:
        self._transaction_repository = transaction_repository
        self._account_repository = account_repository

    def create_transaction(self, user_id: int, transaction_data: TransactionCreate) -> Transaction:
        """Create a transaction linked to an account owned by the caller."""
        self._require_owned_account(transaction_data.account_id, user_id)
        data = transaction_data.model_dump()
        data["receipt_url"] = str(data["receipt_url"]) if data["receipt_url"] else None
        return self._transaction_repository.create(Transaction(user_id=user_id, **data))

    def list_transactions(self, user_id: int, filters: TransactionFilter):
        """List only the caller's transactions with server-side pagination."""
        return self._transaction_repository.list_by_user_id(user_id, filters)

    def get_transaction(self, transaction_id: int, user_id: int) -> Transaction:
        """Get a caller-owned transaction without disclosing foreign records."""
        return self._get_owned_transaction(transaction_id, user_id)

    def update_transaction(
        self, transaction_id: int, user_id: int, transaction_data: TransactionUpdate
    ) -> Transaction:
        """Update a transaction only after confirming ownership."""
        transaction = self._get_owned_transaction(transaction_id, user_id)
        data = transaction_data.model_dump(exclude_unset=True)
        if "account_id" in data and data["account_id"] != transaction.account_id:
            self._require_owned_account(data["account_id"], user_id)
        if "receipt_url" in data:
            data["receipt_url"] = str(data["receipt_url"]) if data["receipt_url"] else None
        for field, value in data.items():
            setattr(transaction, field, value)
        return self._transaction_repository.update(transaction)

    def delete_transaction(self, transaction_id: int, user_id: int) -> None:
        """Delete a transaction only after confirming ownership."""
        self._transaction_repository.delete(self._get_owned_transaction(transaction_id, user_id))

    def search_transactions(self, user_id: int, search: TransactionSearch):
        """Search only within transactions owned by the caller."""
        return self._transaction_repository.search_by_user_id(
            user_id, search.query, search.limit, search.offset
        )

    def summarize_transactions(self, user_id: int, filters: TransactionFilter):
        """Return aggregate values only for transactions owned by the caller."""
        return self._transaction_repository.summary_by_user_id(user_id, filters)

    def _get_owned_transaction(self, transaction_id: int, user_id: int) -> Transaction:
        transaction = self._transaction_repository.get_by_id_and_user_id(transaction_id, user_id)
        if transaction is None:
            raise NotFoundException("Transaction not found.")
        return transaction

    def _require_owned_account(self, account_id: int, user_id: int) -> None:
        if self._account_repository.get_by_id_and_user_id(account_id, user_id) is None:
            raise NotFoundException("Account not found.")
