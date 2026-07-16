"""
Tests for src/primary.py -- the Phase 1c orchestration layer. All synthetic,
per Hard Rule 4 (tests before real data). Since every underlying formula
(vol.rolling_volatility, vol.asset_target_weight, vol.portfolio_leverage_scalar,
costs.cost_per_side_pct, portfolio.xs_raw_signal/ts_raw_signal/apply_rebalance_costs)
is already independently tested elsewhere, these tests focus on what's NEW
here: correct temporal sequencing (no look-ahead), correct live-universe
handling per month, and correct aggregation -- verified by calling the same
underlying primitives directly as an oracle, not by re-deriving their
formulas symbolically.
"""
import numpy as np
import pandas as pd
import pytest

from src import config, vol as vol_mod, costs
from src.portfolio import xs_raw_signal, ts_raw_signal
from src.primary import (
    symbol_vol_at_month_end, symbol_settle_at_month_end,
    build_pre_leverage_weights, expand_monthly_to_daily, compute_arm_daily_returns,
)


def test_tercile_split_respects_per_month_live_universe_17_then_18():
    """The orchestration-specific behavior under test: a symbol that enters
    mid-panel (17 live -> 18 live, e.g. KE's real entry) must be excluded
    from the signal entirely at the month it is not yet live, and included
    as a normal candidate the month it is. n_leg(17)==n_leg(18)==6 (both
    round to 6, already proven in test_portfolio.py) so this test is
    NOT about leg-size arithmetic -- it is about whether
    build_pre_leverage_weights actually consults live_symbols_at() per
    month rather than using a fixed universe."""
    months = pd.DatetimeIndex(["2020-01-31", "2020-02-29"])
    seventeen = [f"S{i}" for i in range(17)]
    new_symbol = "NEW"
    all_cols = seventeen + [new_symbol]

    carry_panel = pd.DataFrame(0.0, index=months, columns=all_cols)
    # spread distinct carry values across the 17 so tercile membership is unambiguous
    for i, s in enumerate(seventeen):
        carry_panel.loc[:, s] = float(i) - 8.0  # -8..+8, distinct values
    carry_panel.loc[months[1], new_symbol] = 100.0  # unambiguously top-tercile once live
    carry_panel.loc[months[0], new_symbol] = float("nan")  # not yet live

    entry_dates = {s: pd.Timestamp("2019-01-01") for s in seventeen}
    entry_dates[new_symbol] = pd.Timestamp("2020-02-01")  # enters between month0 and month1

    vol_flat = pd.DataFrame(0.10, index=months, columns=all_cols)  # constant vol -> isolates the signal/live-set logic

    weights = build_pre_leverage_weights(carry_panel, vol_flat, entry_dates, xs_raw_signal)

    assert weights.at[months[0], new_symbol] == 0.0  # not live -> never a candidate
    assert weights.at[months[1], new_symbol] != 0.0  # live, unambiguously top carry -> nonzero weight
    assert weights.at[months[1], new_symbol] > 0  # top tercile -> long


def test_inverse_vol_leg_weights():
    """Within a leg (both symbols top-tercile here), weights must be in
    INVERSE proportion to realized vol -- calls vol.asset_target_weight()
    directly as the oracle for what the ratio must be, rather than
    asserting a hand-derived numeric ratio."""
    months = pd.DatetimeIndex(["2020-01-31"])
    # n_leg(6)=2 -> a 2-wide leg, so A and B can both land in the top leg
    cols = ["A", "B", "C", "D", "E", "F"]
    carry_panel = pd.DataFrame({"A": [10.0], "B": [9.0], "C": [1.0], "D": [-1.0], "E": [-9.0], "F": [-10.0]}, index=months)
    vol_panel = pd.DataFrame({"A": [0.20], "B": [0.40], "C": [0.10], "D": [0.10], "E": [0.10], "F": [0.10]}, index=months)
    entry_dates = {s: pd.Timestamp("2019-01-01") for s in cols}

    weights = build_pre_leverage_weights(carry_panel, vol_panel, entry_dates, xs_raw_signal)

    # A and B are both in the top leg (n_leg(6)=2) -> both signal=+1
    expected_a = vol_mod.asset_target_weight(1.0, 0.20)
    expected_b = vol_mod.asset_target_weight(1.0, 0.40)
    assert weights.at[months[0], "A"] == pytest.approx(expected_a)
    assert weights.at[months[0], "B"] == pytest.approx(expected_b)
    # B has double A's vol -> half A's weight (inverse-vol scaling)
    assert weights.at[months[0], "B"] == pytest.approx(weights.at[months[0], "A"] / 2.0)


def test_vol_targeting_scalar_and_gross_cap_behavior():
    """Direct check of compute_arm_daily_returns' leverage sequencing: (a)
    in the normal (uncapped) regime, leverage * gross must equal
    target_vol / realized_vol * gross exactly as
    vol.portfolio_leverage_scalar() itself would compute; (b) when that
    would push gross above MAX_GROSS_LEVERAGE, leverage must be capped so
    leveraged gross == MAX_GROSS_LEVERAGE exactly, never more."""
    n = 70  # > 60-day vol window, so leverage is defined by the tail of the series
    daily_index = pd.date_range("2020-01-01", periods=n, freq="D")
    month_end_index = pd.DatetimeIndex([daily_index[59], daily_index[-1]])

    # single symbol, constant weight, an alternating return series so realized
    # vol is nonzero and directly computable via vol.rolling_volatility itself
    sym_returns = pd.Series([0.001 if i % 2 == 0 else -0.001 for i in range(n)], index=daily_index)
    weights_by_month = pd.DataFrame({"A": [1.0, 1.0]}, index=month_end_index)
    settle_by_month = pd.DataFrame({"A": [100.0, 100.0]}, index=month_end_index)

    result = compute_arm_daily_returns(
        weights_by_month, {"A": sym_returns}, settle_by_month, month_end_index, daily_index,
        symbol_of_column={"A": "CL"},
    )
    pre_lev = result["pre_leverage_returns"]
    expected_vol_lagged = vol_mod.rolling_volatility(pre_lev).shift(1)
    gross_daily = expand_monthly_to_daily(
        weights_by_month.abs().sum(axis=1).to_frame("gross"), month_end_index, daily_index)["gross"]

    for d in daily_index[61:]:  # skip the NaN ramp-up window
        expected_leverage = vol_mod.portfolio_leverage_scalar(expected_vol_lagged.at[d], gross_daily.at[d])
        assert result["leverage"].at[d] == pytest.approx(expected_leverage)
        assert result["daily_net_returns"].at[d] == pytest.approx(expected_leverage * pre_lev.at[d])

    # gross cap: gross=10 with realistic vol would demand far more leverage
    # than MAX_GROSS_LEVERAGE allows
    weights_hi_gross = pd.DataFrame({"A": [10.0, 10.0]}, index=month_end_index)
    result_capped = compute_arm_daily_returns(
        weights_hi_gross, {"A": sym_returns}, settle_by_month, month_end_index, daily_index,
        symbol_of_column={"A": "CL"},
    )
    for d in daily_index[61:]:
        lev = result_capped["leverage"].at[d]
        if lev > 0:
            assert lev * 10.0 <= config.MAX_GROSS_LEVERAGE + 1e-9


def test_cost_charged_on_scripted_rebalance_only_on_execution_day():
    """Rebalance cost (weight CHANGE month-to-month) must appear exactly
    once, on the first daily date of the new window (the execution day),
    matching costs.cost_per_side_pct() exactly -- zero on every other day,
    including the month-end signal date itself."""
    daily_index = pd.date_range("2020-01-01", periods=65, freq="D")
    month_end_index = pd.DatetimeIndex([daily_index[29], daily_index[59]])
    weights_by_month = pd.DataFrame({"A": [1.0, -1.0]}, index=month_end_index)  # full flip, delta=2.0
    settle_by_month = pd.DataFrame({"A": [80.0, 82.0]}, index=month_end_index)
    zero_returns = pd.Series(0.0, index=daily_index)

    result = compute_arm_daily_returns(
        weights_by_month, {"A": zero_returns}, settle_by_month, month_end_index, daily_index,
        symbol_of_column={"A": "CL"},
    )
    execution_day_1 = daily_index[daily_index > month_end_index[0]][0]
    execution_day_2 = daily_index[daily_index > month_end_index[1]][0]

    # month-end 1: weight moves 0 -> 1.0 (delta=1.0)
    expected_cost_1 = 1.0 * costs.cost_per_side_pct("CL", 80.0)
    assert result["rebalance_cost"].at[execution_day_1] == pytest.approx(expected_cost_1)
    # month-end 2: weight moves 1.0 -> -1.0 (delta=2.0)
    expected_cost_2 = 2.0 * costs.cost_per_side_pct("CL", 82.0)
    assert result["rebalance_cost"].at[execution_day_2] == pytest.approx(expected_cost_2)

    assert result["rebalance_cost"].at[month_end_index[0]] == 0.0  # not on the signal date itself
    non_execution_days = [d for d in daily_index if d not in (execution_day_1, execution_day_2)]
    assert all(result["rebalance_cost"].at[d] == 0.0 for d in non_execution_days)


def test_roll_cost_embedded_in_daily_returns_flows_through_scaled_by_weight():
    """Roll-leg cost is already charged inside daily_returns_by_symbol
    (pipeline.symbol_daily_returns -> returns.chain_returns) before this
    module ever sees it -- this test proves compute_arm_daily_returns does
    not double-charge or drop it: a scripted day with an embedded roll-cost
    drag must appear in pre_leverage_returns scaled by exactly that day's
    weight, nothing more or less."""
    daily_index = pd.date_range("2020-01-01", periods=65, freq="D")
    month_end_index = pd.DatetimeIndex([daily_index[29], daily_index[59]])
    weights_by_month = pd.DataFrame({"A": [0.5, 0.5]}, index=month_end_index)  # no rebalance, no rebalance cost
    settle_by_month = pd.DataFrame({"A": [80.0, 80.0]}, index=month_end_index)

    roll_day = daily_index[35]
    sym_returns = pd.Series(0.001, index=daily_index)
    sym_returns.at[roll_day] = -0.05  # a scripted roll day: a real return-chaining roll would embed a cost drag like this

    result = compute_arm_daily_returns(
        weights_by_month, {"A": sym_returns}, settle_by_month, month_end_index, daily_index,
        symbol_of_column={"A": "CL"},
    )
    assert result["pre_leverage_returns"].at[roll_day] == pytest.approx(0.5 * -0.05)


def test_execution_timing_no_same_day_signal_to_trade():
    """A weight decided AT month-end t must have ZERO effect on or before
    t -- it only takes effect starting the first trading day strictly
    after t (Sec 3: a full day separates signal from trade)."""
    daily_index = pd.date_range("2020-01-01", periods=40, freq="D")
    month_end_index = pd.DatetimeIndex([daily_index[19], daily_index[-1]])
    weights_by_month = pd.DataFrame({"A": [1.0, 1.0]}, index=month_end_index)
    daily_returns = pd.Series(0.01, index=daily_index)  # nonzero every day, to make a same-day leak visible

    daily_w = expand_monthly_to_daily(weights_by_month, month_end_index, daily_index)
    on_or_before = daily_index[daily_index <= month_end_index[0]]
    assert (daily_w.loc[on_or_before, "A"] == 0.0).all()

    result = compute_arm_daily_returns(
        weights_by_month, {"A": daily_returns},
        pd.DataFrame({"A": [80.0, 80.0]}, index=month_end_index),
        month_end_index, daily_index, symbol_of_column={"A": "CL"},
    )
    assert (result["pre_leverage_returns"].loc[on_or_before] == 0.0).all()
    first_execution_day = daily_index[daily_index > month_end_index[0]][0]
    assert result["pre_leverage_returns"].at[first_execution_day] != 0.0


def test_symbol_vol_and_settle_at_month_end_use_last_value_on_or_before():
    """Both month-end lookup helpers must use the last available date
    ON OR BEFORE the month-end, matching pipeline.month_end_carry_panel's
    own established convention (not an exact-date match, which would break
    whenever a month-end itself isn't a trading day in some other context)."""
    daily_index = pd.date_range("2020-01-01", periods=65, freq="D")  # ends 2020-03-05
    month_end = pd.Timestamp("2020-03-10")  # deliberately NOT in daily_index, and past it entirely
    sym_returns = pd.Series([0.001 if i % 2 == 0 else -0.001 for i in range(len(daily_index))], index=daily_index)
    rv = symbol_vol_at_month_end(sym_returns, pd.DatetimeIndex([month_end]))
    expected = vol_mod.rolling_volatility(sym_returns).at[daily_index[daily_index <= month_end].max()]
    assert rv.at[month_end] == pytest.approx(expected)

    front = pd.Series(["C1"] * len(daily_index), index=daily_index)
    settle_wide = pd.DataFrame({"C1": np.linspace(50, 60, len(daily_index))}, index=daily_index)
    sv = symbol_settle_at_month_end(front, settle_wide, pd.DatetimeIndex([month_end]))
    assert sv.at[month_end] == pytest.approx(settle_wide.at[daily_index[daily_index <= month_end].max(), "C1"])


def test_end_to_end_tiny_universe_net_sharpe_matches_hand_traced_computation():
    """Full pipeline, 2 symbols, ~4 months: builds pre-leverage weights from
    a raw TS signal, runs compute_arm_daily_returns, then re-derives the
    entire chain independently (calling the same underlying primitives
    directly, in a plain Python loop, not through src/primary.py) and
    checks the two daily_net_returns series match exactly, date for date.
    This is the 'end-to-end, net Sharpe computable by hand' fixture --
    Sharpe itself is then computed the same way stats.py does (mean/std*sqrt(252))
    on both series and checked to match."""
    n = 130
    daily_index = pd.date_range("2020-01-01", periods=n, freq="D")
    month_end_index = pd.DatetimeIndex(
        [daily_index[29], daily_index[59], daily_index[89], daily_index[119]])

    rng = np.random.default_rng(42)
    ret_a = pd.Series(rng.normal(0.0003, 0.01, n), index=daily_index)
    ret_b = pd.Series(rng.normal(-0.0002, 0.015, n), index=daily_index)
    carry_panel = pd.DataFrame({"A": [1.0, 1.0, -1.0, -1.0], "B": [-1.0, 1.0, 1.0, -1.0]}, index=month_end_index)
    entry_dates = {"A": pd.Timestamp("2019-01-01"), "B": pd.Timestamp("2019-01-01")}
    settle_by_month = pd.DataFrame({"A": [80.0, 81.0, 79.0, 78.0], "B": [50.0, 51.0, 49.0, 52.0]}, index=month_end_index)

    vol_a = symbol_vol_at_month_end(ret_a, month_end_index)
    vol_b = symbol_vol_at_month_end(ret_b, month_end_index)
    vol_panel = pd.DataFrame({"A": vol_a, "B": vol_b})

    weights = build_pre_leverage_weights(carry_panel, vol_panel, entry_dates, ts_raw_signal)
    result = compute_arm_daily_returns(
        weights, {"A": ret_a, "B": ret_b}, settle_by_month, month_end_index, daily_index,
        symbol_of_column={"A": "CL", "B": "GC"},
    )

    # independent re-derivation, in a plain loop, calling the same primitives
    # directly (not primary.py's own helpers -- a genuinely separate path).
    # Each month-end's window runs to the NEXT month-end, except the last,
    # which runs to the end of daily_index (a decided position holds going
    # forward until the next rebalance -- there just isn't one yet).
    def _window(i):
        t = month_end_index[i]
        if i + 1 < len(month_end_index):
            return t, daily_index[(daily_index > t) & (daily_index <= month_end_index[i + 1])]
        return t, daily_index[daily_index > t]

    daily_w = pd.DataFrame(0.0, index=daily_index, columns=["A", "B"])
    for i in range(len(month_end_index)):
        t, window = _window(i)
        daily_w.loc[window, "A"] = weights.at[t, "A"]
        daily_w.loc[window, "B"] = weights.at[t, "B"]
    gross_ret = daily_w["A"] * ret_a.reindex(daily_index).fillna(0.0) + daily_w["B"] * ret_b.reindex(daily_index).fillna(0.0)

    rebal = pd.Series(0.0, index=daily_index)
    w_prev = {"A": 0.0, "B": 0.0}
    for i in range(len(month_end_index)):
        t, window = _window(i)
        if len(window) == 0:
            continue
        exec_day = window[0]
        cost = 0.0
        for sym, root in (("A", "CL"), ("B", "GC")):
            delta = abs(weights.at[t, sym] - w_prev[sym])
            if delta > 0:
                cost += delta * costs.cost_per_side_pct(root, settle_by_month.at[t, sym])
            w_prev[sym] = weights.at[t, sym]
        rebal.at[exec_day] = cost
    pre_lev = gross_ret - rebal

    port_vol_lagged = vol_mod.rolling_volatility(pre_lev).shift(1)
    gross_by_month = weights.abs().sum(axis=1)
    gross_daily = pd.Series(0.0, index=daily_index)
    for i in range(len(month_end_index)):
        t, window = _window(i)
        gross_daily.loc[window] = gross_by_month.at[t]
    expected_net = pd.Series(
        [vol_mod.portfolio_leverage_scalar(port_vol_lagged.at[d], gross_daily.at[d]) * pre_lev.at[d] for d in daily_index],
        index=daily_index,
    )

    pd.testing.assert_series_equal(result["daily_net_returns"], expected_net, check_names=False)

    ann = config.TRADING_DAYS_PER_YEAR ** 0.5
    actual_sharpe = result["daily_net_returns"].mean() / result["daily_net_returns"].std(ddof=1) * ann
    expected_sharpe = expected_net.mean() / expected_net.std(ddof=1) * ann
    assert actual_sharpe == pytest.approx(expected_sharpe)
