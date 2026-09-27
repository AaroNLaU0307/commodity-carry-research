"""
Statistical inference utilities. PREREGISTRATION.md Sec 6 (primary
inference + promotion gate), Sec 7 (premise test), Sec 10 (N_trials).

Provenance: written in this repository (commodity-carry-research); not
vendored from another repo. BH-FDR default level q = 0.10
(config.BH_FDR_Q). Sharpe CI method: Politis-Romano stationary bootstrap,
geometric blocks with mean 21 trading days, circular wrap, 10,000
replications, 95% percentile interval, seeds (7, 13, 31). The source of
every function below is pinned by sha256 in
tests/test_stats_provenance.py: any edit must update that pin in the same
commit, with the reason in the commit message.

- Stationary block bootstrap for the primary Sharpe CI (Sec 6): expected
  block length 21 trading days, 10,000 replications, 3 recorded seeds --
  affirmed as the primary inference method (advisor ruling, 2026-07-10),
  not a fallback. Block lengths are geometric with mean
  expected_block_length and the resample wraps circularly, so the result
  is stationary (no edge effects from a fixed tiling).
- Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014), gated at >= 0.95
  with N_trials = config.N_TRIALS. The study passes the sample skewness
  and excess kurtosis of the daily net returns and the empirical standard
  deviation of the registered trial Sharpes (correction, 2026-09-27;
  reports/ADDENDUM_2026-09-27.md). dsr_sharpe_threshold() gives the Sharpe
  a series would need to clear the gate.
- Benjamini-Hochberg FDR control at q = 0.10 (Sec 6), applied across the
  m=2 primary family {H1, H2}.
- Newey-West HAC t-statistic and cluster-robust (by month) regression SEs
  for the Sec 7 premise tests, built on statsmodels' tested implementations
  rather than hand-rolled HAC/cluster machinery.
"""
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
import statsmodels.api as sm

from . import config


def stationary_bootstrap_sharpe(daily_net_returns: np.ndarray,
                                 expected_block_length: int = None,
                                 n_replications: int = None,
                                 seed: int = None,
                                 ci_level: float = None) -> dict:
    """Sec 6 primary inference. Returns point estimate, CI bounds, and the
    full resampled distribution (for diagnostics / DSR skew-kurtosis input)."""
    expected_block_length = config.BOOTSTRAP_EXPECTED_BLOCK_LENGTH if expected_block_length is None else expected_block_length
    n_replications = config.BOOTSTRAP_N_REPLICATIONS if n_replications is None else n_replications
    ci_level = config.BOOTSTRAP_CI_LEVEL if ci_level is None else ci_level
    seed = config.BOOTSTRAP_SEEDS[0] if seed is None else seed

    x = np.asarray(daily_net_returns, dtype=float)
    n = len(x)
    if n < 2:
        raise ValueError("need at least 2 observations for a bootstrap")

    rng = np.random.default_rng(seed)
    p_restart = 1.0 / expected_block_length
    ann = np.sqrt(config.TRADING_DAYS_PER_YEAR)

    sharpes = np.empty(n_replications)
    idx = np.empty(n, dtype=np.int64)
    for b in range(n_replications):
        idx[0] = rng.integers(0, n)
        restarts = rng.random(n) < p_restart
        for i in range(1, n):
            if restarts[i]:
                idx[i] = rng.integers(0, n)
            else:
                idx[i] = (idx[i - 1] + 1) % n  # circular wrap -> stationary, no edge bias
        sample = x[idx]
        sigma = sample.std(ddof=1)
        sharpes[b] = (sample.mean() / sigma * ann) if sigma > 0 else 0.0

    point_sigma = x.std(ddof=1)
    point = (x.mean() / point_sigma * ann) if point_sigma > 0 else 0.0
    alpha = 1 - ci_level
    lo = np.percentile(sharpes, 100 * alpha / 2)
    hi = np.percentile(sharpes, 100 * (1 - alpha / 2))
    return {
        "point_estimate": point,
        "ci_low": lo,
        "ci_high": hi,
        "excludes_zero": bool((lo > 0) or (hi < 0)),
        "n_replications": n_replications,
        "expected_block_length": expected_block_length,
        "seed": seed,
        "bootstrap_distribution": sharpes,
    }


def stationary_bootstrap_multi_seed(daily_net_returns: np.ndarray,
                                     seeds: tuple = None, **kwargs) -> list:
    """Runs stationary_bootstrap_sharpe once per recorded seed (Sec 6: "the
    3 seeds and their outcomes will be individually recorded"). Returns a
    list of the 3 individual result dicts -- callers report all 3, not just
    an average."""
    seeds = config.BOOTSTRAP_SEEDS if seeds is None else seeds
    return [stationary_bootstrap_sharpe(daily_net_returns, seed=s, **kwargs) for s in seeds]


def sample_moments(daily_returns) -> dict:
    """Sample skewness and excess kurtosis (Fisher, 0 for a normal) of a
    daily return series, NaNs dropped -- the non-normality inputs to
    deflated_sharpe_ratio()."""
    x = np.asarray(daily_returns, dtype=float)
    x = x[~np.isnan(x)]
    return {"skew": float(scipy_stats.skew(x)), "excess_kurtosis": float(scipy_stats.kurtosis(x, fisher=True))}


def trial_sharpe_std(trial_sharpes) -> float:
    """Empirical standard deviation (ddof=1) of the annualized Sharpes of
    every registered trial series -- the cross-trial dispersion input to
    deflated_sharpe_ratio()."""
    x = np.asarray(list(trial_sharpes), dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        raise ValueError("need at least 2 trial Sharpes to estimate their dispersion")
    return float(x.std(ddof=1))


def deflated_sharpe_ratio(observed_sharpe: float, n_trials: int, n_obs: int,
                           skew: float = 0.0, excess_kurtosis: float = 0.0,
                           periods_per_year: int = None,
                           sharpe_std_across_trials: float = None) -> float:
    """
    Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio": the
    probability that the true Sharpe exceeds the expected maximum Sharpe of
    n_trials unskilled trials, given the observed Sharpe's standard error
    under the return distribution's skew and kurtosis. Gate: DSR >= 0.95
    (Sec 6).

    `observed_sharpe` is ANNUALIZED (as every Sharpe in this codebase). The
    standard error is defined for the per-period Sharpe SR_p:
        SE_p = sqrt((1 - skew * SR_p + (excess_kurtosis + 2) / 4 * SR_p**2) / (n_obs - 1))
    ((gamma4 - 1)/4 with gamma4 = excess_kurtosis + 3), then scaled back to
    annual terms (x sqrt(periods_per_year)) so it is on the same scale as
    observed_sharpe and the expected maximum (skipping the conversion
    saturates the CDF regardless of n_trials).

    sharpe_std_across_trials: the empirical dispersion of the trial Sharpes
    (trial_sharpe_std()). If omitted it falls back to the observed Sharpe's
    own SE -- the assumption behind the DSRs published before 2026-09-27,
    which also passed skew = excess_kurtosis = 0.
    """
    periods_per_year = config.TRADING_DAYS_PER_YEAR if periods_per_year is None else periods_per_year
    euler_mascheroni = 0.5772156649015329

    sr_period = observed_sharpe / np.sqrt(periods_per_year)
    variance_term = 1 - skew * sr_period + ((excess_kurtosis + 2.0) / 4.0) * sr_period ** 2
    if variance_term <= 0:
        return 0.0
    se = np.sqrt(variance_term / (n_obs - 1)) * np.sqrt(periods_per_year)

    if sharpe_std_across_trials is None:
        sharpe_std_across_trials = se

    if n_trials <= 1:
        expected_max_sharpe = 0.0
    else:
        z1 = scipy_stats.norm.ppf(1 - 1.0 / n_trials)
        z2 = scipy_stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
        expected_max_sharpe = sharpe_std_across_trials * (
            (1 - euler_mascheroni) * z1 + euler_mascheroni * z2
        )

    return float(scipy_stats.norm.cdf((observed_sharpe - expected_max_sharpe) / se))


def dsr_sharpe_threshold(n_trials: int, n_obs: int, skew: float = 0.0, excess_kurtosis: float = 0.0,
                          periods_per_year: int | None = None, sharpe_std_across_trials: float | None = None,
                          gate: float | None = None) -> float:
    """The smallest annualized Sharpe whose deflated_sharpe_ratio() reaches
    `gate` (default config.DSR_GATE_MIN) under the same inputs -- what the
    DSR gate actually demands at this sample size and trial count. NaN if
    no Sharpe up to 20 reaches it."""
    from itertools import pairwise

    from scipy.optimize import brentq
    gate = config.DSR_GATE_MIN if gate is None else gate

    def gap(sr):
        return deflated_sharpe_ratio(sr, n_trials, n_obs, skew, excess_kurtosis, periods_per_year,
                                     sharpe_std_across_trials) - gate

    grid = np.linspace(0.0, 20.0, 2001)
    for lo, hi in pairwise(grid):
        if gap(lo) < 0 <= gap(hi):
            return float(brentq(gap, lo, hi, xtol=1e-10))
    return float("nan")


def benjamini_hochberg(p_values: list, q: float = None) -> list:
    """Sec 6: BH-FDR at q=0.10. Returns a list of booleans (True = rejected,
    i.e. passes FDR control), same order as the input p_values."""
    q = config.BH_FDR_Q if q is None else q
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    if m == 0:
        return []
    order = np.argsort(p)
    ranked = p[order]
    thresholds = (np.arange(1, m + 1) / m) * q
    passed = ranked <= thresholds
    reject_sorted = np.zeros(m, dtype=bool)
    if passed.any():
        max_i = np.max(np.where(passed)[0])
        reject_sorted[: max_i + 1] = True
    result = np.zeros(m, dtype=bool)
    result[order] = reject_sorted
    return result.tolist()


def newey_west_tstat(x: np.ndarray, lags: int = None) -> dict:
    """Sec 7 XS premise: t-stat of the mean of x under a Newey-West HAC
    standard error. Implemented as OLS of x on a constant with
    cov_type='HAC' (statsmodels), which is the standard way to get a HAC
    mean/t-stat rather than hand-rolling the long-run-variance estimator."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if lags is None:
        lags = int(np.floor(4 * (n / 100) ** (2 / 9)))  # Newey-West (1994) plug-in rule
    model = sm.OLS(x, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"mean": float(model.params[0]), "tstat": float(model.tvalues[0]),
            "pvalue": float(model.pvalues[0]), "lags": lags}


def clustered_regression(y: np.ndarray, x: np.ndarray, cluster_ids: np.ndarray) -> dict:
    """Sec 7 TS premise: pooled panel regression of next-month excess return
    on sign(carry), SEs clustered by month. y, x are 1-D arrays (pooled
    across symbols and months); cluster_ids identifies the month each
    observation belongs to."""
    y = np.asarray(y, dtype=float)
    x_design = sm.add_constant(np.asarray(x, dtype=float))
    model = sm.OLS(y, x_design).fit(cov_type="cluster", cov_kwds={"groups": np.asarray(cluster_ids)})
    return {
        "intercept": float(model.params[0]), "slope": float(model.params[1]),
        "slope_tstat": float(model.tvalues[1]), "slope_pvalue": float(model.pvalues[1]),
    }
