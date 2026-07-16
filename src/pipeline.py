"""
Phase 1b/1c real-data assembly pipeline. PREREGISTRATION.md Sec 2 (entry
rule), Sec 3 (roll rule, carry, returns), Sec 7 (premise-test panels).

This module is the ONLY place that turns the raw per-day `definition` and
`statistics` deliveries into the per-symbol front/carry/return series the
rest of the engine (roll.py, carry.py, returns.py, premise.py) consumes.
Two functions in this module (build_definition_lookup, build_settlement_oi_panel)
require real DBN files in DATA_DIR and are exercised only manually, never in
the automated suite -- same convention as data_loader.py's own DBN-reading
functions (see that module's docstring). Every other function here takes
already-loaded DataFrames and is synthetic-fixture-testable, and IS tested
that way (tests/test_pipeline.py) before being run on real data, per the
Phase 1b governing prompt's Hard Rule 4.

Identity-safety note (F6, F8 -- docs/DATA_QA_REPORT.md addenda): neither
`instrument_id` nor `raw_symbol` alone is a stable key across this
dataset's 16-year history (both are reused/collide at different points).
Every join in this module against real multi-date data is either (a) a
single-date join (safe: instrument_id correctly identifies one contract on
one specific day), or (b) keyed by the full (asset, raw_symbol,
instrument_id) triple via `_contract_key` below (safe: unique by
construction, verified in the full-corpus registry this session -- see the
consistency-sweep section of the QA addendum). No function here ever
deduplicates or joins on `instrument_id` or `raw_symbol` alone across
multiple dates.
"""
import re
from pathlib import Path

import pandas as pd

_FILENAME_DATE_RE = re.compile(r"(\d{8})")

from . import carry as carry_mod
from . import config
from . import returns as returns_mod
from . import roll as roll_mod
from .data_loader import build_month_end_calendar


def build_definition_lookup(data_dir: Path = None) -> pd.DataFrame:
    """Real data only, not unit-tested (see module docstring). Thin
    (date, instrument_id, asset, raw_symbol, instrument_class, expiration)
    table from every `definition` per-day file.

    Reads and column-trims each file individually before concatenating
    (rather than routing through data_loader.load_dbn_partitioned(), which
    concatenates the full ~64-column frame across all 5,000+ files first)
    -- the same per-file-then-concatenate approach already proven
    tractable for the full corpus this session (docs/DATA_QA_REPORT.md's
    Phase 1a Completion addendum)."""
    import databento as db
    data_dir = config.DATA_DIR if data_dir is None else data_dir
    schema_dir = Path(data_dir) / "definition"
    files = sorted(schema_dir.glob("*.dbn.zst"))
    if not files:
        raise FileNotFoundError(f"No definition files found at {schema_dir}")

    frames = []
    for f in files:
        file_date = pd.Timestamp(_FILENAME_DATE_RE.search(f.name).group(1))
        d = db.DBNStore.from_file(f).to_df()
        thin = d[["instrument_id", "asset", "raw_symbol", "instrument_class", "expiration"]].copy()
        thin["date"] = file_date
        frames.append(thin)
    out = pd.concat(frames, ignore_index=True)
    return out.drop_duplicates(subset=["date", "instrument_id"])


def build_settlement_oi_panel(data_dir: Path = None) -> pd.DataFrame:
    """Real data only, not unit-tested (see module docstring). Thin
    (date, instrument_id, settlement, oi) table -- last value of the day
    for stat_type=3 (settlement) and stat_type=6 (OI), empirically
    identified in docs/DATA_QA_REPORT.md's Phase 1a Completion addendum
    (settlement anchored to the 2020-04-20 CLK0 = -37.63 value; OI
    identified by its pre-expiry decay shape).

    Same per-file-then-concatenate approach as build_definition_lookup()
    and for the same reason."""
    import databento as db
    data_dir = config.DATA_DIR if data_dir is None else data_dir
    schema_dir = Path(data_dir) / "statistics"
    files = sorted(schema_dir.glob("*.dbn.zst"))
    if not files:
        raise FileNotFoundError(f"No statistics files found at {schema_dir}")

    frames = []
    for f in files:
        file_date = pd.Timestamp(_FILENAME_DATE_RE.search(f.name).group(1))
        d = db.DBNStore.from_file(f).to_df().reset_index()
        date_col = d.columns[0]
        sub = d[d["stat_type"].isin([3, 6])].sort_values(date_col)
        last = sub.groupby(["instrument_id", "stat_type"], as_index=False).last()
        last = last[["instrument_id", "stat_type", "price", "quantity"]].copy()
        last["date"] = file_date
        frames.append(last)
    full = pd.concat(frames, ignore_index=True)
    settle = full[full["stat_type"] == 3][["date", "instrument_id", "price"]].rename(columns={"price": "settlement"})
    oi = full[full["stat_type"] == 6][["date", "instrument_id", "quantity"]].rename(columns={"quantity": "oi"})
    return settle.merge(oi, on=["date", "instrument_id"], how="outer")


def build_outright_panel(definition_lookup: pd.DataFrame, settlement_oi_panel: pd.DataFrame) -> pd.DataFrame:
    """
    Safe date-aware join: definition_lookup and settlement_oi_panel are
    merged on (date, instrument_id) -- a single-date key, safe from F6's
    instrument_id-reuse hazard by construction (a given (date, id) pair
    unambiguously identifies one real instrument on one real day; reuse
    only bites when instrument_id is used WITHOUT a date, which nothing in
    this module does).

    Filtered to instrument_class == 'F' (outright only, per F1). Adds
    `_contract_key` = instrument_id + "__" + expiration.date() -- the
    calendar DATE of expiration only, NOT the full timestamp, and NOT
    raw_symbol. Two identity hazards were found and fixed on this
    pipeline's first real-data runs, both a single real contract's own
    identifying fields drifting across its OWN listed lifetime (distinct
    from F6, which is instrument_id reused across DIFFERENT real
    contracts):

    F9 -- raw_symbol instability: instrument_id 551735 (a CL contract
    expiring 2019-05-21) appears as raw_symbol "CLM19" on its first 2
    listed days (2010-11-04/05) and "CLM9" for the remaining ~9 years
    through expiry. `raw_symbol + instrument_id` silently split one real
    contract's settlement/OI history across two spurious columns (caught
    via an implausible ~49% held-front missing-settlement rate
    concentrated from 2019 onward). Fixed by dropping raw_symbol from the
    key entirely.

    F10 -- expiration-timestamp correction: instrument_id 827180 (a KE
    contract) is recorded with expiration "2014-09-12 18:15:00" for its
    first 186 listed days (2013-12-15 to 2014-07-18) and
    "2014-09-12 17:01:00" for its remaining 48 (2014-07-20 to 2014-09-12)
    -- same calendar date, a mid-life metadata correction to the exact
    time. Keying on the full timestamp split this one contract's OI
    history into two fragments, and because the fragmentation happened to
    land exactly where an adjacent contract's roll should have occurred,
    roll.py's crossover condition (correctly implementing the F7
    hold-on-missing ruling) could never observe both sides of the
    crossover simultaneously again -- front froze permanently on the
    now-expired prior contract for the rest of the sample. Confirmed via
    audit_contract_key_unification() below: unifying 827180's two
    fragments restores 173 real, overlapping OI dates against the
    contract it should have rolled into. This is corrupted input, not a
    flaw in roll.py or the F7 ruling -- the ruling behaved exactly as
    specified once given a correctly-unified contract identity.

    Truncating expiration to its date component fixes both without
    reintroducing F6: two genuinely different real contracts sharing a
    reused instrument_id have been confirmed (docs/DATA_QA_REPORT.md's
    F6/F10 evidence) to differ in expiration by months to years, never by
    a same-day time-of-day correction, so a date-level match remains a
    safe disambiguator.
    """
    merged = definition_lookup.merge(settlement_oi_panel, on=["date", "instrument_id"], how="left")
    outright = merged[merged["instrument_class"] == "F"].copy()
    expiration_date = pd.to_datetime(outright["expiration"]).dt.date.astype(str)
    outright["_contract_key"] = outright["instrument_id"].astype(str) + "__" + expiration_date
    return outright


def audit_contract_key_unification(definition_lookup: pd.DataFrame) -> dict:
    """
    F10 fix audit (required by the Phase 1b Riders): for every outright
    (instrument_id, asset) pair with more than one distinct expiration
    TIMESTAMP, classifies it as either "unify" (all distinct timestamps
    share the same calendar date -- F9/F10-style same-contract metadata
    drift, correctly merged into one _contract_key by
    build_outright_panel()) or "keep_separate" (timestamps span different
    calendar dates -- genuine F6 instrument_id reuse across different real
    contracts, correctly kept as distinct _contract_keys). Asserts every
    fragment being unified shares the same `asset` -- a sanity check that
    unification never silently merges data across different commodities.

    Grouped by (instrument_id, asset), not instrument_id alone: real data
    surfaced an instrument_id reused across TWO DIFFERENT ASSETS entirely
    (id 60: both SI and GF), an even more extreme case of F6 than the
    within-asset reuse this audit originally anticipated. Cross-asset
    fragments can never be a same-contract metadata correction almost by
    definition and are always classified "keep_separate" without needing
    the date check at all -- build_outright_panel()'s per-symbol filtering
    (every symbol_*_wide() function filters to one asset before touching
    _contract_key) means a cross-asset _contract_key collision, if the
    calendar dates ever also happened to coincide, would not actually
    contaminate either symbol's own wide panel, but keeping the grouping
    asset-aware here is the correct, unambiguous audit regardless.

    Returns {"unify": [...], "keep_separate": [...], "n_unify": int,
    "n_keep_separate": int} -- one record per (instrument_id, asset) in
    each list, with the fragment-level (expiration_timestamp, n_rows,
    date_min, date_max) detail.
    """
    outright = definition_lookup[definition_lookup["instrument_class"] == "F"]
    per_id_asset_exp_count = outright.groupby(["instrument_id", "asset"])["expiration"].nunique()
    multi = per_id_asset_exp_count[per_id_asset_exp_count > 1].index  # MultiIndex of (instrument_id, asset)

    unify, keep_separate = [], []
    for iid, asset in multi:
        rows = outright[(outright["instrument_id"] == iid) & (outright["asset"] == asset)]
        assert (rows["asset"] == asset).all()  # true by construction of the groupby key; documents the invariant
        exps = rows["expiration"].unique()
        dates_only = set(pd.Timestamp(e).date() for e in exps)
        fragments = []
        for e in sorted(exps):
            frag_rows = rows[rows["expiration"] == e]
            fragments.append({
                "expiration": str(e), "n_rows": int(len(frag_rows)),
                "date_min": str(frag_rows["date"].min()), "date_max": str(frag_rows["date"].max()),
            })
        record = {"instrument_id": int(iid), "asset": asset, "fragments": fragments}
        if len(dates_only) == 1:
            unify.append(record)
        else:
            keep_separate.append(record)

    # instrument_ids reused across different assets entirely (e.g. id 60:
    # SI and GF) are, by construction of the (instrument_id, asset)
    # groupby above, never candidates for "unify" (their rows never share
    # a group at all) -- recorded separately for visibility, not folded
    # into keep_separate's per-asset counts, since they were never a
    # same-asset multi-expiration case to begin with.
    per_id_assets = outright.groupby("instrument_id")["asset"].nunique()
    cross_asset_ids = per_id_assets[per_id_assets > 1]
    cross_asset = []
    for iid in cross_asset_ids.index:
        rows = outright[outright["instrument_id"] == iid]
        cross_asset.append({"instrument_id": int(iid), "assets": sorted(rows["asset"].unique().tolist())})

    return {
        "unify": unify, "keep_separate": keep_separate, "cross_asset": cross_asset,
        "n_unify": len(unify), "n_keep_separate": len(keep_separate), "n_cross_asset": len(cross_asset),
    }


def assert_front_not_past_expiry(front_series: pd.Series, expiry_by_key: dict, asset: str) -> None:
    """
    Permanent tripwire (Phase 1b Riders): raises immediately if the held
    front contract's own expiration is before the date it is supposedly
    still held on -- the exact "stuck front" failure mode F10 caused and
    this fix resolves. A stuck front must be a loud, unmissable failure
    forever, never something that surfaces only as an implausible
    fill-rate statistic in a generated report (as F10 first did). Call
    this immediately after building front_series, before it feeds into
    any carry or return computation.
    """
    for date, contract in front_series.items():
        expiry = expiry_by_key.get(contract)
        if expiry is None:
            continue
        if pd.Timestamp(expiry) < pd.Timestamp(date):
            raise AssertionError(
                f"STUCK FRONT: {asset}'s held front contract {contract!r} expired {expiry} "
                f"but is still recorded as held on {date} -- the roll rule's crossover "
                f"condition never fired again after this contract's own data ended. This is "
                f"exactly the F10 failure mode; if it fires after the date-truncation fix, "
                f"it is a NEW, unexplained stuck-front instance requiring its own diagnosis, "
                f"not a silent pass-through."
            )


def symbol_listed_sequence(outright_panel: pd.DataFrame, asset: str) -> list:
    """Every distinct contract-instance (`_contract_key`) ever listed as an
    outright for `asset`, in exchange-listed expiry order (front-most
    first) -- the `listed_sequence` roll.compute_front_contract_series()
    needs."""
    sub = outright_panel[outright_panel["asset"] == asset]
    per_contract = sub.drop_duplicates(subset=["_contract_key"])[["_contract_key", "expiration"]]
    per_contract = per_contract.sort_values("expiration")
    return per_contract["_contract_key"].tolist()


def symbol_date_index(outright_panel: pd.DataFrame, asset: str) -> pd.DatetimeIndex:
    """Every distinct date `asset` has at least one outright row for --
    the single common row index symbol_oi_wide() and symbol_settle_wide()
    are both reindexed to, so the two panels (and anything derived from
    either one's index, e.g. front_series) are always aligned. Without
    this, pivot_table's own row set can differ subtly between the "oi" and
    "settlement" pivots (e.g. a date where one value happens to be present
    for at least one contract but the other is null for all of them),
    silently producing two same-symbol panels with different date indices
    -- exactly the failure this function exists to prevent (caught for
    real on the first real-data run of this pipeline: a KeyError inside
    held_front_zero_price_guard() when front_series, indexed off oi_wide,
    hit a date settle_wide didn't have)."""
    sub = outright_panel[outright_panel["asset"] == asset]
    return pd.DatetimeIndex(sorted(sub["date"].unique()))


def symbol_oi_wide(outright_panel: pd.DataFrame, asset: str, listed_sequence: list) -> pd.DataFrame:
    """(date x contract_key) wide OI panel for one symbol, for
    roll.compute_front_contract_series(). Reindexed to symbol_date_index()
    -- see that function's docstring for why this reindex is load-bearing,
    not defensive boilerplate."""
    sub = outright_panel[outright_panel["asset"] == asset]
    wide = sub.pivot_table(index="date", columns="_contract_key", values="oi", aggfunc="last")
    return wide.reindex(index=symbol_date_index(outright_panel, asset), columns=listed_sequence).sort_index()


def symbol_settle_wide(outright_panel: pd.DataFrame, asset: str, listed_sequence: list) -> pd.DataFrame:
    """(date x contract_key) wide settlement panel for one symbol, for
    returns.chain_returns(). Reindexed to symbol_date_index() -- see that
    function's docstring for why."""
    sub = outright_panel[outright_panel["asset"] == asset]
    wide = sub.pivot_table(index="date", columns="_contract_key", values="settlement", aggfunc="last")
    return wide.reindex(index=symbol_date_index(outright_panel, asset), columns=listed_sequence).sort_index()


def symbol_front_series(oi_wide: pd.DataFrame, listed_sequence: list) -> pd.Series:
    """Thin wrapper over roll.compute_front_contract_series() -- kept as
    its own function so the pipeline's per-symbol assembly order (build the
    OI panel, then the front series, then carry, then returns) is explicit
    and each step is independently callable/testable."""
    return roll_mod.compute_front_contract_series(oi_wide, listed_sequence)


def symbol_carry_series(outright_panel: pd.DataFrame, front_series: pd.Series,
                         listed_sequence: list, asset: str) -> pd.Series:
    """
    Sec 3 carry, amended by F11 Amendment A2 (DEVIATIONS.md, 2026-07-15):
    for each date, front = front_series.at[date]; next(t) is the
    earliest-expiration outright with expiration strictly greater than
    front's AND OI at t-1 strictly positive -- scanning forward through
    listed_sequence past the front's own position, skipping any listed-but-
    never-traded ("dead serial") candidate whose t-1 OI is missing or zero,
    landing on the first one that is genuinely OI-bearing. Same t-1 lag
    discipline as the A1 roll rule (never same-day OI): the OI used to
    decide date t's "next" is always t-1's, so this selection is exactly as
    look-ahead-safe as A1's front selection, just applied to a different
    role. Pre-A2, "next" was simply listed_sequence[pos + 1] regardless of
    whether that contract ever traded -- amended because F11's census found
    the serial-settlement quality check making dead-serial marks unfit for
    signal measurement (see DEVIATIONS.md's A2 entry for the full
    justification).

    Returns NaN for dates where: front isn't in listed_sequence; no later
    contract has strictly positive t-1 OI (A2's own "none exists" case,
    including every date for a front that IS the last-listed contract, and
    every symbol's very first date, where t-1 is structurally unobserved
    for everything); either settlement is missing; or the next-settlement
    is <= 0 (2026-07-11 ruling, unchanged by A2, checked after next(t) is
    selected). A NaN carry is a genuine "not computable" case, not an
    error.
    """
    sub = outright_panel[outright_panel["asset"] == asset]
    settle_by_key_date = sub.set_index(["_contract_key", "date"])["settlement"]
    oi_by_key_date = sub.set_index(["_contract_key", "date"])["oi"]
    expiry_by_key = sub.drop_duplicates(subset=["_contract_key"]).set_index("_contract_key")["expiration"]

    assert_front_not_past_expiry(front_series, expiry_by_key.to_dict(), asset)

    index_of = {key: i for i, key in enumerate(listed_sequence)}
    dates = list(front_series.index)
    prev_date_of = {dates[i]: dates[i - 1] for i in range(1, len(dates))}

    out_index, out_values = [], []
    for date, front_key in front_series.items():
        pos = index_of.get(front_key)
        if pos is None:
            out_index.append(date)
            out_values.append(float("nan"))
            continue

        # A2 next-selection: earliest-expiration later-listed outright with
        # strictly positive OI at t-1. front is last-listed (nothing after
        # it) and the series' first date (no t-1 at all) both fall through
        # to next_key staying None, exactly like the pre-A2 "no next" case.
        next_key = None
        t_minus_1 = prev_date_of.get(date)
        if t_minus_1 is not None:
            for candidate in listed_sequence[pos + 1:]:
                try:
                    oi_prev = oi_by_key_date.at[(candidate, t_minus_1)]
                except KeyError:
                    continue
                if pd.notna(oi_prev) and oi_prev > 0:
                    next_key = candidate
                    break

        if next_key is None:
            out_index.append(date)
            out_values.append(float("nan"))
            continue

        try:
            f_price = settle_by_key_date.at[(front_key, date)]
            n_price = settle_by_key_date.at[(next_key, date)]
        except KeyError:
            out_index.append(date)
            out_values.append(float("nan"))
            continue
        # Sec 3's carry formula divides by next_settle; a reported settlement
        # <= 0 is treated identically to a missing one (NaN) -- adjudicated
        # 2026-07-11, DEVIATIONS.md (Aaron + advisor), unchanged by A2: found on
        # this pipeline's first real-data run (RuntimeWarning: divide by zero),
        # not covered by Step 0's held-front-only zero-price guard. Almost
        # entirely far-dated, not-yet-actively-traded contracts CME lists
        # years ahead of real trading, reported as settlement=0.00 rather
        # than omitted (8,635 outright rows, 0.31%, all 18 symbols) -- not
        # economically meaningful data, so "not computable" (NaN) is the
        # symmetric extension of the pre-existing missing-data convention,
        # not a new threshold or parameter.
        if pd.isna(f_price) or pd.isna(n_price) or f_price <= 0 or n_price <= 0:
            out_index.append(date)
            out_values.append(float("nan"))
            continue
        f_exp, n_exp = expiry_by_key[front_key], expiry_by_key[next_key]
        try:
            c = carry_mod.compute_carry(f_price, n_price, f_exp, n_exp)
        except ValueError:
            c = float("nan")  # D <= 0 -- not expected for a genuinely-ordered listed_sequence, but never silently wrong
        out_index.append(date)
        out_values.append(c)

    return pd.Series(out_values, index=out_index)


def symbol_daily_returns(settle_wide: pd.DataFrame, front_series: pd.Series,
                          asset: str, cost_multiplier: float = 1.0) -> dict:
    """
    Applies the Phase 1b Step 0 specifications in order: mark-to-last-
    settlement fill, then the zero-price guard (checked against the RAW,
    pre-fill panel -- see returns.held_front_zero_price_guard's own
    docstring for why), then chain_returns().

    `asset` is passed through to chain_returns()'s `symbol` parameter --
    required here, not optional, because settle_wide's columns are
    `_contract_key` values (instrument_id + expiration, per
    build_outright_panel()'s docstring), which do not start with a
    parseable root-symbol prefix the way a raw contract code like "CLZ26"
    would; chain_returns()'s own _symbol_of() fallback cannot infer the
    root from a key in that shape, so relying on it here would raise.

    n_filled is the PRECISE held-front occurrence count
    (returns.count_held_front_missing_settlement()), not
    fill_missing_settlement_mark_to_last()'s whole-panel mask sum -- the
    settle_wide panel carries one column per contract ever listed for this
    symbol (~150-350 for the liquid roots), and at any date only one of
    those columns is the held front; summing the whole-panel mask counts
    every OTHER contract's unrelated missing cells too, which chain_returns()
    never reads and which are not a "held-front missing-settlement
    occurrence" in the Step 0 spec's sense (this produced an impossible
    >100% figure on this pipeline's first real-data run).

    Returns {"returns": pd.Series, "n_filled": int, "guard_violations": list}.
    Does not raise on a guard violation -- the caller (the runner script)
    decides what "HALT" means operationally; violations is simply non-empty.
    """
    violations = returns_mod.held_front_zero_price_guard(settle_wide, front_series)
    filled, _ = returns_mod.fill_missing_settlement_mark_to_last(settle_wide)
    n_filled = returns_mod.count_held_front_missing_settlement(settle_wide, front_series)
    daily_returns = returns_mod.chain_returns(filled, front_series, cost_multiplier=cost_multiplier, symbol=asset)
    return {"returns": daily_returns, "n_filled": n_filled, "guard_violations": violations}


def month_end_carry_panel(carry_by_symbol: dict, entry_dates: dict = None) -> pd.DataFrame:
    """
    Sec 2 month-end signal panel: last available daily carry value on or
    before each month-end date, per symbol. entry_dates defaults to
    config.py's frozen Sec 2 entry dates (dataset floor for 17 symbols,
    config.KE_ENTRY_DATE for KE) -- the QA-confirmed "first trading day"
    per symbol (docs/DATA_QA_REPORT.md, KE's entry date independently
    confirmed 4 times this project). No backfill before a symbol's entry
    date (data_loader.apply_entry_rule).
    """
    from .data_loader import apply_entry_rule
    if entry_dates is None:
        entry_dates = {s: config.SAMPLE_START for s in config.ALL_SYMBOLS}
        entry_dates["KE"] = config.KE_ENTRY_DATE

    all_dates = sorted(set().union(*[s.index for s in carry_by_symbol.values()]))
    calendar = build_month_end_calendar(pd.DatetimeIndex(all_dates))

    panel = {}
    for symbol, series in carry_by_symbol.items():
        series = series.sort_index()
        # last known value on/before each month-end -- asof-style lookup
        reindexed = series.reindex(series.index.union(calendar)).sort_index().ffill()
        panel[symbol] = reindexed.reindex(calendar)
    df = pd.DataFrame(panel, index=calendar)
    return apply_entry_rule(df, entry_dates)


def month_end_next_month_return_panel(daily_returns_by_symbol: dict, month_end_index: pd.DatetimeIndex,
                                       entry_dates: dict = None) -> pd.DataFrame:
    """
    For each month-end t in month_end_index, each symbol's compounded net
    return over the NEXT calendar month (t, t+1] -- i.e. from the day
    after month-end t through month-end t+1 inclusive -- aligned at index
    t, so that carry_panel.loc[t] and this panel's .loc[t] are directly
    comparable as (signal(t), realized-outcome-over-t-to-t+1) per Sec 7.
    """
    from .data_loader import apply_entry_rule
    if entry_dates is None:
        entry_dates = {s: config.SAMPLE_START for s in config.ALL_SYMBOLS}
        entry_dates["KE"] = config.KE_ENTRY_DATE

    panel = {}
    for symbol, daily in daily_returns_by_symbol.items():
        daily = daily.sort_index()
        values = []
        for i in range(len(month_end_index) - 1):
            t, t_next = month_end_index[i], month_end_index[i + 1]
            window = daily[(daily.index > t) & (daily.index <= t_next)]
            if len(window) == 0:
                values.append(float("nan"))
            else:
                values.append(float((1.0 + window).prod() - 1.0))
        values.append(float("nan"))  # no next month after the last month-end
        panel[symbol] = pd.Series(values, index=month_end_index)
    df = pd.DataFrame(panel, index=month_end_index)
    return apply_entry_rule(df, entry_dates)


def truncation_invariant_carry_panel(carry_by_symbol: dict, months_to_truncate: int, entry_dates: dict = None) -> pd.DataFrame:
    """
    Real-data truncation-invariance check (Phase 1b Step 1.2): rebuilds the
    month-end carry panel with the final `months_to_truncate` calendar
    months of daily data removed from every symbol's series, then returns
    the truncated panel for the caller to compare against the full panel
    (every signal up to the truncation date must be bit-identical).

    The truncated series' own LAST calendar month is almost always partial
    (the cutoff rarely lands exactly on a real month-end), and
    build_month_end_calendar() -- correctly, by its own contract -- treats
    whatever the last available trading day in that partial month is as
    that month's "month-end." That synthetic partial-month value is NOT a
    meaningful truncation-invariance check (the full series legitimately
    has more data in that same month, so the two are not expected to
    match) -- it is dropped from this function's output so the caller can
    compare its full return value against the corresponding slice of the
    full panel with no special-casing.
    """
    all_dates = sorted(set().union(*[s.index for s in carry_by_symbol.values()]))
    cutoff = pd.DatetimeIndex(all_dates).max() - pd.DateOffset(months=months_to_truncate)
    truncated = {symbol: series[series.index <= cutoff] for symbol, series in carry_by_symbol.items()}
    panel = month_end_carry_panel(truncated, entry_dates=entry_dates)
    return panel.iloc[:-1] if len(panel) > 0 else panel
