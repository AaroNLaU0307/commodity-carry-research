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

Rebalance-trade cost (as distinct from roll-leg cost in returns.py): charged
on the CHANGE in a symbol's portfolio weight at each monthly rebalance,
using costs.cost_per_side_pct() -- the same primitive returns.py uses for
roll legs, applied here to portfolio weight deltas instead of contract
switches.
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


def apply_rebalance_costs(weights_by_month: pd.DataFrame, settle_by_month: pd.DataFrame,
                           symbol_of_column: dict, cost_multiplier: float = 1.0) -> pd.Series:
    """
    weights_by_month : DataFrame indexed by month-end date, one column per
        symbol, values = portfolio weight established for the following
        month (already vol-scaled -- this function only prices the trade
        needed to MOVE from last month's weight to this month's).
    settle_by_month : DataFrame, same shape, the settlement price used to
        convert a weight change into a percentage cost via
        costs.cost_per_side_pct() (which needs a price and a symbol).
    symbol_of_column : maps each column name to its cost-table root symbol
        (usually the identity mapping if columns are already root symbols).

    Returns a pd.Series of monthly rebalance cost (as a return drag, i.e. a
    positive number to be SUBTRACTED from that month's gross return),
    indexed like weights_by_month.
    """
    weights_prev = weights_by_month.shift(1).fillna(0.0)
    delta = (weights_by_month - weights_prev).abs()

    cost = pd.Series(0.0, index=weights_by_month.index)
    for month in weights_by_month.index:
        total = 0.0
        for col in weights_by_month.columns:
            d = delta.at[month, col]
            if d == 0:
                continue
            price = settle_by_month.at[month, col]
            if pd.isna(price):
                continue
            symbol = symbol_of_column.get(col, col)
            total += d * costs.cost_per_side_pct(symbol, price, cost_multiplier)
        cost.at[month] = total
    return cost
