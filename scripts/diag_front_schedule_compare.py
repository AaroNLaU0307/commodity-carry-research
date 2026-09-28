"""
Read-only materiality check for the OPEN_INTEREST dating rule (delegate decision of
2026-09-28T04:57:40Z, item 3; reports/ADDENDUM_2026-09-27.md §10).

Builds the front-contract schedule of every registered symbol before 2015-11-20 twice, with the pipeline's
own functions (build_definition_lookup, build_settlement_oi_panel, build_outright_panel,
symbol_listed_sequence, symbol_oi_wide, symbol_front_series):
  - "replacement": the committed rule, OI without ts_ref -> the previous weekday before its file's date;
  - "withdrawn":   the settlement-anchored rule of 2026-09-27T19:54:48Z (commit 1bf51d2), reproduced
                   below verbatim and swapped in for the run.
Reports, over the instrument-days present in both schedules, the count and share where the front
differs; the instrument-days present in only one schedule (calendar differences); every roll date that
moves (a roll in one schedule and not the other); and stuck-front violations in each schedule.

    DATA_DIR=/path/to/commodity-carry python scripts/diag_front_schedule_compare.py

Reads DATA_DIR only; prints a report, writes nothing.
"""
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import config, pipeline
from src.study import find_stuck_front_violations

CUTOFF = pd.Timestamp("2015-11-20")
REPLACEMENT = pipeline.infer_missing_oi_trade_dates


def withdrawn_infer(records, file_date, latest):
    """Settlement-anchored rule of 2026-09-27T19:54:48Z, as committed at 1bf51d2 (withdrawn)."""
    r = records.sort_values("ts_recv", kind="stable").copy()
    is_settle = r["stat_type"] == pipeline.SETTLEMENT_STAT_TYPE
    running = r["date"].where(is_settle).groupby(r["instrument_id"], sort=False).cummax()
    running = running.groupby(r["instrument_id"], sort=False).ffill()
    carried = pd.Series([latest.get((i, pipeline.SETTLEMENT_STAT_TYPE), pd.NaT) for i in r["instrument_id"]],
                        index=r.index, dtype="datetime64[ns]")
    prior_settle = pd.concat([running, carried], axis=1).max(axis=1)
    missing = (r["stat_type"] == pipeline.OPEN_INTEREST_STAT_TYPE) & r["date"].isna()
    r.loc[missing, "date"] = prior_settle[missing]
    return r, int((missing & r["date"].notna()).sum())


def schedules(definition_lookup, infer):
    pipeline.infer_missing_oi_trade_dates = infer
    try:
        panel = pipeline.build_settlement_oi_panel()
    finally:
        pipeline.infer_missing_oi_trade_dates = REPLACEMENT
    outright = pipeline.build_outright_panel(definition_lookup, panel)
    out = {}
    for symbol in config.ALL_SYMBOLS:
        seq = pipeline.symbol_listed_sequence(outright, symbol)
        if not seq:
            continue
        front = pipeline.symbol_front_series(pipeline.symbol_oi_wide(outright, symbol, seq), seq)
        expiry = (outright[outright["asset"] == symbol].drop_duplicates(subset=["_contract_key"])
                  .set_index("_contract_key")["expiration"].to_dict())
        out[symbol] = (front[front.index < CUTOFF], expiry)
    return out, panel.attrs["diagnostics"]


def rolls(front: pd.Series) -> set:
    changed = front.ne(front.shift(1)) & front.shift(1).notna()
    return {(d, front.shift(1)[d], front[d]) for d in front.index[changed]}


def main() -> int:
    definition_lookup = pipeline.build_definition_lookup()
    new, new_diag = schedules(definition_lookup, REPLACEMENT)
    old, old_diag = schedules(definition_lookup, withdrawn_infer)
    for name, diag in (("replacement", new_diag), ("withdrawn", old_diag)):
        print(f"{name}: " + ", ".join(f"{k}={v}" for k, v in diag.items() if k != "weekend_trade_date_dropped"))
    total = differ = only_new = only_old = 0
    moved, cal_new, cal_old = [], Counter(), Counter()
    print(f"\nper symbol, instrument-days before {CUTOFF.date()}:")
    for symbol in config.ALL_SYMBOLS:
        if symbol not in new or symbol not in old:
            print(f"  {symbol}: missing in one schedule")
            continue
        a, b = new[symbol][0], old[symbol][0]
        common = a.index.intersection(b.index)
        d = int((a[common] != b[common]).sum())
        total, differ = total + len(common), differ + d
        only_new += len(a.index.difference(b.index))
        only_old += len(b.index.difference(a.index))
        cal_new.update(d_.date() for d_ in a.index.difference(b.index))
        cal_old.update(d_.date() for d_ in b.index.difference(a.index))
        ra, rb = rolls(a), rolls(b)
        for tag, s in (("replacement only", ra - rb), ("withdrawn only", rb - ra)):
            moved += [(symbol, tag, dt.date(), f, t) for dt, f, t in s]
        va = find_stuck_front_violations(a, new[symbol][1])
        vb = find_stuck_front_violations(b, old[symbol][1])
        print(f"  {symbol}: common={len(common)} front_differs={d} only_replacement={len(a.index.difference(b.index))} "
              f"only_withdrawn={len(b.index.difference(a.index))} rolls={len(ra)}/{len(rb)} "
              f"stuck_front={len(va)}/{len(vb)}")
    print(f"\nTOTAL: common instrument-days={total}, front differs={differ}, share={differ / total:.6%}; "
          f"days only in replacement={only_new}, only in withdrawn={only_old}")
    for name, cal in (("replacement", cal_new), ("withdrawn", cal_old)):
        print(f"calendar dates only in the {name} schedule (date: symbols): "
              + ", ".join(f"{d} ({k}, {pd.Timestamp(d).day_name()[:3]})" for d, k in sorted(cal.items())))
    print(f"roll dates that move ({len(moved)} roll events):")
    for symbol, tag, dt, f, t in sorted(moved, key=lambda x: (x[0], x[2], x[1])):
        print(f"  {symbol} {dt} {tag}: {f} -> {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
