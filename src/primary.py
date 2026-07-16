"""
Phase 1c primary-family backtest orchestration. PREREGISTRATION.md Sec 3
(signal timing), Sec 4 (portfolio construction, vol targeting, leverage),
Sec 5 (cost model).

Wiring only -- every formula and parameter here is already frozen and
tested in src/vol.py, src/portfolio.py, src/costs.py, src/pipeline.py;
this module's only job is to sequence them in the correct temporal order
with no look-ahead, for both H1 (cross-sectional tercile) and H2
(time-series sign) arms. No new parameter, threshold, or formula is
introduced anywhere in this file.

Signal timing (Sec 3): a month-end t's signal (raw +-1/0 tercile-rank or
sign(carry)) is converted to a vol-scaled weight using data available
THROUGH month-end t only (no look-ahead), and that weight is HELD for the
daily window (t, t_next] -- the day after month-end t through the
following month-end inclusive -- exactly the same "next month" window
pipeline.month_end_next_month_return_panel() already uses for the premise
test, reused here for consistency rather than re-derived.

Portfolio-level vol targeting (Sec 4) avoids look-ahead by construction:
the "pre-leverage" (unlevered, per-asset-vol-scaled-only) daily portfolio
return series is computed FIRST; ITS OWN trailing 60-day realized vol
(vol.rolling_volatility) is computed on THAT series; the leverage scalar
applied to day d's return uses the trailing vol AS OF d-1 (a 1-day lag,
exactly the same shift(1) look-ahead-safety discipline already used
throughout this project's roll rule and carry-next selection) -- never
same-day vol deciding same-day leverage.

Per-asset vol sizing reuses each symbol's own daily net return series
(pipeline.symbol_daily_returns' "returns" output, already roll-cost-
charged) for BOTH the vol estimate and the realized P&L -- this is the
only per-symbol daily return series this codebase builds; introducing a
separate cost-free series solely for vol estimation would be a new design
choice, not wiring.
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
    portfolio.apply_rebalance_costs() needs to convert a weight change into
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


def expand_monthly_to_daily(monthly_df: pd.DataFrame, month_end_index: pd.DatetimeIndex,
                             daily_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Same windowing convention as pipeline.month_end_next_month_return_panel:
    month-end t's row applies to every daily date in (t, t_next] -- the day
    after month-end t (the execution day, Sec 3: "first trading day of
    month t+1") through the following month-end inclusive. The LAST
    month-end's row applies to every remaining daily date after it through
    the end of daily_index (a decided position is held going forward until
    the next rebalance; there being no next month-end yet is a property of
    the sample's end, not a reason for the position to vanish -- unlike
    pipeline.month_end_next_month_return_panel, which reports NaN for "no
    month after the last month-end" because THAT function measures a
    completed month's realized return, not a held position). Days on or
    before month_end_index[0] get 0.0 (no signal has ever been established
    yet).
    """
    out = pd.DataFrame(0.0, index=daily_index, columns=monthly_df.columns)
    for i in range(len(month_end_index)):
        t = month_end_index[i]
        if i + 1 < len(month_end_index):
            mask = (daily_index > t) & (daily_index <= month_end_index[i + 1])
        else:
            mask = daily_index > t
        out.loc[mask, :] = monthly_df.loc[t].values
    return out


def compute_arm_daily_returns(pre_leverage_weights_by_month: pd.DataFrame,
                               daily_returns_by_symbol: dict,
                               settle_by_month: pd.DataFrame,
                               month_end_index: pd.DatetimeIndex,
                               daily_index: pd.DatetimeIndex,
                               symbol_of_column: dict = None,
                               cost_multiplier: float = 1.0) -> dict:
    """
    Sequences, in strict temporal/no-look-ahead order:
      1. Daily pre-leverage weights (expand_monthly_to_daily).
      2. Daily pre-leverage GROSS portfolio return: sum_i weight_i(d) *
         symbol_i's own already-roll-cost-charged daily return(d)
         (pipeline.symbol_daily_returns' "returns" series), MINUS that
         month's rebalance cost (portfolio.apply_rebalance_costs), charged
         once on the FIRST day of each (t, t_next] window (the execution
         day a real rebalance trade actually happens).
      3. That pre-leverage return series' own trailing 60-day realized vol
         (vol.rolling_volatility), LAGGED BY ONE DAY (shift(1)) before
         being used to size day d's leverage -- day d's leverage is
         decided using vol computed only through d-1, never same-day.
      4. Daily leverage scalar (vol.portfolio_leverage_scalar), using that
         lagged vol and the CURRENT month's pre-leverage gross exposure
         (sum of |pre-leverage weights| for whichever month-end governs
         day d).
      5. Final daily net return = leverage(d) * pre_leverage_return(d).

    Returns {"daily_net_returns", "pre_leverage_returns", "leverage",
    "daily_weights", "rebalance_cost"} -- all pd.Series/DataFrame indexed
    like daily_index (rebalance_cost is the daily-placed version, non-zero
    only on each window's first day).
    """
    symbol_of_column = symbol_of_column or {s: s for s in pre_leverage_weights_by_month.columns}

    daily_weights = expand_monthly_to_daily(pre_leverage_weights_by_month, month_end_index, daily_index)

    returns_matrix = pd.DataFrame(index=daily_index, columns=pre_leverage_weights_by_month.columns, dtype=float)
    for symbol in pre_leverage_weights_by_month.columns:
        s = daily_returns_by_symbol.get(symbol)
        returns_matrix[symbol] = s.reindex(daily_index) if s is not None else 0.0
    returns_matrix = returns_matrix.fillna(0.0)

    gross_pre_cost = (daily_weights * returns_matrix).sum(axis=1)

    rebalance_cost_monthly = portfolio_mod.apply_rebalance_costs(
        pre_leverage_weights_by_month, settle_by_month, symbol_of_column, cost_multiplier)

    rebalance_cost_daily = pd.Series(0.0, index=daily_index)
    for i in range(len(month_end_index)):
        t = month_end_index[i]
        if i + 1 < len(month_end_index):
            window = daily_index[(daily_index > t) & (daily_index <= month_end_index[i + 1])]
        else:
            window = daily_index[daily_index > t]
        if len(window) == 0:
            continue
        rebalance_cost_daily.at[window[0]] = rebalance_cost_monthly.at[t]

    pre_leverage_returns = gross_pre_cost - rebalance_cost_daily

    portfolio_vol_lagged = vol_mod.rolling_volatility(pre_leverage_returns).shift(1)

    gross_by_month = pre_leverage_weights_by_month.abs().sum(axis=1)
    gross_daily = expand_monthly_to_daily(gross_by_month.to_frame("gross"), month_end_index, daily_index)["gross"]

    leverage = pd.Series(
        [vol_mod.portfolio_leverage_scalar(portfolio_vol_lagged.at[d], gross_daily.at[d]) for d in daily_index],
        index=daily_index,
    )

    daily_net_returns = leverage * pre_leverage_returns

    return {
        "daily_net_returns": daily_net_returns,
        "pre_leverage_returns": pre_leverage_returns,
        "leverage": leverage,
        "daily_weights": daily_weights,
        "rebalance_cost": rebalance_cost_daily,
    }
