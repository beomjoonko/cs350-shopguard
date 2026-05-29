"""
Security primitives — post-Supabase migration.

JWT validation only: Supabase Auth issues and manages all tokens.
FastAPI validates the Supabase-issued JWT using SUPABASE_JWT_SECRET.

All password management (hashing, verification, reset) is now delegated
to Supabase Auth. The Argon2 and token-issuance code has been removed.
"""
from jose import JWTError, jwt

from app.config import settings


def decode_supabase_token(token: str) -> dict | None:
    """
    Validate a Supabase-issued JWT and return its claims.

    Supabase uses HS256 signed with SUPABASE_JWT_SECRET.
    The `sub` claim contains the Supabase Auth user UUID.
    The `aud` claim is always "authenticated" for user sessions.

    Returns None if the token is invalid, expired, or untrusted.
    """
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        return None
