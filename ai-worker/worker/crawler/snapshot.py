"""
CrawlSnapshot — output of the crawler, input to crawl_classifier.

Schema mirrors the phishpedia training corpus so the inference module can feed
the same fields through the preprocessor that was fitted in Colab. Raw fields
only — token derivation (html_to_tokens / css_to_tokens) lives in
crawl_classifier.py to keep the snapshot serializable and the classifier the
sole owner of preprocessing parity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CrawlSnapshot:
    url: str
    scan_date: datetime

    # HTTP fetch outcome
    protocol: str | None = None        # "http" / "https"
    fetch_status: int | None = None
    fetch_ok: bool = False

    # Page content (raw — classifier converts to tokens at inference time)
    features_text: str = ""                                  # visible text
    features_html: list[str] = field(default_factory=list)   # tag-name list
    features_css: dict[str, list[str]] = field(default_factory=dict)  # {prop:[vals]}

    # Page metadata
    language: str | None = None
    assets_downloaded: int = 0

    # TLS (None on plain HTTP or handshake failure)
    security_state: str | None = None
    security_protocol: str | None = None
    security_issuer: str | None = None
    security_valid_from: datetime | None = None
    security_valid_to: datetime | None = None

    # WHOIS — populated by a later iteration (python-whois). None for now.
    whois_domain_age: float | None = None
    whois_registry_expired_at: datetime | None = None
    whois_registrar: str | None = None

    # Remote IP geo — populated by a later iteration (geoip2 / MaxMind). None for now.
    remote_ip_country: str | None = None
    remote_ip_asn: str | None = None
    remote_ip_isp: str | None = None
