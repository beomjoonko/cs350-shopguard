"""
URL classifier — supplementary fraud signal from URL string alone.

Model: MLP (16 -> 64 -> 32 -> 1) trained on the LegitPhish dataset
(Mendeley hx4m73v2sf v2). Label semantics in the training set:
    1 = Legitimate
    0 = Phishing
ONNX output is the pre-sigmoid `logit`. We apply sigmoid to get
P(legitimate), then return fraud_score = (1 - P_legit) * 100.

NOTE on domain mismatch: training URLs are general web (URLHaus malware
+ Wikipedia/StackOverflow), not e-commerce. Treat this as a supplementary
signal for ShopGuard; primary content-based scoring should dominate once
the crawlers (TBD-2) are implemented.

NOTE: Data Quality and Feature Extraction Logic Anomalies
The dataset 'url_features_extracted1.csv' contains several intentionally 
miscalculated features or logic-based inconsistencies. Please account for 
the following when performing data analysis or model training:

1. query_param_count (1-based indexing error):
   - This feature starts at 1 even when no query parameters are present.
   - It is likely the result of using len(url.split('?')) without subtracting 1.
   - To get the true count, subtract 1 from the current values.

2. tld_length (Port number inclusion):
   - The TLD length calculation includes the port number string (e.g., ':8080').
   - This results in abnormally high tld_length values for URLs specifying ports.

3. IP Address Parsing:
   - Hostnames that are IP addresses are parsed using the same logic as 
     standard domains.
   - The last octet of the IP is incorrectly treated as the TLD, and 
     tld_length reflects the length of that octet.

4. Subdomain Parsing:(Compound TLD and IP misclassification):                                     
    - subdomain_count is computed as len(netloc.split('.')) - 2, which does                 
     not account for compound TLDs (e.g. ".co.uk", ".go.tz"). The                                 
     second-level part of such TLDs is incorrectly counted as a subdomain,                      
     inflating the value by 1.                                                                  
    - For IP-address hostnames (e.g. "127.0.0.1"), each octet is split on                   
     '.' and treated as a hostname label, producing subdomain_count = 2                    
     even though IP addresses have no real subdomains.                                     
    - The port suffix on the last segment (e.g. "com:8080") does not affect                 
     the count, since splitting on '.' leaves it as a single token. 

5. General Consistency:
   - Other features like path_length may show fixed or inconsistent values 
     due to extraction tool limitations or intentional testing of 
     model robustness against noisy data.

Feature reference: ai-worker/worker/pipeline/url_model_artifacts/
  - feature_columns.json     — canonical input order expected by the model
  - url_features_extracted1.csv — full training set with reference values
  - scaler.pkl                — sklearn StandardScaler fit during training

url_length                            0    0.00%  OK
has_ip_address                       22    0.02%  22 differ
dot_count                             0    0.00%  OK
https_flag                            0    0.00%  OK
url_entropy                           0    0.00%  OK
token_count                         499    0.49%  499 differ
subdomain_count                    1308    1.29%  1308 differ
query_param_count                   609    0.60%  609 differ
tld_length                            0    0.00%  OK
path_length                           1    0.00%  1 differ
has_hyphen_in_domain                  0    0.00%  OK
number_of_digits                      0    0.00%  OK
tld_popularity                      115    0.11%  115 differ
suspicious_file_extension          1801    1.78%  1801 differ
domain_name_length                    8    0.01%  8 differ
percentage_numeric_chars              0    0.00%  OK
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import ipaddress
from collections import Counter
import re

import joblib
import numpy as np
import onnxruntime as ort


# ─── Artifact loading (runs once at import) ─────────────────────────────
_ARTIFACT_DIR = Path(__file__).resolve().parent / "url_model_artifacts"

with open(_ARTIFACT_DIR / "feature_columns.json") as _f:
    FEATURE_COLUMNS: list[str] = json.load(_f)

_SCALER = joblib.load(_ARTIFACT_DIR / "scaler.pkl")

_SESSION = ort.InferenceSession(str(_ARTIFACT_DIR / "fraud_model.onnx"))
_INPUT_NAME = _SESSION.get_inputs()[0].name

# ─── Helper Functions ───────────────────────────────────────────────────

def _get_tld_true(url: str) -> str:
    parsed_result = urlparse(url)
    # domain = www.example.com:8080
    domain = parsed_result.netloc
    # domain_ = www.example.com
    domain_ = domain.split(':')[0]
    # tld = com
    tld = domain_.split('.')[-1]
    return tld

def _get_tld(url: str) -> str:
    # get_tld with Feature Extraction Anomalies
    parsed_result = urlparse(url)
    # domain = www.example.com:8080
    domain = parsed_result.netloc
    # tld = com:8080
    tld = domain.split('.')[-1]
    return tld

# ─── Feature calculation Functions ──────────────────────────────────────
# Each function takes the raw URL string and returns the value as defined
# in the LegitPhish dataset. Fill these in by referencing the CSV at
# url_model_artifacts/url_features_extracted1.csv (the URL column +
# corresponding feature column give input/output pairs to verify against).

def _url_length(url: str) -> int:
    return len(url)


def _has_ip_address(url: str) -> int:
    parsed_result = urlparse(url)
    # domain = www.example.com:8080
    domain = parsed_result.netloc
    # domain_ = www.example.com
    domain_ = domain.split(':')[0]
    try:
        # IPv4 (0.0.0.0) or IPv6 ([2001:db8::1])
        ipaddress.ip_address(domain_)
        return 1
    # normal domain name, ValueError
    except ValueError:
        return 0


def _dot_count(url: str) -> int:
    return url.count('.')


def _https_flag(url: str) -> int:
    return int(url.startswith('https://'))


def _url_entropy(url: str) -> float:
    # calculate Shanon Entropy of url
    if not url:
        return 0.0

    # 1. Count frequencies of each letters in url.
    frequencies = Counter(url)
    url_length = len(url)

    # 2. Shannon Entropy Formula.
    # H(X) = -sum(P(xi) * log2(P(xi)))
    entropy = 0.0
    for count in frequencies.values():
        # P(xi)
        p_xi = count / url_length
        # log calculation (p_xi > 0)
        entropy -= p_xi * math.log2(p_xi)

    return entropy


def _token_count(url: str) -> int:
    delimiters = r"\.|\/|\?|\="
    return len(re.split(delimiters, url))


def _subdomain_count(url: str) -> int:
    # subdomain count with Feature Extraction Anomalies
    parsed_result = urlparse(url)
    # domain = www.example.com:8080
    domain = parsed_result.netloc
    # parts = ['www', 'example', 'com:8080']
    parts = domain.split('.')
    # 'www' -> return 1
    return max(0, len(parts)-2)


def _query_param_count(url: str) -> int:
    # query_param_count with Feature Extraction Anomalies
    return len(url.split('?'))


def _tld_length(url: str) -> int:
    return len(_get_tld(url))

def _path_length(url: str) -> int:
    return len(urlparse(url).path)


def _has_hyphen_in_domain(url: str) -> int:
    parse_result = urlparse(url)
    return int('-' in parse_result.netloc)


def _number_of_digits(url: str) -> int:
    return sum(c.isdigit() for c in url)


def _tld_popularity(url: str) -> int:
    POPULAR_TLDS = {"com", "org", "net", "edu", "gov"}
    return int(_get_tld_true(url) in POPULAR_TLDS)


def _suspicious_file_extension(url: str) -> int:
    SUSPICIOUS_EXTS = {".exe", ".bin", ".zip", ".scr", ".bat", ".rar", ".js", ".vbs", ".msi", ".dll"}
    ext = "." + url.rsplit(".", 1)[-1].lower()
    return int(ext in SUSPICIOUS_EXTS)

def _domain_name_length(url: str) -> int:
    parsed_result = urlparse(url)
    # domain = www.example.com:8080
    domain = parsed_result.netloc
    # parts = ['www', 'example', 'com:8080']
    parts = domain.split('.')
    # there can be url without dots
    if len(parts) < 2:
        return 0
    return len(parts[-2])


def _percentage_numeric_chars(url: str) -> float:
    digits = _number_of_digits(url)
    return 100 * digits / len(url)


_EXTRACTORS = {
    "url_length": _url_length,
    "has_ip_address": _has_ip_address,
    "dot_count": _dot_count,
    "https_flag": _https_flag,
    "url_entropy": _url_entropy,
    "token_count": _token_count,
    "subdomain_count": _subdomain_count,
    "query_param_count": _query_param_count,
    "tld_length": _tld_length,
    "path_length": _path_length,
    "has_hyphen_in_domain": _has_hyphen_in_domain,
    "number_of_digits": _number_of_digits,
    "tld_popularity": _tld_popularity,
    "suspicious_file_extension": _suspicious_file_extension,
    "domain_name_length": _domain_name_length,
    "percentage_numeric_chars": _percentage_numeric_chars,
}


# ─── Public API ─────────────────────────────────────────────────────────
def extract_url_features(url: str) -> dict[str, float]:
    """Compute the 16 LegitPhish features for a single URL."""
    return {col: _EXTRACTORS[col](url) for col in FEATURE_COLUMNS}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def compute_url_risk_score(url: str) -> float:
    """Return URL-based fraud risk score in [0, 100].

    raw URL -> 16 features -> StandardScaler -> ONNX MLP -> sigmoid(logit)
    = P(legitimate); fraud_score = (1 - P_legit) * 100.
    """
    feats = extract_url_features(url)
    x = np.array([[feats[c] for c in FEATURE_COLUMNS]], dtype=np.float32)
    x_scaled = _SCALER.transform(x).astype(np.float32)
    logit = float(_SESSION.run(None, {_INPUT_NAME: x_scaled})[0].ravel()[0])
    p_legit = _sigmoid(logit)
    return (1.0 - p_legit) * 100.0
