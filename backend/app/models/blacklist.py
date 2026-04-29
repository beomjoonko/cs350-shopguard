"""
BLACKLIST table — SRS Appendix B Figure B.3.

Required by SRS §4.4 REQ-5: blocked emails cannot re-register.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base


class Blacklist(Base):
    __tablename__ = "blacklist"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
