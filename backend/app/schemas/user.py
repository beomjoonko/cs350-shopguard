"""
Pydantic schemas for auth and user-facing endpoints.

Post-Supabase migration: TokenResponse, UserLogin, PasswordChange, and
PasswordResetRequest have been removed. Login, password-change, and
password-reset are now handled directly by the Supabase JS SDK on the frontend.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole, UserStatus


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    status: UserStatus
    created_at: datetime

    class Config:
        from_attributes = True
