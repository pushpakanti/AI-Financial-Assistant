"""Business logic for authenticated users' transactions."""

from app.core.exceptions import NotFoundException
from app.models.transaction import Transaction, TransactionType
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
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
        category_repository: CategoryRepository,
    ) -> None:
        self._transaction_repository = transaction_repository
        self._account_repository = account_repository
        self._category_repository = category_repository

    def create_transaction(self, user_id: int, transaction_data: TransactionCreate) -> Transaction:
        """Create a transaction linked to an account owned by the caller."""
        self._require_owned_account(transaction_data.account_id, user_id)
        self._require_visible_category(transaction_data.category_id, user_id)
        data = transaction_data.model_dump()
        data["receipt_url"] = str(data["receipt_url"]) if data["receipt_url"] else None
        return self._transaction_repository.create(Transaction(user_id=user_id, **data))

    def create_withdrawal(self, user_id: int, transaction_data: TransactionCreate) -> Transaction:
        """Record a confirmed debit and decrease the caller-owned account in one commit."""
        if transaction_data.transaction_type != TransactionType.EXPENSE:
            raise ValueError("A withdrawal must be recorded as an expense transaction.")
        account = self._account_repository.get_by_id_and_user_id(transaction_data.account_id, user_id)
        if account is None:
            raise NotFoundException("Account not found.")
        if account.balance < transaction_data.amount:
            raise ValueError("Insufficient available balance for this withdrawal.")
        self._require_visible_category(transaction_data.category_id, user_id)
        data = transaction_data.model_dump()
        data["receipt_url"] = str(data["receipt_url"]) if data["receipt_url"] else None
        return self._transaction_repository.create_with_account_debit(
            Transaction(user_id=user_id, **data), account
        )

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
        if "category_id" in data:
            self._require_visible_category(data["category_id"], user_id)
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

    def _require_visible_category(self, category_id: int | None, user_id: int) -> None:
        if category_id is not None and self._category_repository.get_visible_by_id_and_user_id(
            category_id, user_id
        ) is None:
            raise NotFoundException("Category not found.")
