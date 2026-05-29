"""
ADMIN_AUDIT_LOGS table — SRS Appendix B Figure B.3.

Required by SRS §4.4 REQ-6 (record admin id, reason, timestamp on user
suspension) and §5.3 (security event logging).
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    target_id = Column(String(255), nullable=False)  # user id, report id, URL id, etc.
    action_type = Column(String(64), nullable=False) # e.g., "BLOCK_USER", "HIDE_REPORT"
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
