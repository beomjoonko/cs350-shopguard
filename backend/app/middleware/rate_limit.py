"""
Rate limiting — SRS §4.8 REQ-1.

We use slowapi (a Starlette/FastAPI port of Flask-Limiter) backed by Redis
so the limit is shared across multiple API server replicas.

Per SRS: 60 requests per minute per IP address.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
)
