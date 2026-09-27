"""
Read-only diagnostic for RERUN_RUNBOOK.md step 2: late SETTLEMENT_PRICE records.

The pipeline keys each settlement on its CME trade date (`ts_ref`) and keeps
the last-received record per (trade date, instrument) across files
(src/pipeline.py). That assumes a record for trade date T never arrives after
the same instrument's settlement for a later trade date. This script tests the
assumption over the whole statistics corpus: records are replayed in ts_recv
order, and a record for (instrument, T) is "late" when a settlement for a later
trade date of that instrument has already been received. Late records whose
price differs from the value already held for T are the ones that change what
the pipeline keeps; they are printed and written to a CSV.

    DATA_DIR=/path/to/commodity-carry python scripts/diag_late_settlements.py [out.csv]

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

SETTLE = int(StatType.SETTLEMENT_PRICE)


def main(out_csv=None) -> int:
    files = sorted((Path(config.DATA_DIR) / "statistics").glob("*.dbn.zst"))
    value, latest, late, n_late_same = {}, {}, [], 0
    for i, f in enumerate(files):
        s = db.DBNStore.from_file(f).to_df().reset_index()
        s = s[s["stat_type"] == SETTLE]
        if s.empty:
            continue
        s = s.assign(ref=pd.to_datetime(s["ts_ref"], utc=True).dt.normalize()).sort_values("ts_recv")
        for row in s.itertuples(index=False):
            iid, ref, px = int(row.instrument_id), row.ref.value, float(row.price)
            lr = latest.get(iid)
            if lr is not None and ref < lr[0]:
                prev = value.get((iid, ref))
                if prev == px:
                    n_late_same += 1
                else:
                    late.append({"file": f.name, "instrument_id": iid, "ts_ref": row.ref.date(),
                                 "ts_recv": row.ts_recv, "price": px, "prior_value_for_ts_ref": prev,
                                 "latest_ts_ref": pd.Timestamp(lr[0], tz="UTC").date(), "latest_price": lr[1],
                                 "equals_latest_price": px == lr[1], "stat_flags": int(row.stat_flags),
                                 "update_action": int(row.update_action)})
            value[(iid, ref)] = px
            if lr is None or ref >= lr[0]:
                latest[iid] = (ref, px)
        if i % 500 == 0:
            cutoff = (pd.Timestamp(f.name.split(".")[0].split("-")[-1], tz="UTC") - pd.Timedelta(days=30)).value
            value = {k: v for k, v in value.items() if k[1] >= cutoff}
    df = pd.DataFrame(late)
    print(f"files={len(files)} late_records_same_price={n_late_same} "
          f"late_records_different_price={len(df)} "
          f"of_which_equal_to_later_trade_date_price={int(df['equals_latest_price'].sum()) if len(df) else 0}")
    if len(df):
        print(df.to_string(index=False))
    if out_csv:
        df.to_csv(out_csv, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
