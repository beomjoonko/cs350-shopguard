"""Hashing for password-reset link tokens (never store raw tokens)."""
import hashlib
import secrets


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
