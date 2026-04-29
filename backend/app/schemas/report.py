"""Pydantic schemas for fraud reports — SRS §4.2."""
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

from app.models.report import FraudType, ReportStatus


class ReportCreate(BaseModel):
    """Body for POST /reports — fraud reporting form."""
    url: HttpUrl
    fraud_type: FraudType
    description: str = Field(min_length=20)  # see "Please enter at least 20 characters" in SRS UI
    evidence_image_url: str | None = None
    legal_consent: bool = Field(..., description="Required — SRS §4.2 REQ-3")


class ReportPublic(BaseModel):
    id: str
    url_id: str
    fraud_type: FraudType
    description: str
    evidence_image_url: str | None
    status: ReportStatus
    created_at: datetime

    class Config:
        from_attributes = True


class ReportStatusUpdate(BaseModel):
    """Admin action — SRS §4.4 REQ-3."""
    status: ReportStatus
