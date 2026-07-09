"""Tests for src/vol.py -- vol targeting reproduces the TSMOM formulas on
a fixture with known volatility -- all synthetic, per Phase 1a Hard Rule 1."""
import numpy as np
import pandas as pd
import pytest

from src import config
from src.vol import rolling_volatility, asset_target_weight, portfolio_leverage_scalar


def test_rolling_volatility_converges_to_known_std():
    """A synthetic i.i.d. return series with a KNOWN annualized std should
    make rolling_volatility() converge close to that std (60-day window,
    ddof=1, x sqrt(252) -- Sec 4)."""
    rng = np.random.default_rng(42)
    known_annual_vol = 0.20
    daily_std = known_annual_vol / np.sqrt(config.TRADING_DAYS_PER_YEAR)
    n = 2000
    daily_returns = pd.Series(rng.normal(0, daily_std, n))
    rv = rolling_volatility(daily_returns)
    tail_mean = rv.iloc[-500:].mean()  # average over the well-populated tail
    assert tail_mean == pytest.approx(known_annual_vol, rel=0.10)  # within 10% given sampling noise


def test_rolling_volatility_nan_before_full_window_no_look_ahead():
    """min_periods=window means the first (window-1) values must be NaN --
    a partial window would itself be a form of look-ahead-adjacent leakage
    (using less history than the spec requires)."""
    daily_returns = pd.Series(np.ones(config.VOL_WINDOW_DAYS - 1) * 0.001)
    rv = rolling_volatility(daily_returns)
    assert rv.isna().all()


def test_asset_target_weight_scales_inversely_with_vol():
    w_low_vol = asset_target_weight(signal=1.0, realized_vol=0.05)
    w_high_vol = asset_target_weight(signal=1.0, realized_vol=0.20)
    # quadruple the vol -> quarter the weight, holding signal/target fixed
    assert w_low_vol == pytest.approx(4 * w_high_vol)


def test_asset_target_weight_respects_cap():
    # target_vol/realized_vol = 0.10/0.01 = 10, far above MAX_ASSET_WEIGHT=2.0
    w = asset_target_weight(signal=1.0, realized_vol=0.01)
    assert w == pytest.approx(config.MAX_ASSET_WEIGHT)
    w_short = asset_target_weight(signal=-1.0, realized_vol=0.01)
    assert w_short == pytest.approx(-config.MAX_ASSET_WEIGHT)


def test_asset_target_weight_zero_on_undefined_vol():
    assert asset_target_weight(signal=1.0, realized_vol=0.0) == 0.0
    assert asset_target_weight(signal=1.0, realized_vol=-0.05) == 0.0
    assert asset_target_weight(signal=1.0, realized_vol=float("nan")) == 0.0


def test_portfolio_leverage_scalar_deleveraging_formula():
    # L = target / realized, per TSMOM's leverage() -- Sec 4
    L = portfolio_leverage_scalar(realized_portfolio_vol=0.05, current_gross=1.0)
    assert L == pytest.approx(config.PORTFOLIO_VOL_TARGET_ANNUAL / 0.05)


def test_portfolio_leverage_scalar_respects_gross_cap():
    # target/realized would be huge; must be capped so L * current_gross <= MAX_GROSS_LEVERAGE
    current_gross = 1.0
    L = portfolio_leverage_scalar(realized_portfolio_vol=0.001, current_gross=current_gross)
    assert L * current_gross == pytest.approx(config.MAX_GROSS_LEVERAGE)


def test_portfolio_leverage_scalar_shrinks_when_vol_rises_grows_when_vol_falls():
    """This IS the dynamic-deleveraging mechanism per Sec 4 -- there is no
    separate rule beyond this scalar."""
    L_calm = portfolio_leverage_scalar(realized_portfolio_vol=0.05, current_gross=1.0)
    L_stressed = portfolio_leverage_scalar(realized_portfolio_vol=0.20, current_gross=1.0)
    assert L_stressed < L_calm
