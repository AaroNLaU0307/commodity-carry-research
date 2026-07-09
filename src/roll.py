"""
Roll-rule state machine. PREREGISTRATION.md Sec 3, "Front contract".

At date t, the front contract switches from c1 to the next-listed contract
c2 at the first t such that OI_{t-1}(c2) > OI_{t-1}(c1) -- open interest as
of the PRIOR trading day only. CME publishes official open interest on a
T+1 basis, so using same-day OI to decide a same-day roll would embed
look-ahead bias; t-1 OI is the latest figure genuinely known before trading
on day t. Rolls are monotonic: once front has moved from c1 to c2 it cannot
revert to c1, regardless of what OI does afterward.
"""
import pandas as pd


def compute_front_contract_series(oi_panel: pd.DataFrame, listed_sequence: list) -> pd.Series:
    """
    oi_panel : DataFrame indexed by date (ascending, no gaps assumed), one
        column per contract code in `listed_sequence`, values = officially
        published open interest for that date.
    listed_sequence : contract codes in exchange-listed expiry order
        (front-most first).

    Returns a pd.Series indexed like oi_panel, values = the contract code
    that is "front" on that date, decided using strictly t-1 OI and
    monotonic (never rolls backward).
    """
    if not listed_sequence:
        raise ValueError("listed_sequence must be non-empty")

    oi_lagged = oi_panel.shift(1)  # this shift IS the look-ahead-safety mechanism
    dates = oi_panel.index
    front = pd.Series(index=dates, dtype=object)

    current_idx = 0
    for date in dates:
        # Only ever compare the CURRENT front to the NEXT contract in sequence --
        # a single crossover event advances at most one step per date, and the
        # monotonic invariant means we never look at an earlier contract again.
        while current_idx + 1 < len(listed_sequence):
            c1 = listed_sequence[current_idx]
            c2 = listed_sequence[current_idx + 1]
            oi_c1 = oi_lagged.at[date, c1] if c1 in oi_lagged.columns else None
            oi_c2 = oi_lagged.at[date, c2] if c2 in oi_lagged.columns else None
            if oi_c1 is not None and oi_c2 is not None and pd.notna(oi_c1) and pd.notna(oi_c2) and oi_c2 > oi_c1:
                current_idx += 1
                continue  # re-check in case of a further immediate crossover
            break
        front.at[date] = listed_sequence[current_idx]

    return front
