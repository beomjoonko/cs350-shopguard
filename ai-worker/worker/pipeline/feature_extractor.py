"""
Feature extraction — SRS §4.6 REQ-4.

The SRS calls out four indicators explicitly:
  - review repetition rate
  - rating distribution
  - price anomalies
  - image similarity

This module produces a flat feature dict that the NLP analyzer (and any
downstream classifier) consumes. Each feature defaults to a neutral value
when the input is empty so the pipeline never crashes on a missing crawl.
"""
from collections import Counter
from worker.crawler.base import CrawlResult


def _review_repetition_rate(reviews) -> float:
    """Fraction of review texts that are not unique."""
    if not reviews:
        return 0.0
    counts = Counter(r.text for r in reviews if r.text)
    if not counts:
        return 0.0
    duplicates = sum(c for c in counts.values() if c > 1)
    return duplicates / len(reviews)


def _rating_skew(reviews) -> float:
    """
    A heuristic for unnaturally skewed ratings.

    Returns 0 for natural-looking distributions and approaches 1 when
    >90% of ratings are 5 stars (a classic fake-review signal).
    """
    ratings = [r.rating for r in reviews if r.rating is not None]
    if len(ratings) < 5:
        return 0.0
    five_star_share = sum(1 for r in ratings if r >= 4.9) / len(ratings)
    return max(0.0, (five_star_share - 0.5) * 2)  # 0.5 → 0, 1.0 → 1


def _price_anomaly(product) -> float:
    """Placeholder — needs market-price reference data to be meaningful."""
    if product is None or product.price is None:
        return 0.0
    # TBD: compare against product-category baseline
    return 0.0


def _image_similarity_score(product) -> float:
    """Placeholder — would use perceptual hashing against a known-stolen-images DB."""
    return 0.0


def extract_features(crawl: CrawlResult) -> dict:
    return {
        "review_repetition_rate": _review_repetition_rate(crawl.reviews),
        "rating_skew": _rating_skew(crawl.reviews),
        "price_anomaly": _price_anomaly(crawl.product),
        "image_similarity": _image_similarity_score(crawl.product),
        "review_count": len(crawl.reviews),
        "has_product": crawl.product is not None,
    }
