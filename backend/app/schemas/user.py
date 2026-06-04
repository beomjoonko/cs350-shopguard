"""Pydantic schemas for auth and user-facing endpoints."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole, UserStatus
from app.utils.password_policy import validate_password_complexity


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_meets_complexity(cls, value: str) -> str:
        message = validate_password_complexity(value)
        if message:
            raise ValueError(message)
        return value


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

    @field_validator("new_password")
    @classmethod
    def new_password_meets_complexity(cls, value: str) -> str:
        message = validate_password_complexity(value)
        if message:
            raise ValueError(message)
        return value


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def new_password_meets_complexity(cls, value: str) -> str:
        message = validate_password_complexity(value)
        if message:
            raise ValueError(message)
        return value


class PasswordResetResponse(BaseModel):
    detail: str
