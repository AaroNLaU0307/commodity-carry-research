"""
Volatility estimator, vol targeting, leverage cap, dynamic deleveraging.
PREREGISTRATION.md Sec 4, "Convention inheritance (mandatory)".

Every formula here is inherited VERBATIM from multi-asset-tsmom-research
(read-only reference; that repo was never modified). File+line citations
are in PREREGISTRATION.md Sec 4's table; restated in code form here:

  - Per-asset vol estimator: 60-trading-day rolling std (ddof=1) of daily
    simple returns, min_periods=window (no partial windows -- NaN until a
    full window exists, so no look-ahead), annualized by x sqrt(252).
    (TSMOM config.py L168, L171; src/sizing.py::rolling_volatility() L51-63.)
  - Same method at the portfolio level (TSMOM config.py L183;
    src/portfolio.py::realized_portfolio_vol() L156-165).
  - Per-asset annualized vol target: 10% (TSMOM config.py L169).
  - Portfolio annualized vol target: 10% (TSMOM config.py L182).
  - Per-asset weight cap: |weight| <= 2.0 (TSMOM config.py L170;
    src/sizing.py::target_weights() L93).
  - Portfolio gross-leverage cap: sum|weights| <= 3.0 (TSMOM config.py L184;
    src/portfolio.py::leverage() L171-189).
  - Dynamic deleveraging: the leverage scalar L = target_vol / realized_vol
    IS the deleveraging mechanism -- no separate layer (TSMOM
    src/portfolio.py module docstring L21-26, leverage() L184).

No no-trade band: TSMOM defines one (NO_TRADE_BAND=0.05) but does not apply
it in its adopted pipeline -- tested and rejected (PREREGISTRATION.md Sec 4).
Not implemented here for the same reason.
"""
import pandas as pd

from . import config


def rolling_volatility(daily_returns: pd.Series, window: int = None) -> pd.Series:
    """TSMOM src/sizing.py::rolling_volatility(), mirrored exactly."""
    window = window or config.VOL_WINDOW_DAYS
    return daily_returns.rolling(window=window, min_periods=window).std(ddof=1) * (config.TRADING_DAYS_PER_YEAR ** 0.5)


def asset_target_weight(signal: float, realized_vol: float,
                         target_vol: float = None, max_weight: float = None) -> float:
    """TSMOM src/sizing.py::target_weights(), mirrored exactly: raw =
    signal * target_vol / realized_vol, clipped to +/- max_weight. Returns
    0.0 if realized_vol is zero, negative, or NaN (matches TSMOM's
    `.where(vol > 0)` guard against divide-by-zero)."""
    target_vol = config.ASSET_VOL_TARGET_ANNUAL if target_vol is None else target_vol
    max_weight = config.MAX_ASSET_WEIGHT if max_weight is None else max_weight
    if realized_vol is None or pd.isna(realized_vol) or realized_vol <= 0:
        return 0.0
    raw = signal * target_vol / realized_vol
    return max(-max_weight, min(max_weight, raw))


def portfolio_leverage_scalar(realized_portfolio_vol: float, current_gross: float,
                               target_vol: float = None, max_gross: float = None) -> float:
    """TSMOM src/portfolio.py::leverage(), mirrored exactly: L = target /
    realized, capped so that L * current_gross never exceeds max_gross.
    Returns 0.0 if realized_portfolio_vol is zero, negative, or NaN."""
    target_vol = config.PORTFOLIO_VOL_TARGET_ANNUAL if target_vol is None else target_vol
    max_gross = config.MAX_GROSS_LEVERAGE if max_gross is None else max_gross
    if realized_portfolio_vol is None or pd.isna(realized_portfolio_vol) or realized_portfolio_vol <= 0:
        return 0.0
    l_raw = target_vol / realized_portfolio_vol
    if current_gross <= 0:
        return l_raw
    l_cap = max_gross / current_gross
    return min(l_raw, l_cap)
