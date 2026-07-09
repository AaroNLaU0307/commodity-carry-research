"""Tests for the synthetic-safe parts of src/data_loader.py (calendar,
entry rule, live-symbols query). load_dbn() itself requires real files in
DATA_DIR and is exercised manually during Phase 1a QA, never here -- see
that module's docstring and Phase 1a Hard Rule 1."""
import pandas as pd

from src.data_loader import build_month_end_calendar, live_symbols_at


def test_month_end_calendar_picks_last_trading_day_not_calendar_end():
    # Business days for Jan-Feb 2021; Jan 31 2021 is a Sunday, so the last
    # trading day of January is Jan 29 (Friday), not the 31st.
    daily = pd.bdate_range("2021-01-01", "2021-02-26")
    calendar = build_month_end_calendar(daily)
    assert pd.Timestamp("2021-01-29") in calendar
    assert pd.Timestamp("2021-01-31") not in calendar
    assert pd.Timestamp("2021-02-26") in calendar  # Feb 26 2021 is a Friday, last bday of Feb


def test_month_end_calendar_one_entry_per_month():
    daily = pd.bdate_range("2020-01-01", "2020-06-30")
    calendar = build_month_end_calendar(daily)
    assert len(calendar) == 6  # Jan through June


def test_live_symbols_at_boundary_is_inclusive():
    entry_dates = {"KE": pd.Timestamp("2013-12-16")}
    assert "KE" in live_symbols_at(pd.Timestamp("2013-12-16"), entry_dates)
    assert "KE" not in live_symbols_at(pd.Timestamp("2013-12-15"), entry_dates)
