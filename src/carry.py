"""
Carry computation. PREREGISTRATION.md Sec 3, "Carry".

    carry_i(t) = [F_front(t) - F_next(t)] / F_next(t) * 365 / D

F_front(t), F_next(t): same-date settlement prices (Databento `statistics`
schema) for the front and next contract respectively. D: calendar days
between the two contracts' expiry dates (Databento `definition` schema).
Positive carry = backwardation (front trades above next, annualized).

"Next contract" is the contract immediately following the front in the
exchange-listed expiry sequence -- see roll.py for how "front" itself is
determined.
"""
from datetime import date


def compute_carry(front_settle: float, next_settle: float,
                   front_expiry: date, next_expiry: date) -> float:
    """Single-observation carry. Raises if next_expiry <= front_expiry
    (D must be positive -- "next" must genuinely expire later than "front")."""
    d = (next_expiry - front_expiry).days
    if d <= 0:
        raise ValueError(
            f"next_expiry ({next_expiry}) must be strictly after front_expiry "
            f"({front_expiry}); got D={d} calendar days"
        )
    return (front_settle - next_settle) / next_settle * 365.0 / d


def compute_carry_series(front_settle: "pd.Series", next_settle: "pd.Series",
                          front_expiry: date, next_expiry: date) -> "pd.Series":
    """Vectorized carry over a date-indexed pair of settlement series sharing
    a single (front, next) contract pair -- i.e. call once per roll segment,
    not once for the whole history (D is fixed per contract pair, not per
    date, since expiries don't move)."""
    d = (next_expiry - front_expiry).days
    if d <= 0:
        raise ValueError(
            f"next_expiry ({next_expiry}) must be strictly after front_expiry "
            f"({front_expiry}); got D={d} calendar days"
        )
    return (front_settle - next_settle) / next_settle * 365.0 / d
