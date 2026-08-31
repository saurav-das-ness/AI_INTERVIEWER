"""Focused tests for the first auth backend slice."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.models.domain.user import UserRole
from app.models.schemas.auth import LoginRequest, RegisterRequest
from app.repositories.user_repository import SqliteUserRepository
from app.services.auth.service import AuthConflictError, AuthService, AuthenticationError


class AuthServiceTests(unittest.TestCase):
    """Business-rule tests for registration and login."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp_dir.cleanup)
        db_path = str(Path(temp_dir.name) / "test.db")
        repository = SqliteUserRepository(db_path)
        self.auth_service = AuthService(repository)

    def test_register_user_persists_role_and_hashed_password(self) -> None:
        user = self.auth_service.register_user(
            RegisterRequest(
                email="admin@example.com",
                password="StrongPass123",
                role=UserRole.ADMIN,
            )
        )

        self.assertEqual(user.role, UserRole.ADMIN)
        self.assertEqual(user.email, "admin@example.com")
        self.assertNotEqual(user.password_hash, "StrongPass123")

    def test_duplicate_registration_is_rejected(self) -> None:
        payload = RegisterRequest(
            email="candidate@example.com",
            password="Candidate123",
            role=UserRole.CANDIDATE,
        )
        self.auth_service.register_user(payload)

        with self.assertRaises(AuthConflictError):
            self.auth_service.register_user(payload)

    def test_login_succeeds_for_valid_credentials(self) -> None:
        self.auth_service.register_user(
            RegisterRequest(
                email="candidate@example.com",
                password="Candidate123",
                role=UserRole.CANDIDATE,
            )
        )

        user = self.auth_service.authenticate(
            LoginRequest(email="candidate@example.com", password="Candidate123")
        )

        self.assertEqual(user.role, UserRole.CANDIDATE)

    def test_login_fails_for_invalid_password(self) -> None:
        self.auth_service.register_user(
            RegisterRequest(
                email="candidate@example.com",
                password="Candidate123",
                role=UserRole.CANDIDATE,
            )
        )

        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate(
                LoginRequest(email="candidate@example.com", password="WrongPassword123")
            )


if __name__ == "__main__":
    unittest.main()
