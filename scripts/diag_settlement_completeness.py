"""
Read-only corpus-quality scan: weekday trade dates with fewer settled contracts than their neighbours
(reports/ADDENDUM_2026-09-27.md §10, corpus-quality note requested by the
delegate decision of 2026-09-28T04:57:40Z). A settlement missing from the corpus leaves that contract
without a settlement for that trade date; the pipeline marks it to the last settlement, so it feeds the
carry signal and returns directly, and no dating rule repairs it.

For each weekday trade date: the number of distinct instruments with a SETTLEMENT_PRICE record carrying
that ts_ref, in any file (Friday's arrive in the Friday and the Sunday file), and the size in bytes of
the file named for that date. A trade date is flagged
  - "partial" when its instrument count is above zero but below half the median of the previous 20
    weekday trade dates with a non-zero count;
  - "none" when it is zero (an exchange holiday, or a day missing from the corpus).
Weekdays with no statistics file at all are listed too.

    DATA_DIR=/path/to/commodity-carry python scripts/diag_settlement_completeness.py [per_file.csv]

Reads DATA_DIR/statistics/*.dbn.zst only; writes nothing but the optional CSV.
"""
import sys
from pathlib import Path

import databento as db
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import config
from src.pipeline import SETTLEMENT_STAT_TYPE, statistics_records


def main(out_csv=None) -> int:
    files = sorted((Path(config.DATA_DIR) / "statistics").glob("*.dbn.zst"))
    size = {pd.Timestamp(f.name.split(".")[0].split("-")[-1]): f.stat().st_size for f in files}
    open_sets, counts = {}, {}
    for f in files:
        day = pd.Timestamp(f.name.split(".")[0].split("-")[-1])
        rec = statistics_records(db.DBNStore.from_file(f).to_df())
        s = rec[(rec["stat_type"] == SETTLEMENT_STAT_TYPE) & rec["date"].notna()]
        for ref, ids in s.groupby("date")["instrument_id"]:
            open_sets.setdefault(ref, set()).update(ids.astype(int))
        cutoff = day - pd.Timedelta(days=10)
        for ref in [r for r in open_sets if r < cutoff]:
            # a record arriving more than 10 days late re-opens its date; add, never overwrite
            counts[ref] = counts.get(ref, 0) + len(open_sets.pop(ref))
    for ref, ids in open_sets.items():
        counts[ref] = counts.get(ref, 0) + len(ids)
    days = pd.bdate_range(min(size), max(size))
    wk = pd.DataFrame({"trade_date": days})
    wk["weekday"] = wk["trade_date"].dt.day_name().str[:3]
    wk["instruments_settled"] = [counts.get(d, 0) for d in days]
    wk["file_bytes"] = [size.get(d) for d in days]
    ref_ = wk["instruments_settled"].where(wk["instruments_settled"] > 0)
    wk["median_prev20"] = ref_.shift(1).rolling(20, min_periods=5).median()
    wk["flag"] = ""
    wk.loc[(wk["instruments_settled"] > 0) & (wk["instruments_settled"] < 0.5 * wk["median_prev20"]), "flag"] = "partial"
    wk.loc[wk["instruments_settled"] == 0, "flag"] = "none"
    print(f"files={len(files)} weekday trade dates={len(wk)}")
    for flag in ("partial", "none"):
        sel = wk[wk["flag"] == flag]
        print(f"\n{flag}: {len(sel)} weekday trade dates")
        if len(sel):
            print(sel.drop(columns="flag").to_string(index=False))
    missing = [d for d in days if d not in size]
    print(f"\nweekdays with no statistics file: {len(missing)}: " + ", ".join(f"{d.date()} ({d.day_name()[:3]})" for d in missing))
    if out_csv:
        wk.to_csv(out_csv, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
