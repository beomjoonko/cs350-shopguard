"""Pydantic schemas for auth and user-facing endpoints."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole, UserStatus


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    role: UserRole
    status: UserStatus
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class PasswordResetRequest(BaseModel):
    email: EmailStr
