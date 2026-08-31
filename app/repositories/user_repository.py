"""SQLite-backed user repository for the auth slice."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from app.db.sqlite import connect, initialize_schema
from app.models.domain.user import User, UserRole, UserStatus


class UserRepository(Protocol):
    """Persistence contract for user account operations."""

    def get_by_email(self, email: str) -> User | None:
        """Return a user by email if the account exists."""

    def create(self, email: str, password_hash: str, role: UserRole) -> User:
        """Create and persist a user account."""

    def get_by_id(self, user_id: str) -> User | None:
        """Return a user by identifier if the account exists."""


class SqliteUserRepository:
    """SQLite repository for the first auth and role-management slice."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        with connect(self._db_path) as connection:
            initialize_schema(connection)

    def get_by_email(self, email: str) -> User | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT id, email, password_hash, role, status, created_at FROM users WHERE email = ?",
                (email.lower(),),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_user(row)

    def create(self, email: str, password_hash: str, role: UserRole) -> User:
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            password_hash=password_hash,
            role=role,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
        )

        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO users (id, email, password_hash, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.email,
                    user.password_hash,
                    user.role.value,
                    user.status.value,
                    user.created_at.isoformat(),
                ),
            )
            connection.commit()

        return user

    def get_by_id(self, user_id: str) -> User | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT id, email, password_hash, role, status, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_user(row)

    @staticmethod
    def _row_to_user(row: object) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=UserRole(row["role"]),
            status=UserStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
