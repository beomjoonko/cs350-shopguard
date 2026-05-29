"""
USERS table — SRS Appendix B Figure B.3.

Columns: id, supabase_uid, email, role, status, created_at, updated_at

Post-Supabase migration:
  - password_hash, failed_login_attempts, locked_until removed
    (password management delegated to Supabase Auth)
  - supabase_uid added — stores the Supabase Auth UUID (JWT `sub` claim)
  - LOCKED status removed (account lockout handled by Supabase Auth)
"""
import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"  # admin-imposed (SRS §4.4 REQ-4)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Supabase Auth user UUID — matches the `sub` claim in Supabase JWTs
    supabase_uid = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(Enum(UserRole, name="userrole"), nullable=False, default=UserRole.USER)
    status = Column(Enum(UserStatus, name="userstatus"), nullable=False, default=UserStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )
