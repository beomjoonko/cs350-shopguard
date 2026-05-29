"""
URLS table — SRS Appendix B Figure B.3.

One row per *normalized* URL. URL normalization (SRS §4.5 REQ-2) prevents
duplicate analysis of equivalent links.
"""
import enum
import hashlib
import uuid

from sqlalchemy import Column, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class RiskLevel(str, enum.Enum):
    """SRS §1.2 — Risk levels derived from Risk Score."""
    SAFE = "SAFE"          # 0–30
    WARNING = "WARNING"    # 31–60
    DANGER = "DANGER"      # 61–80
    CRITICAL = "CRITICAL"  # 81–100


class Url(Base):
    __tablename__ = "urls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    normalized_url = Column(String(2048), nullable=False)
    # Keep uniqueness on a fixed-size hash to avoid index length limits on long URLs.
    normalized_url_hash = Column(String(64), unique=True, nullable=False, index=True)
    current_risk_score = Column(Integer, nullable=True)  # 0–100, SRS §4.7 REQ-3
    current_risk_level = Column(Enum(RiskLevel, name="risklevel"), nullable=True)
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @staticmethod
    def compute_hash(normalized_url: str) -> str:
        return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
