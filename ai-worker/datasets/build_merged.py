"""Merge the legitphish URL dataset and the phishpedia content dataset.

Output: ai-worker/datasets/merged_v1.parquet

Label convention (user-specified):
    0 = phishing
    1 = legitimate

Sources:
    legitphish   — ai-worker/worker/pipeline/url_model_artifacts/url_features_extracted1.csv
                   (URL + 16 URL-derived features + ClassLabel)
                   Only URL and ClassLabel are carried; URL-derived features
                   are re-computed at inference by url_classifier.
    phishpedia   — ai-worker/temp_dataset/{phishing,not-phishing}.csv
                   Rich content features (text/html/css), WHOIS, TLS, IP, brands.

URL-derived columns are intentionally dropped because the URL string itself
is the canonical source and the existing url_classifier re-derives them.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

csv.field_size_limit(2**31 - 1)

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_WORKER = REPO_ROOT / "ai-worker"

LEGITPHISH_CSV = AI_WORKER / "worker" / "pipeline" / "url_model_artifacts" / "url_features_extracted1.csv"
PHISHING_CSV = AI_WORKER / "temp_dataset" / "phishing.csv"
NOT_PHISHING_CSV = AI_WORKER / "temp_dataset" / "not-phishing.csv"

OUT_PATH = AI_WORKER / "datasets" / "merged_v1.parquet"

# Columns kept from the phishpedia CSVs. Dots in source names are replaced
# with underscores so the parquet schema is friendlier to downstream tools.
PHISHPEDIA_COLUMNS = {
    "url": "url",
    "domain": "domain",
    "protocol": "protocol",
    "language": "language",
    "assets_downloaded": "assets_downloaded",
    "features.text": "features_text",
    "features.html": "features_html",
    "features.css": "features_css",
    "remote_ip_country": "remote_ip_country",
    "remote_ip_asn": "remote_ip_asn",
    "remote_ip_isp": "remote_ip_isp",
    "security_state": "security_state",
    "security_protocol": "security_protocol",
    "security_issuer": "security_issuer",
    "security_valid_from": "security_valid_from",
    "security_valid_to": "security_valid_to",
    "whois_domain_age": "whois_domain_age",
    "whois_registrar": "whois_registrar",
    "whois_registry_created_at": "whois_registry_created_at",
    "whois_registry_expired_at": "whois_registry_expired_at",
    "scan_date": "scan_date",
    "brands": "brands",
}

# Columns deliberately dropped from phishpedia, recorded for traceability:
#   _id, folder_path, whois_raw_text, remote_ip_address, remote_ip_domain,
#   remote_ip_isp_org, whois_registrar_url, whois_registry_updated_at


def load_legitphish() -> pd.DataFrame:
    print(f"[legitphish] loading {LEGITPHISH_CSV.name} ...", flush=True)
    df = pd.read_csv(
        LEGITPHISH_CSV,
        usecols=["URL", "ClassLabel"],
        dtype={"URL": "string", "ClassLabel": "Int8"},
    )
    df = df.rename(columns={"URL": "url", "ClassLabel": "label"})
    before = len(df)
    df = df.dropna(subset=["url", "label"])
    dropped = before - len(df)
    if dropped:
        print(f"[legitphish] dropped {dropped} rows with null url/label", flush=True)
    df["source"] = "legitphish"
    print(f"[legitphish] {len(df):,} rows", flush=True)
    return df


def load_phishpedia_csv(path: Path, label: int) -> pd.DataFrame:
    print(f"[phishpedia] loading {path.name} (label={label}) ...", flush=True)
    src_cols = [c for c in PHISHPEDIA_COLUMNS if c != "brands" or "phishing" in path.stem]
    if "brands" in src_cols and label == 1:
        src_cols.remove("brands")

    df = pd.read_csv(
        path,
        usecols=src_cols,
        dtype="string",
        engine="python",
    )
    df = df.rename(columns=PHISHPEDIA_COLUMNS)

    if "assets_downloaded" in df.columns:
        df["assets_downloaded"] = pd.to_numeric(df["assets_downloaded"], errors="coerce")
    if "whois_domain_age" in df.columns:
        df["whois_domain_age"] = pd.to_numeric(df["whois_domain_age"], errors="coerce")

    df["label"] = pd.Series([label] * len(df), dtype="Int8")
    df["source"] = "phishpedia"
    if "brands" not in df.columns:
        df["brands"] = pd.NA
    print(f"[phishpedia] {len(df):,} rows from {path.name}", flush=True)
    return df


def main() -> int:
    if not LEGITPHISH_CSV.exists():
        print(f"missing: {LEGITPHISH_CSV}", file=sys.stderr)
        return 1
    if not PHISHING_CSV.exists() or not NOT_PHISHING_CSV.exists():
        print(f"missing phishpedia CSVs under {PHISHING_CSV.parent}", file=sys.stderr)
        return 1

    parts: list[pd.DataFrame] = [
        load_legitphish(),
        load_phishpedia_csv(PHISHING_CSV, label=0),
        load_phishpedia_csv(NOT_PHISHING_CSV, label=1),
    ]

    column_order = [
        "url", "label", "source",
        "domain", "protocol", "language",
        "features_text", "features_html", "features_css",
        "assets_downloaded",
        "remote_ip_country", "remote_ip_asn", "remote_ip_isp",
        "security_state", "security_protocol", "security_issuer",
        "security_valid_from", "security_valid_to",
        "whois_domain_age", "whois_registrar",
        "whois_registry_created_at", "whois_registry_expired_at",
        "scan_date", "brands",
    ]
    for i, df in enumerate(parts):
        for col in column_order:
            if col not in df.columns:
                df[col] = pd.NA
        parts[i] = df[column_order]

    print("[merge] concatenating ...", flush=True)
    merged = pd.concat(parts, ignore_index=True)

    print("[merge] label distribution by source:")
    print(merged.groupby(["source", "label"], dropna=False).size())

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"[write] {OUT_PATH} ({len(merged):,} rows × {len(merged.columns)} cols) ...", flush=True)
    merged.to_parquet(OUT_PATH, engine="pyarrow", compression="zstd", index=False)
    size_mb = OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"[write] done - {size_mb:.1f} MB on disk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
