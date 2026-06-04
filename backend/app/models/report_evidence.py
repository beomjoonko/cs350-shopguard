"""Binary evidence images stored per report — SRS §4.2."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class ReportEvidence(Base):
    __tablename__ = "report_evidence"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(CHAR(36), ForeignKey("reports.id"), nullable=False, unique=True, index=True)
    content_type = Column(String(128), nullable=False)
    filename = Column(String(255), nullable=False)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    report = relationship("Report", back_populates="evidence")
