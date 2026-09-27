"""
Read-only diagnostic for the 2026-09-27 re-run halt (reports/ADDENDUM_2026-09-27.md §10).

Per statistics file: how many SETTLEMENT_PRICE and OPEN_INTEREST records carry no ts_ref (the pipeline
drops those: it keys every value on ts_ref), and every record of those two stat types whose ts_ref falls
on a Saturday or Sunday (the pipeline drops those too, and RERUN_RUNBOOK.md step 3 requires the count to
be 0). Prints the per-year totals, the first and last files in which OPEN_INTEREST lacks ts_ref, and the
weekend-dated records.

    DATA_DIR=/path/to/commodity-carry python scripts/diag_ts_ref_coverage.py [per_file.csv]

Reads DATA_DIR/statistics/*.dbn.zst only; writes nothing but the optional CSV.
"""
import sys
from pathlib import Path

import databento as db
import pandas as pd
from databento_dbn import StatType

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import config

SETTLE, OI = int(StatType.SETTLEMENT_PRICE), int(StatType.OPEN_INTEREST)


def main(out_csv=None) -> int:
    files = sorted((Path(config.DATA_DIR) / "statistics").glob("*.dbn.zst"))
    rows, weekend = [], []
    for f in files:
        d = db.DBNStore.from_file(f).to_df().reset_index()
        d = d[d["stat_type"].isin([SETTLE, OI])]
        ref = pd.to_datetime(d["ts_ref"], utc=True)
        row = {"file": f.name, "day": f.name.split(".")[0].split("-")[-1]}
        for st, name in ((SETTLE, "settle"), (OI, "oi")):
            m = d["stat_type"] == st
            row[f"{name}_n"] = int(m.sum())
            row[f"{name}_no_ts_ref"] = int((m & ref.isna()).sum())
        rows.append(row)
        wk = ref.notna() & (ref.dt.dayofweek >= 5)
        for r, t in zip(d[wk].itertuples(index=False), ref[wk]):
            weekend.append({"file": f.name, "instrument_id": int(r.instrument_id), "stat_type": int(r.stat_type),
                            "ts_recv": r.ts_recv, "ts_ref": t, "price": float(r.price),
                            "quantity": int(r.quantity), "stat_flags": int(r.stat_flags),
                            "update_action": int(r.update_action)})
    df = pd.DataFrame(rows)
    df["year"] = df["day"].str[:4]
    print(f"files={len(files)}")
    print(df.groupby("year")[["settle_n", "settle_no_ts_ref", "oi_n", "oi_no_ts_ref"]].sum().to_string())
    missing = df[df["oi_no_ts_ref"] > 0]
    full = df[(df["oi_n"] > 0) & (df["oi_no_ts_ref"] == 0)]
    if len(missing):
        print(f"OPEN_INTEREST without ts_ref: first file {missing['file'].iloc[0]}, last file {missing['file'].iloc[-1]}")
    if len(full):
        print(f"OPEN_INTEREST all with ts_ref: first file {full['file'].iloc[0]}")
    print(f"weekend-dated SETTLEMENT_PRICE/OPEN_INTEREST records: {len(weekend)}")
    if weekend:
        print(pd.DataFrame(weekend).to_string(index=False))
    if out_csv:
        df.to_csv(out_csv, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
