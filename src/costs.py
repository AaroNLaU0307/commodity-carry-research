"""
Cost model. PREREGISTRATION.md Sec 5, "Cost model (frozen before any computation)".

    cost_per_side_$  = max(1 tick value, conservative half-spread) + all-in fee
    cost_per_side_pct = cost_per_side_$ / (settlement_price_t * contract_multiplier)

No systematic per-product half-spread data was found (Sec 5); the formula's
own max(1 tick, ...) structure makes the tick value the operative floor
throughout -- there is no separate half-spread input in this implementation
because none was ever obtained, which is itself documented in Sec 5, not a
simplification introduced here.

The fee term is a uniform $2.50/side all-in allowance (advisor ruling,
2026-07-10, WORKSPACE/PREREG_OPEN_ITEMS.md item 2) -- exchange + clearing +
NFA + brokerage, deliberately conservative, not a per-product figure.

Charged on every rebalance trade and every roll leg (Sec 3, Sec 5).
"""
from . import config


def cost_per_side_usd(symbol: str, cost_multiplier: float = 1.0) -> float:
    """cost_multiplier=2.0 applies the Sec 8 item 6 robustness variant (2x cost table)."""
    spec = config.CONTRACT_SPECS[symbol]
    return cost_multiplier * (spec["tick_value"] + config.ALL_IN_FEE_PER_SIDE_USD)


def cost_per_side_pct(symbol: str, settle_price: float, cost_multiplier: float = 1.0) -> float:
    """Percentage-of-notional cost for one side of one contract, at the given
    settlement price. This is the only place a percentage cost is computed --
    the dollar table in Sec 5 is frozen, this conversion is not (it depends on
    the actual price on the actual date, per Sec 5's own explanation)."""
    spec = config.CONTRACT_SPECS[symbol]
    usd = cost_per_side_usd(symbol, cost_multiplier)
    notional = settle_price * spec["multiplier"]
    if notional <= 0:
        raise ValueError(f"non-positive notional for {symbol}: settle_price={settle_price}, multiplier={spec['multiplier']}")
    return usd / notional
