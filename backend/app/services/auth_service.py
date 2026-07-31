"""Business logic for registration and JWT authentication."""

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    """Raised when registration is attempted with an existing email address."""


class InvalidCredentialsError(Exception):
    """Raised when credentials do not identify a valid active account."""


class AuthService:
    """Coordinate authentication rules while reusing user persistence operations."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    def register_user(self, user_data: UserCreate) -> User:
        """Register a user after enforcing unique, normalized email addresses."""
        email = str(user_data.email).strip().lower()
        if self._user_repository.exists(email):
            raise EmailAlreadyRegisteredError("A user with this email already exists.")

        user = User(
            full_name=user_data.full_name,
            email=email,
            hashed_password=hash_password(user_data.password),
        )
        return self._user_repository.create_user(user)

    def authenticate_user(self, email: str, password: str) -> User:
        """Validate credentials and return the authenticated active user."""
        user = self._user_repository.get_by_email(email.strip().lower())
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Incorrect email or password.")
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Incorrect email or password.")
        return user

    def login(self, email: str, password: str) -> str:
        """Authenticate credentials and return a JWT access token."""
        user = self.authenticate_user(email, password)
        return create_access_token({"sub": str(user.id)})
