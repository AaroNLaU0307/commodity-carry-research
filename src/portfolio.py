"""
Portfolio construction. PREREGISTRATION.md Sec 4.

H1 (cross-sectional): rank the live cross-section by carry each month-end.
Long the top tercile, short the bottom tercile, n_leg = round(N/3) per leg.
Within each leg, weight constituents inversely to individual volatility
(vol.py). Scale to the portfolio-level volatility target.

H2 (time-series): position_i = sign(carry_i(t)) per symbol, vol-scaled,
aggregated equal-risk, scaled to the portfolio-level volatility target.

Symbol entry rule (Sec 2): a symbol enters at the first month-end its carry
signal is computable -- no backfill before that date, no exclusion after.
This module takes the live cross-section as given (already filtered by the
caller / data_loader.py's entry-rule logic) rather than re-deriving entry
dates itself, so that the entry rule has exactly one implementation.

Trading cost (as distinct from roll-leg cost in returns.py):
cost_pct_by_month() prices one unit of position change per symbol with
costs.cost_per_side_pct() -- the same primitive returns.py uses for roll
legs; primary.compute_arm_daily_returns() applies it to every daily change
in the levered position (monthly rebalance and daily leverage resize).
"""
import pandas as pd

from . import costs


def n_leg(n_live: int) -> int:
    """Sec 4: n_leg = round(N/3). Python's round() uses banker's rounding
    (round-half-to-even), which matters at exact .5 boundaries -- verified
    against the pre-registration's own worked examples (N=17 -> 6, N=18 -> 6)
    in tests/test_portfolio.py, not merely assumed to match."""
    return round(n_live / 3)


def xs_raw_signal(carry_snapshot: pd.Series) -> pd.Series:
    """Sec 4 H1: rank the live cross-section by carry; +1 for the top
    tercile, -1 for the bottom tercile, 0 for the middle. `carry_snapshot`
    must already be restricted to the live (entered) symbols for this
    month -- see module docstring."""
    n_live = len(carry_snapshot)
    leg = n_leg(n_live)
    ranked = carry_snapshot.sort_values(ascending=False)
    signal = pd.Series(0, index=carry_snapshot.index, dtype=float)
    signal.loc[ranked.index[:leg]] = 1.0
    signal.loc[ranked.index[-leg:]] = -1.0
    return signal


def ts_raw_signal(carry_snapshot: pd.Series) -> pd.Series:
    """Sec 4 H2: position_i = sign(carry_i(t)) for every live symbol."""
    return carry_snapshot.apply(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0))


def cost_pct_by_month(settle_by_month: pd.DataFrame, symbol_of_column: dict,
                      cost_multiplier: float = 1.0) -> pd.DataFrame:
    """
    settle_by_month : DataFrame indexed by month-end date, one column per
        symbol, values = the front settlement at that month-end.
    symbol_of_column : maps each column to its cost-table root symbol.

    Returns a same-shaped DataFrame of cost per side as a fraction of
    notional (costs.cost_per_side_pct) -- the cost of trading one unit of
    weight in that symbol during the month that month-end governs. 0.0
    where the settlement is missing (no price to convert with), as before.
    """
    out = pd.DataFrame(0.0, index=settle_by_month.index, columns=settle_by_month.columns)
    for col in settle_by_month.columns:
        symbol = symbol_of_column.get(col, col)
        for month in settle_by_month.index:
            price = settle_by_month.at[month, col]
            if pd.notna(price):
                out.at[month, col] = costs.cost_per_side_pct(symbol, price, cost_multiplier)
    return out
