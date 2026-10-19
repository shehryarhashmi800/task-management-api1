"""Authentication endpoints: register, login, refresh and the current user."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import limiter, login_limit, refresh_limit, register_limit
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.common import error_responses
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description=(
        "Registers a new user. The password must be at least 8 characters and "
        "contain a letter and a digit. Registration does not log you in; call "
        "`POST /auth/login` next. Rate limited per IP address."
    ),
    responses=error_responses(409, 422, 429),
)
@limiter.limit(register_limit)
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
    return AuthService(db).register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in",
    description=(
        "Exchanges an email and password for an access token (short-lived) and a "
        "refresh token (long-lived). Send the access token as "
        "`Authorization: Bearer <token>`. Rate limited per IP address to slow "
        "down password guessing."
    ),
    responses=error_responses(401, 403, 422, 429),
)
@limiter.limit(login_limit)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    """Log a user in and return a token pair."""
    return AuthService(db).login(payload.email, payload.password)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Get a new access token",
    description=(
        "Send the refresh token from login to receive a new access token without "
        "asking for the password again. Fails with 401 once the refresh token has "
        "expired, at which point the user must log in again."
    ),
    responses=error_responses(401, 422, 429),
)
@limiter.limit(refresh_limit)
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access token."""
    access_token = AuthService(db).refresh_access_token(payload.refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user",
    description="Returns the profile of the user the access token belongs to.",
    responses=error_responses(401, 403),
)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the logged-in user's profile."""
    return current_user
