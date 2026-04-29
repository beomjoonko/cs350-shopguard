"""
Security primitives — SRS §5.3.

  - Password hashing: Argon2 (RFC 9106)
  - Token issuance: JWT (RFC 7519)

All sensitive crypto operations go through this module so we have a single
place to audit / rotate algorithms.
"""
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.config import settings


_password_hasher = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)


# ─── Password ───────────────────────────────────────────────
def hash_password(plain_password: str) -> str:
    """Hash a password using Argon2id (SRS §5.3)."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed: str) -> bool:
    """Constant-time password verification."""
    try:
        _password_hasher.verify(hashed, plain_password)
        return True
    except VerifyMismatchError:
        return False


# ─── JWT ────────────────────────────────────────────────────
def create_access_token(
    subject: str | int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a JWT access token. `subject` is the user id."""
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Return token claims if valid, otherwise None."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return None
