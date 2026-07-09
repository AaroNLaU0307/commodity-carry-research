"""Tests for src/returns.py -- roll-day cost charging and truncation
invariance -- all synthetic, per Phase 1a Hard Rule 1."""
import pandas as pd
import pytest

from src.costs import cost_per_side_pct
from src.returns import chain_returns


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
