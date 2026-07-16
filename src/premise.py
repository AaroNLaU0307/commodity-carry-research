"""
Premise test. PREREGISTRATION.md Sec 7 ("Premise test (Phase 1 gate,
before any portfolio backtest)").

XS premise: monthly cross-sectional Spearman rank IC between carry_i(t)
and symbol i's next-month excess return; report the mean IC with a
Newey-West-adjusted t-statistic. NW lag fixed at 3 (Phase 1b Step 0
specification completion, DEVIATIONS.md 2026-07-11 -- Sec 7 specifies the
NW adjustment but not its lag order).

TS premise: pooled panel regression of next-month excess return on
sign(carry_i(t)), standard errors clustered by month.

Gate (Sec 7, mechanical): if an arm's premise point estimate is <= 0, that
arm closes at the premise stage -- no portfolio backtest is run for it. A
positive-but-insignificant estimate is NOT a gate failure -- it proceeds to
Phase 1c, where the bootstrap (Sec 6) is the primary evidence, not this
test. Both results are reported in full regardless of outcome -- a closed
arm is reported as closed with its point estimate, never omitted.
"""
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from .stats import newey_west_tstat, clustered_regression

XS_PREMISE_NW_LAGS = 3  # Phase 1b Step 0 specification completion, DEVIATIONS.md 2026-07-11


def monthly_spearman_ic(carry_panel: pd.DataFrame, next_return_panel: pd.DataFrame) -> pd.Series:
    """
    carry_panel, next_return_panel : DataFrames indexed by the SAME
    month-end date, one column per symbol. Both panels are aligned by the
    caller before this function sees them: the row at month-end t in
    next_return_panel must already be that symbol's excess return realized
    OVER the following month (t -> t+1) -- this function performs no
    shifting itself, so the carry(t)-vs-return(t+1) relationship being
    tested is explicit and independently checkable in the panels
    themselves, not hidden inside this function.

    Returns a pd.Series indexed by month-end date, one Spearman rank
    correlation per month, computed only over symbols with a non-null
    value in both panels that month (Sec 2's entry rule already governs
    which symbols are live; this function just needs a complete pair to
    rank). A month with fewer than 3 such symbols is skipped -- a rank
    correlation over 1-2 points is not meaningful.
    """
    ics = {}
    for month in carry_panel.index:
        if month not in next_return_panel.index:
            continue
        c = carry_panel.loc[month]
        r = next_return_panel.loc[month]
        both = pd.DataFrame({"carry": c, "ret": r}).dropna()
        if len(both) < 3:
            continue
        ic, _ = scipy_stats.spearmanr(both["carry"], both["ret"])
        if pd.notna(ic):
            ics[month] = ic
    return pd.Series(ics, dtype=float).sort_index()


def xs_premise_test(carry_panel: pd.DataFrame, next_return_panel: pd.DataFrame, nw_lags: int = None) -> dict:
    """Sec 7 XS premise. Returns mean IC, NW(nw_lags) t-stat/p-value,
    months used, and the mechanical gate verdict (mean IC > 0)."""
    nw_lags = XS_PREMISE_NW_LAGS if nw_lags is None else nw_lags
    ic_series = monthly_spearman_ic(carry_panel, next_return_panel)
    if len(ic_series) < 2:
        raise ValueError(f"Only {len(ic_series)} usable month(s) for the XS premise IC series -- cannot proceed.")
    nw = newey_west_tstat(ic_series.values, lags=nw_lags)
    return {
        "mean_ic": nw["mean"],
        "tstat": nw["tstat"],
        "pvalue": nw["pvalue"],
        "n_months": len(ic_series),
        "nw_lags": nw_lags,
        "gate_passes": bool(nw["mean"] > 0),
        "ic_series": ic_series,
    }


def ts_premise_test(carry_panel: pd.DataFrame, next_return_panel: pd.DataFrame) -> dict:
    """Sec 7 TS premise. Pools every (symbol, month) observation with a
    non-null carry and next-month return into one panel regression of
    return on sign(carry), SEs clustered by month. Returns the slope
    coefficient, clustered t-stat/p-value, N, and the mechanical gate
    verdict (slope > 0)."""
    rows_y, rows_x, rows_month = [], [], []
    for month in carry_panel.index:
        if month not in next_return_panel.index:
            continue
        c = carry_panel.loc[month]
        r = next_return_panel.loc[month]
        both = pd.DataFrame({"carry": c, "ret": r}).dropna()
        for _, row in both.iterrows():
            sign = 1.0 if row["carry"] > 0 else (-1.0 if row["carry"] < 0 else 0.0)
            rows_y.append(row["ret"])
            rows_x.append(sign)
            rows_month.append(month)

    if len(rows_y) < 2:
        raise ValueError(f"Only {len(rows_y)} usable (symbol, month) observation(s) for the TS premise -- cannot proceed.")

    y = np.array(rows_y, dtype=float)
    x = np.array(rows_x, dtype=float)
    cluster_ids = np.array(rows_month)
    result = clustered_regression(y, x, cluster_ids)
    return {
        "coefficient": result["slope"],
        "tstat": result["slope_tstat"],
        "pvalue": result["slope_pvalue"],
        "n_obs": len(y),
        "gate_passes": bool(result["slope"] > 0),
    }
