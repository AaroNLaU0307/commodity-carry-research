"""
Gap audit on outright ohlcv-1d data: the known June 2014 degraded-quality
window (Pass 1 finding, carried over), plus a general missing-trading-day
scan per root symbol against the observed calendar (not a full CME holiday
calendar -- that's noted as a limitation, not silently assumed). Also
re-examines the residual outright zero/negative-close rows (3,490) to see
if they cluster in a way that suggests a specific cause. Integrity only,
per Hard Rule 1.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import databento as db
import pandas as pd

DATA_DIR = Path(r"C:\Users\Aaron\quant-data\commodity-carry")
WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")
OUT_PATH = WORKSPACE / "phase1a_qa_ohlcv_gaps_findings.json"

CME_UNIVERSE = {
    "energy": ["CL", "HO", "RB", "NG"],
    "metals": ["GC", "SI", "HG", "PL", "PA"],
    "grains": ["ZC", "ZS", "ZW", "ZM", "ZL", "KE"],
    "livestock": ["LE", "HE", "GF"],
}
ROOT_SYMBOLS = [s for syms in CME_UNIVERSE.values() for s in syms]
JUNE_2014_WINDOW = pd.date_range("2014-06-11", "2014-06-13", tz="UTC")


def root_of(raw_symbol: str) -> str:
    for root in sorted(ROOT_SYMBOLS, key=len, reverse=True):
        if raw_symbol.startswith(root):
            return root
    return "UNKNOWN"


def main():
    store = db.DBNStore.from_file(DATA_DIR / "ohlcv-1d.dbn.zst")
    df = store.to_df().reset_index()
    date_col = df.columns[0]

    is_spread = df["symbol"].str.contains("-", regex=False)
    outright = df[~is_spread].copy()
    outright["_root"] = outright["symbol"].apply(root_of)

    findings = {"generated_utc": datetime.now(timezone.utc).isoformat()}

    # June 2014 degraded window: does data exist for these dates at all (not
    # whether it's "correct" -- that's the point of the known-degraded flag)?
    june14 = outright[outright[date_col].isin(JUNE_2014_WINDOW)]
    findings["june_2014_degraded_window"] = {
        "dates_checked": [str(d.date()) for d in JUNE_2014_WINDOW],
        "outright_rows_present": int(len(june14)),
        "roots_present": sorted(june14["_root"].unique().tolist()) if len(june14) else [],
    }

    # Trading-day count per calendar year, all-roots pooled -- a rough
    # eyeball gap check (exact CME-holiday-calendar reconciliation is a
    # finer-grained Phase 1b/QA-continuation task, noted as a limitation).
    outright["_year"] = outright[date_col].dt.year
    days_per_year = outright.groupby("_year")[date_col].nunique().to_dict()
    findings["distinct_trading_days_per_year_pooled"] = {str(k): int(v) for k, v in sorted(days_per_year.items())}

    # Residual zero/negative-close outright rows: cluster by root/date to
    # see if it's concentrated (e.g. one root, one period) or diffuse.
    bad = outright[outright["close"] <= 0]
    findings["residual_bad_close_outright"] = {
        "total": int(len(bad)),
        "by_root": bad["_root"].value_counts().to_dict(),
        "by_year": bad[date_col].dt.year.value_counts().sort_index().to_dict(),
        "sample": bad.head(10)[[date_col, "symbol", "open", "high", "low", "close", "volume"]].astype(str).to_dict(orient="records"),
    }

    OUT_PATH.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    print(json.dumps(findings, indent=2, default=str))


if __name__ == "__main__":
    main()
