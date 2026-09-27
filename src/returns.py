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

Scope note: this module computes the ROLL leg's cost only (a contract-level
event), embedded as a per-unit drag in the returned series. The portfolio
layer (primary.compute_arm_daily_returns) takes it as the difference from
the cost-free series and charges it on |position|, so a short position pays
it too; trading cost on every change in the levered position is charged
there as well, using the same costs.cost_per_side_pct() primitive
(portfolio.cost_pct_by_month).
"""
import pandas as pd

from . import config, costs


def chain_returns(settle_panel: pd.DataFrame, front_series: pd.Series,
                   cost_multiplier: float = 1.0, symbol: str = None) -> pd.Series:
    """
    settle_panel : DataFrame indexed by date, one column per contract code,
        values = settlement prices.
    front_series : pd.Series indexed like settle_panel, values = which
        contract is held on that date (from roll.compute_front_contract_series,
        or a fixed single-contract series for a non-rolling test fixture).
    cost_multiplier : 1.0 for the frozen cost table, 2.0 for the Sec 8 item 6
        robustness variant.
    symbol : the root symbol for the Sec 5 cost-table lookup, if the caller
        already knows it (pipeline.py always does -- it processes one
        symbol's contracts at a time). If omitted, falls back to
        _symbol_of()'s string-prefix inference from the contract code
        itself, for backward compatibility with callers whose contract
        codes are already root-symbol-prefixed (e.g. this module's own
        tests). Explicit `symbol` is preferred and required when contract
        codes do NOT start with a parseable root prefix -- e.g.
        pipeline.py's `_contract_key`, which is instrument_id + expiration,
        not raw_symbol-prefixed (see pipeline.py's build_outright_panel()
        docstring for why raw_symbol was dropped from the key).

    Returns a pd.Series of daily net returns, indexed like settle_panel
    minus its first row (no t-1 exists for the first observation).
    """
    dates = settle_panel.index
    if len(dates) < 2:
        return pd.Series(dtype=float)

    root_symbol = symbol  # may be None -> _symbol_of() fallback per leg below

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
            close_symbol = root_symbol if root_symbol is not None else _symbol_of(held_yesterday)
            open_symbol = root_symbol if root_symbol is not None else _symbol_of(held_today)
            cost_close = costs.cost_per_side_pct(close_symbol, price_t_minus_1, cost_multiplier)
            cost_open = costs.cost_per_side_pct(open_symbol, price_t, cost_multiplier)
            cost = cost_close + cost_open

        out_index.append(t)
        out_values.append(gross_r - cost)

    return pd.Series(out_values, index=out_index)


def fill_missing_settlement_mark_to_last(settle_panel: pd.DataFrame) -> tuple:
    """
    Phase 1b Step 0 specification completion (DEVIATIONS.md, 2026-07-11):
    held-front missing-settlement handling is mark-to-last-settlement with
    a zero return that day, occurrences counted and reported, no gate.

    Forward-fills each contract column independently (pandas ffill() never
    fills backward and never fills before a contract's own first real
    value, so this cannot manufacture pre-existence data or look ahead).
    Feeding the filled panel into chain_returns() produces exactly a 0.0
    return on every filled day: the filled price at t equals the last real
    price, which is either the same value chain_returns() already uses at
    t-1 (a single-day gap) or itself the carried-forward mark from an
    earlier day in a longer gap -- either way the ratio is 1.0. No changes
    to chain_returns() itself are needed; this is a preprocessing step.

    Returns (filled_panel, occurrence_mask) -- occurrence_mask is a boolean
    DataFrame, same shape as settle_panel, True at every cell that was NaN
    and got filled from an earlier real value. Leading NaNs before a
    contract's first real settlement are NOT counted as "filled" (there is
    no prior value to mark to yet -- that is the entry-rule's concern, not
    a missing-settlement occurrence).
    """
    filled_panel = settle_panel.ffill()
    occurrence_mask = settle_panel.isna() & filled_panel.notna()
    return filled_panel, occurrence_mask


def count_held_front_missing_settlement(settle_panel: pd.DataFrame, front_series: pd.Series) -> int:
    """
    Phase 1b Step 0 specification: "occurrences counted and reported" for
    the held-front missing-settlement rule -- counted precisely, by
    mirroring chain_returns()'s own indexing, not by counting NaN-to-filled
    cells across the whole settle_panel.

    fill_missing_settlement_mark_to_last()'s occurrence_mask (this
    module's other function) is correct as a general-purpose "which cells
    got filled" mask, but settle_panel typically carries one column per
    contract EVER listed for a symbol across its full history (~150-350
    columns for the liquid energy/metals roots) -- at any given date, only
    ONE of those columns is the held front; the other columns' missing
    values on that date are never read by chain_returns() and are not a
    "held-front missing-settlement occurrence" in the Step 0 spec's sense,
    even though the whole-panel mask would count them (this produced an
    impossible >100% "fill rate" on this pipeline's first real-data run --
    caught in the generated report, not silently shipped).

    Counts, for each t from the second date onward, whether the OLD
    (yesterday's) held contract's settlement on date t -- exactly
    chain_returns()'s "price_t" lookup, `settle_panel.at[t, held_yesterday]`
    -- was originally missing. One occurrence per day the fill was
    actually exercised for the return computation, no double-counting
    across the price_t / price_t_minus_1 pair (price_t_minus_1 on this
    iteration is the same cell as price_t on the PRIOR iteration, already
    counted there if it was itself filled).
    """
    dates = settle_panel.index
    if len(dates) < 2:
        return 0
    count = 0
    for i in range(1, len(dates)):
        t, t_minus_1 = dates[i], dates[i - 1]
        held_yesterday = front_series.at[t_minus_1]
        if held_yesterday not in settle_panel.columns:
            continue
        if pd.isna(settle_panel.at[t, held_yesterday]):
            count += 1
    return count


def held_front_zero_price_guard(settle_panel: pd.DataFrame, front_series: pd.Series) -> list:
    """
    Phase 1b Step 0 specification completion (DEVIATIONS.md, 2026-07-11):
    zero-price guard -- if the held front contract's settlement is <= 0 on
    any date, the pipeline must HALT rather than silently compute a return
    through it (a settlement of exactly 0 is as nonsensical to divide by as
    a negative one for this guard's purpose, unlike the F2 KEEP ruling,
    which was specifically about a genuine, well-documented negative
    settlement on a contract that was NOT the OI-determined front that
    day).

    Checked against the RAW (pre-fill) settlement -- a real, reported
    non-positive settlement is a discovery to halt and report, never
    something to mark-to-last past silently.

    Returns a list of (date, contract_code, price) for every violation
    found (empty list = guard did not fire). Does not raise or halt itself
    -- the caller (the pipeline runner) decides what "HALT the run" means
    operationally (e.g. exit the script) after inspecting this list, so
    that a fired guard is always visible rather than raising mid-pipeline
    where it might be caught and swallowed.
    """
    violations = []
    for date, contract in front_series.items():
        if contract not in settle_panel.columns:
            continue
        price = settle_panel.at[date, contract]
        if pd.notna(price) and price <= 0:
            violations.append((date, contract, price))
    return violations


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
