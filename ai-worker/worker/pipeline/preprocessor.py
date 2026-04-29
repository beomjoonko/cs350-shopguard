"""
Preprocessing — SRS §4.6 REQ-3.

Cleans and structures crawled data before feature extraction:
  - drop empty / non-text reviews
  - lower-case + whitespace-normalize review text
  - parse rating to float
  - de-duplicate exact review duplicates
"""
import re

from worker.crawler.base import CrawlResult, Review


_WHITESPACE = re.compile(r"\s+")


def _clean_text(s: str) -> str:
    return _WHITESPACE.sub(" ", s).strip().lower()


def preprocess(raw: CrawlResult) -> CrawlResult:
    seen: set[str] = set()
    cleaned_reviews: list[Review] = []
    for r in raw.reviews:
        text = _clean_text(r.text or "")
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        cleaned_reviews.append(Review(
            rating=r.rating,
            text=text,
            author=r.author,
            date=r.date,
        ))
    raw.reviews = cleaned_reviews
    return raw
