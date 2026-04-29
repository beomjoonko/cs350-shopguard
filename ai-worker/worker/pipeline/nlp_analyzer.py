"""
NLP analyzer — SRS §4.6 REQ-5.

Computes an "AI score" in [0, 100] from the feature dict produced by the
feature extractor. Currently a transparent linear combination so the pipeline
can run with no trained model. Replace with a real classifier once TBD-3
(NLP model selection) is resolved.
"""
from __future__ import annotations


# Weights are intentionally simple — DO NOT ship to prod without retraining.
_WEIGHTS = {
    "review_repetition_rate": 40.0,
    "rating_skew": 30.0,
    "price_anomaly": 20.0,
    "image_similarity": 10.0,
}


def compute_ai_score(features: dict) -> float:
    """Return an AI score in [0, 100]."""
    if not features.get("has_product"):
        # No data → mildly suspicious but not strongly so.
        return 25.0

    score = 0.0
    for k, w in _WEIGHTS.items():
        score += float(features.get(k, 0.0)) * w

    return max(0.0, min(100.0, score))
