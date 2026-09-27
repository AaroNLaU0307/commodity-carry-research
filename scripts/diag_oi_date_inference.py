"""
Read-only validation of the OPEN_INTEREST trade-date inference (delegate decision of
2026-09-27T19:54:48Z, reports/ADDENDUM_2026-09-27.md §10), before any pipeline stage runs.

src/pipeline.py::infer_missing_oi_trade_dates() dates an OPEN_INTEREST record that carries no ts_ref
(every one delivered before 2015-11-20) to the latest trade date for which the same instrument has a
settlement received before it. This script applies that same function to every OPEN_INTEREST record that
DOES carry a ts_ref (2015-11-20 onward), with the ts_ref hidden, and compares the inferred date with the
actual ts_ref. The carried state is built exactly as build_settlement_oi_panel() builds it (files in
delivery order; weekend-dated records dropped as read; drop_late_records() on the actually-dated
records updates it).

Reports the agreement rate overall, for records in Sunday-dated files, and for records in post-holiday
files (a weekday file whose preceding weekday had no settlement dated that weekday, i.e. an exchange
holiday), each also restricted to the study's contracts (outright futures of the 18 registered symbols,
from that day's definition file), and tabulates the disagreements by pattern (file class x
inferred-minus-actual trade-date gap). The 99.9% gate in the decision is on all records.

    DATA_DIR=/path/to/commodity-carry python scripts/diag_oi_date_inference.py [disagreements.csv]

Reads DATA_DIR/statistics/ and DATA_DIR/definition/ only; writes nothing but the optional CSV.
"""
import sys
from collections import Counter
from pathlib import Path

import databento as db
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import config
from src.pipeline import (OPEN_INTEREST_STAT_TYPE, drop_late_records, infer_missing_oi_trade_dates,
                          statistics_records)


def main(out_csv=None) -> int:
    files = sorted((Path(config.DATA_DIR) / "statistics").glob("*.dbn.zst"))
    latest, trading_days, n, agree, disagree_rows = {}, set(), Counter(), Counter(), []
    def_dir = Path(config.DATA_DIR) / "definition"
    for f in files:
        day = pd.Timestamp(f.name.split(".")[0].split("-")[-1])
        universe = set()
        for df_ in def_dir.glob(f"*{day:%Y%m%d}*.dbn.zst"):
            dd = db.DBNStore.from_file(df_).to_df()
            universe |= set(dd.loc[dd["asset"].isin(config.ALL_SYMBOLS) & (dd["instrument_class"] == "F"),
                                   "instrument_id"].astype(int))
        rec = statistics_records(db.DBNStore.from_file(f).to_df())
        rec = rec[~(rec["date"].notna() & (rec["date"].dt.dayofweek >= 5))]   # as read by the pipeline
        if rec.empty:
            continue
        is_oi = rec["stat_type"] == OPEN_INTEREST_STAT_TYPE
        test = is_oi & rec["date"].notna()
        if day.dayofweek == 6:
            cls = "sunday_file"
        elif day.dayofweek < 5 and (day - pd.offsets.BDay(1)) not in trading_days and trading_days:
            cls = "post_holiday_file"
        else:
            cls = "other"
        if test.any():
            masked = rec.copy()
            masked.loc[test, "date"] = pd.NaT
            inferred, _ = infer_missing_oi_trade_dates(masked, latest)
            got = inferred.loc[test[test].index, "date"]
            want = rec.loc[test, "date"]
            ok = got == want
            in_univ = rec.loc[test, "instrument_id"].astype(int).isin(universe)
            for c in (cls, "all"):
                n[c] += int(test.sum())
                agree[c] += int(ok.sum())
                n[c + "|universe_outright"] += int(in_univ.sum())
                agree[c + "|universe_outright"] += int((ok & in_univ).sum())
            bad = rec.loc[test].loc[~ok]
            for (i, r), g in zip(bad.iterrows(), got[~ok]):
                gap = None if pd.isna(g) else (pd.Timestamp(g) - r["date"]).days
                disagree_rows.append({"file": f.name, "file_class": cls, "instrument_id": int(r["instrument_id"]),
                                      "universe_outright": int(r["instrument_id"]) in universe,
                                      "ts_recv": r["ts_recv"], "actual_ts_ref": r["date"].date(),
                                      "inferred": None if pd.isna(g) else pd.Timestamp(g).date(),
                                      "inferred_minus_actual_days": gap})
        # update the carried state exactly as the pipeline does (actual dates; undated records excluded)
        drop_late_records(rec[rec["date"].notna()], latest)
        if day.dayofweek < 5 and ((rec["stat_type"] != OPEN_INTEREST_STAT_TYPE) & (rec["date"] == day)).any():
            trading_days.add(day)
    print(f"files={len(files)}")
    for c in ("all", "sunday_file", "post_holiday_file", "other"):
        for k in (c, c + "|universe_outright"):
            if n[k]:
                print(f"{k}: records={n[k]} agree={agree[k]} rate={agree[k] / n[k]:.6f}")
    df = pd.DataFrame(disagree_rows)
    if len(df):
        df["gap"] = df["inferred_minus_actual_days"].astype("object").fillna("none")
        print("disagreements by pattern (file class x inferred-minus-actual days):")
        print(df.groupby(["file_class", "gap"]).size().to_string())
        print("disagreements on universe outrights (18 study symbols, instrument_class F) by pattern:")
        u = df[df["universe_outright"]]
        print(u.groupby(["file_class", "gap"]).size().to_string() if len(u) else "none")
        print("disagreements by file (top 15):")
        print(df.groupby("file").size().sort_values(ascending=False).head(15).to_string())
    if out_csv:
        df.to_csv(out_csv, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
