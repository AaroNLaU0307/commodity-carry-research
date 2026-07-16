"""
Phase 1c robustness suite constructions. PREREGISTRATION.md Sec 8 (items
1-5, 7, 10; item 6 needs no new construction -- see below), plus the F7
ex-PA/PL diagnostic (`DEVIATIONS.md`, 2026-07-11) and the fixed-calendar
roll rule's day-count specification completion (`DEVIATIONS.md`, dated the
day this module was written -- decided before this module was ever run,
without reference to any robustness result).

Kept separate from src/primary.py, src/pipeline.py, src/roll.py: these are
ONE-OFF, non-gating diagnostic variants, not part of the core, heavily-
tested primary-family engine those modules implement. None of Sec 8's items
are new hypotheses or new signals in the falsification sense -- every
function here is a bounded, parameter-free (or already-parameterized by
Sec 8's own wording) variation on the primary construction, reported with
sign and magnitude, never gating promotion.

Item 6 (2x cost table) needs no new construction at all: cost_multiplier is
already threaded through costs.py -> pipeline.symbol_daily_returns() ->
primary.compute_arm_daily_returns() -- see scripts/phase1c_primary_backtest.py,
which already computed and reported it as part of gate 4. This module does
not duplicate that.

Items 8-9 (sub-period/per-year/jackknife) need no new construction either:
they are diagnostics of the ALREADY-COMPUTED primary daily_net_returns
series (slicing by date range, sector, or year), not a different signal or
weighting -- see scripts/phase1c_robustness.py for that slicing logic
directly; nothing to wire here.
"""
import pandas as pd

from . import config, vol as vol_mod, carry as carry_mod
from .portfolio import n_leg, xs_raw_signal
from .data_loader import live_symbols_at


# ---------------------------------------------------------------------
# Item 1: sector-neutral XS (rank within sector, equal sector risk)
# ---------------------------------------------------------------------

def sector_neutral_xs_raw_signal(carry_snapshot: pd.Series, symbol_sector: dict) -> pd.Series:
    """
    Sec 8 item 1. Ranks WITHIN each sector present in carry_snapshot
    (n_leg() applied to that sector's own live count, same rounding
    convention as the global tercile split -- no new parameter), giving a
    per-sector +1/0/-1 raw signal exactly like xs_raw_signal() but scoped
    to one sector at a time.

    "Equal sector risk": each symbol's raw signal is then divided by the
    number of ACTIVE (nonzero-signal) symbols in its own sector, so every
    sector's total gross raw-signal magnitude sums to the same constant
    (1.0 long + 1.0 short) regardless of how many names are actually in
    that sector or how many ended up in its own long/short legs -- a
    populous sector's active names get individually smaller raw signals,
    a sparse sector's active names get individually larger ones, so that
    (combined with the existing per-asset vol-scaling in
    vol.asset_target_weight()) no single sector structurally dominates
    portfolio risk just by having more members. This is a normalization,
    not a new threshold: nothing here is tunable.
    """
    sectors = {}
    for s in carry_snapshot.index:
        sectors.setdefault(symbol_sector.get(s), []).append(s)

    raw = pd.Series(0.0, index=carry_snapshot.index)
    for sector, members in sectors.items():
        if sector is None:
            continue
        sub = carry_snapshot.loc[members]
        sig = xs_raw_signal(sub)  # per-sector tercile signal, same n_leg() rounding
        n_active = int((sig != 0).sum())
        if n_active == 0:
            continue
        raw.loc[members] = sig / n_active
    return raw


# ---------------------------------------------------------------------
# Item 2: quintile cutoffs instead of terciles
# ---------------------------------------------------------------------

def n_leg_quintile(n_live: int) -> int:
    """Sec 8 item 2: same round-half-to-even convention as n_leg(), divisor
    5 instead of 3 -- explicitly named in Sec 8's own text ("quintile"),
    not a free parameter."""
    return round(n_live / 5)


def xs_raw_signal_quintile(carry_snapshot: pd.Series) -> pd.Series:
    """Sec 8 item 2: same structure as portfolio.xs_raw_signal(), leg size
    from n_leg_quintile() instead of n_leg()."""
    n_live = len(carry_snapshot)
    leg = n_leg_quintile(n_live)
    ranked = carry_snapshot.sort_values(ascending=False)
    signal = pd.Series(0, index=carry_snapshot.index, dtype=float)
    if leg > 0:
        signal.loc[ranked.index[:leg]] = 1.0
        signal.loc[ranked.index[-leg:]] = -1.0
    return signal


# ---------------------------------------------------------------------
# Item 3: equal-weight legs instead of inverse-vol weighting
# ---------------------------------------------------------------------

def equal_weight_pre_leverage_weights(carry_panel: pd.DataFrame, entry_dates: dict) -> pd.DataFrame:
    """
    Sec 8 item 3. Same live-universe handling and tercile signal
    (xs_raw_signal, i.e. Sec 4's own leg definition is unchanged -- only
    the WITHIN-LEG weighting rule changes) as
    primary.build_pre_leverage_weights(), but each active symbol's
    pre-leverage weight is signal / (count of active symbols on ITS OWN
    side, long or short) instead of vol.asset_target_weight()'s
    inverse-vol scaling -- an equal notional split within each leg (each
    leg sums to 1.0 gross), bypassing per-asset vol-scaling entirely.
    Portfolio-level vol targeting and leverage (Sec 4's separate,
    unaffected mechanism) still applies on top, exactly as for every other
    arm -- this isolates the within-leg weighting choice alone.
    """
    out = pd.DataFrame(0.0, index=carry_panel.index, columns=carry_panel.columns)
    for month in carry_panel.index:
        live = [s for s in live_symbols_at(month, entry_dates) if s in carry_panel.columns]
        snapshot = carry_panel.loc[month, live].dropna()
        if len(snapshot) == 0:
            continue
        raw_signal = xs_raw_signal(snapshot)
        n_long = int((raw_signal > 0).sum())
        n_short = int((raw_signal < 0).sum())
        for symbol, sig in raw_signal.items():
            if sig > 0 and n_long > 0:
                out.at[month, symbol] = 1.0 / n_long
            elif sig < 0 and n_short > 0:
                out.at[month, symbol] = -1.0 / n_short
    return out


# ---------------------------------------------------------------------
# Item 4: carry smoothed over 1 month
# ---------------------------------------------------------------------

def smooth_carry_panel(carry_panel: pd.DataFrame, window: int = 2) -> pd.DataFrame:
    """
    Sec 8 item 4: "carry smoothed over 1 month" -- a 2-point trailing
    average of the month-end carry panel (this month + the immediately
    preceding month), i.e. incorporating exactly 1 additional month of
    history, the plain reading of "smoothed over 1 month" applied to a
    series that is already monthly. window=2 is not a free/tuned
    parameter -- it is what "smoothed over 1 month" means for a monthly
    series (this month plus 1 more). min_periods=window (no partial
    windows) means a symbol's first live month has no smoothed value yet
    (NaN) rather than smoothing across its own entry boundary -- the same
    no-look-ahead, no-backfill discipline used throughout this project.
    """
    return carry_panel.rolling(window=window, min_periods=window).mean()


# ---------------------------------------------------------------------
# Item 5: 12-month-deferred carry definition (front vs ~1-year contract)
# ---------------------------------------------------------------------

def symbol_deferred_carry_series(outright_panel: pd.DataFrame, front_series: pd.Series,
                                  listed_sequence: list, asset: str, defer_days: int = 365) -> pd.Series:
    """
    Sec 8 item 5: same Sec 3 carry formula, but "next" is replaced by the
    listed outright whose OWN expiration is CLOSEST to (front's expiration
    + defer_days) among contracts later-listed than front -- "front vs.
    ~1-year contract instead of front vs. next." Ties (two candidates
    equally close to the target date) break to the earlier expiration,
    the same convention used throughout this project (A1's tie-break,
    etc.). D in the carry formula remains the ACTUAL calendar-day gap
    between front's and the selected far contract's expirations (not
    hardcoded to 365 -- the target is ~1 year, the realized gap is
    whatever the nearest actually-listed contract gives).

    No existence/OI filter here (unlike A2) -- Sec 8 item 5 is testing the
    CARRY DEFINITION'S horizon, not re-litigating A2's dead-serial finding;
    if the nearest-to-1-year contract happens to be a serial month, that is
    itself part of what this robustness item is diagnosing, reported with
    sign and magnitude like every other item, not filtered out.
    """
    sub = outright_panel[outright_panel["asset"] == asset]
    settle_by_key_date = sub.set_index(["_contract_key", "date"])["settlement"]
    expiry_by_key = sub.drop_duplicates(subset=["_contract_key"]).set_index("_contract_key")["expiration"]

    index_of = {key: i for i, key in enumerate(listed_sequence)}
    out_index, out_values = [], []
    for date, front_key in front_series.items():
        pos = index_of.get(front_key)
        if pos is None or pos + 1 >= len(listed_sequence):
            out_index.append(date)
            out_values.append(float("nan"))
            continue
        front_expiry = expiry_by_key[front_key]
        target = pd.Timestamp(front_expiry) + pd.Timedelta(days=defer_days)
        candidates = listed_sequence[pos + 1:]
        best_key, best_dist = None, None
        for c in candidates:
            c_expiry = expiry_by_key.get(c)
            if c_expiry is None:
                continue
            dist = abs((pd.Timestamp(c_expiry) - target).days)
            if best_dist is None or dist < best_dist or (dist == best_dist and pd.Timestamp(c_expiry) < pd.Timestamp(expiry_by_key[best_key])):
                best_key, best_dist = c, dist
        if best_key is None:
            out_index.append(date)
            out_values.append(float("nan"))
            continue
        try:
            f_price = settle_by_key_date.at[(front_key, date)]
            far_price = settle_by_key_date.at[(best_key, date)]
        except KeyError:
            out_index.append(date)
            out_values.append(float("nan"))
            continue
        if pd.isna(f_price) or pd.isna(far_price) or f_price <= 0 or far_price <= 0:
            out_index.append(date)
            out_values.append(float("nan"))
            continue
        far_expiry = expiry_by_key[best_key]
        try:
            c_val = carry_mod.compute_carry(f_price, far_price, front_expiry, far_expiry)
        except ValueError:
            c_val = float("nan")
        out_index.append(date)
        out_values.append(c_val)
    return pd.Series(out_values, index=out_index)


# ---------------------------------------------------------------------
# Item 7: fixed-calendar roll rule instead of OI-crossover
# ---------------------------------------------------------------------

def fixed_calendar_front_series(oi_panel: pd.DataFrame, listed_sequence: list, expiry_by_key: dict) -> pd.Series:
    """
    Sec 8 item 7. Day-count specification completion (DEVIATIONS.md,
    dated the day this module was written, decided without reference to
    any robustness result): roll timing = the last business day of the
    month preceding the front's expiry month -- the standard
    parameter-free academic convention, no N to tune. Candidate selection
    at each roll = the SAME A2 existence filter (earliest-expiration
    outright with expiration > incumbent's and OI at t-1 strictly
    positive) -- using the OI-crossover rule's own next-listed-only logic
    here would re-import F11's dead-serial deadlock and test nothing new;
    the point of this variant is to cross-check the AMENDED (A1) roll
    rule's timing against an independent, calendar-driven timing
    mechanism, not to resurrect the pre-A1 bug.

    Still strictly t-1 OI throughout (oi_panel.shift(1)) for the existence
    check -- no look-ahead anywhere in this variant either.
    """
    oi_lagged = oi_panel.reindex(columns=listed_sequence).shift(1)
    dates = oi_panel.index
    current_idx = 0

    def roll_date_for(idx):
        expiry = pd.Timestamp(expiry_by_key[listed_sequence[idx]])
        month_start = pd.Timestamp(year=expiry.year, month=expiry.month, day=1)
        return month_start - pd.tseries.offsets.BMonthEnd(1)

    front_codes = [None] * len(dates)
    for i, date in enumerate(dates):
        scheduled = roll_date_for(current_idx)
        if date >= scheduled and current_idx + 1 < len(listed_sequence):
            for j in range(current_idx + 1, len(listed_sequence)):
                candidate = listed_sequence[j]
                if candidate not in oi_lagged.columns:
                    continue
                oi_val = oi_lagged.at[date, candidate]
                if pd.notna(oi_val) and oi_val > 0:
                    current_idx = j
                    break
            # if no candidate exists yet, hold at the incumbent (same
            # hold-on-missing/nonexistent principle as F7/A2) -- this
            # variant's own tripwire-equivalent behavior is reported, not
            # silently routed around.
        front_codes[i] = listed_sequence[current_idx]
    return pd.Series(front_codes, index=dates, dtype=object)
