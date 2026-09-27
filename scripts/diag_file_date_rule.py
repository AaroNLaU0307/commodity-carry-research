"""
Read-only diagnostic: what the delegate's 2026-09-27 file-date rule would drop.

Rule under test (reports/ADDENDUM_2026-09-27.md §10, "Decision and rule"):
ignore any statistics record whose ts_ref trade date is earlier than the trade
date of the file it arrives in, except when the file is dated on a non-trading
day (weekend or holiday), in which case records for the immediately preceding
trading day are accepted.

Operationalised here: a file's date is the date in its name (Databento splits
by UTC day). A file date is a non-trading day if it is a Saturday/Sunday or
the file holds no SETTLEMENT_PRICE record whose ts_ref is that date. The
"immediately preceding trading day" is the last earlier file date that was a
trading day. For SETTLEMENT_PRICE and OPEN_INTEREST it reports, per
(instrument, trade date): how many records the rule drops, how many
(instrument, trade date) values it removes entirely, and how many values it
changes from what the current last-received rule keeps.

    DATA_DIR=/path/to/commodity-carry python scripts/diag_file_date_rule.py

Reads DATA_DIR/statistics/*.dbn.zst only; prints a summary, writes nothing.
"""
import sys
from collections import Counter
from pathlib import Path

import databento as db
import pandas as pd
from databento_dbn import StatType

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import config

SETTLE, OI = int(StatType.SETTLEMENT_PRICE), int(StatType.OPEN_INTEREST)
DAY_NS = 86_400 * 10**9


def main() -> int:
    files = sorted((Path(config.DATA_DIR) / "statistics").glob("*.dbn.zst"))
    dropped_by_type, kept_by_type = Counter(), Counter()
    # (stat, iid, ref_ns) -> [last value overall, last kept value or None, any kept]
    state = {}
    out = Counter()
    last_trading = None
    for i, f in enumerate(files):
        fday = pd.Timestamp(f.name.split(".")[0].split("-")[-1], tz="UTC")
        d = db.DBNStore.from_file(f).to_df().reset_index()
        if d.empty:
            continue
        refs = pd.to_datetime(d["ts_ref"], utc=True).dt.normalize()
        d = d.assign(ref=refs).sort_values("ts_recv")
        own_settle = bool(((d["stat_type"] == SETTLE) & (d["ref"] == fday)).any())
        trading = fday.dayofweek < 5 and own_settle
        earlier = d["ref"] < fday
        if not trading and last_trading is not None:
            drop = earlier & (d["ref"] != last_trading)
        else:
            drop = earlier
        for st, n in d.loc[drop, "stat_type"].value_counts().items():
            dropped_by_type[int(st)] += int(n)
        for st, n in d.loc[~drop, "stat_type"].value_counts().items():
            kept_by_type[int(st)] += int(n)
        sub = d[d["stat_type"].isin([SETTLE, OI])]
        sub = pd.DataFrame({"st": sub["stat_type"].astype(int), "iid": sub["instrument_id"].astype(int),
                            "ref": sub["ref"].astype("int64"),
                            "val": sub["price"].where(sub["stat_type"] == SETTLE, sub["quantity"]).astype(float),
                            "drop": drop[sub.index]})
        last_all = sub.groupby(["st", "iid", "ref"], sort=False)["val"].last()
        last_kept = sub[~sub["drop"]].groupby(["st", "iid", "ref"], sort=False)["val"].last()
        for key, val in last_all.items():
            state.setdefault(key, [None, None, False])[0] = val
        for key, val in last_kept.items():
            s = state[key]
            s[1], s[2] = val, True
        if trading:
            last_trading = fday
        cutoff = fday.value - 40 * DAY_NS
        for key in [k for k in state if k[2] < cutoff]:
            _tally(out, key, state.pop(key))
        if i % 500 == 0:
            print(f"{i}/{len(files)} {f.name}", flush=True)
    for key, s in state.items():
        _tally(out, key, s)
    name = {SETTLE: "SETTLEMENT_PRICE", OI: "OPEN_INTEREST"}
    print(f"files={len(files)}")
    for st in (SETTLE, OI):
        print(f"{name[st]}: records dropped={dropped_by_type[st]} kept={kept_by_type[st]}; "
              f"(instrument, trade date) values={out[(st, 'n')]} removed entirely={out[(st, 'lost')]} "
              f"changed={out[(st, 'changed')]}")
    others = sum(v for k, v in dropped_by_type.items() if k not in (SETTLE, OI))
    print(f"other stat types: records dropped={others}")
    return 0


def _tally(out, key, s):
    st = key[0]
    out[(st, "n")] += 1
    if not s[2]:
        out[(st, "lost")] += 1
    elif s[1] != s[0]:
        out[(st, "changed")] += 1


if __name__ == "__main__":
    sys.exit(main())
