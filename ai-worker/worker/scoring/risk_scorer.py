"""
Risk Score Model — SRS §4.7.

Inputs (REQ-2): ai_score, report_score, report_count
Output  (REQ-1, 3, 4): integer in [0, 100], rounded
Levels (REQ-5):
  Safe     0–30
  Warning  31–60
  Danger   61–80
  Critical 81–100

Stateless by design: each run recomputes the score from scratch. The only
cumulative input is report_count (a fresh DB COUNT of active/verified
reports); the previous final_risk_score is NOT fed back in — we overwrite
urls.current_risk_score each run rather than smoothing against history.

This is deliberate to prevent a score-dilution (bust-out) attack: an
attacker could keep a page benign and pre-seed it so it accumulates a
history of low/safe scores, then flip it to a fraud page. If past scores
were blended into the current one, that accumulated "safe" history would
drag the score down and even fresh reports might not push it out of the
SAFE band fast enough. By scoring purely from the *current* crawl, URL,
and report count, a page that turns malicious is judged on what it is now,
not on the clean reputation it banked earlier.

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
