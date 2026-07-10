"""
Tests for src/instrument_filter.py -- the F1-ruling outright-only filter.
Adjudication (WORKSPACE/PREREG_OPEN_ITEMS.md, "Aaron + advisor, decided
blind to results"): filtering to outright futures via the `definition`
schema's instrument-class field is a clarification of the pre-registered
universe, not a deviation -- PREREGISTRATION Sec 2-3's "contracts" denote
outright futures by design. Symbol-string heuristics are PROHIBITED as the
filter mechanism -- these tests exist specifically to prove the filter
does NOT rely on symbol-string patterns (hyphens, ":CF" suffixes) even
though the synthetic fixtures include those patterns as red herrings.

All fixtures here are synthetic, per Hard Rule 1 -- the real instrument-
class field values used by src/instrument_filter.py are verified
empirically against real definition data in docs/DATA_QA_REPORT.md's
addendum, not hardcoded here from memory of the Databento spec.
"""
import pandas as pd
import pytest

from src.instrument_filter import filter_outright_only, outright_instrument_ids, OUTRIGHT_INSTRUMENT_CLASS


def _definition_fixture():
    """A synthetic definition-schema panel mixing outrights, hyphenated
    calendar spreads, and ':CF' combo instruments -- deliberately using
    symbol strings that WOULD fool a naive hyphen/colon heuristic, so a
    passing filter here proves the classification is field-based."""
    return pd.DataFrame([
        {"raw_symbol": "CLZ6", "instrument_class": OUTRIGHT_INSTRUMENT_CLASS, "expiration": pd.Timestamp("2026-12-21", tz="UTC")},
        {"raw_symbol": "CLF7", "instrument_class": OUTRIGHT_INSTRUMENT_CLASS, "expiration": pd.Timestamp("2027-01-20", tz="UTC")},
        {"raw_symbol": "NGV0-NGX0", "instrument_class": "S", "expiration": pd.Timestamp("2010-10-27", tz="UTC")},
        {"raw_symbol": "ZS:CF N1Q1U1X1", "instrument_class": "B", "expiration": pd.Timestamp("2021-07-14", tz="UTC")},
        # A red herring: an outright-looking, hyphen-free, non-":CF" symbol
        # that is nonetheless classified as a spread in the field -- proves
        # the filter trusts the field over the symbol's surface appearance.
        {"raw_symbol": "GCQ6Z6", "instrument_class": "S", "expiration": pd.Timestamp("2026-08-26", tz="UTC")},
    ])


def test_filter_keeps_only_outright_instrument_class():
    df = _definition_fixture()
    result = filter_outright_only(df)
    assert set(result["raw_symbol"]) == {"CLZ6", "CLF7"}


def test_filter_excludes_hyphenated_spread_via_field_not_string():
    df = _definition_fixture()
    result = filter_outright_only(df)
    assert "NGV0-NGX0" not in result["raw_symbol"].values


def test_filter_excludes_cf_combo_via_field_not_string():
    df = _definition_fixture()
    result = filter_outright_only(df)
    assert "ZS:CF N1Q1U1X1" not in result["raw_symbol"].values


def test_filter_excludes_field_classified_spread_even_with_outright_looking_symbol():
    """The red-herring case: proves the filter does not fall back to any
    symbol-string heuristic, prohibited by the F1 ruling."""
    df = _definition_fixture()
    result = filter_outright_only(df)
    assert "GCQ6Z6" not in result["raw_symbol"].values


def test_filter_raises_if_instrument_class_column_missing():
    df = _definition_fixture().drop(columns=["instrument_class"])
    with pytest.raises(KeyError):
        filter_outright_only(df)


def test_filter_on_empty_frame_returns_empty():
    df = _definition_fixture().iloc[0:0]
    result = filter_outright_only(df)
    assert len(result) == 0


def test_outright_instrument_ids_single_day_returns_set():
    """No date/ts_recv info at all (like _definition_fixture()) is treated
    as an implicit single snapshot -- backward compatible with the existing
    synthetic fixtures above."""
    df = _definition_fixture()
    df["instrument_id"] = [111, 222, 333, 444, 555]
    ids = outright_instrument_ids(df)
    assert ids == {111, 222}


def test_outright_instrument_ids_raises_on_multiple_dates_via_datetime_index():
    """F6 (docs/DATA_QA_REPORT.md addendum): instrument_id is reused across
    this dataset's history -- ~20% of outright instrument_ids (668/3,314)
    were also assigned to a different, usually non-outright, instrument at
    another point in time (confirmed example: instrument_id 4948 was a ZL
    spread in 2010, a PL spread later, the outright PLU5 in 2015, then
    another PL spread). A definition_df spanning multiple dates must never
    be collapsed into one static instrument_id set -- this test proves the
    guard actually fires rather than silently unioning across dates."""
    day1 = _definition_fixture().copy()
    day1["instrument_id"] = [111, 222, 333, 444, 555]
    day1.index = pd.DatetimeIndex([pd.Timestamp("2020-01-01", tz="UTC")] * len(day1))

    day2 = _definition_fixture().copy()
    day2["instrument_id"] = [111, 222, 333, 444, 555]
    day2.index = pd.DatetimeIndex([pd.Timestamp("2020-01-02", tz="UTC")] * len(day2))

    two_day_df = pd.concat([day1, day2])
    with pytest.raises(ValueError, match="distinct dates"):
        outright_instrument_ids(two_day_df)


def test_outright_instrument_ids_single_day_via_datetime_index_is_fine():
    df = _definition_fixture().copy()
    df["instrument_id"] = [111, 222, 333, 444, 555]
    df.index = pd.DatetimeIndex([pd.Timestamp("2020-01-01", tz="UTC")] * len(df))
    ids = outright_instrument_ids(df)
    assert ids == {111, 222}


def test_outright_instrument_ids_raises_on_multiple_dates_via_ts_recv_column():
    df = _definition_fixture().copy()
    df["instrument_id"] = [111, 222, 333, 444, 555]
    df["ts_recv"] = [pd.Timestamp("2020-01-01", tz="UTC")] * 3 + [pd.Timestamp("2020-01-02", tz="UTC")] * 2
    with pytest.raises(ValueError, match="distinct dates"):
        outright_instrument_ids(df)


def test_outright_instrument_ids_falls_back_to_raw_symbol_without_instrument_id():
    df = _definition_fixture()
    ids = outright_instrument_ids(df)
    assert ids == {"CLZ6", "CLF7"}
