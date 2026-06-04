"""
USERS table — SRS Appendix B Figure B.3.

Columns: id, email, password_hash, role, status, failed_login_attempts,
         token_version, created_at, updated_at
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"        # temporary, after failed-login threshold
    SUSPENDED = "SUSPENDED"  # admin-imposed (SRS §4.4 REQ-4)


class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)  # supports SRS §4.1 REQ-3
    token_version = Column(Integer, nullable=False, default=0)  # SRS §4.4 REQ-4
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow,
    )
