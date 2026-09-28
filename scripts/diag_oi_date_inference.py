"""
Historical: validated the previous-weekday rule, withdrawn by the delegate decision of
2026-09-28T06:47:48Z; run it at commit 808c472, where the pipeline's rule is the one it describes.

Read-only validation of the OPEN_INTEREST trade-date rule for records without ts_ref (delegate decision
of 2026-09-28T04:57:40Z, reports/ADDENDUM_2026-09-27.md §10), before any pipeline stage runs. The
settlement-anchored rule it replaces was validated by this script's version at commit 1bf51d2.

src/pipeline.py::infer_missing_oi_trade_dates() dates an OPEN_INTEREST record that carries no ts_ref
(every one delivered before 2015-11-20) to the previous weekday before the UTC date of the file it
arrives in (holidays included; Saturday/Sunday files -> the preceding Friday). This script applies that
same function to every OPEN_INTEREST record that DOES carry a ts_ref (2015-11-20 onward), with the ts_ref
hidden, and compares the inferred date with the actual ts_ref.

Reports the agreement rate overall, for records in Sunday-dated files, in post-holiday files (a weekday
file whose preceding weekday had no settlement dated that weekday) and in the rest, and classifies the
disagreements:
  - delayed publication: the actual trade date is EARLIER than the inferred one (the record arrived in a
    later file than the day after its trade date), split into "across a holiday" (a weekday between the
    trade date and the file date had no settlement dated that day: no OI was published for the holiday
    and the pre-holiday OI arrived after it) and "ordinary days" (no holiday in between: a late batch);
  - early publication: the actual trade date is LATER than the inferred one (the record arrived on or
    before its trade date's UTC day);
with the files, trade dates and UTC arrival hours of each.

    DATA_DIR=/path/to/commodity-carry python scripts/diag_oi_date_inference.py [disagreements.csv]

Reads DATA_DIR/statistics/*.dbn.zst only; writes nothing but the optional CSV.
"""
import sys
from collections import Counter
from pathlib import Path

import databento as db
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import config
from src.pipeline import (OPEN_INTEREST_STAT_TYPE, SETTLEMENT_STAT_TYPE, infer_missing_oi_trade_dates,
                          statistics_records)


def main(out_csv=None) -> int:
    files = sorted((Path(config.DATA_DIR) / "statistics").glob("*.dbn.zst"))
    trading_days, n, agree, rows = set(), Counter(), Counter(), []
    for f in files:
        day = pd.Timestamp(f.name.split(".")[0].split("-")[-1])
        rec = statistics_records(db.DBNStore.from_file(f).to_df())
        rec = rec[~(rec["date"].notna() & (rec["date"].dt.dayofweek >= 5))]   # as read by the pipeline
        if rec.empty:
            continue
        test = (rec["stat_type"] == OPEN_INTEREST_STAT_TYPE) & rec["date"].notna()
        if day.dayofweek == 6:
            cls = "sunday_file"
        elif day.dayofweek < 5 and trading_days and (day - pd.offsets.BDay(1)) not in trading_days:
            cls = "post_holiday_file"
        else:
            cls = "other"
        if test.any():
            masked = rec.copy()
            masked.loc[test, "date"] = pd.NaT
            inferred, _ = infer_missing_oi_trade_dates(masked, day)
            got, want = inferred.loc[test, "date"], rec.loc[test, "date"]
            ok = got == want
            for c in (cls, "all"):
                n[c] += int(test.sum())
                agree[c] += int(ok.sum())
            bad = rec.loc[test & ~ok]
            for (_, r), g in zip(bad.iterrows(), got[~ok]):
                if r["date"] < g:
                    between = pd.bdate_range(r["date"] + pd.Timedelta(days=1), day - pd.Timedelta(days=1))
                    holiday = any(d not in trading_days for d in between)
                    pattern = "delayed_across_holiday" if holiday else "delayed_ordinary_days"
                else:
                    pattern = "early_publication"
                rows.append({"file": f.name, "file_class": cls, "instrument_id": int(r["instrument_id"]),
                             "ts_recv": r["ts_recv"], "actual_ts_ref": r["date"].date(),
                             "inferred": pd.Timestamp(g).date(), "pattern": pattern})
        if day.dayofweek < 5 and ((rec["stat_type"] == SETTLEMENT_STAT_TYPE) & (rec["date"] == day)).any():
            trading_days.add(day)
    print(f"files={len(files)}")
    for c in ("all", "sunday_file", "post_holiday_file", "other"):
        if n[c]:
            print(f"{c}: records={n[c]} agree={agree[c]} rate={agree[c] / n[c]:.6f}")
    df = pd.DataFrame(rows)
    if len(df):
        df["recv_hour_utc"] = pd.to_datetime(df["ts_recv"], utc=True).dt.hour
        print("disagreements by pattern and file class:")
        print(df.groupby(["pattern", "file_class"]).size().to_string())
        print("disagreements by pattern, file and actual trade date (records; UTC arrival hours):")
        for (pat, fname, ref), g in df.groupby(["pattern", "file", "actual_ts_ref"]):
            print(f"  {pat:20s} {fname}  ts_ref {ref}  n={len(g)}  hours={sorted(set(g['recv_hour_utc']))}")
    if out_csv:
        df.to_csv(out_csv, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
