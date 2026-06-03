"""
Auth endpoints — SRS §4.1 User Account Management.

  POST /auth/register   create account                    (REQ-1)
  POST /auth/login      issue JWT, count failures         (REQ-1, REQ-3)
  POST /auth/password-reset/request   send reset email    (REQ-2)
  POST /auth/password-reset/confirm   apply new password  (REQ-2)
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.blacklist import Blacklist
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import (
    PasswordResetRequest,
    TokenResponse,
    UserLogin,
    UserPublic,
    UserRegister,
)

router = APIRouter()


@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """SRS §4.1 REQ-1 + §4.4 REQ-5 (blacklist enforcement)."""
    if db.query(Blacklist).filter(Blacklist.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This email is not allowed to register",
        )

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """SRS §4.1 REQ-3: lock account for 30 minutes after 5 failed attempts."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check temporary lock
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked until {user.locked_until.isoformat()}",
        )

    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="Account suspended")

    if not verify_password(payload.password, user.password_hash):
        # Atomic increment at DB level to prevent race condition on concurrent requests
        db.query(User).filter(User.id == user.id).update(
            {User.failed_login_attempts: User.failed_login_attempts + 1},
            synchronize_session="fetch",
        )
        db.commit()
        db.refresh(user)
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=settings.LOGIN_LOCKOUT_MINUTES
            )
            user.failed_login_attempts = 0
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Success — reset counters
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(access_token=token)


@router.post("/password-reset/request", status_code=202)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    SRS §4.1 REQ-2 — send reset email.

    Always returns 202 to avoid leaking which emails are registered.
    TODO: enqueue an email job via SMTP (SRS §3.4) with a signed reset token.
    """
    return {"detail": "If the address exists, a reset link has been sent."}
