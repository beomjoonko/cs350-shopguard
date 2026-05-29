"""
Rate limiting — SRS §4.8 REQ-1.

Per SRS: 60 requests per minute per IP address (in-memory storage).
"""
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import Request, HTTPException

_request_times = defaultdict(list)


async def check_rate_limit(request: Request) -> None:
    """Check if IP has exceeded rate limit (60/min)."""
    from app.config import settings

    client_ip = request.client.host
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=1)

    _request_times[client_ip] = [t for t in _request_times[client_ip] if t > cutoff]

    if len(_request_times[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    _request_times[client_ip].append(now)
