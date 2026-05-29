"""
AI Worker entry point — SRS §4.6 AI Analysis Pipeline.

Runs a blocking BLPOP loop on the Redis analysis queue. For each job:

  1. Crawl the URL (worker/crawler) → CrawlSnapshot
  2. NLP analysis (worker/pipeline/nlp_analyzer)
  3. Compute final risk score (worker/scoring/risk_scorer)
  4. Persist results to PostgreSQL (Supabase) + cache in Redis

In production this should be replaced or wrapped with Celery / RQ / Dramatiq
once the team picks an orchestrator. For the skeleton we keep it minimal so
nothing else has to be installed to see the loop run.
"""
from __future__ import annotations
import json
import logging
import time
import uuid
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
    import os
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        return redis.from_url(redis_url, decode_responses=True)
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


def _persist_snapshot(db: Session, job_id: str, url_id: str, snapshot) -> None:
    """Store the raw CrawlSnapshot in crawl_snapshots (own commit, so the crawl
    record survives even if downstream scoring fails)."""
    db.execute(
        text("""
            INSERT INTO crawl_snapshots (
                id, analysis_job_id, url_id, scan_date,
                protocol, fetch_status, fetch_ok,
                features_text, features_html, features_css,
                language, assets_downloaded,
                security_state, security_protocol, security_issuer,
                security_valid_from, security_valid_to,
                whois_domain_age, whois_registry_expired_at, whois_registrar,
                remote_ip_country, remote_ip_asn, remote_ip_isp,
                created_at
            ) VALUES (
                :id, :job_id, :url_id, :scan_date,
                :protocol, :fetch_status, :fetch_ok,
                :features_text, :features_html, :features_css,
                :language, :assets_downloaded,
                :security_state, :security_protocol, :security_issuer,
                :security_valid_from, :security_valid_to,
                :whois_domain_age, :whois_registry_expired_at, :whois_registrar,
                :remote_ip_country, :remote_ip_asn, :remote_ip_isp,
                :created_at
            )
        """),
        {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "url_id": url_id,
            "scan_date": snapshot.scan_date,
            "protocol": snapshot.protocol,
            "fetch_status": snapshot.fetch_status,
            "fetch_ok": snapshot.fetch_ok,
            "features_text": snapshot.features_text,
            "features_html": json.dumps(snapshot.features_html),
            "features_css": json.dumps(snapshot.features_css),
            "language": snapshot.language,
            "assets_downloaded": snapshot.assets_downloaded,
            "security_state": snapshot.security_state,
            "security_protocol": snapshot.security_protocol,
            "security_issuer": snapshot.security_issuer,
            "security_valid_from": snapshot.security_valid_from,
            "security_valid_to": snapshot.security_valid_to,
            "whois_domain_age": snapshot.whois_domain_age,
            "whois_registry_expired_at": snapshot.whois_registry_expired_at,
            "whois_registrar": snapshot.whois_registrar,
            "remote_ip_country": snapshot.remote_ip_country,
            "remote_ip_asn": snapshot.remote_ip_asn,
            "remote_ip_isp": snapshot.remote_ip_isp,
            "created_at": datetime.utcnow(),
        },
    )
    db.commit()


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
        _persist_snapshot(db, job_id, url_id, snapshot)

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
