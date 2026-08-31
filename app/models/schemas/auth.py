"""Typed auth schemas for route contracts."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.domain.user import UserRole, UserStatus

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailValidatedModel(BaseModel):
    """Base model with lightweight email validation that avoids optional extras."""

    @field_validator("email", check_fields=False)
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized):
            raise ValueError("A valid email address is required")
        return normalized


class RegisterRequest(EmailValidatedModel):
    """Request body for user registration during early environment setup."""

    email: str
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class LoginRequest(EmailValidatedModel):
    """Request body for email and password authentication."""

    email: str
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Safe user projection for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: UserRole
    status: UserStatus
    created_at: datetime


class LoginResponse(BaseModel):
    """Successful authentication response for the first vertical slice."""

    authenticated: bool
    message: str
    user: UserResponse
