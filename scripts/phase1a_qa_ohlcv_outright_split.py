"""
Follow-up: parent symbology returns calendar-spread instruments alongside
outright contract months (symbol format ROOT+MONTH+YEAR-ROOT+MONTH+YEAR,
e.g. "NGV0-NGX0", distinguished by a literal "-"). Splits the ohlcv-1d
population into outright vs spread and re-summarizes per-root coverage on
OUTRIGHT ONLY, which is the actually relevant population for the roll rule
and carry formula. Integrity/inventory check only, per Hard Rule 1.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import databento as db

DATA_DIR = Path(r"C:\Users\Aaron\quant-data\commodity-carry")
WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")
OUT_PATH = WORKSPACE / "phase1a_qa_ohlcv_outright_split_findings.json"

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
    df = store.to_df().reset_index()
    date_col = df.columns[0]

    is_spread = df["symbol"].str.contains("-", regex=False)
    outright = df[~is_spread].copy()
    spread = df[is_spread].copy()

    outright["_root"] = outright["symbol"].apply(root_of)
    per_root_outright = outright.groupby("_root").agg(
        n_rows=("symbol", "count"),
        n_instruments=("symbol", "nunique"),
        first_date=(date_col, "min"),
        last_date=(date_col, "max"),
    )

    findings = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(df),
        "outright_rows": len(outright),
        "spread_rows": len(spread),
        "outright_fraction": len(outright) / len(df),
        "outright_zero_or_negative_close": int((outright["close"] <= 0).sum()),
        "spread_zero_or_negative_close": int((spread["close"] <= 0).sum()),
        "per_root_outright_only": {
            root: {
                "n_rows": int(row["n_rows"]),
                "n_instruments": int(row["n_instruments"]),
                "first_date": str(row["first_date"]),
                "last_date": str(row["last_date"]),
            }
            for root, row in per_root_outright.iterrows()
        },
        "missing_root_symbols_outright_only": sorted(set(ROOT_SYMBOLS) - set(per_root_outright.index)),
    }
    if "KE" in per_root_outright.index:
        findings["ke_first_date_outright_only"] = str(per_root_outright.loc["KE", "first_date"])

    OUT_PATH.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    print(json.dumps(findings, indent=2, default=str))


if __name__ == "__main__":
    main()
