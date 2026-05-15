"""
NLP analyzer — SRS §4.6 REQ-5.

Computes an "AI score" in [0, 100] for a URL by combining:
  1. URL classifier (always available) — worker.pipeline.url_classifier
  2. Content-based features (when crawler returned product/reviews)

When content is unavailable (TBD-2 crawlers are still stubs), the URL
classifier becomes the sole signal. Once real crawlers ship, the URL
score acts as a supplementary signal blended with the content score.
"""
from __future__ import annotations

from worker.pipeline.url_classifier import compute_url_risk_score


# Content-feature weights — same shape as the original placeholder formula.
_CONTENT_WEIGHTS = {
    "review_repetition_rate": 40.0,
    "rating_skew": 30.0,
    "price_anomaly": 20.0,
    "image_similarity": 10.0,
}

# Blend ratio when content is available.
_CONTENT_BLEND_WEIGHT = 0.7
_URL_BLEND_WEIGHT = 0.3


def _content_score(features: dict) -> float:
    score = 0.0
    for k, w in _CONTENT_WEIGHTS.items():
        score += float(features.get(k, 0.0)) * w
    return max(0.0, min(100.0, score))


def compute_ai_score(features: dict, url: str) -> float:
    """Return an AI score in [0, 100]."""
    url_score = compute_url_risk_score(url)

    if not features.get("has_product"):
        return url_score

    blended = _CONTENT_BLEND_WEIGHT * _content_score(features) + _URL_BLEND_WEIGHT * url_score
    return max(0.0, min(100.0, blended))
