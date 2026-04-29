"""
Risk Score Model — SRS §4.7.

Inputs (REQ-2): ai_score, report_score, report_count
Output  (REQ-1, 3, 4): integer in [0, 100], rounded
Levels (REQ-5):
  Safe     0–30
  Warning  31–60
  Danger   61–80
  Critical 81–100

TBD-1 (Appendix C) will replace this placeholder formula with a calibrated one.
"""
from __future__ import annotations


# How heavily we weigh user reports vs. the AI score.
_AI_WEIGHT = 0.7
_REPORT_WEIGHT = 0.3
# Each active report is worth N points of "report score", capped.
_POINTS_PER_REPORT = 10
_REPORT_SCORE_CAP = 100


def _report_score(report_count: int) -> float:
    return float(min(report_count * _POINTS_PER_REPORT, _REPORT_SCORE_CAP))


def compute_final_risk_score(ai_score: float, report_count: int) -> int:
    raw = ai_score * _AI_WEIGHT + _report_score(report_count) * _REPORT_WEIGHT
    raw = max(0.0, min(100.0, raw))
    return int(round(raw))


def score_to_level(score: int) -> str:
    if score <= 30:
        return "SAFE"
    if score <= 60:
        return "WARNING"
    if score <= 80:
        return "DANGER"
    return "CRITICAL"
