"""Tests for src/roll.py -- all on synthetic fixtures, per Phase 1a Hard Rule 1."""
import pandas as pd

from src.roll import compute_front_contract_series


def test_roll_uses_strictly_t_minus_1_oi_not_same_day():
    """Fixture where SAME-DAY OI would already show c2 > c1 on day T, but
    T-1's OI does not yet show the crossover. Correct (look-ahead-safe)
    behavior: front stays c1 through day T, rolls to c2 only on T+1 (using
    T's OI, now available as T+1's t-1)."""
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 80, 75],   # day0=T-1: 100, day1=T: 80, day2=T+1: 75
            "c2": [90, 95, 98],    # day0=T-1: 90,  day1=T: 95, day2=T+1: 98
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2"])

    # Day0 (T-1): no t-1 data at all (nothing before it) -> stays at initial front c1.
    assert front.iloc[0] == "c1"
    # Day1 (T): t-1 OI is day0's (c1=100 > c2=90) -> still c1. A same-day-OI
    # implementation would incorrectly roll here, since day1's OWN OI already
    # has c2=95 > c1=80.
    assert front.iloc[1] == "c1"
    # Day2 (T+1): t-1 OI is day1's (c1=80 < c2=95) -> NOW rolls to c2.
    assert front.iloc[2] == "c2"


def test_roll_is_monotonic_no_roll_back_on_oscillating_oi():
    """Once front has moved from c1 to c2, OI later favoring c1 again must
    NOT roll it back."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 80, 120, 130, 140],  # c1 OI recovers above c2 at day3-4
            "c2": [90, 95, 90, 85, 80],
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2"])

    assert front.iloc[0] == "c1"
    assert front.iloc[1] == "c1"   # t-1 (day0) still favors c1
    assert front.iloc[2] == "c2"   # t-1 (day1): c2=95 > c1=80 -> rolled
    # From here on, even though c1's OI recovers above c2's, front must stay c2.
    assert front.iloc[3] == "c2"
    assert front.iloc[4] == "c2"


def test_roll_truncation_invariance_future_oi_rows_do_not_change_past_front():
    """Appending future rows must leave every already-computed front-contract
    decision unchanged -- the state machine only ever looks at t-1, never
    forward, so truncating (or extending) the series should not alter the
    front assignment for any date already covered."""
    dates = pd.date_range("2020-01-01", periods=6, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 80, 60, 40, 20, 10],
            "c2": [90, 95, 96, 97, 98, 99],
        },
        index=dates,
    )
    front_full = compute_front_contract_series(oi, ["c1", "c2"])

    front_truncated = compute_front_contract_series(oi.iloc[:3], ["c1", "c2"])
    pd.testing.assert_series_equal(front_truncated, front_full.iloc[:3])


def test_roll_with_three_contracts_advances_at_most_one_step_per_date():
    """A crossover skipping straight from c1 to c3 in one day (c2 never
    briefly leads) should still land on c2 first if c2's t-1 OI already
    exceeds c1's, then progress to c3 only once c3's t-1 OI exceeds c2's on
    a later date -- the state machine must not skip a contract."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 50, 40, 30],
            "c2": [90, 95, 96, 20],
            "c3": [10, 15, 97, 98],
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2", "c3"])
    assert front.iloc[0] == "c1"
    assert front.iloc[1] == "c1"   # t-1 (day0): c1=100 still > c2=90
    assert front.iloc[2] == "c2"   # t-1 (day1): c2=95 > c1=50 -> roll to c2 (not c3)
    assert front.iloc[3] == "c3"   # t-1 (day2): c3=97 > c2=96 -> roll to c3
