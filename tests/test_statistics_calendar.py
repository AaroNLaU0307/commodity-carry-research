"""Trade-date keying, session calendar and field mapping of the `statistics`
reader (src/pipeline.py). Writes small synthetic DBN files with the pinned
databento_dbn encoder and reads them back through the same
build_settlement_oi_panel() the runners use, so the file-reading path is
exercised end to end without licensed data.

The feed is split by UTC day. CME trade dates run Monday-Friday; the Sunday
22:00 UTC session open re-sends Friday's settlement (ts_ref = Friday) inside
a Sunday-dated file, and open interest for trade date D is published in a
later file with ts_ref = D."""
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
    """A settlement whose last record is a DELETE is NaN, and a record with
    an undefined ts_ref (no trade date) is dropped and counted."""
    day = "2020-04-15"
    _write_statistics_files(tmp_path, [
        _stat(7, SETTLE, f"{day} 19:30", day, price=19.87),
        _stat(7, SETTLE, f"{day} 19:31", day, price=19.87, update_action=dbn.StatUpdateAction.DELETE),
        _stat(7, OPEN_INTEREST, f"{day} 19:32", day, quantity=500),
        _stat(7, OPEN_INTEREST, f"{day} 19:33", None, quantity=123456),
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
