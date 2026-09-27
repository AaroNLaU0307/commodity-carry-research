"""
Read-only diagnostic for RERUN_RUNBOOK.md step 2: late SETTLEMENT_PRICE and
OPEN_INTEREST records.

The pipeline keys each value on its CME trade date (`ts_ref`) and keeps the
last-received record per (trade date, instrument, stat type). A record for
trade date d that arrives after the same instrument's record of the same stat
type for a later trade date cannot be the CME value for d (the feed was seen
to re-send a later trade date's settlement under an earlier ts_ref), and the
late-record rule in src/pipeline.py (drop_late_records(), delegate decision
2026-09-27T18:15:08Z) drops it.

This script replays every record of the two stat types in ts_recv order,
independently of the pipeline code, and reports per stat type (records
without ts_ref and weekend-dated records are left out, as the pipeline drops
them before this rule; OI records dated by inference are not covered):
  - late records (the ones the rule drops), split into those whose value
    equals the value already held for (instrument, d) and those that differ;
  - how many kept (instrument, trade date) values the rule changes, compared
    with plain last-received;
  - records received more than 7 calendar days after their ts_ref, and how
    many of those the rule does not drop.
Late records with a differing value are printed (settlement) and written to
the optional CSV (both stat types).

    DATA_DIR=/path/to/commodity-carry python scripts/diag_late_settlements.py [out.csv]

Reads DATA_DIR/statistics/*.dbn.zst only; writes nothing but the optional CSV.
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
NAME = {SETTLE: "SETTLEMENT_PRICE", OI: "OPEN_INTEREST"}
DAY_NS = 86_400 * 10**9


def main(out_csv=None) -> int:
    files = sorted((Path(config.DATA_DIR) / "statistics").glob("*.dbn.zst"))
    value = {}    # (stat, iid, ref_ns) -> [last value received, last value kept by the rule]
    latest = {}   # (stat, iid) -> (latest ref_ns received, its current value)
    late, count = [], Counter()
    for f in files:
        d = db.DBNStore.from_file(f).to_df().reset_index()
        s = d[d["stat_type"].isin([SETTLE, OI])]
        if s.empty:
            continue
        s = s.assign(ref=pd.to_datetime(s["ts_ref"], utc=True).dt.normalize())
        s = s[s["ref"].notna() & (s["ref"].dt.dayofweek < 5)]   # weekend-dated records dropped as read
        s = s.sort_values("ts_recv", kind="stable")
        for row in s.itertuples(index=False):
            st, iid, ref = int(row.stat_type), int(row.instrument_id), row.ref.value
            val = float(row.price) if st == SETTLE else float(row.quantity)
            recv = pd.Timestamp(row.ts_recv).value
            old = recv - ref > 7 * DAY_NS
            count[(st, "records")] += 1
            count[(st, "older_than_7d")] += old
            v = value.setdefault((st, iid, ref), [None, None])
            lr = latest.get((st, iid))
            if lr is not None and ref < lr[0]:
                if v[1] == val:
                    count[(st, "late_same")] += 1
                else:
                    count[(st, "late_diff")] += 1
                    late.append({"stat_type": NAME[st], "file": f.name, "instrument_id": iid,
                                 "ts_ref": row.ref.date(), "ts_recv": row.ts_recv, "value": val,
                                 "kept_value_for_ts_ref": v[1],
                                 "latest_ts_ref": pd.Timestamp(lr[0], tz="UTC").date(),
                                 "latest_value": lr[1], "equals_latest_value": val == lr[1],
                                 "stat_flags": int(row.stat_flags), "update_action": int(row.update_action)})
            else:
                v[1] = val
                count[(st, "older_than_7d_kept")] += old
            v[0] = val
            if lr is None or ref >= lr[0]:
                latest[(st, iid)] = (ref, val)
        cutoff = pd.Timestamp(f.name.split(".")[0].split("-")[-1], tz="UTC").value - 60 * DAY_NS
        for k in [k for k in value if k[2] < cutoff]:
            _tally(count, k, value.pop(k))
    for k, v in value.items():
        _tally(count, k, v)
    df = pd.DataFrame(late)
    print(f"files={len(files)}")
    for st in (SETTLE, OI):
        print(f"{NAME[st]}: records={count[(st, 'records')]} "
              f"late_dropped={count[(st, 'late_same')] + count[(st, 'late_diff')]} "
              f"(same_value={count[(st, 'late_same')]}, different_value={count[(st, 'late_diff')]}); "
              f"kept_values_changed={count[(st, 'changed')]} of {count[(st, 'keys')]} "
              f"(of which removed entirely={count[(st, 'removed')]}); "
              f"received_more_than_7d_after_ts_ref={count[(st, 'older_than_7d')]} "
              f"(not dropped by the rule: {count[(st, 'older_than_7d_kept')]})")
    if len(df):
        print(df[df["stat_type"] == NAME[SETTLE]].to_string(index=False))
    if out_csv:
        df.to_csv(out_csv, index=False)
    return 0


def _tally(count, key, v):
    count[(key[0], "keys")] += 1
    count[(key[0], "changed")] += v[0] != v[1]
    count[(key[0], "removed")] += v[1] is None


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
