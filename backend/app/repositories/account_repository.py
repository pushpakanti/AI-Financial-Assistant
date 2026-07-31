"""Database access operations for user-owned accounts."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account


class AccountRepository:
    """Encapsulate persistence operations for accounts scoped to a user."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, account: Account) -> Account:
        """Persist and return a new account."""
        self._db.add(account)
        self._db.commit()
        self._db.refresh(account)
        return account

    def list_by_user_id(self, user_id: int) -> list[Account]:
        """Return all accounts owned by a user, newest first."""
        statement = select(Account).where(Account.user_id == user_id).order_by(Account.id.desc())
        return list(self._db.scalars(statement))

    def get_by_id_and_user_id(self, account_id: int, user_id: int) -> Account | None:
        """Return an account only when it belongs to the supplied user."""
        statement = select(Account).where(Account.id == account_id, Account.user_id == user_id)
        return self._db.scalar(statement)

    def update(self, account: Account) -> Account:
        """Commit changes made to an account and return its refreshed state."""
        self._db.commit()
        self._db.refresh(account)
        return account

    def delete(self, account: Account) -> None:
        """Remove an account permanently."""
        self._db.delete(account)
        self._db.commit()
