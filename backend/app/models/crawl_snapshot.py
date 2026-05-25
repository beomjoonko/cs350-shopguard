"""
CRAWL_SNAPSHOTS table.

One row per crawl performed by the ai-worker. Persists the raw `CrawlSnapshot`
the crawler produces (ai-worker/worker/crawler/snapshot.py) so crawl results are
retained for auditing, re-scoring, and later WHOIS/geo enrichment instead of
being discarded after the risk score is computed.

The column set mirrors the `CrawlSnapshot` dataclass field-for-field. The worker
writes rows via raw SQL; this model exists so Alembic can manage the schema and
the backend can query snapshots.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.mysql import CHAR, LONGTEXT

from app.core.database import Base


class CrawlSnapshot(Base):
    __tablename__ = "crawl_snapshots"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_job_id = Column(CHAR(36), ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    url_id = Column(CHAR(36), ForeignKey("urls.id"), nullable=False, index=True)

    scan_date = Column(DateTime, nullable=False)

    # HTTP fetch outcome
    protocol = Column(String(16), nullable=True)
    fetch_status = Column(Integer, nullable=True)
    fetch_ok = Column(Boolean, nullable=False, default=False)

    # Page content (raw — classifier tokenizes at inference time)
    features_text = Column(LONGTEXT, nullable=True)   # visible text
    features_html = Column(JSON, nullable=True)       # list[str] of tag names
    features_css = Column(JSON, nullable=True)        # {prop: [vals]}

    # Page metadata
    language = Column(String(16), nullable=True)
    assets_downloaded = Column(Integer, nullable=True)

    # TLS (None on plain HTTP or handshake failure)
    security_state = Column(String(64), nullable=True)
    security_protocol = Column(String(64), nullable=True)
    security_issuer = Column(String(512), nullable=True)
    security_valid_from = Column(DateTime, nullable=True)
    security_valid_to = Column(DateTime, nullable=True)

    # WHOIS — populated by a later iteration
    whois_domain_age = Column(Float, nullable=True)
    whois_registry_expired_at = Column(DateTime, nullable=True)
    whois_registrar = Column(String(255), nullable=True)

    # Remote IP geo — populated by a later iteration
    remote_ip_country = Column(String(8), nullable=True)
    remote_ip_asn = Column(String(64), nullable=True)
    remote_ip_isp = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
