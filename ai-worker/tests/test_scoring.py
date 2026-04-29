"""Pure unit tests for scoring + feature extraction (no Redis/DB)."""
from worker.scoring.risk_scorer import compute_final_risk_score, score_to_level
from worker.pipeline.feature_extractor import extract_features
from worker.crawler.base import CrawlResult, Review, Product


def test_score_levels():
    assert score_to_level(0) == "SAFE"
    assert score_to_level(30) == "SAFE"
    assert score_to_level(31) == "WARNING"
    assert score_to_level(60) == "WARNING"
    assert score_to_level(61) == "DANGER"
    assert score_to_level(80) == "DANGER"
    assert score_to_level(81) == "CRITICAL"
    assert score_to_level(100) == "CRITICAL"


def test_score_bounds():
    assert 0 <= compute_final_risk_score(ai_score=0, report_count=0) <= 100
    assert 0 <= compute_final_risk_score(ai_score=100, report_count=999) <= 100


def test_review_repetition_picks_up_duplicates():
    reviews = [Review(text="great"), Review(text="great"), Review(text="ok")]
    f = extract_features(
        CrawlResult(url="x", html="", reviews=reviews, product=Product(title="t"))
    )
    assert f["review_repetition_rate"] > 0
