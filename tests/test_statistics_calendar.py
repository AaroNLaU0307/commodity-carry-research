"""Trade-date keying, session calendar and field mapping of the `statistics`
reader (src/pipeline.py). Writes small synthetic DBN files with the pinned
databento_dbn encoder and reads them back through the same
build_settlement_oi_panel() the runners use, so the file-reading path is
exercised end to end without licensed data.

The feed is split by UTC day. CME trade dates run Monday-Friday; the Sunday
22:00 UTC session open re-sends Friday's settlement (ts_ref = Friday) inside
a Sunday-dated file, and open interest for trade date D is published in a
later file with ts_ref = D."""
from pathlib import Path

import databento_dbn as dbn
import numpy as np
import pandas as pd
import pytest
import zstandard

from src import config
from src.pipeline import (
    build_outright_panel,
    build_settlement_oi_panel,
    symbol_date_index,
)

SETTLE = dbn.StatType.SETTLEMENT_PRICE
OPEN_INTEREST = dbn.StatType.OPEN_INTEREST
CLEARED_VOLUME = dbn.StatType.CLEARED_VOLUME


def _ns(ts) -> int:
    return int(pd.Timestamp(ts, tz="UTC").value)


def _stat(iid, stat_type, ts_recv, ts_ref, price=None, quantity=None, update_action=dbn.StatUpdateAction.NEW):
    return dbn.StatMsg(
        publisher_id=1, instrument_id=iid, ts_event=_ns(ts_recv), ts_recv=_ns(ts_recv),
        ts_ref=dbn.UNDEF_TIMESTAMP if ts_ref is None else _ns(ts_ref),
        price=dbn.UNDEF_PRICE if price is None else round(price * 1e9),
        quantity=dbn.UNDEF_STAT_QUANTITY if quantity is None else quantity,
        stat_type=stat_type, update_action=update_action,
    )


def _write_statistics_files(data_dir, records):
    """Groups records by the UTC date of ts_recv into one
    glbx-mdp3-YYYYMMDD.statistics.dbn.zst per day, as Databento delivers."""
    out = data_dir / "statistics"
    out.mkdir(parents=True, exist_ok=True)
    by_day = {}
    for r in records:
        day = pd.Timestamp(r.ts_recv, unit="ns").normalize()
        by_day.setdefault(day, []).append(r)
    for day, recs in by_day.items():
        recs = sorted(recs, key=lambda r: r.ts_recv)
        meta = dbn.Metadata(
            dataset="GLBX.MDP3", start=_ns(day), end=_ns(day + np.timedelta64(1, "D")),
            stype_in=dbn.SType.PARENT, stype_out=dbn.SType.INSTRUMENT_ID,
            schema=dbn.Schema.STATISTICS, symbols=["CL.FUT"],
        )
        raw = bytes(meta) + b"".join(bytes(r) for r in recs)
        (out / f"glbx-mdp3-{day:%Y%m%d}.statistics.dbn.zst").write_bytes(zstandard.ZstdCompressor().compress(raw))


def test_stat_types_come_from_the_pinned_enum():
    from src.pipeline import OPEN_INTEREST_STAT_TYPE, SETTLEMENT_STAT_TYPE
    assert SETTLEMENT_STAT_TYPE == int(SETTLE)
    assert OPEN_INTEREST_STAT_TYPE == int(OPEN_INTEREST)
    assert OPEN_INTEREST_STAT_TYPE != int(CLEARED_VOLUME)


def test_sunday_file_settlement_is_keyed_to_its_friday_trade_date(tmp_path):
    """Friday 2020-04-03: preliminary then final settlement. The Sunday
    2020-04-05 22:00 UTC session open re-sends Friday's final settlement and
    publishes Friday's OI, both with ts_ref = Friday. No row may be keyed
    to Sunday; Friday carries the last-received (final) settlement."""
    fri, sun, mon = "2020-04-03", "2020-04-05", "2020-04-06"
    _write_statistics_files(tmp_path, [
        _stat(42, SETTLE, f"{fri} 18:30", fri, price=28.00),     # preliminary
        _stat(42, SETTLE, f"{fri} 21:40", fri, price=28.34),     # final
        _stat(42, SETTLE, f"{sun} 22:00", fri, price=28.34),     # Sunday re-send of Friday
        _stat(42, OPEN_INTEREST, f"{sun} 22:00:01", fri, quantity=1100),
        _stat(42, SETTLE, f"{mon} 19:30", mon, price=26.08),
    ])
    panel = build_settlement_oi_panel(tmp_path)

    dates = set(panel["date"])
    assert pd.Timestamp(sun) not in dates
    assert (panel["date"].dt.dayofweek < 5).all()
    assert dates == {pd.Timestamp(fri), pd.Timestamp(mon)}
    friday = panel[panel["date"] == pd.Timestamp(fri)].iloc[0]
    assert friday["settlement"] == pytest.approx(28.34)
    assert friday["oi"] == pytest.approx(1100)
    assert panel.attrs["diagnostics"]["n_weekend_trade_date_dropped"] == 0


def test_cleared_volume_is_never_taken_as_open_interest(tmp_path):
    """CLEARED_VOLUME (StatType 6) and OPEN_INTEREST (StatType 9) for the
    same contract and trade date: `oi` must be the OPEN_INTEREST quantity."""
    day = "2020-04-15"
    _write_statistics_files(tmp_path, [
        _stat(7, SETTLE, f"{day} 19:30", day, price=19.87),
        _stat(7, CLEARED_VOLUME, f"{day} 22:00", day, quantity=111),
        _stat(7, OPEN_INTEREST, f"{day} 22:00:01", day, quantity=999),
    ])
    panel = build_settlement_oi_panel(tmp_path)
    assert len(panel) == 1
    assert panel["oi"].iloc[0] == pytest.approx(999)
    assert panel["settlement"].iloc[0] == pytest.approx(19.87)


def test_deleted_and_undated_statistics_are_not_used(tmp_path):
    """A settlement whose last record is a DELETE is NaN, and a settlement
    with an undefined ts_ref (no trade date) is dropped and counted.
    (Open-interest records without ts_ref are dated instead, see
    test_pre_2015_open_interest_without_ts_ref_is_dated_to_the_previous_weekday.)"""
    day = "2020-04-15"
    _write_statistics_files(tmp_path, [
        _stat(7, SETTLE, f"{day} 19:30", day, price=19.87),
        _stat(7, SETTLE, f"{day} 19:31", day, price=19.87, update_action=dbn.StatUpdateAction.DELETE),
        _stat(7, OPEN_INTEREST, f"{day} 19:32", day, quantity=500),
        _stat(7, SETTLE, f"{day} 19:33", None, price=99.0),
    ])
    panel = build_settlement_oi_panel(tmp_path)
    assert len(panel) == 1
    assert pd.isna(panel["settlement"].iloc[0])
    assert panel["oi"].iloc[0] == pytest.approx(500)
    assert panel.attrs["diagnostics"]["n_undefined_ts_ref"] == 1
    assert panel.attrs["diagnostics"]["n_deleted"] == 1


# 2021 CME-style calendar: 261 weekdays minus 9 exchange holidays = 252 trade dates.
HOLIDAYS_2021 = pd.DatetimeIndex([
    "2021-01-01", "2021-01-18", "2021-02-15", "2021-04-02", "2021-05-31",
    "2021-07-05", "2021-09-06", "2021-11-25", "2021-12-24",
])


def _one_year_feed():
    trade_dates = pd.bdate_range("2021-01-01", "2021-12-31").difference(HOLIDAYS_2021)
    records = []
    for i, d in enumerate(trade_dates):
        price = 50.0 + 0.01 * i
        records.append(_stat(1, SETTLE, d + np.timedelta64(19 * 60 + 30, "m"), d, price=price))
        records.append(_stat(2, SETTLE, d + np.timedelta64(19 * 60 + 31, "m"), d, price=price + 1.0))
        # next session opens 22:00 UTC the day before the next trade date: Sunday
        # after a Friday, the holiday itself after a pre-holiday session
        nxt = trade_dates[i + 1] if i + 1 < len(trade_dates) else d + pd.offsets.BDay(1)
        reopen = nxt - np.timedelta64(1, "D") + np.timedelta64(22, "h")
        records.append(_stat(1, SETTLE, reopen, d, price=price))
        records.append(_stat(1, OPEN_INTEREST, reopen + np.timedelta64(1, "s"), d, quantity=2000 - i))
        records.append(_stat(2, OPEN_INTEREST, reopen + np.timedelta64(2, "s"), d, quantity=100 + i))
        records.append(_stat(1, CLEARED_VOLUME, reopen + np.timedelta64(3, "s"), d, quantity=50_000))
    return trade_dates, records


def _definition_lookup_every_non_saturday(start, end):
    """Definition files exist for every non-Saturday UTC day (5,031 in the
    real corpus), each listing both live outrights."""
    days = [d for d in pd.date_range(start, end, freq="D") if d.dayofweek != 5]
    rows = []
    for d in days:
        rows.append({"date": d, "instrument_id": 1, "asset": "CL", "raw_symbol": "CLF2",
                     "instrument_class": "F", "expiration": pd.Timestamp("2021-12-20")})
        rows.append({"date": d, "instrument_id": 2, "asset": "CL", "raw_symbol": "CLG2",
                     "instrument_class": "F", "expiration": pd.Timestamp("2022-01-20")})
    return pd.DataFrame(rows)


def test_daily_calendar_holds_only_trade_dates_and_matches_252_annualisation(tmp_path):
    """A year of synthetic feed (settlements, Sunday/holiday session-open
    re-sends, next-day OI) through the real reader and outright-panel join:
    the per-symbol daily index must hold exactly the 252 trade dates -- no
    Sunday, no holiday -- which is the row count TRADING_DAYS_PER_YEAR
    annualises. Keying on the file date instead yields every non-Saturday
    day (~313/yr), overstating the row count by ~24%."""
    trade_dates, records = _one_year_feed()
    _write_statistics_files(tmp_path, records)
    panel = build_settlement_oi_panel(tmp_path)
    outright = build_outright_panel(_definition_lookup_every_non_saturday("2021-01-01", "2021-12-31"), panel)
    index = symbol_date_index(outright, "CL")

    assert not (index.dayofweek >= 5).any()
    assert not index.isin(HOLIDAYS_2021).any()
    pd.testing.assert_index_equal(index, pd.DatetimeIndex(trade_dates))
    rows_per_year = len(index[index.year == 2021])
    assert abs(rows_per_year - config.TRADING_DAYS_PER_YEAR) / config.TRADING_DAYS_PER_YEAR < 0.03
    # OI of each trade date is the OPEN_INTEREST quantity, not the cleared volume
    oi = outright[(outright["instrument_id"] == 1)].set_index("date")["oi"]
    assert oi.loc[trade_dates[0]] == pytest.approx(2000)
    assert (oi < 50_000).all()


# ---------------------------------------------------------------------------
# Late-record rule (DATA_FIX, delegate decision 2026-09-27T18:15:08Z;
# reports/ADDENDUM_2026-09-27.md §10)
# ---------------------------------------------------------------------------
def _clk0_feed():
    """The real CLK0 records for trade dates 2020-04-17 (Friday) and
    2020-04-20 (Monday), as RERUN_RUNBOOK.md step 2 printed them: Friday's
    18.27 three times and its Sunday re-send, Monday's -37.63 twice, then a
    Monday-evening record carrying Monday's -37.63 under ts_ref = Friday."""
    fri, sun, mon = "2020-04-17", "2020-04-19", "2020-04-20"
    return [
        _stat(22770, SETTLE, f"{fri} 18:32:07", fri, price=18.27),
        _stat(22770, SETTLE, f"{fri} 18:45:30", fri, price=18.27),
        _stat(22770, SETTLE, f"{fri} 21:38:03", fri, price=18.27),
        _stat(22770, SETTLE, f"{sun} 18:05:26", fri, price=18.27),
        _stat(22770, SETTLE, f"{mon} 18:33:01", mon, price=-37.63),
        _stat(22770, SETTLE, f"{mon} 18:53:15", mon, price=-37.63),
        _stat(22770, SETTLE, f"{mon} 21:43:42", fri, price=-37.63),   # late: Monday's value, Friday's ts_ref
    ]


def test_late_settlement_cannot_overwrite_an_earlier_trade_date_clk0(tmp_path):
    """Pre-fix (last received per trade date, no late filter) Friday
    2020-04-17 takes Monday's -37.63; with the late-record rule it keeps the
    CME settlement 18.27, and the dropped record is counted."""
    import databento as db
    from src.pipeline import settlement_oi_from_statistics, thin_statistics_records

    _write_statistics_files(tmp_path, _clk0_feed())
    files = sorted((tmp_path / "statistics").glob("*.dbn.zst"))
    pre_fix = settlement_oi_from_statistics(pd.concat(
        [thin_statistics_records(db.DBNStore.from_file(f).to_df())[0] for f in files], ignore_index=True))
    assert pre_fix.set_index("date").loc[pd.Timestamp("2020-04-17"), "settlement"] == pytest.approx(-37.63)

    panel = build_settlement_oi_panel(tmp_path).set_index("date")
    assert panel.loc[pd.Timestamp("2020-04-17"), "settlement"] == pytest.approx(18.27)
    assert panel.loc[pd.Timestamp("2020-04-20"), "settlement"] == pytest.approx(-37.63)
    assert panel.attrs["diagnostics"]["n_late_settlement_dropped"] == 1
    assert panel.attrs["diagnostics"]["n_late_open_interest_dropped"] == 0


def test_next_day_open_interest_is_kept(tmp_path):
    """Open interest for trade date d is published after d's session, in
    the next UTC day's file (CLK0: 2020-04-13's OI at 2020-04-14 01:07 UTC;
    Friday's in the Sunday file), and settlements for d + 1 arrive before
    d + 1's OI. None of these is late: every OI value must be kept. (The
    withdrawn file-date rule of 2026-09-27T16:54:16Z dropped all but
    Friday's.)"""
    oi = {"2020-04-13": ("2020-04-14 01:07:48", 324547), "2020-04-14": ("2020-04-15 01:18:08", 231678),
          "2020-04-15": ("2020-04-16 01:21:28", 203897), "2020-04-16": ("2020-04-17 01:31:57", 148838),
          "2020-04-17": ("2020-04-19 17:30:30", 108593), "2020-04-20": ("2020-04-21 01:30:07", 13044)}
    records = []
    for d, (recv, qty) in oi.items():
        records.append(_stat(22770, SETTLE, f"{d} 18:30", d, price=20.0))
        records.append(_stat(22770, OPEN_INTEREST, recv, d, quantity=qty))
    _write_statistics_files(tmp_path, records)
    panel = build_settlement_oi_panel(tmp_path).set_index("date")
    for d, (_, qty) in oi.items():
        assert panel.loc[pd.Timestamp(d), "oi"] == pytest.approx(qty)
    assert panel.attrs["diagnostics"]["n_late_open_interest_dropped"] == 0
    assert panel.attrs["diagnostics"]["n_late_settlement_dropped"] == 0


# ---------------------------------------------------------------------------
# Open interest without ts_ref (DATA_FIX, delegate decision
# 2026-09-27T19:54:48Z; reports/ADDENDUM_2026-09-27.md §10)
# ---------------------------------------------------------------------------
def test_pre_2015_open_interest_without_ts_ref_is_dated_to_the_previous_weekday(tmp_path):
    """Before 2015-11-20 the feed delivers OPEN_INTEREST with no ts_ref, in
    the next UTC day's file (06:00-15:00 UTC on weekdays; Friday's in the
    Sunday file at ~20:00 UTC and again on Monday). Each is dated to the
    weekday before its file's date, holidays included (delegate decision of
    2026-09-28T04:57:40Z): the Tuesday file after the 2014-01-20 MLK holiday
    carries the holiday session's OI, dated Monday although no settlement
    exists for it. An OI record that carries a ts_ref keeps it."""
    tue, wed, thu, fri, sun, mon = ("2014-06-10", "2014-06-11", "2014-06-12", "2014-06-13",
                                    "2014-06-15", "2014-06-16")
    _write_statistics_files(tmp_path, [
        _stat(5, OPEN_INTEREST, f"{wed} 06:07", None, quantity=900),       # -> Tuesday
        _stat(5, SETTLE, f"{wed} 18:30", wed, price=100.0),
        _stat(5, OPEN_INTEREST, f"{thu} 06:07", None, quantity=1000),      # -> Wednesday
        _stat(5, SETTLE, f"{thu} 18:30", thu, price=101.0),
        _stat(5, OPEN_INTEREST, f"{fri} 06:12", None, quantity=1100),      # -> Thursday
        _stat(5, SETTLE, f"{fri} 18:30", fri, price=102.0),
        _stat(5, SETTLE, f"{sun} 20:00", fri, price=102.0),                # Sunday re-send of Friday
        _stat(5, OPEN_INTEREST, f"{sun} 20:07", None, quantity=1200),      # -> Friday
        _stat(5, OPEN_INTEREST, f"{mon} 14:16", None, quantity=1190),      # -> Friday (revised)
        _stat(5, SETTLE, f"{mon} 18:30", mon, price=103.0),
        _stat(6, SETTLE, f"{mon} 18:31", mon, price=50.0),
        _stat(6, OPEN_INTEREST, f"{mon} 18:40", fri, quantity=77),         # carries ts_ref: kept as Friday
        _stat(7, SETTLE, "2014-01-17 18:30", "2014-01-17", price=60.0),   # Friday before MLK
        _stat(7, OPEN_INTEREST, "2014-01-21 14:10", None, quantity=555),   # Tuesday file -> MLK Monday
    ])
    panel = build_settlement_oi_panel(tmp_path)
    oi = panel.dropna(subset=["oi"]).set_index(["instrument_id", "date"])["oi"]
    assert oi.to_dict() == {(5, pd.Timestamp(tue)): 900, (5, pd.Timestamp(wed)): 1000,
                            (5, pd.Timestamp(thu)): 1100, (5, pd.Timestamp(fri)): 1190,
                            (6, pd.Timestamp(fri)): 77, (7, pd.Timestamp("2014-01-20")): 555}
    assert panel.attrs["diagnostics"]["n_oi_ts_ref_inferred"] == 6
    assert panel.attrs["diagnostics"]["n_undefined_ts_ref"] == 0
    assert panel.attrs["diagnostics"]["n_late_open_interest_dropped"] == 0


_JUNE_2010 = pd.date_range("2010-06-06", "2010-07-02")


def _real_june_2010_corpus(tmp_path):
    import shutil
    src = Path(config.DATA_DIR)
    days = [f"{d:%Y%m%d}" for d in _JUNE_2010]
    stats = [f for d in days for f in (src / "statistics").glob(f"*{d}*.dbn.zst")]
    defs = [f for d in days for f in (src / "definition").glob(f"*{d}*.dbn.zst")]
    if not stats or not defs:
        pytest.skip("needs the licensed Databento corpus in DATA_DIR")
    for schema, files in (("statistics", stats), ("definition", defs)):
        (tmp_path / schema).mkdir()
        for f in files:
            shutil.copy(f, tmp_path / schema / f.name)
    return tmp_path


def test_real_june_2010_cl_front_rolls_at_the_2010_06_22_expiry(tmp_path):
    """Real files, 2010-06-06..2010-07-02 (licensed data; skipped without
    it). Before the OI trade-date fix CL had no open interest here and its
    front, CLN0 (expiry 2010-06-22), was held past expiry -- the 6786973
    halt. With it, the front is never held past its expiry, and on the
    first trade date after 2010-06-22 it is a later contract."""
    from src import pipeline
    data = _real_june_2010_corpus(tmp_path)
    outright = build_outright_panel(pipeline.build_definition_lookup(data), build_settlement_oi_panel(data))
    seq = pipeline.symbol_listed_sequence(outright, "CL")
    front = pipeline.symbol_front_series(pipeline.symbol_oi_wide(outright, "CL", seq), seq)
    expiry = (outright[outright["asset"] == "CL"].drop_duplicates("_contract_key")
              .set_index("_contract_key")["expiration"])
    exp_of_front = pd.to_datetime(front.map(expiry)).dt.tz_localize(None).dt.normalize()
    assert (exp_of_front >= front.index).all()
    after = front[front.index > pd.Timestamp("2010-06-22")]
    assert exp_of_front[after.index[0]] > pd.Timestamp("2010-06-22")
    assert not front.loc["2010-06-23":].str.startswith("182055").any()


def test_sunday_dated_settlement_is_dropped_as_read_and_leaves_friday_intact(tmp_path):
    """CLJ4 (instrument 819161), real sequence: Friday 2014-02-21 settles
    102.2; the Sunday 2014-02-23 file carries a settlement dated the Sunday
    itself (102.21) at 19:00:27, then the re-send of Friday's (102.2) at
    19:02:05, then Friday's undated OI at 21:07 and again on Monday, the last
    revised. The Sunday-dated record is dropped as it is read, counted and
    listed. Kept in the carried state, it would make Friday's re-send "late"
    and date every one of Friday's OI records to the Sunday, leaving Friday
    without OI."""
    fri, sun, mon = "2014-02-21", "2014-02-23", "2014-02-24"
    _write_statistics_files(tmp_path, [
        _stat(819161, OPEN_INTEREST, f"{fri} 07:06:59", None, quantity=329655),   # Thursday's
        _stat(819161, SETTLE, f"{fri} 21:33:53", fri, price=102.2),
        _stat(819161, SETTLE, f"{sun} 19:00:27", sun, price=102.21),              # Sunday-dated
        _stat(819161, SETTLE, f"{sun} 19:02:05", fri, price=102.2),
        _stat(819161, OPEN_INTEREST, f"{sun} 21:07:05", None, quantity=322108),
        _stat(819161, OPEN_INTEREST, f"{mon} 07:07:09", None, quantity=322108),
        _stat(819161, OPEN_INTEREST, f"{mon} 14:58:34", None, quantity=320747),   # Friday's, revised
        _stat(819161, SETTLE, f"{mon} 21:33:48", mon, price=102.82),
    ])
    panel = build_settlement_oi_panel(tmp_path)
    diag = panel.attrs["diagnostics"]
    friday = panel.set_index("date").loc[pd.Timestamp(fri)]
    assert friday["settlement"] == pytest.approx(102.2)
    assert friday["oi"] == pytest.approx(320747)
    assert pd.Timestamp(sun) not in set(panel["date"])
    assert diag["n_weekend_trade_date_dropped"] == 1
    assert diag["weekend_trade_date_dropped"] == [f"{sun} instrument_id=819161 stat_type={int(SETTLE)}"]
    assert diag["n_late_settlement_dropped"] == 0
