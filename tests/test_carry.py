"""Tests for src/carry.py against hand-computed values, including the
365/D annualization -- all synthetic, per Phase 1a Hard Rule 1."""
from datetime import date

import pandas as pd
import pytest

from src.carry import compute_carry, compute_carry_series


def test_carry_hand_computed_backwardation():
    # front=105, next=100, D=91 days (a quarterly gap)
    # carry = (105-100)/100 * 365/91 = 0.05 * 4.010989... = 0.2005494...
    front_expiry = date(2020, 1, 1)
    next_expiry = date(2020, 4, 1)  # 91 days later
    d = (next_expiry - front_expiry).days
    assert d == 91
    expected = 0.05 * 365.0 / 91.0
    got = compute_carry(105.0, 100.0, front_expiry, next_expiry)
    assert got == pytest.approx(expected, rel=1e-12)
    assert got == pytest.approx(0.2005494505494505, rel=1e-9)
    assert got > 0  # backwardation: front > next -> positive carry


def test_carry_hand_computed_contango():
    # front=95, next=100, D=30 days
    # carry = (95-100)/100 * 365/30 = -0.05 * 12.1666... = -0.60833...
    front_expiry = date(2020, 1, 1)
    next_expiry = date(2020, 1, 31)  # 30 days later
    got = compute_carry(95.0, 100.0, front_expiry, next_expiry)
    expected = -0.05 * 365.0 / 30.0
    assert got == pytest.approx(expected, rel=1e-12)
    assert got < 0  # contango: front < next -> negative carry


def test_carry_zero_when_front_equals_next():
    front_expiry = date(2020, 1, 1)
    next_expiry = date(2020, 6, 1)
    got = compute_carry(100.0, 100.0, front_expiry, next_expiry)
    assert got == pytest.approx(0.0, abs=1e-12)


def test_carry_raises_on_non_positive_d():
    # next_expiry must be strictly after front_expiry
    with pytest.raises(ValueError):
        compute_carry(105.0, 100.0, date(2020, 6, 1), date(2020, 1, 1))
    with pytest.raises(ValueError):
        compute_carry(105.0, 100.0, date(2020, 1, 1), date(2020, 1, 1))  # D=0


def test_carry_series_matches_scalar_hand_computation():
    front_expiry = date(2020, 1, 1)
    next_expiry = date(2020, 4, 1)  # D=91
    front = pd.Series([105.0, 110.0, 95.0])
    next_ = pd.Series([100.0, 100.0, 100.0])
    got = compute_carry_series(front, next_, front_expiry, next_expiry)
    expected = pd.Series([
        compute_carry(105.0, 100.0, front_expiry, next_expiry),
        compute_carry(110.0, 100.0, front_expiry, next_expiry),
        compute_carry(95.0, 100.0, front_expiry, next_expiry),
    ])
    pd.testing.assert_series_equal(got, expected)
