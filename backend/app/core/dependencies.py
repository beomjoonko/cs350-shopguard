"""
FastAPI dependency injectables — post-Supabase migration.

  - `get_current_user`: validate Supabase JWT, auto-provision user row, enforce
                        active status
  - `require_admin`:   role gate for admin endpoints (SRS §4.4 REQ-1)

Authentication flow:
  1. Frontend logs in via Supabase JS SDK → gets a Supabase JWT
  2. Frontend sends JWT as `Authorization: Bearer <token>` to FastAPI
  3. `get_current_user` validates the JWT using SUPABASE_JWT_SECRET (HS256)
  4. On first request the user row is auto-provisioned in our `users` table
"""
import uuid as _uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_supabase_token
from app.models.user import User, UserRole, UserStatus

# HTTPBearer extracts the raw token from Authorization: Bearer <token>
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_supabase_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    # `sub` in a Supabase JWT is the Supabase Auth user UUID (string)
    supabase_uid_str: str | None = payload.get("sub")
    if not supabase_uid_str:
        raise credentials_exception

    try:
        supabase_uid = _uuid.UUID(supabase_uid_str)
    except ValueError:
        raise credentials_exception

    # Look up by supabase_uid — this is the stable Supabase identifier
    user = db.query(User).filter(User.supabase_uid == supabase_uid).first()

    if user is None:
        # Auto-provision on the user's first authenticated API request.
        # The email claim is always present in Supabase user session JWTs.
        email: str = payload.get("email", "")
        user = User(
            supabase_uid=supabase_uid,
            email=email,
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Gate for admin-only endpoints. SRS §4.4 REQ-1."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
