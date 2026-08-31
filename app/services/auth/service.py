"""Auth service for the first backend vertical slice."""

from __future__ import annotations

from app.core.security import hash_password, verify_password
from app.models.domain.user import User
from app.models.schemas.auth import LoginRequest, RegisterRequest
from app.repositories.user_repository import UserRepository


class AuthConflictError(ValueError):
    """Raised when trying to create a user that already exists."""


class AuthenticationError(ValueError):
    """Raised when authentication fails."""


class AuthService:
    """Business logic for account registration and email/password login."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    def register_user(self, payload: RegisterRequest) -> User:
        existing_user = self._user_repository.get_by_email(payload.email)
        if existing_user is not None:
            raise AuthConflictError("A user with this email already exists")

        password_hash = hash_password(payload.password)
        return self._user_repository.create(payload.email, password_hash, payload.role)

    def authenticate(self, payload: LoginRequest) -> User:
        user = self._user_repository.get_by_email(payload.email)
        if user is None:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(payload.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        return user
