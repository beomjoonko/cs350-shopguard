"""
REPORTS table — SRS Appendix B Figure B.3 + state-transition diagram (Fig B.2).

State machine:
    DRAFT → SUBMITTED → ACTIVE → UNDER_REVIEW → VERIFIED | BLINDED_DELETED
"""
import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class FraudType(str, enum.Enum):
    """SRS §4.2.2 — fraud type dropdown options."""
    NON_DELIVERY = "NON_DELIVERY"
    FALSE_ADVERTISING = "FALSE_ADVERTISING"
    REFUSAL_OF_REFUND = "REFUSAL_OF_REFUND"
    DEFECTIVE_PRODUCTS = "DEFECTIVE_PRODUCTS"
    PERSONAL_DATA_LEAKAGE = "PERSONAL_DATA_LEAKAGE"
    OTHERS = "OTHERS"


class ReportStatus(str, enum.Enum):
    """SRS Figure B.2 — Fraud Report State-Transition Diagram."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACTIVE = "ACTIVE"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    BLINDED_DELETED = "BLINDED_DELETED"
    PENDING = "PENDING"     # admin-controlled state per §4.4 REQ-3
    HIDDEN = "HIDDEN"       # admin-controlled state per §4.4 REQ-3


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    url_id = Column(UUID(as_uuid=True), ForeignKey("urls.id"), nullable=False, index=True)
    fraud_type = Column(Enum(FraudType, name="fraudtype"), nullable=False)
    description = Column(Text, nullable=False)
    evidence_image_url = Column(String(2048), nullable=True)  # Supabase Storage — SRS §3.3
    status = Column(Enum(ReportStatus, name="reportstatus"), nullable=False, default=ReportStatus.SUBMITTED)
    legal_consent = Column(Boolean, nullable=False, default=False)  # §4.2 REQ-3
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )
