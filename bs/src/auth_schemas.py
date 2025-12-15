"""Pydantic schemas for auth: login, register, tokens, and profiles.

Centralizes validation for authentication flows and user info payloads.
Last Updated: 2025-12-14.
"""
# bs/src/auth_schemas.py
"""Pydantic schemas for authentication."""
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request payload."""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """User registration request payload."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: EmailStr
    role: str = Field(default="user", pattern="^(user|admin)$")


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserInfo"


class UserInfo(BaseModel):
    """User information."""
    username: str
    email: str
    role: str


class UpdateUserRequest(BaseModel):
    """Update user request payload."""
    email: EmailStr | None = None
    role: str | None = Field(None, pattern="^(user|admin)$")
    password: str | None = Field(None, min_length=6)
