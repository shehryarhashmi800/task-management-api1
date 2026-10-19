"""Request and response bodies for the authentication endpoints."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials sent to log in."""

    email: str = Field(..., max_length=255, examples=["alice@example.com"])
    password: str = Field(..., max_length=128, examples=["SecurePass1"])


class TokenResponse(BaseModel):
    """The token pair returned after a successful login."""

    access_token: str = Field(..., description="Short-lived token for API calls.")
    refresh_token: str = Field(..., description="Long-lived token used to get a new access token.")
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Body of the refresh request."""

    refresh_token: str = Field(..., max_length=2048)


class AccessTokenResponse(BaseModel):
    """A fresh access token."""

    access_token: str
    token_type: str = "bearer"
