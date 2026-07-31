"""Business logic for user management."""

from passlib.context import CryptContext

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Coordinate user business rules independently of persistence details."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    def create_user(self, user_data: UserCreate) -> User:
        """Create a user after enforcing the unique-email business rule."""
        email = str(user_data.email).lower()

        if self._user_repository.exists(email):
            raise ValueError("A user with this email already exists.")

        user = User(
            full_name=user_data.full_name,
            email=email,
            hashed_password=_password_context.hash(user_data.password),
        )
        return self._user_repository.create_user(user)
