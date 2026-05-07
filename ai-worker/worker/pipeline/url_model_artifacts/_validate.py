"""Validate the currently-implemented url_classifier feature functions
against the ground-truth CSV. Skips functions that raise NotImplementedError
or return non-numeric values.

Run from repo root:
    python ai-worker/worker/pipeline/url_model_artifacts/_validate.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

# Make `worker.pipeline.url_classifier` importable.
HERE = Path(__file__).resolve()
AI_WORKER_ROOT = HERE.parents[3]  # ai-worker/
sys.path.insert(0, str(AI_WORKER_ROOT))

from worker.pipeline import url_classifier as uc  # noqa: E402

CSV_PATH = HERE.parent / "url_features_extracted1.csv"

SKIP_KNOWN_UNIMPLEMENTED: set[str] = set()

FLOAT_FEATURES = {"url_entropy", "percentage_numeric_chars"}


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    n = len(df)
    print(f"Loaded {n} rows from {CSV_PATH.name}\n")

    rows = []
    for col in uc.FEATURE_COLUMNS:
        fn = uc._EXTRACTORS[col]
        if col in SKIP_KNOWN_UNIMPLEMENTED:
            rows.append((col, "-", "-", "skipped (NotImplementedError)"))
            continue

        # Probe a single URL to detect runtime errors quickly.
        try:
            sample_val = fn(df["URL"].iloc[0])
        except Exception as e:
            rows.append((col, "-", "-", f"runtime error: {type(e).__name__}: {e}"))
            continue
        if sample_val is None:
            rows.append((col, "-", "-", "function returned None (no return statement)"))
            continue

        # Run full pass.
        try:
            ours = df["URL"].apply(fn)
        except Exception as e:
            rows.append((col, "-", "-", f"failed mid-run: {type(e).__name__}: {e}"))
            continue

        if col in FLOAT_FEATURES:
            mismatch = int((~((ours - df[col]).abs() < 1e-3)).sum())
        else:
            try:
                ours_int = ours.astype(int)
                ds_int = df[col].astype(int)
                mismatch = int((ours_int != ds_int).sum())
            except Exception:
                mismatch = int((ours != df[col]).sum())

        rate = 100 * mismatch / n
        status = "OK" if mismatch == 0 else f"{mismatch} differ"
        rows.append((col, mismatch, f"{rate:5.2f}%", status))

    # Pretty print.
    print(f"{'feature':<28} {'#mismatch':>10} {'rate':>8}  status")
    print("-" * 80)
    for col, m, r, s in rows:
        print(f"{col:<28} {str(m):>10} {str(r):>8}  {s}")


if __name__ == "__main__":
    main()
