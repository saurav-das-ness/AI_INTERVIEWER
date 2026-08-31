"""User domain entity for authentication and authorization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """Supported product roles for the MVP."""

    ADMIN = "admin"
    CANDIDATE = "candidate"


class UserStatus(str, Enum):
    """Lifecycle states for a user account."""

    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass(slots=True)
class User:
    """Domain representation of a system user."""

    id: str
    email: str
    password_hash: str
    role: UserRole
    status: UserStatus
    created_at: datetime
