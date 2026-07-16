"""
Roll-rule state machine. PREREGISTRATION.md Sec 3, "Front contract",
amended by F11 Amendment A1 (DEVIATIONS.md, 2026-07-15).

A1 (current). At date t, front is the outright contract that maximizes OI
at t-1 among candidates whose expiration is >= the incumbent front's
expiration; ties break toward the earlier expiration (so the incumbent is
retained on ties); if OI at t-1 is unobserved for every candidate, the
incumbent is held (F7's hold-on-missing ruling, unchanged by this
amendment). Initialization at the first date needs no special case: the
incumbent starts at listed_sequence[0] (the earliest-expiration live
contract), so "candidates >= incumbent's expiration" is every live
outright on that first comparison -- exactly "argmax OI at t-1 over all
live outrights."

Monotonic by construction, not by a separate check: the eligible candidate
set at any step is listed_sequence[current_idx:], which never includes an
earlier expiration than the incumbent's, so current_idx is non-decreasing
across the whole date loop and front can never revert to an earlier
expiration (no ping-pong possible, regardless of how OI moves afterward).

Superseded (pre-A1) rule, kept here for provenance only, not used: front
switched from c1 to the single next-listed contract c2 at the first t such
that OI_{t-1}(c2) > OI_{t-1}(c1) -- i.e. this same rule restricted to a
candidate set of size 1 (just the immediately-next contract). A1 is a
strict generalization: candidates now include every later-expiration
contract, not only the one immediately next. Amended because the
single-candidate restriction deadlocks permanently whenever that one
candidate is a listed-but-never-traded ("dead serial") month -- F11,
docs/DATA_QA_REPORT.md -- even when a later, real, liquid contract is
perfectly observable throughout.

Strictly t-1 OI throughout, unchanged by A1: CME publishes official open
interest on a T+1 basis, so using same-day OI to decide a same-day roll
would embed look-ahead bias; t-1 OI is the latest figure genuinely known
before trading on day t. A1 only changed which CONTRACTS are compared at a
given point in time, never the temporal lag itself -- "multi-candidate
OI-max," never "lookahead" (that word is reserved for temporal/future-date
leakage, which remains completely absent).
"""
import numpy as np
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
    monotonic (never rolls backward). See module docstring for the A1
    multi-candidate OI-max rule this implements.
    """
    if not listed_sequence:
        raise ValueError("listed_sequence must be non-empty")

    oi_lagged = oi_panel.reindex(columns=listed_sequence).shift(1)  # this shift IS the look-ahead-safety mechanism
    oi_values = oi_lagged.to_numpy(dtype="float64")
    dates = oi_panel.index
    n_dates = len(dates)

    current_idx = 0
    front_codes = [None] * n_dates
    for i in range(n_dates):
        # Eligible candidates are listed_sequence[current_idx:] -- every
        # contract from the incumbent onward in expiry order, i.e. exactly
        # {c : expiry(c) >= incumbent's expiry}, since listed_sequence is
        # expiry-sorted. A positional slice, no per-candidate expiry
        # comparison needed.
        row = oi_values[i, current_idx:]
        if not np.all(np.isnan(row)):
            # np.nanargmax ignores NaN entries and, on ties among the max
            # value, returns the FIRST (lowest-index) occurrence -- since
            # this slice starts at the incumbent's own position and is
            # expiry-ascending, that is exactly "ties break toward the
            # earlier expiration (the incumbent is retained on ties)."
            local_best = int(np.nanargmax(row))
            current_idx = current_idx + local_best
        # else: every eligible candidate's t-1 OI is unobserved -> hold
        # the incumbent (F7 ruling) -- current_idx unchanged.
        front_codes[i] = listed_sequence[current_idx]

    return pd.Series(front_codes, index=dates, dtype=object)
