"""
URLS table — SRS Appendix B Figure B.3.

One row per *normalized* URL. URL normalization (SRS §4.5 REQ-2) prevents
duplicate analysis of equivalent links.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base


class RiskLevel(str, enum.Enum):
    """SRS §1.2 — Risk levels derived from Risk Score."""
    SAFE = "SAFE"          # 0–30
    WARNING = "WARNING"    # 31–60
    DANGER = "DANGER"      # 61–80
    CRITICAL = "CRITICAL"  # 81–100


class Url(Base):
    __tablename__ = "urls"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Keep this indexable under MySQL utf8mb4 index-size limits.
    normalized_url = Column(String(768), unique=True, nullable=False, index=True)
    current_risk_score = Column(Integer, nullable=True)  # 0–100, SRS §4.7 REQ-3
    current_risk_level = Column(Enum(RiskLevel), nullable=True)
    last_analyzed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
