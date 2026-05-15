"""Pydantic schemas for admin operations — SRS §4.4."""
from pydantic import BaseModel, Field


class BlockUserRequest(BaseModel):
    reason: str = Field(min_length=1, description="Required for audit log — SRS §4.4 REQ-6")
