"""
REPORTS table — SRS Appendix B Figure B.3 + state-transition diagram (Fig B.2).

State machine:
    DRAFT → SUBMITTED → ACTIVE → UNDER_REVIEW → VERIFIED | BLINDED_DELETED
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

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

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    url_id = Column(CHAR(36), ForeignKey("urls.id"), nullable=False, index=True)
    fraud_type = Column(Enum(FraudType), nullable=False)
    description = Column(Text, nullable=False)
    evidence_image_url = Column(String(2048), nullable=True)  # S3 — SRS §3.3
    status = Column(Enum(ReportStatus), nullable=False, default=ReportStatus.SUBMITTED)
    legal_consent = Column(Boolean, nullable=False, default=False)  # §4.2 REQ-3
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    evidence = relationship(
        "ReportEvidence",
        back_populates="report",
        uselist=False,
        lazy="select",
    )
