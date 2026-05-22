"""
NLP analyzer — SRS §4.6 REQ-5.

Combines two fraud signals into a single AI score in [0, 100]:

  - url_classifier:   raw URL string only           (LegitPhish-trained MLP)
  - crawl_classifier: page content + WHOIS/TLS/IP   (phishpedia-trained MLP)

Both emit `(1 - P_legit) * 100`, so they share direction and can be blended
linearly. The crawl signal carries more information when available, so the
default weighting leans on it; but because the crawl model was trained on
brand-impersonation phishing (Microsoft/UPS/DHL) and ShopGuard targets
e-commerce, the weight is deliberately not extreme.

Fallback: when the crawler failed to fetch the page (fetch_ok=False), the
crawl signal is dropped and the URL score becomes the sole input — feeding
empty content into the classifier would produce an unreliable score.
"""
from __future__ import annotations

from worker.crawler.snapshot import CrawlSnapshot
from worker.pipeline.crawl_classifier import compute_crawl_risk_score
from worker.pipeline.url_classifier import compute_url_risk_score


_CRAWL_WEIGHT = 0.6
_URL_WEIGHT = 0.4


def _clamp(score: float) -> float:
    return max(0.0, min(100.0, score))


def compute_ai_score(url: str, snapshot: CrawlSnapshot | None = None) -> float:
    url_score = compute_url_risk_score(url)
    if snapshot is None or not snapshot.fetch_ok:
        return _clamp(url_score)
    crawl_score = compute_crawl_risk_score(snapshot)
    return _clamp(_CRAWL_WEIGHT * crawl_score + _URL_WEIGHT * url_score)
