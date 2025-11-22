from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str
    role: Optional[str] = "user"


class UserRead(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    remaining_calls: int


class TokenRead(BaseModel):
    jti: str
    issued_at: datetime
    expires_at: datetime
    remaining_calls: int
    revoked: bool

    class Config:
        orm_mode = True
