"""Tests for src/premise.py -- XS/TS premise tests against synthetic
panels with known, constructed carry/return relationships -- all
synthetic, per Hard Rule 1 (no real data in this session's premise-test
code until the real-data pipeline itself, exercised only via the runner
script, never in the automated suite)."""
import numpy as np
import pandas as pd
import pytest

from src.premise import monthly_spearman_ic, xs_premise_test, ts_premise_test


def _months(n):
    return pd.date_range("2015-01-31", periods=n, freq="ME")


def _constant_ranking_carry_panel(months):
    """Every month, A<B<C<D<E in carry value -- a fixed cross-sectional
    ranking repeated across all months, the simplest fixture for testing
    a per-month rank correlation."""
    symbols = ["A", "B", "C", "D", "E"]
    row = [1.0, 2.0, 3.0, 4.0, 5.0]
    data = {s: [row[i]] * len(months) for i, s in enumerate(symbols)}
    return pd.DataFrame(data, index=months)


def test_monthly_spearman_ic_perfect_positive_relationship():
    months = _months(6)
    carry = _constant_ranking_carry_panel(months)
    # next-month return exactly ranks the same as carry every month -> IC = 1.0
    ret = carry.copy()
    ic = monthly_spearman_ic(carry, ret)
    assert len(ic) == len(months)
    assert np.allclose(ic.values, 1.0)


def test_monthly_spearman_ic_perfect_negative_relationship():
    months = _months(6)
    carry = _constant_ranking_carry_panel(months)
    ret = -carry  # exactly inverse rank -> IC = -1.0
    ic = monthly_spearman_ic(carry, ret)
    assert np.allclose(ic.values, -1.0)


def test_monthly_spearman_ic_skips_months_with_fewer_than_3_symbols():
    months = _months(3)
    carry = pd.DataFrame({"A": [1, 1, 1], "B": [2, 2, 2]}, index=months)  # only 2 symbols
    ret = pd.DataFrame({"A": [1, 1, 1], "B": [2, 2, 2]}, index=months)
    ic = monthly_spearman_ic(carry, ret)
    assert len(ic) == 0  # every month has only 2 usable symbols -> all skipped


def test_monthly_spearman_ic_only_uses_months_present_in_both_panels():
    months = _months(4)
    carry = pd.DataFrame({"A": [1, 2, 3], "B": [3, 2, 1], "C": [2, 1, 3]}, index=months[:3])
    ret = pd.DataFrame({"A": [1, 2, 3], "B": [3, 2, 1], "C": [2, 1, 3]}, index=months[1:])
    ic = monthly_spearman_ic(carry, ret)
    # only months[1], months[2] are present in both
    assert set(ic.index) == {months[1], months[2]}


def test_xs_premise_gate_passes_for_positive_relationship():
    months = _months(24)
    symbols = ["A", "B", "C", "D", "E", "F"]
    rng = np.random.default_rng(1)
    carry = pd.DataFrame(rng.normal(0, 1, (len(months), len(symbols))), index=months, columns=symbols)
    # next-month return is a monotone (rank-preserving) function of carry, same sign each month
    ret = carry.rank(axis=1)
    result = xs_premise_test(carry, ret)
    assert result["gate_passes"] is True
    assert result["mean_ic"] > 0
    assert result["nw_lags"] == 3
    assert result["n_months"] == len(months)


def test_xs_premise_gate_fails_for_negative_relationship():
    months = _months(24)
    symbols = ["A", "B", "C", "D", "E", "F"]
    rng = np.random.default_rng(2)
    carry = pd.DataFrame(rng.normal(0, 1, (len(months), len(symbols))), index=months, columns=symbols)
    ret = -carry.rank(axis=1)  # inverse relationship every month
    result = xs_premise_test(carry, ret)
    assert result["gate_passes"] is False
    assert result["mean_ic"] < 0


def test_xs_premise_uses_declared_nw_lag_by_default():
    months = _months(10)
    symbols = ["A", "B", "C", "D"]
    rng = np.random.default_rng(3)
    carry = pd.DataFrame(rng.normal(0, 1, (len(months), len(symbols))), index=months, columns=symbols)
    ret = carry.copy()
    result = xs_premise_test(carry, ret)
    assert result["nw_lags"] == 3
    result_custom = xs_premise_test(carry, ret, nw_lags=5)
    assert result_custom["nw_lags"] == 5


def test_xs_premise_raises_on_too_few_usable_months():
    months = _months(1)
    carry = pd.DataFrame({"A": [1], "B": [2], "C": [3]}, index=months)
    ret = carry.copy()
    with pytest.raises(ValueError):
        xs_premise_test(carry, ret)


def test_ts_premise_gate_passes_for_positive_relationship():
    months = _months(30)
    symbols = ["A", "B", "C", "D", "E"]
    rng = np.random.default_rng(4)
    carry_vals = rng.choice([-1.0, 1.0], size=(len(months), len(symbols)))
    carry = pd.DataFrame(carry_vals, index=months, columns=symbols)
    # return = +k when carry>0, -k when carry<0 (deterministic, k>0) -> slope should be ~k, clearly positive
    k = 0.05
    ret = carry.apply(lambda col: col * k)  # sign(carry)*k exactly since carry is already +-1
    result = ts_premise_test(carry, ret)
    assert result["gate_passes"] is True
    assert result["coefficient"] == pytest.approx(k, rel=0.05)
    assert result["n_obs"] == len(months) * len(symbols)


def test_ts_premise_gate_fails_for_negative_relationship():
    months = _months(30)
    symbols = ["A", "B", "C", "D", "E"]
    rng = np.random.default_rng(5)
    carry_vals = rng.choice([-1.0, 1.0], size=(len(months), len(symbols)))
    carry = pd.DataFrame(carry_vals, index=months, columns=symbols)
    k = -0.05
    ret = carry.apply(lambda col: col * k)
    result = ts_premise_test(carry, ret)
    assert result["gate_passes"] is False
    assert result["coefficient"] == pytest.approx(k, rel=0.05)


def test_ts_premise_zero_carry_maps_to_sign_zero():
    months = _months(6)
    carry = pd.DataFrame({"A": [0.0] * 6, "B": [1.0] * 6, "C": [-1.0] * 6}, index=months)
    ret = pd.DataFrame({"A": [0.5] * 6, "B": [1.0] * 6, "C": [-1.0] * 6}, index=months)
    result = ts_premise_test(carry, ret)
    # A's sign(carry)=0 contributes x=0 rows -- just confirm this runs and N counts all rows
    assert result["n_obs"] == 18


def test_ts_premise_raises_on_too_few_usable_observations():
    months = _months(1)
    carry = pd.DataFrame({"A": [1.0]}, index=months)
    ret = pd.DataFrame({"A": [1.0]}, index=months)
    with pytest.raises(ValueError):
        ts_premise_test(carry, ret)
