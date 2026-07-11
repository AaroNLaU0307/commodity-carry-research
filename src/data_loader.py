"""
Data loading, calendar, and symbol-entry rule. PREREGISTRATION.md Sec 2.

Loads the pulled DBN files from DATA_DIR (never committed to the repo --
see data/README.md and .gitignore) into pandas structures, and implements
the Sec 2 symbol-entry rule: a symbol enters the cross-section (H1) or the
traded set (H2) at the first month-end where its carry signal is
computable from available data -- no backfill before that date, no
exclusion of the symbol once entered.

This module's DBN-reading functions require the `databento` package and
real files in DATA_DIR; they are exercised only against real data manually
(Phase 1a QA), never in the automated test suite, which uses the
build_month_end_calendar() / apply_entry_rule() functions below against
synthetic panels instead (Hard Rule 1 of the Phase 1a brief: real data
never flows through the signal path in this session).
"""
from pathlib import Path

import pandas as pd

from . import config


def load_dbn(schema: str, data_dir: Path = None) -> "databento.DBNStore":
    """Loads one schema's single-file DBN delivery from DATA_DIR (currently
    only `ohlcv-1d`, delivered as one file). Local import of databento keeps
    it optional for the synthetic-only test suite."""
    import databento as db
    data_dir = config.DATA_DIR if data_dir is None else data_dir
    path = Path(data_dir) / f"{schema}.dbn.zst"
    if not path.exists():
        raise FileNotFoundError(f"Expected {schema} data at {path} -- has the Phase 1a corpus pull run?")
    return db.DBNStore.from_file(path)


def load_dbn_partitioned(schema: str, data_dir: Path = None) -> pd.DataFrame:
    """Loads a per-day-partitioned DBN delivery (`definition`, `statistics`
    -- Databento batch jobs default to `split_duration="day"`) from
    DATA_DIR/{schema}/*.dbn.zst, concatenated into one DataFrame with a
    DatetimeIndex preserved from each file.

    Looks ONLY inside DATA_DIR/{schema}/ -- never at loose
    DATA_DIR/{schema}_*.dbn.zst files. This is a deliberate, load-bearing
    restriction, not an incidental implementation detail: session 1 pulled
    `statistics` as ad hoc yearly chunks (`statistics_2010-06-06_2011-01-01
    .dbn.zst` etc.) before the batch-job API was adopted; those chunks are
    billed provenance and are retained in DATA_DIR/_superseded/ (never
    DATA_DIR/{schema}/) precisely so this function cannot resolve them even
    by accident -- see docs/DATA_QA_REPORT.md's addenda for the full
    single-provenance rationale. Mixing chunk-era and batch-era files into
    one carry/roll computation would silently blend two different pull
    mechanisms' worth of data into what must be one clean, auditable
    dataset.

    Raises FileNotFoundError if DATA_DIR/{schema}/ doesn't exist or is
    empty, rather than silently returning an empty/partial result.
    """
    import databento as db
    data_dir = config.DATA_DIR if data_dir is None else data_dir
    schema_dir = Path(data_dir) / schema
    if not schema_dir.is_dir():
        raise FileNotFoundError(
            f"Expected a per-day-partitioned {schema} delivery at {schema_dir} "
            f"(a directory) -- has the Phase 1a batch-job pull completed?"
        )
    files = sorted(schema_dir.glob("*.dbn.zst"))
    if not files:
        raise FileNotFoundError(f"{schema_dir} exists but contains no .dbn.zst files.")
    frames = [db.DBNStore.from_file(f).to_df() for f in files]
    return pd.concat(frames)


def build_month_end_calendar(daily_index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Sec 2: monthly rebalance frequency. Returns the last trading day of
    each calendar month present in `daily_index` (not a generic
    calendar-month-end, which might not be a trading day)."""
    s = pd.Series(daily_index, index=daily_index)
    month_ends = s.groupby([daily_index.year, daily_index.month]).max()
    return pd.DatetimeIndex(sorted(month_ends.values))


def apply_entry_rule(carry_by_symbol: pd.DataFrame, entry_dates: dict) -> pd.DataFrame:
    """
    Sec 2 symbol-entry rule: a symbol enters at the first month-end its
    carry signal is computable -- no backfill, no exclusion once entered.

    carry_by_symbol : DataFrame indexed by month-end date, one column per
        symbol, values = that month's carry (may already be non-null only
        from each symbol's true first-computable date, or may contain
        leading NaNs that this function will null out defensively based on
        entry_dates, guarding against accidental backfill upstream).
    entry_dates : {symbol: pd.Timestamp} -- each symbol's first live
        month-end, e.g. config.KE_ENTRY_DATE for KE, dataset-floor month-end
        for the other 17.

    Returns a copy of carry_by_symbol with every value before a symbol's
    entry date forced to NaN (defense in depth against upstream backfill),
    and every value from the entry date onward left untouched even if NaN
    (a genuine data gap after entry is not "backfill" and is not this
    function's concern -- see the QA findings register for real gaps).
    """
    out = carry_by_symbol.copy()
    for symbol in out.columns:
        entry = entry_dates.get(symbol)
        if entry is None:
            continue
        entry = pd.Timestamp(entry)
        out.loc[out.index < entry, symbol] = float("nan")
    return out


def live_symbols_at(month_end: pd.Timestamp, entry_dates: dict) -> list:
    """Which symbols are live (entered) as of a given month-end -- e.g. 17
    before config.KE_ENTRY_DATE's month, 18 from then on."""
    month_end = pd.Timestamp(month_end)
    return [s for s, entry in entry_dates.items() if pd.Timestamp(entry) <= month_end]
