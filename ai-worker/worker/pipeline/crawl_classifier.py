"""
Crawl classifier — content-based fraud signal from a CrawlSnapshot.

Model: MLP (3796 -> 256 -> 64 -> 1) trained on the phishpedia subset of
merged_v1.parquet. Label semantics:
    1 = Legitimate
    0 = Phishing
ONNX output is the pre-sigmoid `logit`. We apply sigmoid to get
P(legitimate), then return fraud_score = (1 - P_legit) * 100 — same
direction as url_classifier so the two scores can be blended.

The helper functions html_to_tokens / css_to_tokens / parse_iso /
days_between are **verbatim** copies from crawl_fraud_model_training.ipynb
section 3. Any divergence breaks fit/transform parity and the model is
meaningless. Update notebook and this file together if they ever change.

Distribution caveat: training data is phishpedia (Microsoft / UPS / DHL
impersonation). E-commerce scam pages are out of distribution. The blend
weight in nlp_analyzer should reflect that.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import joblib
import numpy as np
import onnxruntime as ort
import pandas as pd

from worker.crawler.snapshot import CrawlSnapshot


# ─── Artifact loading (runs once at import) ─────────────────────────────
_ARTIFACT_DIR = Path(__file__).resolve().parent / "crawl_model_artifacts"

_PRE = joblib.load(_ARTIFACT_DIR / "preprocessor.pkl")
_SESSION = ort.InferenceSession(str(_ARTIFACT_DIR / "fraud_model.onnx"))
_INPUT_NAME = _SESSION.get_inputs()[0].name

with open(_ARTIFACT_DIR / "feature_metadata.json") as _f:
    _META: dict = json.load(_f)

_COLUMNS: list[str] = _META["columns_required"]
_CATEGORICAL: list[str] = _META["categorical_cols"]


# ─── Helper functions (VERBATIM copies from notebook section 3) ─────────

def html_to_tokens(s):
    """features_html is a JSON list of tag tokens. Return space-delimited string."""
    if not isinstance(s, str) or not s.strip():
        return ''
    try:
        tags = json.loads(s)
        if not isinstance(tags, list):
            return ''
        return ' '.join(str(t).lower() for t in tags if isinstance(t, str))
    except Exception:
        return ''


def css_to_tokens(s):
    """features_css is a JSON dict {property: [values]}. Return space-delimited property names.
    Values are intentionally dropped - presence of a property is the signal."""
    if not isinstance(s, str) or not s.strip():
        return ''
    try:
        d = json.loads(s)
        if not isinstance(d, dict):
            return ''
        return ' '.join(str(k).lower().replace(' ', '_') for k in d.keys())
    except Exception:
        return ''


def parse_iso(s):
    if not isinstance(s, str) or not s.strip():
        return pd.NaT
    try:
        return pd.to_datetime(s, errors='coerce', utc=True)
    except Exception:
        return pd.NaT


def days_between(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    return (a - b).total_seconds() / 86400.0


# ─── Snapshot -> 1-row DataFrame ────────────────────────────────────────

def _iso(dt) -> str | None:
    """datetime -> ISO string. The verbatim helper above expects strings,
    so we round-trip datetimes through ISO to keep one parse path."""
    if dt is None:
        return None
    return dt.isoformat()


def _row_from_snapshot(snap: CrawlSnapshot) -> pd.DataFrame:
    """Mirror notebook cell `feat-build` for a single CrawlSnapshot."""
    text_tokens = snap.features_text or ''
    html_tokens = html_to_tokens(json.dumps(snap.features_html))
    css_tokens = css_to_tokens(json.dumps(snap.features_css))

    scan_dt = parse_iso(_iso(snap.scan_date))
    cert_from_dt = parse_iso(_iso(snap.security_valid_from))
    cert_to_dt = parse_iso(_iso(snap.security_valid_to))
    whois_exp_dt = parse_iso(_iso(snap.whois_registry_expired_at))

    row = {
        'text_tokens': text_tokens,
        'html_tokens': html_tokens,
        'css_tokens': css_tokens,
        'assets_downloaded': snap.assets_downloaded,
        'whois_domain_age': snap.whois_domain_age,
        'cert_validity_days': days_between(cert_to_dt, cert_from_dt),
        'cert_remaining_at_scan': days_between(cert_to_dt, scan_dt),
        'cert_age_at_scan': days_between(scan_dt, cert_from_dt),
        'domain_age_to_expiry': days_between(whois_exp_dt, scan_dt),
        'has_tls': 1 if snap.security_protocol is not None else 0,
        'language': snap.language,
        'protocol': snap.protocol,
        'security_state': snap.security_state,
        'security_protocol': snap.security_protocol,
        'security_issuer': snap.security_issuer,
        'remote_ip_country': snap.remote_ip_country,
    }
    df = pd.DataFrame([row])

    # Numeric coercion + categorical fillna — same order as the training cell.
    df['domain_age_days'] = pd.to_numeric(df['whois_domain_age'], errors='coerce')
    df['assets_downloaded'] = pd.to_numeric(df['assets_downloaded'], errors='coerce')

    for c in _CATEGORICAL:
        df[c] = df[c].fillna('__missing__').astype(str)

    return df[_COLUMNS]


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


# ─── Public API ─────────────────────────────────────────────────────────

def compute_crawl_risk_score(snapshot: CrawlSnapshot) -> float:
    """Return crawl-based fraud risk score in [0, 100].

    snapshot -> 1-row DataFrame -> ColumnTransformer -> ONNX MLP
    -> sigmoid(logit) = P(legitimate); fraud_score = (1 - P_legit) * 100.
    """
    df = _row_from_snapshot(snapshot)
    sp = _PRE.transform(df)
    dense = sp.toarray() if hasattr(sp, "toarray") else np.asarray(sp)
    x = dense.astype(np.float32)
    logit = float(_SESSION.run(None, {_INPUT_NAME: x})[0].ravel()[0])
    p_legit = _sigmoid(logit)
    return (1.0 - p_legit) * 100.0
