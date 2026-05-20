# ShopGuard Merged Training Dataset

`merged_v1.parquet` — combined phishing / legitimate training set used by the
content-based NLP classifier (planned successor to the URL-only classifier in
`ai-worker/worker/pipeline/url_classifier.py`).

## File

| | |
|---|---|
| Path | `ai-worker/datasets/merged_v1.parquet` |
| Format | Parquet (zstd compression) |
| Rows | 111,613 |
| Columns | 24 |
| Size | 26 MB |
| Build script | `build_merged.py` |

## Label

```
label = 0 → phishing
label = 1 → legitimate
```

This matches the legitphish `ClassLabel` convention used by the existing URL
classifier ONNX model. The classifier output is also `P(legitimate)`, so any
downstream code converting to a "fraud score" should use `1 - P(legitimate)`.

> **Open verification:** the legitphish label direction (1=Legitimate, 0=Phishing)
> is taken from the user-supplied dataset description. It has not been confirmed
> against the original Colab training notebook. Re-check before serious model
> work — a flipped label silently inverts every downstream score.

## Sources

| `source` value | Origin | Rows | Notes |
|---|---|---|---|
| `legitphish` | `ai-worker/worker/pipeline/url_model_artifacts/url_features_extracted1.csv` | 101,218 | URL only. The 16 URL-derived features in the source CSV were **dropped** — they are re-computed at inference time by `url_classifier`. |
| `phishpedia` | `ai-worker/temp_dataset/phishing.csv`, `not-phishing.csv` | 10,395 | Rich content features (text / HTML / CSS), WHOIS, TLS, IP, brand impersonation labels. |

Label x source breakdown:

| source | label=0 (phishing) | label=1 (legit) |
|---|---:|---:|
| legitphish | 63,678 | 37,540 |
| phishpedia | 5,151 | 5,244 |
| **total** | **68,829** | **42,784** |

One legitphish row with a null `ClassLabel` was dropped during the merge.

## Schema

| Column | Type | Populated where | Description |
|---|---|---|---|
| `url` | string | all | Original URL string. Not normalized. |
| `label` | Int8 | all | 0=phishing, 1=legitimate. |
| `source` | string | all | `legitphish` or `phishpedia`. |
| `domain` | string | phishpedia | Hostname. |
| `protocol` | string | phishpedia | e.g. `http/1.1`, `h2`. |
| `language` | string | phishpedia | Detected page language. |
| `features_text` | string | phishpedia | Visible page text extracted at crawl time. |
| `features_html` | string | phishpedia | JSON array of HTML tag tokens in DOM order. |
| `features_css` | string | phishpedia | JSON dict `{property: [values]}` aggregated from page CSS. |
| `assets_downloaded` | float64 | phishpedia | Fraction of referenced assets the crawler retrieved. |
| `remote_ip_country` | string | phishpedia | GeoIP country of the host's IP. |
| `remote_ip_asn` | string | phishpedia | Autonomous System Number. |
| `remote_ip_isp` | string | phishpedia | Host's ISP name. |
| `security_state` | string | phishpedia | TLS state (`secure`, `insecure`, ...). |
| `security_protocol` | string | phishpedia (8,265 only) | e.g. `TLS 1.2`. Null where the page was served over plain HTTP. |
| `security_issuer` | string | phishpedia (8,262 only) | Issuing CA. |
| `security_valid_from` | string | phishpedia (8,265 only) | Cert NotBefore (ISO 8601). |
| `security_valid_to` | string | phishpedia (8,265 only) | Cert NotAfter (ISO 8601). |
| `whois_domain_age` | float64 | phishpedia (8,878 only) | Domain age in days at scan time. |
| `whois_registrar` | string | **none** | Empty in source CSVs — kept for schema completeness but unusable. |
| `whois_registry_created_at` | string | phishpedia (8,878 only) | WHOIS creation date. |
| `whois_registry_expired_at` | string | phishpedia (8,818 only) | WHOIS expiry date. |
| `scan_date` | string | phishpedia | When the page was crawled (use for time-based train/test split). |
| `brands` | string | phishpedia phishing rows only (5,151) | JSON list of brand identifiers being impersonated. See `temp_dataset/brands.csv` for the canonical brand vocabulary (86 brands). |

### Dropped columns (recorded for traceability)

From the source phishpedia CSVs the following columns were intentionally
discarded — either redundant, identifier-only, or too bulky:

- `_id` (source-specific Mongo IDs)
- `folder_path` (relative path inside the raw zip captures)
- `whois_raw_text` (large; parsed WHOIS fields cover what we need)
- `remote_ip_address`, `remote_ip_domain`, `remote_ip_isp_org` (redundant with ASN/country/ISP)
- `whois_registrar_url`, `whois_registry_updated_at` (low value)

From the legitphish CSV the 16 URL-derived feature columns (`url_length`,
`has_ip_address`, `dot_count`, `https_flag`, `url_entropy`, `token_count`,
`subdomain_count`, `query_param_count`, `tld_length`, `path_length`,
`has_hyphen_in_domain`, `number_of_digits`, `tld_popularity`,
`suspicious_file_extension`, `domain_name_length`, `percentage_numeric_chars`)
were dropped. The URL string itself is the source of truth; the existing
`url_classifier.py` recomputes these features at inference, and the dataset
should not bake in feature-extraction logic that has known bugs (see the long
"Data Quality" note in `url_classifier.py`).

## Phase plan (how this dataset will be used)

This single parquet supports all phases of the content classifier roadmap by
varying the subset of rows and columns used:

| Phase | Selector | Trained on |
|---|---|---|
| Phase 1 — metadata only | `source == "phishpedia"` and drop rows missing WHOIS/TLS | scalar columns: `assets_downloaded`, `whois_domain_age`, `security_*`, `remote_ip_*`, `protocol`, `language` |
| Phase 2 — content NLP | `features_text.notna()` (phishpedia rows) | `features_text` |
| Phase 3 — multi-input | same | `features_text` + `features_html` + `features_css` |
| URL-only retraining | all rows | `url` → recompute 16 features inside the training notebook |

`legitphish` rows are usable only as URL/label pairs (all content columns are
null). They expand the URL-only training set substantially (~101k extra URLs)
but cannot contribute to content-based phases.

## Caveats

- **Distribution mismatch with the ShopGuard target domain.** Phishpedia
  phishing samples impersonate Microsoft / UPS / DHL / Finance brands. Only
  5 of 86 brand entries are e-commerce (Alibaba, Amazon, eBay, Made-in-China,
  Rakuten — no Coupang / AliExpress / Temu). Trained models will detect
  *generic phishing*, not *fake e-commerce storefronts*. Evaluate separately
  on real e-commerce URLs before treating any score as authoritative.
- **`features_text`, `features_html`, `features_css` extraction is opaque.**
  How exactly the phishpedia dataset produced these columns (which crawler,
  JS rendered or not, extraction rules) is not documented. The ai-worker
  crawler must reproduce the same extraction or the model will see
  out-of-distribution inputs at inference. Inspect a sample zip in
  `temp_dataset/` before relying on these columns.
- **Label direction unverified for legitphish.** See "Open verification" above.

## Rebuilding

```bash
cd ai-worker
python datasets/build_merged.py
```

Inputs (must exist):
- `ai-worker/worker/pipeline/url_model_artifacts/url_features_extracted1.csv`
- `ai-worker/temp_dataset/phishing.csv`
- `ai-worker/temp_dataset/not-phishing.csv`

Output:
- `ai-worker/datasets/merged_v1.parquet`

## Git tracking

`merged_v1.parquet` is 26 MB — under typical git limits but already large
enough that further versions or richer schemas (Phase 4 image embeddings)
will warrant Git LFS or external storage. Consider adding `datasets/*.parquet`
to `.gitignore` and distributing through a release asset or S3 once the
schema stabilizes.
