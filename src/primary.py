"""
Phase 1c primary-family backtest orchestration. PREREGISTRATION.md Sec 3
(signal timing), Sec 4 (portfolio construction, vol targeting, leverage),
Sec 5 (cost model).

Wiring only -- every formula and parameter here is already frozen and
tested in src/vol.py, src/portfolio.py, src/costs.py, src/pipeline.py;
this module's only job is to sequence them in the correct temporal order
with no look-ahead, for both H1 (cross-sectional tercile) and H2
(time-series sign) arms. No tunable parameter or threshold is
introduced here: execution_lag takes the two values registered by
preregistration/AMENDMENT_2026-09-27.md.

Signal timing (Sec 3; preregistration/AMENDMENT_2026-09-27.md): a
month-end t's signal (raw +-1/0 tercile-rank or sign(carry)) is converted
to a vol-scaled weight using data available through settle(t). With
`execution_lag=0` -- the registered primary convention -- that weight is
held for the daily window (t, t_next], so the first return it earns is
settle(t) -> settle(t+1): the position is entered at the same settlement
the signal is computed from, the `weights.shift(1)` convention. There is
no full trading day between signal and entry at lag 0. `execution_lag=1`
(a registered sensitivity) shifts the window one trading row later: entry
at settle(t+1), first return settle(t+1) -> settle(t+2). The premise test
uses the same windows (pipeline.month_end_next_month_return_panel()).

Portfolio-level vol targeting (Sec 4) avoids look-ahead by construction:
the pre-leverage GROSS daily portfolio return (weights x cost-free
per-symbol returns) is computed first; its trailing 60-day realized vol
(vol.rolling_volatility), lagged one row, sizes day d's leverage -- never
same-day vol deciding same-day leverage. Costs never feed a vol estimator
(correction, 2026-09-27): before it, rebalance and roll costs were inside
the vol input, so a higher cost table changed the leverage path.

Costs (Sec 5, "every rebalance trade and every roll leg"; correction
2026-09-27): the traded book is the daily levered position p = L x w.
Every change in p -- the monthly rebalance and the daily leverage resize
alike -- is charged |delta p| x cost-per-side, and each roll leg is
charged |p| x the roll cost, so costs are a drag for long and short
positions alike. Before the correction only the monthly pre-leverage
weight change was charged, the daily resize was free, and roll costs,
embedded in the per-symbol return, were credited to short positions.
"""
import pandas as pd

from . import vol as vol_mod
from . import portfolio as portfolio_mod
from .data_loader import live_symbols_at


def symbol_vol_at_month_end(daily_returns: pd.Series, month_end_index: pd.DatetimeIndex) -> pd.Series:
    """Each symbol's own 60-day trailing realized vol (vol.rolling_volatility),
    sampled at the last available date on or before each month-end -- same
    'last value on or before month-end' convention as
    pipeline.month_end_carry_panel(), reused here for consistency."""
    rv = vol_mod.rolling_volatility(daily_returns.sort_index())
    out = {}
    for month in month_end_index:
        eligible = rv.index[rv.index <= month]
        out[month] = rv.at[eligible.max()] if len(eligible) else float("nan")
    return pd.Series(out, dtype=float)


def symbol_settle_at_month_end(front_series: pd.Series, settle_wide: pd.DataFrame,
                                month_end_index: pd.DatetimeIndex) -> pd.Series:
    """Settlement price of whichever contract is front, as of the last
    trading day on or before each month-end -- the price
    portfolio.cost_pct_by_month() uses to convert a position change into
    a percentage cost. Same 'last value on or before month-end' convention
    as symbol_vol_at_month_end() and pipeline.month_end_carry_panel()."""
    out = {}
    for month in month_end_index:
        eligible = front_series.index[front_series.index <= month]
        if len(eligible) == 0:
            out[month] = float("nan")
            continue
        d = eligible.max()
        contract = front_series.at[d]
        out[month] = settle_wide.at[d, contract] if contract in settle_wide.columns else float("nan")
    return pd.Series(out, dtype=float)


def build_pre_leverage_weights(carry_panel: pd.DataFrame, vol_by_symbol_at_month_end: pd.DataFrame,
                                entry_dates: dict, signal_fn) -> pd.DataFrame:
    """
    For each month-end t in carry_panel's index, restricts to the live
    symbols (data_loader.live_symbols_at) with a non-null carry value,
    computes the raw signal via signal_fn (portfolio.xs_raw_signal or
    portfolio.ts_raw_signal) over that live snapshot, then converts each
    live symbol's raw signal to a vol-scaled weight via
    vol.asset_target_weight(), using vol_by_symbol_at_month_end's own value
    at that same month-end t -- legitimate (no look-ahead), since the
    resulting weight is applied only from t's first following trading day
    onward, never on t itself.

    Returns a DataFrame indexed like carry_panel, one column per symbol in
    carry_panel.columns; 0.0 for any non-live symbol, any month with no
    live symbols, or a NaN/non-positive vol (vol.asset_target_weight's own
    guard).
    """
    out = pd.DataFrame(0.0, index=carry_panel.index, columns=carry_panel.columns)
    for month in carry_panel.index:
        live = [s for s in live_symbols_at(month, entry_dates) if s in carry_panel.columns]
        snapshot = carry_panel.loc[month, live].dropna()
        if len(snapshot) == 0:
            continue
        raw_signal = signal_fn(snapshot)
        for symbol in raw_signal.index:
            rv = (vol_by_symbol_at_month_end.at[month, symbol]
                  if symbol in vol_by_symbol_at_month_end.columns and month in vol_by_symbol_at_month_end.index
                  else float("nan"))
            out.at[month, symbol] = vol_mod.asset_target_weight(raw_signal[symbol], rv)
    return out


def _check_lag(execution_lag: int) -> int:
    if int(execution_lag) != execution_lag or execution_lag < 0:
        raise ValueError(f"execution_lag must be a non-negative integer number of trading rows, got {execution_lag!r}")
    return int(execution_lag)


def expand_monthly_to_daily(monthly_df: pd.DataFrame, month_end_index: pd.DatetimeIndex,
                             daily_index: pd.DatetimeIndex, execution_lag: int = 0) -> pd.DataFrame:
    """
    month-end t's row applies to every daily date in (t, t_next] -- the
    day after month-end t through the following month-end inclusive -- so
    with daily returns r(d) = settle(d)/settle(d-1) - 1 the first return a
    month-end-t weight earns is settle(t) -> settle(t+1) (execution at the
    signal's own settlement; module docstring). `execution_lag=k` shifts
    every window k trading rows later: the previous month's row is held k
    more rows and the new row first earns settle(t+k) -> settle(t+k+1).
    The LAST month-end's row applies to every remaining daily date after
    it (a decided position is held until the next rebalance; unlike
    pipeline.month_end_next_month_return_panel, which measures a completed
    month's return and so reports NaN there). Days before the first window
    get 0.0 (no signal established yet).
    """
    lag = _check_lag(execution_lag)
    out = pd.DataFrame(0.0, index=daily_index, columns=monthly_df.columns)
    for i in range(len(month_end_index)):
        t = month_end_index[i]
        if i + 1 < len(month_end_index):
            mask = (daily_index > t) & (daily_index <= month_end_index[i + 1])
        else:
            mask = daily_index > t
        out.loc[mask, :] = monthly_df.loc[t].values
    if lag:
        out = out.shift(lag).fillna(0.0)
    return out


def _returns_matrix(returns_by_symbol: dict, columns, daily_index: pd.DatetimeIndex) -> pd.DataFrame:
    out = pd.DataFrame(index=daily_index, columns=columns, dtype=float)
    for symbol in columns:
        s = returns_by_symbol.get(symbol)
        out[symbol] = s.reindex(daily_index) if s is not None else 0.0
    return out.fillna(0.0)


def compute_arm_daily_returns(pre_leverage_weights_by_month: pd.DataFrame,
                               daily_returns_by_symbol: dict,
                               settle_by_month: pd.DataFrame,
                               month_end_index: pd.DatetimeIndex,
                               daily_index: pd.DatetimeIndex,
                               symbol_of_column: dict = None,
                               cost_multiplier: float = 1.0,
                               gross_returns_by_symbol: dict | None = None,
                               execution_lag: int = 0) -> dict:
    """
    daily_returns_by_symbol : per-symbol daily returns net of roll costs at
        `cost_multiplier` (pipeline.symbol_daily_returns).
    gross_returns_by_symbol : the same series with no roll cost
        (cost_multiplier=0). The per-symbol roll cost is their difference.
        If None, daily_returns_by_symbol is taken to be cost-free.
    execution_lag : 0 = registered primary timing; 1 = registered
        sensitivity (expand_monthly_to_daily).

    Sequence (no look-ahead):
      1. Daily pre-leverage weights w(d) (expand_monthly_to_daily).
      2. Pre-leverage gross return g(d) = sum_i w_i(d) * gross_i(d).
      3. Leverage L(d) = vol.portfolio_leverage_scalar(vol of g through d-1,
         gross exposure sum|w(d)|).
      4. Levered positions p(d) = L(d) * w(d).
      5. Costs: trading_cost(d) = sum_i |p_i(d) - p_i(d-1)| * c_i, with c_i
         the cost per side (costs.cost_per_side_pct at month-end t's front
         settlement, 0 where that price is missing) of the month governing
         day d -- this covers the monthly rebalance and the daily leverage
         resize; roll_cost(d) = sum_i |p_i(d)| * (gross_i(d) - net_i(d)).
      6. Net return = sum_i p_i(d) * gross_i(d) - trading_cost - roll_cost.

    Returns {"daily_net_returns", "daily_gross_returns" (levered, no costs,
    same leverage path), "pre_leverage_returns" (g, the vol input),
    "leverage", "daily_weights", "positions", "trading_cost", "roll_cost",
    "contributions" (per-symbol net contribution, date x symbol)}.
    """
    columns = pre_leverage_weights_by_month.columns
    symbol_of_column = symbol_of_column or {s: s for s in columns}
    lag = _check_lag(execution_lag)

    daily_weights = expand_monthly_to_daily(pre_leverage_weights_by_month, month_end_index, daily_index, lag)
    net_r = _returns_matrix(daily_returns_by_symbol, columns, daily_index)
    gross_r = net_r if gross_returns_by_symbol is None else _returns_matrix(gross_returns_by_symbol, columns, daily_index)
    roll_cost_per_unit = gross_r - net_r

    pre_leverage_returns = (daily_weights * gross_r).sum(axis=1)
    portfolio_vol_lagged = vol_mod.rolling_volatility(pre_leverage_returns).shift(1)

    gross_by_month = pre_leverage_weights_by_month.abs().sum(axis=1)
    gross_daily = expand_monthly_to_daily(gross_by_month.to_frame("gross"), month_end_index, daily_index, lag)["gross"]
    leverage = pd.Series(
        [vol_mod.portfolio_leverage_scalar(portfolio_vol_lagged.at[d], gross_daily.at[d]) for d in daily_index],
        index=daily_index,
    )
    positions = daily_weights.mul(leverage, axis=0)

    settle = settle_by_month.reindex(index=pre_leverage_weights_by_month.index, columns=columns)
    cost_pct_by_month = portfolio_mod.cost_pct_by_month(settle, symbol_of_column, cost_multiplier)
    cost_pct_daily = expand_monthly_to_daily(cost_pct_by_month, month_end_index, daily_index, lag)

    traded = (positions - positions.shift(1).fillna(0.0)).abs()
    trading_cost_by_symbol = traded * cost_pct_daily
    roll_cost_by_symbol = positions.abs() * roll_cost_per_unit
    gross_pnl_by_symbol = positions * gross_r
    contributions = gross_pnl_by_symbol - trading_cost_by_symbol - roll_cost_by_symbol

    return {
        "daily_net_returns": contributions.sum(axis=1),
        "daily_gross_returns": gross_pnl_by_symbol.sum(axis=1),
        "pre_leverage_returns": pre_leverage_returns,
        "leverage": leverage,
        "daily_weights": daily_weights,
        "positions": positions,
        "trading_cost": trading_cost_by_symbol.sum(axis=1),
        "roll_cost": roll_cost_by_symbol.sum(axis=1),
        "contributions": contributions,
    }
