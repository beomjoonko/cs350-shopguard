"""
Redis client used for:
  - Cache (URL analysis results — SRS §2.2 'Results Caching')
  - Message queue (analysis jobs — SRS §2.1.1.2 'Asynchronous Analysis')
  - Rate limit counters (SRS §4.8)
"""
import redis

from app.config import settings

import os as _os

# Support both REDIS_URL (Upstash / cloud) and individual HOST+PORT (local Docker)
_redis_url = _os.environ.get("REDIS_URL")
if _redis_url:
    redis_client = redis.from_url(_redis_url, decode_responses=True)
else:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
    )


# Queue keys — coordinate with ai-worker/worker/main.py
ANALYSIS_QUEUE_KEY = "shopguard:queue:analysis"
ANALYSIS_RESULT_KEY_PREFIX = "shopguard:result:"
URL_CACHE_KEY_PREFIX = "shopguard:url:"


def enqueue_analysis_job(job_id: str, url: str) -> None:
    """Push an analysis job onto the queue. Picked up by ai-worker."""
    import json
    redis_client.rpush(
        ANALYSIS_QUEUE_KEY,
        json.dumps({"job_id": job_id, "url": url}),
    )


def get_cached_url_result(normalized_url: str) -> dict | None:
    """Return cached analysis result for a URL, or None."""
    import json
    raw = redis_client.get(f"{URL_CACHE_KEY_PREFIX}{normalized_url}")
    return json.loads(raw) if raw else None
