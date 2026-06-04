"""Password reset flow — SRS §4.1 REQ-2."""
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password, verify_password
from app.models.blacklist import Blacklist
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User, UserStatus
from app.services.email import send_password_reset_email
from app.utils.password_policy import validate_password_complexity
from app.utils.reset_token import generate_reset_token, hash_reset_token

_RESET_MSG = "If the address exists, a reset link has been sent."
_INVALID_LINK = "Invalid or expired reset link"


def request_password_reset(db: Session, email: str) -> dict:
    """Always return the same message; only send mail for eligible accounts."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"detail": _RESET_MSG}

    if user.status == UserStatus.SUSPENDED:
        return {"detail": _RESET_MSG}

    if db.query(Blacklist).filter(Blacklist.email == email).first():
        return {"detail": _RESET_MSG}

    raw_token = generate_reset_token()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).delete(synchronize_session=False)

    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw_token),
            expires_at=expires_at,
        )
    )
    db.commit()

    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={raw_token}"
    send_password_reset_email(user.email, reset_url)
    return {"detail": _RESET_MSG}


def confirm_password_reset(db: Session, raw_token: str, new_password: str) -> None:
    message = validate_password_complexity(new_password)
    if message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    token_hash = hash_reset_token(raw_token)
    row = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
        .first()
    )
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_LINK)

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or user.status == UserStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_LINK)

    if verify_password(new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current one",
        )

    user.password_hash = hash_password(new_password)
    user.token_version = (user.token_version or 0) + 1
    user.failed_login_attempts = 0
    user.locked_until = None
    row.used_at = datetime.utcnow()
    db.commit()
