"""
Return chaining with roll-day cost charging. PREREGISTRATION.md Sec 3
("Returns"), Sec 5 (cost charged on every roll leg).

    r_t = F_front(t) / F_front(t-1) - 1

settlement-to-settlement. Futures returns are excess returns by
construction (no financing leg). On a roll date, the price return is still
computed off the contract that was actually held overnight (the one
identified as front on t-1) marked to its own settlement on t, then a
round-trip cost (closing that leg + opening the new front) is subtracted.
There is no price splicing across the roll -- the series is chained per
HELD contract, never a synthetic continuous price.

Scope note: this module charges the ROLL leg's cost only (a contract-level
event). Portfolio-level REBALANCE cost -- charged on the change in a
symbol's portfolio weight at each monthly rebalance, independent of whether
that symbol also happens to roll that month -- is a separate layer applied
in portfolio.py, using the same costs.cost_per_side_pct() primitive.
"""
import pandas as pd

from . import config, costs


def chain_returns(settle_panel: pd.DataFrame, front_series: pd.Series,
                   cost_multiplier: float = 1.0) -> pd.Series:
    """
    settle_panel : DataFrame indexed by date, one column per contract code,
        values = settlement prices.
    front_series : pd.Series indexed like settle_panel, values = which
        contract is held on that date (from roll.compute_front_contract_series,
        or a fixed single-contract series for a non-rolling test fixture).
    cost_multiplier : 1.0 for the frozen cost table, 2.0 for the Sec 8 item 6
        robustness variant.

    Returns a pd.Series of daily net returns, indexed like settle_panel
    minus its first row (no t-1 exists for the first observation).
    """
    dates = settle_panel.index
    if len(dates) < 2:
        return pd.Series(dtype=float)

    out_index = []
    out_values = []
    for i in range(1, len(dates)):
        t, t_minus_1 = dates[i], dates[i - 1]
        held_yesterday = front_series.at[t_minus_1]
        held_today = front_series.at[t]

        price_t = settle_panel.at[t, held_yesterday]
        price_t_minus_1 = settle_panel.at[t_minus_1, held_yesterday]
        gross_r = price_t / price_t_minus_1 - 1.0

        cost = 0.0
        if held_today != held_yesterday:
            # round trip: close the old leg, open the new leg, both charged
            # at their own contract's cost-per-side (Sec 5 is per-symbol, and
            # here symbol is fixed -- the contract MONTH changes, not the
            # underlying commodity -- so the same symbol's cost table row
            # applies to both legs).
            cost_close = costs.cost_per_side_pct(_symbol_of(held_yesterday), price_t_minus_1, cost_multiplier)
            cost_open = costs.cost_per_side_pct(_symbol_of(held_today), price_t, cost_multiplier)
            cost = cost_close + cost_open

        out_index.append(t)
        out_values.append(gross_r - cost)

    return pd.Series(out_values, index=out_index)


def _symbol_of(contract_code: str) -> str:
    """Contract codes carry a single-letter CME month code + year suffix
    (e.g. 'CLZ26'); the cost table is keyed by the root symbol only. Matches
    against the known 18-symbol universe rather than assuming a fixed root
    length or stripping "all leading letters" (which breaks for roots like
    NG, whose second letter 'G' collides with February's month code --
    'NGG26' must resolve to 'NG', not 'NGG')."""
    for root in sorted(config.ALL_SYMBOLS, key=len, reverse=True):
        if contract_code.startswith(root):
            return root
    raise ValueError(f"Cannot determine root symbol for contract code {contract_code!r}")
