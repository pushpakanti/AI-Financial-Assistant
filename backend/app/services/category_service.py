"""Business logic for shared default and user-owned custom categories."""

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.category import Category
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    """Coordinate category operations while enforcing visibility and ownership rules."""

    def __init__(
        self,
        category_repository: CategoryRepository,
        transaction_repository: TransactionRepository,
        budget_repository: BudgetRepository | None = None,
    ) -> None:
        self._category_repository = category_repository
        self._transaction_repository = transaction_repository
        self._budget_repository = budget_repository

    def create_category(self, user_id: int, category_data: CategoryCreate) -> Category:
        """Create a custom category after enforcing a per-user unique name."""
        if self._category_repository.custom_name_exists(user_id, category_data.name):
            raise ConflictException("A category with this name already exists.")
        category = Category(user_id=user_id, is_default=False, **category_data.model_dump())
        return self._category_repository.create(category)

    def list_categories(self, user_id: int) -> list[Category]:
        """List active default categories and active custom categories visible to the caller."""
        return self._category_repository.list_visible(user_id)

    def list_default_categories(self) -> list[Category]:
        """List active system default categories."""
        return self._category_repository.list_defaults()

    def list_custom_categories(self, user_id: int) -> list[Category]:
        """List the caller's custom categories, including inactive records for management."""
        return self._category_repository.list_custom_by_user_id(user_id)

    def get_category(self, category_id: int, user_id: int) -> Category:
        """Return a category only when it is shared or belongs to the caller."""
        category = self._category_repository.get_visible_by_id_and_user_id(category_id, user_id)
        if category is None:
            raise NotFoundException("Category not found.")
        return category

    def update_category(self, category_id: int, user_id: int, category_data: CategoryUpdate) -> Category:
        """Update a caller-owned custom category only."""
        category = self._get_mutable_category(category_id, user_id)
        data = category_data.model_dump(exclude_unset=True)
        if "name" in data and self._category_repository.custom_name_exists(
            user_id, data["name"], exclude_category_id=category.id
        ):
            raise ConflictException("A category with this name already exists.")
        for field, value in data.items():
            setattr(category, field, value)
        return self._category_repository.update(category)

    def delete_category(self, category_id: int, user_id: int) -> None:
        """Delete an unused caller-owned custom category."""
        category = self._get_mutable_category(category_id, user_id)
        if self._transaction_repository.has_transactions_for_category(category.id):
            raise ConflictException("Categories assigned to transactions cannot be deleted.")
        if self._budget_repository and self._budget_repository.has_budgets_for_category(category.id):
            raise ConflictException("Categories assigned to budgets cannot be deleted.")
        self._category_repository.delete(category)

    def list_usage(self, user_id: int) -> list[tuple[Category, int]]:
        """Return transaction usage counts scoped to the caller's transactions."""
        return self._category_repository.list_usage_by_user_id(user_id)

    def _get_mutable_category(self, category_id: int, user_id: int) -> Category:
        category = self._category_repository.get_custom_by_id_and_user_id(category_id, user_id)
        if category is not None:
            return category
        visible_category = self._category_repository.get_visible_by_id_and_user_id(category_id, user_id)
        if visible_category is not None and visible_category.is_default:
            raise ForbiddenException("Default categories cannot be modified or deleted.")
        raise NotFoundException("Category not found.")
