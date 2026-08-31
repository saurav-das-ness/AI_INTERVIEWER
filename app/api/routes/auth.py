"""Authentication routes for the first backend vertical slice."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service
from app.models.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserResponse
from app.services.auth.service import AuthConflictError, AuthService, AuthenticationError


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Create a bootstrap user account for admin or candidate flows."""

    try:
        user = auth_service.register_user(payload)
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
def login_user(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate a user by email and password."""

    try:
        user = auth_service.authenticate(payload)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return LoginResponse(
        authenticated=True,
        message="Login successful",
        user=UserResponse.model_validate(user),
    )
