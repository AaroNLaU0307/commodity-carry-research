"""Tests for src/stats.py -- bootstrap/DSR/BH-FDR sanity on synthetic
series with known properties -- all synthetic, per Phase 1a Hard Rule 1."""
import numpy as np
import pytest

from src import config
from src.stats import (
    stationary_bootstrap_sharpe,
    stationary_bootstrap_multi_seed,
    deflated_sharpe_ratio,
    benjamini_hochberg,
    newey_west_tstat,
    clustered_regression,
)


def test_bootstrap_ci_contains_true_sharpe_for_known_iid_series():
    """A series constructed with a KNOWN true Sharpe (via known mean/std)
    should produce a bootstrap CI that contains that true value, and a
    point estimate in its rough neighborhood -- Sharpe estimates carry
    substantial sampling noise even at n=1500 daily observations (~6 years),
    so this checks the CI-containment property (the meaningful guarantee)
    rather than a tight point-estimate tolerance, which would be flaky by
    construction."""
    rng = np.random.default_rng(123)
    n = 1500
    daily_mean = 0.0008
    daily_std = 0.01
    true_annual_sharpe = daily_mean / daily_std * np.sqrt(config.TRADING_DAYS_PER_YEAR)
    x = rng.normal(daily_mean, daily_std, n)

    result = stationary_bootstrap_sharpe(x, n_replications=2000)  # fewer reps for test speed
    assert result["ci_low"] < true_annual_sharpe < result["ci_high"]
    assert result["point_estimate"] == pytest.approx(true_annual_sharpe, rel=0.30)


def test_bootstrap_ci_excludes_zero_for_strong_signal():
    rng = np.random.default_rng(7)
    x = rng.normal(0.002, 0.01, 1000)  # strong positive drift relative to vol
    result = stationary_bootstrap_sharpe(x, n_replications=2000)
    assert result["excludes_zero"] is True
    assert result["ci_low"] > 0


def test_bootstrap_ci_does_not_exclude_zero_for_pure_noise():
    rng = np.random.default_rng(99)
    x = rng.normal(0.0, 0.01, 500)  # zero true mean
    result = stationary_bootstrap_sharpe(x, n_replications=2000)
    assert result["excludes_zero"] is False


def test_bootstrap_multi_seed_returns_three_seeds_recorded_individually():
    rng = np.random.default_rng(1)
    x = rng.normal(0.001, 0.01, 300)
    results = stationary_bootstrap_multi_seed(x, n_replications=500)
    assert len(results) == 3
    assert [r["seed"] for r in results] == list(config.BOOTSTRAP_SEEDS)
    # different seeds should not all produce bit-identical distributions
    assert not np.array_equal(results[0]["bootstrap_distribution"], results[1]["bootstrap_distribution"])


def test_bootstrap_is_reproducible_given_same_seed():
    rng = np.random.default_rng(2)
    x = rng.normal(0.001, 0.01, 300)
    r1 = stationary_bootstrap_sharpe(x, seed=7, n_replications=500)
    r2 = stationary_bootstrap_sharpe(x, seed=7, n_replications=500)
    np.testing.assert_array_equal(r1["bootstrap_distribution"], r2["bootstrap_distribution"])


def test_dsr_increases_with_higher_observed_sharpe():
    dsr_low = deflated_sharpe_ratio(observed_sharpe=0.3, n_trials=config.N_TRIALS, n_obs=1000)
    dsr_high = deflated_sharpe_ratio(observed_sharpe=1.5, n_trials=config.N_TRIALS, n_obs=1000)
    assert dsr_high > dsr_low


def test_dsr_decreases_as_n_trials_increases_holding_sharpe_fixed():
    """More independent trials -> harder to be confident a given Sharpe
    isn't just the best-of-many-tries -- this monotonicity is the whole
    point of the N_trials-aware deflation. Uses a moderate observed_sharpe
    (0.6, not 1.0+) and n_obs=500 so the comparison sits away from the
    DSR's [0, 1] ceiling/floor, where a real difference would otherwise be
    invisible regardless of whether the deflation logic is correct."""
    dsr_1_trial = deflated_sharpe_ratio(observed_sharpe=0.6, n_trials=1, n_obs=500)
    dsr_14_trials = deflated_sharpe_ratio(observed_sharpe=0.6, n_trials=config.N_TRIALS, n_obs=500)
    dsr_100_trials = deflated_sharpe_ratio(observed_sharpe=0.6, n_trials=100, n_obs=500)
    assert dsr_1_trial > dsr_14_trials > dsr_100_trials


def test_dsr_at_n_trials_14_is_between_zero_and_one():
    dsr = deflated_sharpe_ratio(observed_sharpe=1.0, n_trials=config.N_TRIALS, n_obs=1000)
    assert 0.0 <= dsr <= 1.0


def test_bh_fdr_known_example():
    # p=[0.01, 0.03, 0.04, 0.20], q=0.10, m=4
    # thresholds (sorted order): 0.025, 0.05, 0.075, 0.10
    # 0.01<=0.025 T, 0.03<=0.05 T, 0.04<=0.075 T, 0.20<=0.10 F -> reject first 3 (sorted)
    p_values = [0.01, 0.20, 0.03, 0.04]  # deliberately out of sorted order
    reject = benjamini_hochberg(p_values, q=0.10)
    assert reject == [True, False, True, True]


def test_bh_fdr_at_m_2_matches_this_study_primary_family_size():
    # H1, H2 -- Sec 6: m=2, q=0.10. Both significant.
    reject_both = benjamini_hochberg([0.01, 0.02], q=0.10)
    assert reject_both == [True, True]
    # Neither significant.
    reject_neither = benjamini_hochberg([0.5, 0.6], q=0.10)
    assert reject_neither == [False, False]


def test_bh_fdr_no_rejections_when_all_p_values_fail():
    reject = benjamini_hochberg([0.5, 0.9, 0.3], q=0.10)
    assert reject == [False, False, False]


def test_newey_west_tstat_significant_for_strong_mean():
    rng = np.random.default_rng(5)
    x = rng.normal(0.01, 0.02, 500)  # mean clearly away from zero relative to noise
    result = newey_west_tstat(x)
    assert abs(result["tstat"]) > 2  # roughly significant at conventional levels
    assert result["mean"] == pytest.approx(x.mean(), rel=1e-6)


def test_newey_west_tstat_insignificant_for_zero_mean_noise():
    rng = np.random.default_rng(6)
    x = rng.normal(0.0, 0.02, 500)
    result = newey_west_tstat(x)
    assert abs(result["tstat"]) < 3  # should not spuriously blow up


def test_clustered_regression_recovers_known_slope():
    rng = np.random.default_rng(11)
    n_months, n_per_month = 60, 18
    months = np.repeat(np.arange(n_months), n_per_month)
    x = rng.normal(0, 1, n_months * n_per_month)
    true_slope = 0.5
    noise = rng.normal(0, 0.1, n_months * n_per_month)
    y = true_slope * x + noise
    result = clustered_regression(y, x, months)
    assert result["slope"] == pytest.approx(true_slope, abs=0.05)
    assert result["slope_pvalue"] < 0.05
