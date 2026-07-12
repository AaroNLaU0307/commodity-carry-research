"""Tests for src/returns.py -- roll-day cost charging and truncation
invariance -- all synthetic, per Phase 1a Hard Rule 1."""
import pandas as pd
import pytest

from src.costs import cost_per_side_pct
from src.returns import (
    chain_returns, fill_missing_settlement_mark_to_last,
    count_held_front_missing_settlement, held_front_zero_price_guard,
)


def _fixture(n_days=6):
    dates = pd.date_range("2020-01-01", periods=n_days, freq="D")
    # Two CL contract months: "CLF20" (front through day3), "CLG20" (front from day4).
    settle = pd.DataFrame(
        {
            "CLF20": [100.0, 101.0, 102.0, 103.0, None, None],
            "CLG20": [None, None, None, 104.0, 105.0, 106.0],
        },
        index=dates,
    )
    # front rolls from CLF20 to CLG20 on day3 (index 3)
    front = pd.Series(["CLF20", "CLF20", "CLF20", "CLG20", "CLG20", "CLG20"], index=dates)
    return dates, settle, front


def test_non_roll_day_return_is_plain_pct_change():
    dates, settle, front = _fixture()
    r = chain_returns(settle, front)
    # day1 vs day0: both CLF20, no roll -> plain pct change, no cost
    expected_day1 = 101.0 / 100.0 - 1.0
    assert r.iloc[0] == pytest.approx(expected_day1)
    # day2 vs day1: both CLF20, no roll
    expected_day2 = 102.0 / 101.0 - 1.0
    assert r.iloc[1] == pytest.approx(expected_day2)


def test_roll_day_charges_round_trip_cost():
    dates, settle, front = _fixture()
    r = chain_returns(settle, front)
    # day3 vs day2: front switches CLF20 -> CLG20. Price return is computed
    # off the OLD (yesterday's) held contract CLF20: 103/102 - 1, then a
    # round-trip cost (close CLF20 leg + open CLG20 leg) is subtracted.
    gross = 103.0 / 102.0 - 1.0
    cost_close = cost_per_side_pct("CL", 102.0)  # CLF20's settle the day before roll
    cost_open = cost_per_side_pct("CL", 103.0)   # CLG20 opened at the roll day's settle
    expected = gross - (cost_close + cost_open)
    assert r.iloc[2] == pytest.approx(expected)


def test_post_roll_day_is_plain_pct_change_on_new_contract():
    dates, settle, front = _fixture()
    r = chain_returns(settle, front)
    # day4 vs day3: both CLG20, no roll
    expected = 105.0 / 104.0 - 1.0
    assert r.iloc[3] == pytest.approx(expected)


def test_truncation_invariance_appending_future_rows_does_not_change_past_signals():
    dates, settle, front = _fixture(n_days=6)
    r_full = chain_returns(settle, front)

    # Truncate to the first 4 rows (through the roll day) and recompute.
    settle_trunc = settle.iloc[:4]
    front_trunc = front.iloc[:4]
    r_trunc = chain_returns(settle_trunc, front_trunc)

    # Every return computed from the truncated series must match the
    # corresponding return from the full series -- appending future rows
    # must not have altered anything through the truncation point.
    pd.testing.assert_series_equal(r_trunc, r_full.iloc[: len(r_trunc)])


def test_2x_cost_multiplier_doubles_roll_day_cost_only():
    dates, settle, front = _fixture()
    r1 = chain_returns(settle, front, cost_multiplier=1.0)
    r2 = chain_returns(settle, front, cost_multiplier=2.0)
    gross_roll_day = 103.0 / 102.0 - 1.0
    cost1 = gross_roll_day - r1.iloc[2]
    cost2 = gross_roll_day - r2.iloc[2]
    assert cost2 == pytest.approx(2 * cost1)
    # non-roll days are identical regardless of cost_multiplier (no cost charged)
    assert r1.iloc[0] == pytest.approx(r2.iloc[0])


def _missing_settlement_fixture():
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    # day2 (index 2) has a missing settlement for CLF20 -- a genuine gap
    # mid-series, not a leading pre-existence NaN.
    settle = pd.DataFrame({"CLF20": [100.0, 101.0, None, 103.0, 104.0]}, index=dates)
    return dates, settle


def test_fill_missing_settlement_marks_forward_from_last_real_value():
    dates, settle = _missing_settlement_fixture()
    filled, mask = fill_missing_settlement_mark_to_last(settle)
    assert filled.at[dates[2], "CLF20"] == pytest.approx(101.0)  # carried from day1
    assert filled.at[dates[3], "CLF20"] == pytest.approx(103.0)  # day3's own real value untouched


def test_fill_missing_settlement_occurrence_mask_flags_only_the_filled_cell():
    dates, settle = _missing_settlement_fixture()
    filled, mask = fill_missing_settlement_mark_to_last(settle)
    assert mask.at[dates[2], "CLF20"] == True
    for d in [dates[0], dates[1], dates[3], dates[4]]:
        assert mask.at[d, "CLF20"] == False


def test_fill_missing_settlement_leading_nan_not_counted_as_filled():
    """A contract's leading NaNs (before its first real settlement -- e.g. a
    not-yet-listed or not-yet-live contract in a wider panel) must NOT be
    flagged as a missing-settlement occurrence -- that's the entry rule's
    concern (data_loader.apply_entry_rule), not this function's."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    settle = pd.DataFrame({"CLG20": [None, None, 50.0, 51.0]}, index=dates)
    filled, mask = fill_missing_settlement_mark_to_last(settle)
    assert mask.at[dates[0], "CLG20"] == False
    assert mask.at[dates[1], "CLG20"] == False
    assert filled.at[dates[0], "CLG20"] != filled.at[dates[0], "CLG20"]  # still NaN (NaN != NaN)


def test_filled_settlement_produces_zero_return_through_chain_returns():
    """The point of mark-to-last: feeding the filled panel into
    chain_returns() must yield exactly a 0.0 return on the filled day,
    with no special-casing inside chain_returns() itself."""
    dates, settle = _missing_settlement_fixture()
    filled, mask = fill_missing_settlement_mark_to_last(settle)
    front = pd.Series(["CLF20"] * 5, index=dates)
    r = chain_returns(filled, front)
    # r.iloc[1] is day2 vs day1 (both = 101.0 after fill) -> zero return
    assert r.iloc[1] == pytest.approx(0.0)


def test_zero_price_guard_fires_on_nonpositive_held_front_settlement():
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    settle = pd.DataFrame({"CLF20": [100.0, -5.0, 101.0]}, index=dates)
    front = pd.Series(["CLF20", "CLF20", "CLF20"], index=dates)
    violations = held_front_zero_price_guard(settle, front)
    assert len(violations) == 1
    assert violations[0][0] == dates[1]
    assert violations[0][1] == "CLF20"
    assert violations[0][2] == pytest.approx(-5.0)


def test_zero_price_guard_fires_on_exact_zero_too():
    dates = pd.date_range("2020-01-01", periods=2, freq="D")
    settle = pd.DataFrame({"CLF20": [100.0, 0.0]}, index=dates)
    front = pd.Series(["CLF20", "CLF20"], index=dates)
    violations = held_front_zero_price_guard(settle, front)
    assert len(violations) == 1


def test_zero_price_guard_silent_when_all_held_front_prices_positive():
    dates, settle = _missing_settlement_fixture()
    front = pd.Series(["CLF20"] * 5, index=dates)
    violations = held_front_zero_price_guard(settle, front)
    assert violations == []


def test_count_held_front_missing_settlement_ignores_non_front_columns():
    """The bug this function exists to fix: a wide panel with a second,
    never-held column that has its OWN missing values must not inflate the
    count -- only cells chain_returns() actually reads (the held-yesterday
    contract's price on date t) count as an occurrence."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    settle = pd.DataFrame(
        {
            "CLF1__100": [100.0, 101.0, None, 103.0, 104.0],  # front throughout, 1 real gap (day2)
            "CLG1__101": [None, None, None, None, None],       # never held, entirely missing -- must not count
        },
        index=dates,
    )
    front = pd.Series(["CLF1__100"] * 5, index=dates)
    n = count_held_front_missing_settlement(settle, front)
    assert n == 1  # only day2's front-column gap, not CLG1's 5 unrelated missing cells


def test_count_held_front_missing_settlement_matches_whole_panel_mask_for_single_column():
    """Sanity check against the older whole-panel mask sum: for a
    single-contract panel (no other columns to over-count), the two
    methods must agree exactly."""
    dates, settle = _missing_settlement_fixture()
    front = pd.Series(["CLF20"] * 5, index=dates)
    _, mask = fill_missing_settlement_mark_to_last(settle)
    assert count_held_front_missing_settlement(settle, front) == int(mask.to_numpy().sum())


def test_count_held_front_missing_settlement_zero_when_no_gaps():
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    settle = pd.DataFrame({"CLF1__100": [100.0, 101.0, 102.0, 103.0]}, index=dates)
    front = pd.Series(["CLF1__100"] * 4, index=dates)
    assert count_held_front_missing_settlement(settle, front) == 0


def test_count_held_front_missing_settlement_counts_across_a_roll():
    """held_yesterday is what chain_returns() actually reads for BOTH
    price_t and price_t_minus_1 -- a gap in the NEW contract's price
    immediately after a roll is not counted until IT becomes
    held_yesterday on a later iteration."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    settle = pd.DataFrame(
        {"CLF1__100": [100.0, 101.0, 102.0, None], "CLG1__101": [None, None, 200.0, None]},
        index=dates,
    )
    front = pd.Series(["CLF1__100", "CLF1__100", "CLG1__101", "CLG1__101"], index=dates)
    # i=1: held_yesterday=CLF1, settle[day1,CLF1]=101.0 present -> no count
    # i=2: held_yesterday=CLF1 (front on day1), settle[day2,CLF1]=102.0 present -> no count
    # i=3: held_yesterday=CLG1 (front on day2), settle[day3,CLG1]=None -> counted
    assert count_held_front_missing_settlement(settle, front) == 1


def test_zero_price_guard_ignores_non_front_negative_prices():
    """A negative settlement on a contract that is NOT the held front that
    day (e.g. F2's actual CLK0 case) must not trip the guard -- it only
    ever looks at the settlement of whichever contract front_series says
    is held on that specific date."""
    dates = pd.date_range("2020-01-01", periods=2, freq="D")
    settle = pd.DataFrame({"CLF20": [100.0, 101.0], "CLG20": [50.0, -10.0]}, index=dates)
    front = pd.Series(["CLF20", "CLF20"], index=dates)  # CLG20 never held
    violations = held_front_zero_price_guard(settle, front)
    assert violations == []
