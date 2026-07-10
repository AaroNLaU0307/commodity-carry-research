"""
Outright-only instrument filter. PREREGISTRATION.md Sec 2-3; F1 ruling
(WORKSPACE/PREREG_OPEN_ITEMS.md, "Aaron + advisor, decided blind to
results", dated in docs/DATA_QA_REPORT.md's addendum):

    Filtering to outright futures via the `definition` schema's
    instrument-class field is a clarification of the pre-registered
    universe, not a deviation -- Sec 2-3's "contracts" denote outright
    futures by design. Spread/combo instruments are a parent-symbology
    delivery artifact. Symbol-string heuristics are PROHIBITED as the
    filter mechanism.

This module is the ONLY place in the codebase permitted to classify
instruments as outright vs. spread/combo -- roll.py, carry.py, and every
downstream module consume its output rather than re-deriving the
distinction, so there is exactly one implementation to get right (same
principle as data_loader.py owning the symbol-entry rule).

OUTRIGHT_INSTRUMENT_CLASS is verified empirically against real delivered
`definition` data -- see docs/DATA_QA_REPORT.md's addendum for the actual
value(s) found in this dataset and the evidence for it. It is NOT assumed
from memory of the Databento spec, per the F1 ruling's explicit instruction.

instrument_id is NOT a globally-stable key across this dataset's 16-year
history -- Databento/CME recycle numeric instrument_ids once an instrument
is delisted. Empirically, ~20% of this dataset's outright instrument_ids
(668 of 3,314) were also assigned to at least one OTHER instrument (usually
a spread) at a different point in time -- see docs/DATA_QA_REPORT.md's
addendum, "F6: instrument_id reuse", for the confirmed example (id 4948:
a ZL spread in 2010, a PL spread later, the outright PLU5 in 2015, then
another PL spread). A join from `definition` onto `ohlcv-1d`/`statistics`
using a bare instrument_id set, ignoring date, silently misclassifies
recycled-ID rows. outright_instrument_ids() below enforces this at the API
boundary rather than leaving it as a footgun -- see its docstring.
"""
import pandas as pd

# Verified against real definition data pulled this session -- see
# docs/DATA_QA_REPORT.md addendum, "F1 filter: instrument_class values
# found" for the empirical evidence (value counts, sample rows) backing
# this constant.
OUTRIGHT_INSTRUMENT_CLASS = "F"  # Databento/DBZ convention: 'F' = Future (outright)


def filter_outright_only(definition_df: pd.DataFrame) -> pd.DataFrame:
    """
    definition_df : DataFrame from the `definition` schema (or a synthetic
        fixture with the same shape), must have an `instrument_class`
        column. Raises KeyError if that column is missing -- this filter
        refuses to silently fall back to any symbol-string heuristic if the
        real classification field isn't available, per the F1 ruling.

    Returns the subset of rows whose `instrument_class` equals
    OUTRIGHT_INSTRUMENT_CLASS. Symbol strings (hyphens, ":CF" suffixes,
    or anything else about the `raw_symbol`/`symbol` text) are never
    consulted -- see tests/test_instrument_filter.py for fixtures that
    deliberately try to fool a symbol-string-based filter and prove this
    one isn't one.
    """
    if "instrument_class" not in definition_df.columns:
        raise KeyError(
            "definition_df has no 'instrument_class' column -- cannot filter "
            "to outright-only without it. Refusing to fall back to a "
            "symbol-string heuristic (prohibited by the F1 ruling)."
        )
    return definition_df[definition_df["instrument_class"] == OUTRIGHT_INSTRUMENT_CLASS].copy()


def outright_instrument_ids(definition_df: pd.DataFrame) -> set:
    """Convenience: the set of instrument_id values (or raw_symbol, if
    instrument_id isn't present) for outright-only instruments, scoped to a
    SINGLE definition_df snapshot (one date).

    Raises ValueError if definition_df spans more than one distinct date
    (detected via a DatetimeIndex or a ts_recv/date/ts_event column).
    instrument_id is NOT a globally-stable key across this dataset's 16-year
    history -- Databento/CME recycle numeric instrument_ids once an
    instrument is delisted. Empirically ~20% of this dataset's outright
    instrument_ids (668 of 3,314) were also assigned to a different,
    usually non-outright, instrument at another point in time -- see
    docs/DATA_QA_REPORT.md's addendum, "F6: instrument_id reuse", for the
    confirmed example. A caller who unions this set across multiple days
    and then filters a multi-day ohlcv-1d/statistics frame by static
    membership WILL silently misclassify recycled-ID rows -- this guard
    exists so that mistake fails loudly instead. The correct pattern for a
    multi-day join is per-day: call this once per date and match
    ohlcv-1d/statistics rows to that SAME date's set, never a set unioned
    across dates.
    """
    outright = filter_outright_only(definition_df)

    date_values = None
    if isinstance(definition_df.index, pd.DatetimeIndex):
        date_values = definition_df.index.normalize().unique()
    else:
        for candidate in ("ts_recv", "date", "ts_event"):
            if candidate in definition_df.columns:
                date_values = pd.to_datetime(definition_df[candidate]).dt.normalize().unique()
                break
    if date_values is not None and len(date_values) > 1:
        raise ValueError(
            f"outright_instrument_ids() received a definition_df spanning "
            f"{len(date_values)} distinct dates -- instrument_id is reused "
            f"across this dataset's history (see module docstring, 'F6: "
            f"instrument_id reuse'), so a set unioned across dates would "
            f"silently misclassify rows. Call this once per date instead."
        )

    key_col = "instrument_id" if "instrument_id" in outright.columns else "raw_symbol"
    return set(outright[key_col])
