"""
Statistical inference utilities. PREREGISTRATION.md Sec 6 (primary
inference + promotion gate), Sec 7 (premise test), Sec 10 (N_trials).

- Stationary block bootstrap for the primary Sharpe CI (Sec 6): expected
  block length 21 trading days, 10,000 replications, 3 recorded seeds --
  affirmed as the primary inference method (advisor ruling, 2026-07-10,
  WORKSPACE/PREREG_OPEN_ITEMS.md item 1), not a fallback. Politis-Romano
  (1994) construction: block lengths are themselves random, geometrically
  distributed with mean = expected_block_length, and the resample wraps
  circularly so the result is genuinely stationary (no edge effects from a
  fixed tiling).
- Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014), gated at >= 0.95
  with N_trials = config.N_TRIALS (= 14, Sec 10's frozen computation
  ledger) -- never a locally recomputed trial count.
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


def deflated_sharpe_ratio(observed_sharpe: float, n_trials: int, n_obs: int,
                           skew: float = 0.0, excess_kurtosis: float = 0.0,
                           periods_per_year: int = None,
                           sharpe_std_across_trials: float = None) -> float:
    """
    Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio". Deflates an
    observed Sharpe for (a) the number of independent trials that could have
    produced it (n_trials -- here always config.N_TRIALS=14, Sec 10) and
    (b) the non-normality of returns (skew, excess kurtosis), then returns
    the probability the TRUE Sharpe exceeds the expected maximum spurious
    Sharpe under the null, as a one-sided p-value-like quantity in [0, 1].
    Gate: DSR >= 0.95 (Sec 6).

    `observed_sharpe` is taken to be ANNUALIZED (matching every other
    Sharpe in this codebase). The classic SE formula below is defined for
    the PER-PERIOD Sharpe estimator, so observed_sharpe is converted down to
    per-period terms to compute the standard error, then that SE is scaled
    back up to annualized terms (SE_annual = SE_period * sqrt(periods_per_
    year)) so it stays on the same scale as observed_sharpe and
    expected_max_sharpe. Skipping this conversion silently mixes an
    annualized Sharpe with a per-period SE, which inflates (SR - E[max])/SE
    by ~sqrt(periods_per_year) and saturates the CDF at 1.0 regardless of
    n_trials -- caught by test_dsr_decreases_as_n_trials_increases_holding_
    sharpe_fixed during Phase 1a engine testing, not shipped silently.

    sharpe_std_across_trials: if not supplied, approximated as the same
    (annualized) standard error above -- a standard simplification when the
    per-trial Sharpe variance across the N_trials population isn't itself
    estimated (documented here rather than silently assumed).
    """
    periods_per_year = config.TRADING_DAYS_PER_YEAR if periods_per_year is None else periods_per_year
    euler_mascheroni = 0.5772156649015329

    sr_period = observed_sharpe / np.sqrt(periods_per_year)
    se_period = np.sqrt((1 - skew * sr_period + (excess_kurtosis / 4.0) * sr_period ** 2) / (n_obs - 1))
    se = se_period * np.sqrt(periods_per_year)

    if se <= 0:
        return 0.0

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
