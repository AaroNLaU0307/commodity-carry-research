"""
Phase 1a QA -- ohlcv-1d completeness/gap audit. Integrity only, per Hard
Rule 1: this script counts, checksums, and audits coverage. It computes no
carry, no return, no ranking, no portfolio weight.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import databento as db
import pandas as pd

DATA_DIR = Path(r"C:\Users\Aaron\quant-data\commodity-carry")
WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")
OUT_PATH = WORKSPACE / "phase1a_qa_ohlcv_findings.json"

CME_UNIVERSE = {
    "energy": ["CL", "HO", "RB", "NG"],
    "metals": ["GC", "SI", "HG", "PL", "PA"],
    "grains": ["ZC", "ZS", "ZW", "ZM", "ZL", "KE"],
    "livestock": ["LE", "HE", "GF"],
}
ROOT_SYMBOLS = [s for syms in CME_UNIVERSE.values() for s in syms]


def root_of(raw_symbol: str) -> str:
    for root in sorted(ROOT_SYMBOLS, key=len, reverse=True):
        if raw_symbol.startswith(root):
            return root
    return "UNKNOWN"


def main():
    store = db.DBNStore.from_file(DATA_DIR / "ohlcv-1d.dbn.zst")
    df = store.to_df()
    print(f"Loaded ohlcv-1d: {len(df):,} rows")
    print(df.columns.tolist())

    # symbol/instrument inventory
    if "symbol" in df.columns:
        symbol_col = "symbol"
    elif "raw_symbol" in df.columns:
        symbol_col = "raw_symbol"
    else:
        symbol_col = None

    findings = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "schema": "ohlcv-1d",
        "total_rows": len(df),
        "date_min": str(df.index.min()),
        "date_max": str(df.index.max()),
        "columns": df.columns.tolist(),
    }

    if symbol_col:
        # reset_index once, up front -- turns the DatetimeIndex into a plain
        # column so groupby.agg can use fast vectorized min/max directly,
        # instead of repeatedly re-indexing the full 4.5M-row frame inside a
        # per-group lambda (that anti-pattern is what caused the earlier
        # ArrayMemoryError -- a bug in this analysis script, not the data).
        df_flat = df.reset_index()
        date_col = df_flat.columns[0]
        df_flat["_root"] = df_flat[symbol_col].apply(root_of)

        per_root = df_flat.groupby("_root").agg(
            n_rows=(symbol_col, "count"),
            n_instruments=(symbol_col, "nunique"),
            first_date=(date_col, "min"),
            last_date=(date_col, "max"),
        )
        findings["per_root_symbol"] = {
            root: {
                "n_rows": int(row["n_rows"]),
                "n_instruments": int(row["n_instruments"]),
                "first_date": str(row["first_date"]),
                "last_date": str(row["last_date"]),
            }
            for root, row in per_root.iterrows()
        }
        missing_roots = set(ROOT_SYMBOLS) - set(per_root.index)
        findings["missing_root_symbols"] = sorted(missing_roots)

        # KE entry-date check (Sec 2, load-bearing)
        if "KE" in df_flat["_root"].values:
            ke_first = df_flat.loc[df_flat["_root"] == "KE", date_col].min()
            findings["ke_first_date_ohlcv"] = str(ke_first)

        # zero/negative close check (unit-error / bad-data flag)
        close_col = "close" if "close" in df_flat.columns else None
        if close_col:
            bad = df_flat[df_flat[close_col] <= 0]
            findings["zero_or_negative_close_rows"] = int(len(bad))

        # per-instrument (not just per-root) row counts, for the gap audit --
        # how many distinct contract months per root, roughly how many rows
        # (trading days) each individually has.
        per_instrument = df_flat.groupby(symbol_col).agg(
            n_rows=(symbol_col, "count"),
            first_date=(date_col, "min"),
            last_date=(date_col, "max"),
        )
        findings["n_distinct_instruments_total"] = int(df_flat[symbol_col].nunique())
        findings["instrument_row_count_summary"] = {
            "min": int(per_instrument["n_rows"].min()),
            "median": float(per_instrument["n_rows"].median()),
            "max": int(per_instrument["n_rows"].max()),
        }

    OUT_PATH.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    print(f"Findings written to {OUT_PATH}")
    print(json.dumps(findings, indent=2, default=str)[:3000])


if __name__ == "__main__":
    main()
