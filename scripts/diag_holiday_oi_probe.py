"""
Read-only probe of the pre-2015 open-interest feed on US exchange holidays (delegate decision of
2026-09-28T06:47:48Z, item 3; reports/ADDENDUM_2026-09-27.md §10).

For every US exchange holiday from 2010-06-06 to 2015-11-19 (New Year's Day, Martin Luther King Jr. Day,
Presidents' Day, Good Friday, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas; New
Year's observed on the Monday when it falls on a Sunday and not observed when it falls on a Saturday,
Independence Day and Christmas on the nearest weekday), it reports:
  - whether a statistics file exists for the holiday, its OPEN_INTEREST record count, and its
    SETTLEMENT_PRICE records dated the holiday (a non-zero settlement count means the exchange published
    settlements for these contracts that day);
  - the pre-holiday trade date P (the last weekday before the holiday with settlements dated to it) and
    the day-after batch: OPEN_INTEREST records in the first weekday file after the holiday;
  - whether that batch carries P's contracts: the share of its instruments whose settlement is dated P
    (under the settlement-anchored rule those records are dated P, given no settlement dated the
    holiday), and the share of the contracts with OI in P's own file (the pre-holiday batch) it covers.
It also lists weekdays in the window with no settlement dated to them that are not on the holiday list.

The decision's condition: no pre-2015 holiday file contains open interest.

    DATA_DIR=/path/to/commodity-carry python scripts/diag_holiday_oi_probe.py

Reads DATA_DIR/statistics/*.dbn.zst only; prints a report, writes nothing.
"""
import sys
from pathlib import Path

import databento as db
import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay,
                                    USMartinLutherKingJr, USMemorialDay, USPresidentsDay, USThanksgivingDay,
                                    nearest_workday, sunday_to_monday)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import config
from src.pipeline import OPEN_INTEREST_STAT_TYPE, SETTLEMENT_STAT_TYPE, statistics_records

START, END = pd.Timestamp("2010-06-06"), pd.Timestamp("2015-11-19")


class ExchangeHolidays(AbstractHolidayCalendar):
    rules = [
        Holiday("New Year's Day", month=1, day=1, observance=sunday_to_monday),
        USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
        Holiday("Independence Day", month=7, day=4, observance=nearest_workday),
        USLaborDay, USThanksgivingDay,
        Holiday("Christmas", month=12, day=25, observance=nearest_workday),
    ]


def main() -> int:
    hol = [h for h in ExchangeHolidays().holidays(START, END) if h.dayofweek < 5]
    files = {pd.Timestamp(f.name.split(".")[0].split("-")[-1]): f
             for f in sorted((Path(config.DATA_DIR) / "statistics").glob("*.dbn.zst"))}
    settled, oi_ids, oi_n = {}, {}, {}   # one pass over the window's files
    for day, f in files.items():
        if not (START - pd.Timedelta(days=7) <= day <= END + pd.Timedelta(days=7)):
            continue
        rec = statistics_records(db.DBNStore.from_file(f).to_df())
        s = rec[(rec["stat_type"] == SETTLEMENT_STAT_TYPE) & rec["date"].notna()]
        for ref, ids in s.groupby("date")["instrument_id"]:
            settled.setdefault(ref, set()).update(ids.astype(int))
        o = rec[rec["stat_type"] == OPEN_INTEREST_STAT_TYPE]
        oi_n[day], oi_ids[day] = len(o), set(o["instrument_id"].astype(int))

    rows, any_oi = [], []
    for h in hol:
        if not (min(files) < h < max(files)):
            continue
        p = h - pd.offsets.BDay(1)
        while not settled.get(p) and p > min(files):
            p -= pd.offsets.BDay(1)
        a = h + pd.offsets.BDay(1)
        while a not in files and a < max(files):
            a += pd.offsets.BDay(1)
        a_ids, p_ids, p_oi = oi_ids.get(a, set()), settled.get(p, set()), oi_ids.get(p, set())
        n_oi = oi_n.get(h) if h in files else None
        rows.append({"holiday": h.date(), "dow": h.day_name()[:3],
                     "holiday_file": "yes" if h in files else "none",
                     "holiday_file_OI_records": "-" if n_oi is None else n_oi,
                     "settlements_dated_holiday": len(settled.get(h, set())),
                     "pre_holiday_P": p.date(), "day_after_file": a.date(),
                     "day_after_OI_instruments": len(a_ids),
                     "share_with_settlement_on_P": f"{len(a_ids & p_ids) / len(a_ids):.4f}" if a_ids else "-",
                     "share_of_P_file_OI_contracts_covered": f"{len(a_ids & p_oi) / len(p_oi):.4f}" if p_oi else "-"})
        if n_oi:
            any_oi.append(h.date())
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(f"US exchange holidays on weekdays, {START.date()}..{END.date()}: {len(df)}")
    print(df.to_string(index=False))
    hol_set = set(hol)
    zero = [str(d.date()) for d in pd.bdate_range(START, END) if d not in hol_set and not settled.get(d)]
    print(f"\nweekdays in the window, not on the holiday list, with no settlement dated to them: {zero or 'none'}")
    print(f"\nholiday files containing OPEN_INTEREST records: {[str(d) for d in any_oi] or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
