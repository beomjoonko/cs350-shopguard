"""
AI Worker entry point — SRS §4.6 AI Analysis Pipeline.

Runs a blocking BLPOP loop on the Redis analysis queue. For each job:

  1. Crawl the URL (worker/crawler) → CrawlSnapshot
  2. NLP analysis (worker/pipeline/nlp_analyzer)
  3. Compute final risk score (worker/scoring/risk_scorer)
  4. Persist results to MySQL + cache in Redis

In production this should be replaced or wrapped with Celery / RQ / Dramatiq
once the team picks an orchestrator. For the skeleton we keep it minimal so
nothing else has to be installed to see the loop run.
"""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime

import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from worker.config import settings
from worker.database import SessionLocal
from worker.crawler import crawl
from worker.pipeline.nlp_analyzer import compute_ai_score
from worker.scoring.risk_scorer import compute_final_risk_score, score_to_level


ANALYSIS_QUEUE_KEY = "shopguard:queue:analysis"
URL_CACHE_KEY_PREFIX = "shopguard:url:"
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24h

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ai-worker")


def _get_redis() -> redis.Redis:
    return redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)


def _set_job_status(db: Session, job_id: str, status: str) -> None:
    db.execute(
        text("UPDATE analysis_jobs SET status = :s WHERE id = :id"),
        {"s": status, "id": job_id},
    )
    db.commit()


def _count_active_reports(db: Session, url_id: str) -> int:
    row = db.execute(
        text("""
            SELECT COUNT(*) FROM reports
            WHERE url_id = :url_id
              AND status IN ('ACTIVE', 'VERIFIED')
        """),
        {"url_id": url_id},
    ).scalar()
    return int(row or 0)


def process_job(job: dict, db: Session, r: redis.Redis) -> None:
    job_id = job["job_id"]
    url = job["url"]
    log.info("job=%s url=%s START", job_id, url)

    # url_id lookup (the API server already created the URL row)
    url_row = db.execute(
        text("SELECT id FROM urls WHERE normalized_url = :u"),
        {"u": url},
    ).first()
    if not url_row:
        log.error("job=%s url row missing — skipping", job_id)
        _set_job_status(db, job_id, "FAILED")
        return
    url_id = url_row[0]

    try:
        _set_job_status(db, job_id, "CRAWLING")
        snapshot = crawl(url)

        _set_job_status(db, job_id, "ANALYZING")
        ai_score = compute_ai_score(url, snapshot)

        report_count = _count_active_reports(db, url_id)
        final_score = compute_final_risk_score(
            ai_score=ai_score,
            report_count=report_count,
        )
        risk_level = score_to_level(final_score)

        # Persist
        db.execute(
            text("""
                UPDATE analysis_jobs
                   SET status='COMPLETED',
                       ai_score=:ai,
                       report_count=:rc,
                       final_risk_score=:fs,
                       completed_at=:ts
                 WHERE id=:id
            """),
            {
                "ai": ai_score, "rc": report_count, "fs": final_score,
                "ts": datetime.utcnow(), "id": job_id,
            },
        )
        db.execute(
            text("""
                UPDATE urls
                   SET current_risk_score=:fs,
                       current_risk_level=:lvl,
                       last_analyzed_at=:ts
                 WHERE id=:id
            """),
            {"fs": final_score, "lvl": risk_level, "ts": datetime.utcnow(), "id": url_id},
        )
        db.commit()

        # Cache (SRS §2.2 'Results Caching')
        r.setex(
            f"{URL_CACHE_KEY_PREFIX}{url}",
            CACHE_TTL_SECONDS,
            json.dumps({"risk_score": final_score, "risk_level": risk_level}),
        )

        log.info("job=%s DONE score=%s level=%s", job_id, final_score, risk_level)

    except Exception:
        log.exception("job=%s FAILED", job_id)
        db.rollback()
        _set_job_status(db, job_id, "FAILED")


def main() -> None:
    r = _get_redis()
    log.info("AI worker ready — listening on %s", ANALYSIS_QUEUE_KEY)

    while True:
        try:
            popped = r.blpop(ANALYSIS_QUEUE_KEY, timeout=5)
            if popped is None:
                continue
            _, raw_job = popped
            job = json.loads(raw_job)

            db = SessionLocal()
            try:
                process_job(job, db, r)
            finally:
                db.close()

            # Politeness delay between crawls (SRS §2.5)
            time.sleep(settings.CRAWLER_REQUEST_DELAY_MS / 1000)
        except KeyboardInterrupt:
            log.info("Shutting down")
            break
        except Exception:
            log.exception("Unhandled error in main loop")
            time.sleep(1)


if __name__ == "__main__":
    main()
