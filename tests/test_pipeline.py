"""Tests for src/pipeline.py -- the real-data assembly layer. Only the
functions that take already-loaded DataFrames are tested here, against
synthetic fixtures shaped like the real definition/statistics schemas
(same convention as data_loader.py: the two DBN-reading functions,
build_definition_lookup and build_settlement_oi_panel, require real files
and are exercised manually, never here). Per Phase 1b Hard Rule 4, these
tests exist BEFORE any of this module ran on real data."""
import pandas as pd
import pytest

from src.pipeline import (
    build_outright_panel, audit_contract_key_unification, assert_front_not_past_expiry,
    symbol_listed_sequence, symbol_date_index, symbol_oi_wide, symbol_settle_wide,
    symbol_front_series, symbol_carry_series, symbol_daily_returns,
    month_end_carry_panel, month_end_next_month_return_panel, truncation_invariant_carry_panel,
)

# _contract_key = instrument_id + "__" + expiration (NOT raw_symbol -- see
# build_outright_panel()'s docstring: a single real contract's own
# raw_symbol representation is not always stable across its listed
# lifetime, found on this pipeline's first real-data run). Computed here
# via pd.Series.astype(str) -- the same operation build_outright_panel()
# applies -- rather than scalar str(Timestamp(...)), which formats
# differently (a midnight timestamp's "00:00:00" is dropped by
# Series.astype(str) but not by the scalar's own __str__).
F1_EXPIRY = pd.Timestamp("2020-02-01")
G1_EXPIRY = pd.Timestamp("2020-03-01")
KEY_F1 = "100__" + pd.Series([F1_EXPIRY]).astype(str).iloc[0]
KEY_G1 = "101__" + pd.Series([G1_EXPIRY]).astype(str).iloc[0]


def _synthetic_definition_lookup():
    """Two CL contracts (CLF1 front-then-rolled, CLG1 next) across 10 days,
    plus one spread instrument (class 'S') as a red herring that must be
    filtered out. raw_symbol deliberately does NOT appear in the resulting
    _contract_key (see module-level comment above)."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    rows = []
    for d in dates:
        rows.append({"date": d, "instrument_id": 100, "asset": "CL", "raw_symbol": "CLF1",
                     "instrument_class": "F", "expiration": F1_EXPIRY})
        rows.append({"date": d, "instrument_id": 101, "asset": "CL", "raw_symbol": "CLG1",
                     "instrument_class": "F", "expiration": G1_EXPIRY})
        rows.append({"date": d, "instrument_id": 102, "asset": "CL", "raw_symbol": "CLF1-CLG1",
                     "instrument_class": "S", "expiration": F1_EXPIRY})
    return pd.DataFrame(rows)


def _synthetic_settlement_oi_panel():
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    rows = []
    # CLF1 (id=100): OI declines from 1000 towards 100 as it nears "expiry"
    # CLG1 (id=101): OI rises from 200 towards 1200 -- crossover (t-1 basis)
    # happens such that front should roll partway through the window.
    oi_f1 = [1000, 900, 800, 700, 300, 250, 200, 150, 120, 100]
    oi_g1 = [200, 250, 300, 350, 400, 450, 900, 950, 1000, 1100]
    settle_f1 = [50.0, 50.5, 51.0, 51.5, 52.0, 52.5, 53.0, 53.5, 54.0, 54.5]
    settle_g1 = [55.0, 55.5, 56.0, 56.5, 57.0, 57.5, 58.0, 58.5, 59.0, 59.5]
    for i, d in enumerate(dates):
        rows.append({"date": d, "instrument_id": 100, "settlement": settle_f1[i], "oi": oi_f1[i]})
        rows.append({"date": d, "instrument_id": 101, "settlement": settle_g1[i], "oi": oi_g1[i]})
    return pd.DataFrame(rows)


def test_build_outright_panel_filters_spread_and_joins_on_date_and_id():
    defn = _synthetic_definition_lookup()
    stats = _synthetic_settlement_oi_panel()
    outright = build_outright_panel(defn, stats)
    assert set(outright["instrument_class"]) == {"F"}
    assert "CLF1-CLG1" not in outright["raw_symbol"].values  # spread filtered
    assert set(outright["_contract_key"]) == {KEY_F1, KEY_G1}
    # settlement/OI correctly attached per (date, instrument_id)
    row = outright[(outright["_contract_key"] == KEY_F1) & (outright["date"] == "2020-01-01")]
    assert row["settlement"].iloc[0] == pytest.approx(50.0)
    assert row["oi"].iloc[0] == pytest.approx(1000)


def test_F9_build_outright_panel_unifies_a_contract_whose_raw_symbol_format_changes():
    """F9 (docs/DATA_QA_REPORT.md): the SAME instrument_id, with a constant
    expiration, appearing under two different raw_symbol strings on
    different dates (e.g. real instrument_id 551735 showed as "CLM19" on
    its first 2 listed days and "CLM9" for the rest of its ~9-year life)
    must resolve to ONE _contract_key, not two, and its OI/settlement
    history must be continuous under that one key."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    rows = []
    for i, d in enumerate(dates):
        raw_symbol = "CLM19" if i < 2 else "CLM9"  # format changes after day 2, same instrument
        rows.append({"date": d, "instrument_id": 999, "asset": "CL", "raw_symbol": raw_symbol,
                     "instrument_class": "F", "expiration": pd.Timestamp("2021-05-21")})
    defn = pd.DataFrame(rows)
    stats = pd.DataFrame({"date": dates, "instrument_id": 999, "settlement": [10.0, 11.0, 12.0, 13.0], "oi": [500, 480, 460, 440]})
    outright = build_outright_panel(defn, stats)
    assert outright["_contract_key"].nunique() == 1  # one real contract, one key, regardless of raw_symbol drift
    seq = symbol_listed_sequence(outright, "CL")
    assert len(seq) == 1
    settle_wide = symbol_settle_wide(outright, "CL", seq)
    oi_wide = symbol_oi_wide(outright, "CL", seq)
    assert settle_wide.iloc[:, 0].notna().all()  # all 4 days' settlement present under the one unified column
    assert oi_wide.iloc[:, 0].notna().all()      # ...and OI too -- one continuous history, not two fragments


def test_F10_build_outright_panel_unifies_a_contract_whose_expiration_time_of_day_is_corrected():
    """F10 (docs/DATA_QA_REPORT.md): the SAME instrument_id, same
    expiration DATE, but a mid-life correction to the exact expiration
    TIME-OF-DAY (e.g. real instrument_id 827180: "2014-09-12 18:15:00" for
    its first 186 listed days, "2014-09-12 17:01:00" for its last 48) must
    also resolve to ONE _contract_key -- keying on the full timestamp
    fractured this contract's OI history into two incomplete pieces,
    which stalled the roll rule's crossover condition permanently once the
    fracture point coincided with where an adjacent contract should have
    taken over (the real "stuck front" failure this fix resolves)."""
    dates = pd.date_range("2020-01-01", periods=6, freq="D")
    rows = []
    for i, d in enumerate(dates):
        # same calendar date (2021-05-21), time-of-day corrected after day 3
        exp = pd.Timestamp("2021-05-21 18:15:00") if i < 3 else pd.Timestamp("2021-05-21 17:01:00")
        rows.append({"date": d, "instrument_id": 777, "asset": "KE", "raw_symbol": "KEK1",
                     "instrument_class": "F", "expiration": exp})
    defn = pd.DataFrame(rows)
    stats = pd.DataFrame({
        "date": dates, "instrument_id": 777,
        "settlement": [500.0, 501.0, 502.0, 503.0, 504.0, 505.0],
        "oi": [1000, 980, 960, 940, 920, 900],
    })
    outright = build_outright_panel(defn, stats)
    assert outright["_contract_key"].nunique() == 1  # one real contract, one key, despite the time-of-day drift
    seq = symbol_listed_sequence(outright, "KE")
    assert len(seq) == 1
    oi_wide = symbol_oi_wide(outright, "KE", seq)
    settle_wide = symbol_settle_wide(outright, "KE", seq)
    assert oi_wide.iloc[:, 0].notna().all()      # continuous OI across the fracture point (day 3)
    assert settle_wide.iloc[:, 0].notna().all()


def test_genuine_F6_reuse_with_different_expiration_dates_does_not_unify():
    """The negative case Rider 1 requires: two rows sharing an
    instrument_id whose expirations fall on GENUINELY DIFFERENT calendar
    dates (real F6 instrument_id reuse across two different real
    contracts, months or years apart -- not a same-day metadata
    correction) must remain two distinct _contract_keys, never merged."""
    dates = pd.date_range("2020-01-01", periods=2, freq="D")
    rows = [
        {"date": dates[0], "instrument_id": 4948, "asset": "PL", "raw_symbol": "PLU5",
         "instrument_class": "F", "expiration": pd.Timestamp("2015-09-28")},
        {"date": dates[1], "instrument_id": 4948, "asset": "PL", "raw_symbol": "PLZ8",
         "instrument_class": "F", "expiration": pd.Timestamp("2018-12-27")},  # genuinely different real contract
    ]
    defn = pd.DataFrame(rows)
    stats = pd.DataFrame({"date": dates, "instrument_id": 4948, "settlement": [900.0, 1200.0], "oi": [500, 600]})
    outright = build_outright_panel(defn, stats)
    assert outright["_contract_key"].nunique() == 2  # NOT unified -- genuinely different contracts


def test_audit_contract_key_unification_classifies_correctly_and_checks_asset_consistency():
    """Rider 1's required audit: unify-candidates (same date, different
    time) and keep-separate candidates (different dates) must be
    classified correctly, with per-fragment (expiration, n_rows,
    date_min, date_max) detail, and instrument_ids appearing under only
    one expiration value must not appear in either list at all."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    rows = [
        # id=1: F10-style, same date different time -> unify
        {"date": dates[0], "instrument_id": 1, "asset": "KE", "raw_symbol": "KEK1", "instrument_class": "F",
         "expiration": pd.Timestamp("2021-05-21 18:15:00")},
        {"date": dates[1], "instrument_id": 1, "asset": "KE", "raw_symbol": "KEK1", "instrument_class": "F",
         "expiration": pd.Timestamp("2021-05-21 17:01:00")},
        # id=2: F6-style, genuinely different dates -> keep_separate
        {"date": dates[2], "instrument_id": 2, "asset": "PL", "raw_symbol": "PLU5", "instrument_class": "F",
         "expiration": pd.Timestamp("2015-09-28")},
        {"date": dates[3], "instrument_id": 2, "asset": "PL", "raw_symbol": "PLZ8", "instrument_class": "F",
         "expiration": pd.Timestamp("2018-12-27")},
        # id=3: single expiration throughout -> not in either list
        {"date": dates[0], "instrument_id": 3, "asset": "CL", "raw_symbol": "CLZ6", "instrument_class": "F",
         "expiration": pd.Timestamp("2026-12-21")},
        {"date": dates[1], "instrument_id": 3, "asset": "CL", "raw_symbol": "CLZ6", "instrument_class": "F",
         "expiration": pd.Timestamp("2026-12-21")},
    ]
    defn = pd.DataFrame(rows)
    result = audit_contract_key_unification(defn)
    assert result["n_unify"] == 1
    assert result["n_keep_separate"] == 1
    assert result["unify"][0]["instrument_id"] == 1
    assert result["unify"][0]["asset"] == "KE"
    assert len(result["unify"][0]["fragments"]) == 2
    assert result["keep_separate"][0]["instrument_id"] == 2
    assert {f["instrument_id"] for f in result["unify"] + result["keep_separate"]} == {1, 2}  # id=3 excluded


def test_audit_contract_key_unification_reports_cross_asset_reuse_separately():
    """Real data surfaced instrument_id 60 classified outright for BOTH SI
    and GF -- an even more extreme F6 case than same-asset reuse. Grouped
    by (instrument_id, asset), these rows never share a group, so they
    must never appear in "unify" (which would silently merge two
    different commodities) and are reported in their own "cross_asset"
    list instead of contaminating "keep_separate"'s per-asset counts."""
    dates = pd.date_range("2020-01-01", periods=2, freq="D")
    rows = [
        {"date": dates[0], "instrument_id": 60, "asset": "SI", "raw_symbol": "SIX0", "instrument_class": "F",
         "expiration": pd.Timestamp("2020-11-24")},
        {"date": dates[1], "instrument_id": 60, "asset": "GF", "raw_symbol": "GFX1", "instrument_class": "F",
         "expiration": pd.Timestamp("2021-08-26")},
    ]
    defn = pd.DataFrame(rows)
    result = audit_contract_key_unification(defn)
    assert result["n_unify"] == 0
    assert result["n_keep_separate"] == 0
    assert result["n_cross_asset"] == 1
    assert result["cross_asset"][0]["instrument_id"] == 60
    assert result["cross_asset"][0]["assets"] == ["GF", "SI"]


def test_assert_front_not_past_expiry_fires_on_a_stuck_front():
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    front = pd.Series(["A", "A", "A"], index=dates)
    expiry_by_key = {"A": pd.Timestamp("2020-01-02")}  # expires day 2, but still "held" on day 3
    with pytest.raises(AssertionError, match="STUCK FRONT"):
        assert_front_not_past_expiry(front, expiry_by_key, "TEST")


def test_assert_front_not_past_expiry_silent_when_front_rolls_before_its_own_expiry():
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    front = pd.Series(["A", "A", "B"], index=dates)  # rolls to B on day 3, before A's expiry
    expiry_by_key = {"A": pd.Timestamp("2020-01-05"), "B": pd.Timestamp("2020-02-01")}
    assert_front_not_past_expiry(front, expiry_by_key, "TEST")  # must not raise


def test_symbol_listed_sequence_sorted_by_expiration():
    defn = _synthetic_definition_lookup()
    stats = _synthetic_settlement_oi_panel()
    outright = build_outright_panel(defn, stats)
    seq = symbol_listed_sequence(outright, "CL")
    assert seq == [KEY_F1, KEY_G1]  # CLF1 expires first


def test_symbol_oi_wide_and_front_series_roll_at_correct_crossover():
    defn = _synthetic_definition_lookup()
    stats = _synthetic_settlement_oi_panel()
    outright = build_outright_panel(defn, stats)
    seq = symbol_listed_sequence(outright, "CL")
    oi_wide = symbol_oi_wide(outright, "CL", seq)
    front = symbol_front_series(oi_wide, seq)

    # The exact crossover day is already precisely tested at the roll.py unit
    # level (tests/test_roll.py) -- this pipeline-level test only needs to
    # confirm the wiring (oi_wide construction + front-series wrapper) roundtrips
    # correctly: starts at the near contract, ends at the far one, monotonic.
    assert front.iloc[0] == KEY_F1
    assert front.iloc[-1] == KEY_G1
    values = front.tolist()
    first_g1 = values.index(KEY_G1)
    assert all(v == KEY_G1 for v in values[first_g1:])  # monotonic, no roll-back


def test_symbol_oi_wide_and_settle_wide_share_identical_date_index_even_with_asymmetric_nulls():
    """Real-data bug caught on the first Phase 1b run: a date where OI is
    present for a contract but settlement is null for every contract that
    day (or vice versa) can make pivot_table's own row set differ subtly
    between the two panels, silently producing misaligned indices --
    KeyError deep inside held_front_zero_price_guard()/chain_returns()
    when front_series (indexed off oi_wide) is looked up against
    settle_wide. This fixture reproduces that asymmetry directly:
    CLG1 has OI but a null settlement on 2020-01-05, and CLF1 (the only
    other contract) has neither that day either -- so settlement is null
    for every contract on a date OI is not."""
    defn = _synthetic_definition_lookup()
    stats = _synthetic_settlement_oi_panel()
    # blank out settlement (but not OI) for both contracts on one date
    stats.loc[stats["date"] == pd.Timestamp("2020-01-05"), "settlement"] = None
    outright = build_outright_panel(defn, stats)
    seq = symbol_listed_sequence(outright, "CL")

    oi_wide = symbol_oi_wide(outright, "CL", seq)
    settle_wide = symbol_settle_wide(outright, "CL", seq)
    date_index = symbol_date_index(outright, "CL")

    pd.testing.assert_index_equal(oi_wide.index, settle_wide.index)
    pd.testing.assert_index_equal(oi_wide.index, date_index)
    assert pd.Timestamp("2020-01-05") in settle_wide.index  # present as a row...
    assert settle_wide.loc["2020-01-05"].isna().all()        # ...NaN, not dropped

    # and the front series (built off oi_wide) must be safely usable
    # against settle_wide with no KeyError, which is exactly what broke
    # before this fix.
    front = symbol_front_series(oi_wide, seq)
    from src.returns import held_front_zero_price_guard
    violations = held_front_zero_price_guard(settle_wide, front)  # must not raise
    assert violations == []


def test_symbol_settle_wide_matches_input():
    defn = _synthetic_definition_lookup()
    stats = _synthetic_settlement_oi_panel()
    outright = build_outright_panel(defn, stats)
    seq = symbol_listed_sequence(outright, "CL")
    settle_wide = symbol_settle_wide(outright, "CL", seq)
    assert settle_wide.loc["2020-01-01", KEY_F1] == pytest.approx(50.0)
    assert settle_wide.loc["2020-01-01", KEY_G1] == pytest.approx(55.0)


def test_symbol_carry_series_matches_hand_computation_on_a_non_rolled_day():
    defn = _synthetic_definition_lookup()
    stats = _synthetic_settlement_oi_panel()
    outright = build_outright_panel(defn, stats)
    seq = symbol_listed_sequence(outright, "CL")
    oi_wide = symbol_oi_wide(outright, "CL", seq)
    front = symbol_front_series(oi_wide, seq)
    carry = symbol_carry_series(outright, front, seq, "CL")

    # day0: front=CLF1 (50.0, exp 2020-02-01), next=CLG1 (55.0, exp 2020-03-01), D=29 days
    from src.carry import compute_carry
    from datetime import date
    expected = compute_carry(50.0, 55.0, date(2020, 2, 1), date(2020, 3, 1))
    assert carry.iloc[0] == pytest.approx(expected)


def test_symbol_carry_series_nan_when_next_settlement_is_zero_or_negative():
    """Adjudicated 2026-07-11 (DEVIATIONS.md): a next-contract settlement
    <= 0 -- found on the pipeline's first real-data run to be common for
    far-dated, not-yet-actively-traded contracts reported as settlement
    0.00 rather than omitted -- is treated as NaN (not computable),
    symmetric with the pre-existing missing-settlement handling. Also
    proves this does NOT raise/warn (a real divide-by-zero on the first
    real-data run, now guarded)."""
    defn = _synthetic_definition_lookup()
    stats = _synthetic_settlement_oi_panel()
    stats.loc[(stats["date"] == pd.Timestamp("2020-01-01")) & (stats["instrument_id"] == 101), "settlement"] = 0.0
    outright = build_outright_panel(defn, stats)
    seq = symbol_listed_sequence(outright, "CL")
    oi_wide = symbol_oi_wide(outright, "CL", seq)
    front = symbol_front_series(oi_wide, seq)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any RuntimeWarning (e.g. divide by zero) fails this test
        carry = symbol_carry_series(outright, front, seq, "CL")
    assert pd.isna(carry.iloc[0])


def test_symbol_carry_series_nan_when_front_is_last_listed_contract():
    """If front ever becomes the LAST contract in listed_sequence (no next
    contract), carry must be NaN, not an error."""
    defn = _synthetic_definition_lookup()
    stats = _synthetic_settlement_oi_panel()
    outright = build_outright_panel(defn, stats)
    seq = [KEY_G1]  # pretend only one contract is listed
    front = pd.Series([KEY_G1] * 3, index=pd.date_range("2020-01-01", periods=3))
    carry = symbol_carry_series(outright, front, seq, "CL")
    assert carry.isna().all()


def test_symbol_daily_returns_counts_fills_and_detects_guard_violations():
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    settle = pd.DataFrame({KEY_F1: [50.0, None, 51.0, -2.0]}, index=dates)
    front = pd.Series([KEY_F1] * 4, index=dates)
    result = symbol_daily_returns(settle, front, "CL")
    assert result["n_filled"] == 1
    assert len(result["guard_violations"]) == 1
    assert result["guard_violations"][0][2] == pytest.approx(-2.0)
    assert len(result["returns"]) == 3  # chain_returns drops the first row (no t-1)


def test_symbol_daily_returns_passes_symbol_through_for_cost_lookup():
    """_contract_key (instrument_id + expiration) does not start with a
    parseable root-symbol prefix, unlike a raw contract code -- proves
    symbol_daily_returns() supplies the explicit `symbol` chain_returns()
    needs for its Sec 5 cost-table lookup on a roll day, rather than
    relying on chain_returns()'s string-prefix fallback (which would raise
    ValueError on a key in this shape)."""
    dates = pd.date_range("2020-01-01", periods=2, freq="D")
    settle = pd.DataFrame({KEY_F1: [50.0, 51.0], KEY_G1: [55.0, 56.0]}, index=dates)
    front = pd.Series([KEY_F1, KEY_G1], index=dates)  # rolls on day 1
    result = symbol_daily_returns(settle, front, "CL")  # must not raise
    assert len(result["returns"]) == 1


def test_month_end_carry_panel_uses_last_value_on_or_before_month_end():
    dates = pd.date_range("2020-01-01", periods=40, freq="D")
    carry_a = pd.Series(range(40), index=dates, dtype=float)
    panel = month_end_carry_panel({"A": carry_a}, entry_dates={"A": pd.Timestamp("2020-01-01")})
    jan_end = pd.Timestamp("2020-01-31")
    assert jan_end in panel.index
    assert panel.loc[jan_end, "A"] == pytest.approx(30.0)  # index 30 = Jan 31 (day 31 of the series, 0-indexed 30)


def test_month_end_carry_panel_respects_entry_rule_no_backfill():
    dates = pd.date_range("2020-01-01", periods=70, freq="D")
    carry_a = pd.Series(1.0, index=dates)
    late_entry = pd.Timestamp("2020-03-01")
    panel = month_end_carry_panel({"A": carry_a}, entry_dates={"A": late_entry})
    jan_end = pd.Timestamp("2020-01-31")
    assert pd.isna(panel.loc[jan_end, "A"])  # before entry -> NaN despite real underlying data


def test_month_end_next_month_return_panel_compounds_correctly():
    month_ends = pd.DatetimeIndex(["2020-01-31", "2020-02-29", "2020-03-31"])
    daily = pd.Series(
        [0.01, 0.01, -0.02],
        index=pd.DatetimeIndex(["2020-02-10", "2020-02-20", "2020-03-15"]),
    )
    panel = month_end_next_month_return_panel({"A": daily}, month_ends, entry_dates={"A": pd.Timestamp("2020-01-01")})
    # month-end Jan31 -> next-month return = compounded Feb daily returns
    expected_feb = (1.01 * 1.01) - 1.0
    assert panel.loc[pd.Timestamp("2020-01-31"), "A"] == pytest.approx(expected_feb)
    expected_mar = (1 - 0.02) - 1.0
    assert panel.loc[pd.Timestamp("2020-02-29"), "A"] == pytest.approx(expected_mar)
    assert pd.isna(panel.loc[pd.Timestamp("2020-03-31"), "A"])  # no month after the last month-end


def test_month_end_next_month_return_panel_nan_when_no_returns_in_window():
    month_ends = pd.DatetimeIndex(["2020-01-31", "2020-02-29"])
    daily = pd.Series([0.01], index=pd.DatetimeIndex(["2020-01-15"]))  # nothing in Feb
    panel = month_end_next_month_return_panel({"A": daily}, month_ends, entry_dates={"A": pd.Timestamp("2020-01-01")})
    assert pd.isna(panel.loc[pd.Timestamp("2020-01-31"), "A"])


def test_truncation_invariant_carry_panel_matches_full_panel_up_to_cutoff():
    dates = pd.date_range("2020-01-01", periods=200, freq="D")
    carry_a = pd.Series(range(200), index=dates, dtype=float)
    entry = {"A": pd.Timestamp("2020-01-01")}
    full = month_end_carry_panel({"A": carry_a}, entry_dates=entry)
    truncated = truncation_invariant_carry_panel({"A": carry_a}, months_to_truncate=2, entry_dates=entry)
    common_index = truncated.index
    pd.testing.assert_frame_equal(full.loc[common_index], truncated)
