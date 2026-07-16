"""
Phase 1b premise-test runner. PREREGISTRATION.md Sec 7. Generates
reports/PREMISE_REPORT.md -- runner-generated, immutable once committed
(dated addenda only for any future correction, per the same convention as
docs/DATA_QA_REPORT.md).

Hard Rule 2 (Phase 1b/1c governing prompt): no API calls -- the corpus is
local and complete, loaded exclusively from DATA_DIR via src/pipeline.py.
This is the FIRST script in this project's history permitted to compute a
carry value, a return, a ranking, or a portfolio weight from real data.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\commodity-carry-research")
sys.path.insert(0, str(REPO))

from src import config, pipeline, premise  # noqa: E402

REPORT_PATH = REPO / "reports" / "PREMISE_REPORT.md"
TRUNCATION_MONTHS = 6

# The user-pre-authorized "NG single-day graze" (F11 amendment record;
# the governing prompt's own wording: "the NG single-day graze is the one
# known allowed artifact"). NG has TWO such instances, both already
# individually characterized as non-permanent in docs/DATA_QA_REPORT.md's
# F11 census (`_carry-research-workspace/stuck_episodes_classified.csv`) --
# same mechanism, same signature (0 days past expiry, resolves the very
# next trading day via a clean high-OI crossover). Both are the single
# named "NG single-day graze" phenomenon, not two different exceptions.
# Narrowly scoped to NG only -- ANY other symbol's firing (including HG's
# three grazes documented under the PRE-A1 rule, which A1's own Gate 1
# parity check already shows behaving differently and may not even recur
# under the amended rule) is treated as unverified and halts hard pending
# its own check, exactly like any firing that turns out to be permanent.
KNOWN_ALLOWED_TRANSIENT_GRAZES = {
    ("NG", "192047__2010-06-28"),
    ("NG", "192053__2010-12-28"),
}


def _entry_dates():
    entry = {s: pd.Timestamp(config.SAMPLE_START) for s in config.ALL_SYMBOLS}
    entry["KE"] = pd.Timestamp(config.KE_ENTRY_DATE)
    return entry


def _tz_naive(ts):
    return ts.tz_localize(None) if ts.tzinfo is not None else ts


def _find_stuck_front_violations(front_series, expiry_by_key):
    """Mirrors pipeline.assert_front_not_past_expiry()'s exact tz-safe
    comparison, but collects every violation instead of raising on the
    first -- gives the runner full visibility to apply the
    known-allowed-transient-graze check itself, rather than parsing an
    exception message. Does not change what counts as a violation."""
    violations = []
    for date, contract in front_series.items():
        expiry = expiry_by_key.get(contract)
        if expiry is None:
            continue
        if _tz_naive(pd.Timestamp(expiry)) < _tz_naive(pd.Timestamp(date)):
            violations.append((date, contract))
    return violations


def _check_tripwire(symbol, front, expiry_by_key):
    """Returns (ok_to_proceed: bool, skip_tripwire_for_carry: bool,
    disclosure: str or None). ok_to_proceed=False means HALT the whole run.
    skip_tripwire_for_carry=True is only ever returned alongside
    ok_to_proceed=True, for the one verified, known-allowed graze."""
    violations = _find_stuck_front_violations(front, expiry_by_key)
    if not violations:
        return True, False, None

    last_contract = front.iloc[-1]
    last_date = front.index.max()
    last_expiry = expiry_by_key.get(last_contract)
    permanent = last_expiry is not None and _tz_naive(pd.Timestamp(last_expiry)) < _tz_naive(pd.Timestamp(last_date))

    is_known_graze = not permanent and all((symbol, c) in KNOWN_ALLOWED_TRANSIENT_GRAZES for _, c in violations)
    if is_known_graze:
        disclosure = (
            f"{symbol}: known allowed transient graze(s), contract(s) "
            f"{sorted({c for _, c in violations})!r}, held on "
            f"{[str(d) for d, _ in violations]} -- non-permanent, resolves "
            f"the next trading day (F11 amendment record). Not a new "
            f"anomaly; continuing with skip_tripwire=True for this symbol's "
            f"carry computation only."
        )
        return True, True, disclosure

    detail = f"{symbol}: {violations[:5]}{'...' if len(violations) > 5 else ''} (permanent={permanent})"
    return False, False, detail


def main():
    entry_dates = _entry_dates()

    print("Loading definition lookup (real data, all 5,031 files)...", flush=True)
    definition_lookup = pipeline.build_definition_lookup()
    print(f"  {len(definition_lookup):,} rows", flush=True)

    print("Loading settlement/OI panel (real data, all 5,026 files)...", flush=True)
    settlement_oi_panel = pipeline.build_settlement_oi_panel()
    print(f"  {len(settlement_oi_panel):,} rows", flush=True)

    print("Building outright panel...", flush=True)
    outright_panel = pipeline.build_outright_panel(definition_lookup, settlement_oi_panel)
    print(f"  {len(outright_panel):,} outright rows", flush=True)

    carry_by_symbol, daily_returns_by_symbol = {}, {}
    n_filled_by_symbol, n_bars_by_symbol = {}, {}
    all_guard_violations = []
    known_graze_disclosures = []

    for symbol in config.ALL_SYMBOLS:
        print(f"Processing {symbol}...", flush=True)
        seq = pipeline.symbol_listed_sequence(outright_panel, symbol)
        if not seq:
            print(f"  WARNING: no outright contracts found for {symbol}, skipping", flush=True)
            continue
        oi_wide = pipeline.symbol_oi_wide(outright_panel, symbol, seq)
        settle_wide = pipeline.symbol_settle_wide(outright_panel, symbol, seq)
        front = pipeline.symbol_front_series(oi_wide, seq)

        # Permanent tripwire (Phase 1b Riders, post-F10): checked explicitly
        # here, at the earliest point front_series exists -- a stuck front
        # must be a loud, immediate failure, never silently discovered
        # downstream. Collects every violation (not just the first) so the
        # ONE user-pre-authorized transient graze (NG, non-permanent) can be
        # recognized and disclosed rather than crashing the whole run; any
        # OTHER violation, or this same one turning out permanent, still
        # halts exactly as before.
        expiry_by_key = (
            outright_panel[outright_panel["asset"] == symbol]
            .drop_duplicates(subset=["_contract_key"])
            .set_index("_contract_key")["expiration"].to_dict()
        )
        ok, skip_tripwire, disclosure = _check_tripwire(symbol, front, expiry_by_key)
        if not ok:
            print(f"STUCK FRONT (unexpected) -- HALTING. {disclosure}", flush=True)
            write_halt_report_stuck_front(symbol, disclosure)
            sys.exit(1)
        if skip_tripwire:
            print(f"  {disclosure}", flush=True)
            known_graze_disclosures.append(disclosure)

        carry = pipeline.symbol_carry_series(outright_panel, front, seq, symbol, skip_tripwire=skip_tripwire)
        ret_result = pipeline.symbol_daily_returns(settle_wide, front, symbol)

        carry_by_symbol[symbol] = carry
        daily_returns_by_symbol[symbol] = ret_result["returns"]
        n_filled_by_symbol[symbol] = ret_result["n_filled"]
        n_bars_by_symbol[symbol] = len(settle_wide)
        for v in ret_result["guard_violations"]:
            all_guard_violations.append((symbol,) + v)

    if all_guard_violations:
        print("ZERO-PRICE GUARD FIRED -- HALTING. This is a discovery, not an obstacle.", flush=True)
        for v in all_guard_violations:
            print(f"  {v}", flush=True)
        write_halt_report_guard(all_guard_violations)
        sys.exit(1)

    print("Running real-data truncation-invariance check...", flush=True)
    full_panel = pipeline.month_end_carry_panel(carry_by_symbol, entry_dates=entry_dates)
    truncated_panel = pipeline.truncation_invariant_carry_panel(carry_by_symbol, TRUNCATION_MONTHS, entry_dates=entry_dates)
    common_index = truncated_panel.index
    try:
        pd.testing.assert_frame_equal(full_panel.loc[common_index], truncated_panel, check_exact=True)
        print("  PASSED -- bit-identical.", flush=True)
    except AssertionError as e:
        print(f"  FAILED: {e}", flush=True)
        write_halt_report_truncation(str(e))
        sys.exit(1)

    month_end_index = full_panel.index
    return_panel = pipeline.month_end_next_month_return_panel(daily_returns_by_symbol, month_end_index, entry_dates=entry_dates)

    print("Running XS premise test...", flush=True)
    xs_result = premise.xs_premise_test(full_panel, return_panel)
    print("Running TS premise test...", flush=True)
    ts_result = premise.ts_premise_test(full_panel, return_panel)

    write_report(full_panel, return_panel, xs_result, ts_result, n_filled_by_symbol, n_bars_by_symbol,
                 entry_dates, known_graze_disclosures)
    print("Done. See reports/PREMISE_REPORT.md", flush=True)


def write_halt_report_stuck_front(symbol, disclosure):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Premise Report -- HALTED (unexpected stuck front)",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "**The permanent tripwire (`pipeline.assert_front_not_past_expiry`) "
        "fired on a violation that does NOT match a user-pre-authorized "
        f"transient graze** (known set: {sorted(KNOWN_ALLOWED_TRANSIENT_GRAZES)!r}). "
        "This is either a genuinely new stuck-front instance, a different "
        "symbol's own already-documented-but-not-yet-authorized graze (e.g. "
        "HG's, characterized under the pre-A1 rule and not yet confirmed to "
        "recur under A1), or a known graze turning out to be permanent -- "
        "either way, per the F11 amendment record, this requires its own "
        "check before any further computation. No premise test was "
        "computed.",
        "",
        "## Detail",
        "",
        f"- Symbol: {symbol}",
        f"- {disclosure}",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_halt_report_guard(violations):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Premise Report -- HALTED (zero-price guard fired)",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "**Phase 1b Step 0 specification: the zero-price guard halts the run "
        "if any held-front contract's settlement is <= 0 on any date.** This "
        "fired. Per the governing prompt: *\"if it fires, that is a discovery, "
        "not an obstacle.\"* No premise test was computed -- the pipeline "
        "stopped before reaching that stage.",
        "",
        "## Violations",
        "",
        "| Symbol | Date | Contract | Settlement |",
        "|---|---|---|---|",
    ]
    for symbol, date, contract, price in violations:
        lines.append(f"| {symbol} | {date} | {contract} | {price} |")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_halt_report_truncation(error_text):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Premise Report -- HALTED (truncation-invariance check failed)",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "**Phase 1b Step 1.2: recomputing the signal panel with the final "
        f"{TRUNCATION_MONTHS} months of raw data removed must produce "
        "bit-identical signals up to the truncation date.** It did not. No "
        "premise test was computed -- this indicates a look-ahead bug "
        "somewhere in the pipeline and must be fixed before any further "
        "computation, per the governing prompt: *\"Failure = HALT, finding, "
        "no further computation.\"*",
        "",
        "## Details",
        "",
        "```",
        error_text,
        "```",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_report(full_panel, return_panel, xs_result, ts_result, n_filled_by_symbol, n_bars_by_symbol,
                  entry_dates, known_graze_disclosures=None):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    def gate_label(passes):
        return "**PROCEEDS to Phase 1c**" if passes else "**CLOSES at premise (no backtest)**"

    total_filled = sum(n_filled_by_symbol.values())
    total_bars = sum(n_bars_by_symbol.values())

    lines = [
        "# Premise Report",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "Runner-generated, immutable once committed (dated addenda only for "
        "any future correction). PREREGISTRATION.md Sec 7. First real-data "
        "carry/return computation in this project's history.",
        "",
        "## Run-history disclosure",
        "",
        "Three prior pipeline runs were invalidated before this one, each by "
        "an integrity anomaly caught before any premise number was trusted "
        "-- never by a result direction. No directional memory of any "
        "invalidated run's numbers -- premise, primary, or otherwise -- "
        "informs anything below. This is the first valid premise "
        "computation in this project's history.",
        "",
        "| Run | Trigger anomaly | Root cause | Fix |",
        "|---|---|---|---|",
        "| 1 | `RuntimeWarning: divide by zero` inside `carry.compute_carry()` "
        "(GC, SI, PA) | 8,635 outright rows (0.31%, all 18 symbols) with "
        "`statistics` settlement <= 0 -- far-dated, not-yet-traded contracts "
        "reported as 0.00 rather than omitted | Next-contract settlement <= 0 "
        "treated as NaN, symmetric with missing-settlement handling "
        "(`DEVIATIONS.md`, 2026-07-11) |",
        "| 2 | Implausible ~49% held-front missing-settlement rate, "
        "concentrated from 2019 onward | F9: a single real contract's "
        "`raw_symbol` format drifts mid-life (instrument_id 551735: "
        "\"CLM19\" for 2 days, \"CLM9\" for ~9 more years), silently "
        "splitting one contract's OI/settlement history across two spurious "
        "`_contract_key` columns | Dropped `raw_symbol` from `_contract_key`; "
        "key is now `instrument_id + expiration.date()` |",
        "| 3 | Implausible 63.504% held-front missing-settlement rate; "
        "permanent-tripwire dead-front discovery on 13 of 18 symbols | F10: "
        "an `expiration` time-of-day correction mid-life (instrument_id "
        "827180, KE) fractured one contract's OI history, freezing the roll "
        "rule's crossover exactly where an adjacent contract's roll should "
        "have occurred -- and even after that identity fix, 11 of 18 "
        "symbols remained permanently stuck for a structurally different "
        "reason (F11): the single-candidate roll rule deadlocks whenever "
        "the immediately-next contract is a listed-but-illiquid (\"dead\") "
        "serial month | A1 (multi-candidate OI-max roll rule) + A2 "
        "(next-OI-bearing carry-next), adjudicated 2026-07-15 "
        "(`DEVIATIONS.md`) |",
        "",
        "**F12 mechanism note, for the fill-count table below.** The t-1 "
        "look-ahead discipline (Sec 3, unchanged by A1/A2) means the roll "
        "rule can only ever detect a real-market liquidity shift one day "
        "after it happens -- official OI is published T+1, so the roll "
        "always trails the market by exactly one day. When that shift is "
        "abrupt rather than gradual, the day this pipeline is still "
        "nominally holding the old contract for the return calculation is "
        "already a day the real market has moved on from it entirely, and "
        "CME may not publish anything for it that day -- confirmed absent "
        "from both `statistics` and `ohlcv-1d`, not lost anywhere in this "
        "pipeline. This is the cost of the look-ahead-safe design, not a "
        "defect: found 8 times, all on CL, against CL's own ~193 rolls in "
        "the sample (~4%), zero times on any other symbol (`F12`, "
        "`docs/DATA_QA_REPORT.md`).",
        "",
        "**Tripwire firings this run.** The permanent tripwire "
        "(`assert_front_not_past_expiry`) is checked for every symbol "
        "before its carry is computed. Any firing that does not exactly "
        "match the one user-pre-authorized transient graze below would "
        "have halted this run before reaching this report.",
        "",
    ]
    if known_graze_disclosures:
        lines += [f"- {d}" for d in known_graze_disclosures]
    else:
        lines += ["- None -- zero tripwire firings of any kind this run."]
    lines += [
        "",
        "## Pipeline integrity checks",
        "",
        "- **Roll rule and carry-next selection:** A1 (multi-candidate "
        "OI-max roll rule) and A2 (next-OI-bearing carry-next), per "
        "`DEVIATIONS.md` 2026-07-15 -- this run uses the amended pipeline "
        "throughout, verified against the validated read-only counterfactual "
        "before this run (`docs/DATA_QA_REPORT.md`, 2026-07-16 addendum, "
        "Gates 1-4).",
        "- **Zero-price guard (Step 0 spec):** silent -- no held-front "
        "settlement <= 0 was encountered across all 18 symbols' full "
        "history. (F2's confirmed negative CLK0 settlement on 2020-04-20 "
        "was correctly not the OI-determined front that day.)",
        "- **Next-contract settlement <= 0 in the carry formula (found and "
        "adjudicated this session, DEVIATIONS.md 2026-07-11):** treated as "
        "NaN (not computable), symmetric with missing-settlement handling. "
        "8,635 outright rows (0.31%) were affected across all 18 symbols "
        "before this fix, overwhelmingly far-dated not-yet-traded "
        "contracts; carry is NaN on the affected symbol-days rather than "
        "an undefined (inf/nan-from-division) value.",
        f"- **Truncation-invariance check (Step 1.2):** PASSED -- the "
        f"month-end carry panel recomputed with the final {TRUNCATION_MONTHS} "
        "months of raw data removed is bit-identical to the full panel up "
        "to the truncation date.",
        (f"- **Held-front missing-settlement fills (Step 0 spec, "
         f"mark-to-last + zero return, counted precisely per "
         f"returns.count_held_front_missing_settlement() -- only the "
         f"cells chain_returns() actually reads, not every column in the "
         f"wide panel):** {total_filled:,} occurrences across {total_bars:,} "
         f"trading days ({total_filled/total_bars:.3%})."
         if total_bars else ""),
        "",
        "| Symbol | Trading days | Missing-settlement fills |",
        "|---|---|---|",
    ]
    for symbol in config.ALL_SYMBOLS:
        if symbol in n_bars_by_symbol:
            lines.append(f"| {symbol} | {n_bars_by_symbol[symbol]:,} | {n_filled_by_symbol[symbol]:,} |")
    lines += [
        "",
        "## Universe and entry dates",
        "",
        "Per Sec 2 (no backfill); entry dates per config.py's frozen "
        "constants (dataset floor 2010-06-07 for 17 symbols, KE's "
        "confirmed 2013-12-16 entry).",
        "",
        f"- Month-end panel: {len(full_panel)} months, "
        f"{full_panel.index.min().date()} to {full_panel.index.max().date()}",
        f"- Symbols with data: {len(n_bars_by_symbol)} / {len(config.ALL_SYMBOLS)}",
        "",
        "## XS premise (Sec 7)",
        "",
        "Monthly cross-sectional Spearman rank IC between carry_i(t) and "
        "symbol i's next-month excess return, Newey-West(3)-adjusted "
        "t-statistic (lag fixed per DEVIATIONS.md 2026-07-11).",
        "",
        f"- Mean IC: **{xs_result['mean_ic']:.6f}**",
        f"- NW(3) t-statistic: {xs_result['tstat']:.4f}",
        f"- p-value: {xs_result['pvalue']:.4f}",
        f"- Months used: {xs_result['n_months']}",
        f"- **Gate verdict:** {gate_label(xs_result['gate_passes'])} "
        "(point estimate > 0 required to proceed; Sec 7's gate is mechanical "
        "on the sign of the point estimate alone, not significance)",
        "",
        "## TS premise (Sec 7)",
        "",
        "Pooled panel regression of next-month excess return on "
        "sign(carry_i(t)), standard errors clustered by month.",
        "",
        f"- Coefficient: **{ts_result['coefficient']:.6f}**",
        f"- Clustered t-statistic: {ts_result['tstat']:.4f}",
        f"- p-value: {ts_result['pvalue']:.4f}",
        f"- N (symbol-month observations): {ts_result['n_obs']:,}",
        f"- **Gate verdict:** {gate_label(ts_result['gate_passes'])}",
        "",
        "## Summary",
        "",
        "| Arm | Point estimate | Gate verdict |",
        "|---|---|---|",
        f"| H1 (XS) | {xs_result['mean_ic']:.6f} | {gate_label(xs_result['gate_passes'])} |",
        f"| H2 (TS) | {ts_result['coefficient']:.6f} | {gate_label(ts_result['gate_passes'])} |",
        "",
    ]
    if not xs_result["gate_passes"] and not ts_result["gate_passes"]:
        lines += [
            "**Both arms close at the premise stage.** Per Sec 7 and the "
            "governing prompt: *\"a premise-stage falsification is a "
            "complete, successful outcome of this study.\"* Phase 1c and "
            "Sec 8's robustness suite do not run. This report is the final "
            "quantitative output of Phase 1.",
        ]
    else:
        surviving = []
        if xs_result["gate_passes"]:
            surviving.append("H1 (XS)")
        if ts_result["gate_passes"]:
            surviving.append("H2 (TS)")
        lines += [f"**Surviving arm(s) proceeding to Phase 1c: {', '.join(surviving)}.**"]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
