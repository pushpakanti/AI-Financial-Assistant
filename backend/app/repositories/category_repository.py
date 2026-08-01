"""Database access operations for shared and user-owned categories."""

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction


class CategoryRepository:
    """Encapsulate category persistence and user-visible query scopes."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, category: Category) -> Category:
        """Persist and return a custom category."""
        self._db.add(category)
        self._db.commit()
        self._db.refresh(category)
        return category

    def list_visible(self, user_id: int) -> list[Category]:
        """Return active defaults plus active custom categories for a user."""
        statement = (
            select(Category)
            .where(self._visible_to_user(user_id), Category.is_active.is_(True))
            .order_by(Category.is_default.desc(), Category.name.asc(), Category.id.asc())
        )
        return list(self._db.scalars(statement))

    def list_defaults(self) -> list[Category]:
        """Return active shared default categories."""
        statement = (
            select(Category)
            .where(Category.is_default.is_(True), Category.user_id.is_(None), Category.is_active.is_(True))
            .order_by(Category.name.asc(), Category.id.asc())
        )
        return list(self._db.scalars(statement))

    def list_custom_by_user_id(self, user_id: int) -> list[Category]:
        """Return all custom categories owned by a user, including inactive ones."""
        statement = (
            select(Category)
            .where(Category.user_id == user_id, Category.is_default.is_(False))
            .order_by(Category.name.asc(), Category.id.asc())
        )
        return list(self._db.scalars(statement))

    def get_visible_by_id_and_user_id(self, category_id: int, user_id: int) -> Category | None:
        """Return a shared default or a category owned by the supplied user."""
        statement = select(Category).where(Category.id == category_id, self._visible_to_user(user_id))
        return self._db.scalar(statement)

    def get_custom_by_id_and_user_id(self, category_id: int, user_id: int) -> Category | None:
        """Return a mutable custom category only when owned by the supplied user."""
        statement = select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
            Category.is_default.is_(False),
        )
        return self._db.scalar(statement)

    def custom_name_exists(self, user_id: int, name: str, exclude_category_id: int | None = None) -> bool:
        """Return whether a custom category name is already in use by a user."""
        conditions = [
            Category.user_id == user_id,
            Category.is_default.is_(False),
            func.lower(Category.name) == name.casefold(),
        ]
        if exclude_category_id is not None:
            conditions.append(Category.id != exclude_category_id)
        return bool(self._db.scalar(select(exists().where(*conditions))))

    def list_usage_by_user_id(self, user_id: int) -> list[tuple[Category, int]]:
        """Return visible categories with transaction counts limited to the supplied user."""
        statement = (
            select(Category, func.count(Transaction.id).label("transaction_count"))
            .outerjoin(
                Transaction,
                and_(Transaction.category_id == Category.id, Transaction.user_id == user_id),
            )
            .where(self._visible_to_user(user_id))
            .group_by(Category.id)
            .order_by(Category.is_default.desc(), Category.name.asc(), Category.id.asc())
        )
        return [(category, int(count)) for category, count in self._db.execute(statement)]

    def update(self, category: Category) -> Category:
        """Commit changes made to a custom category."""
        self._db.commit()
        self._db.refresh(category)
        return category

    def delete(self, category: Category) -> None:
        """Remove a custom category permanently."""
        self._db.delete(category)
        self._db.commit()

    @staticmethod
    def _visible_to_user(user_id: int):
        return or_(
            Category.user_id == user_id,
            and_(Category.is_default.is_(True), Category.user_id.is_(None)),
        )
