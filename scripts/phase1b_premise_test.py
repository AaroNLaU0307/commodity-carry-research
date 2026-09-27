"""
Phase 1b premise-test runner. PREREGISTRATION.md Sec 7. Writes
reports/rerun/PREMISE_REPORT.md and results/premise_summary.json (read by
the primary runner for the Sec 7 gate). The published
reports/PREMISE_REPORT.md is immutable and never written.

No API calls -- the corpus is local and read from config.DATA_DIR through
src/study.py (shared with every runner). Run alone with
`python scripts/phase1b_premise_test.py`, or as the first stage of
`python scripts/run_all.py`.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src import config, pipeline, premise, study  # noqa: E402

REPORT_PATH = config.RERUN_REPORTS_DIR / "PREMISE_REPORT.md"
RESULTS_PATH = config.RESULTS_DIR / "premise_summary.json"
TRUNCATION_MONTHS = 6


def main():
    try:
        ctx = study.load_context(log=lambda m: print(m, flush=True))
    except study.StudyHalt as halt:
        handle_halt(halt)
        sys.exit(1)
    if run(ctx) is None:
        sys.exit(1)


def handle_halt(halt: "study.StudyHalt") -> None:
    if halt.kind == "stuck_front":
        print(f"STUCK FRONT (unexpected) -- HALTING. {halt.detail['detail']}", flush=True)
        write_halt_report_stuck_front(halt.detail["symbol"], halt.detail["detail"])
    else:
        print("ZERO-PRICE GUARD FIRED -- HALTING. This is a discovery, not an obstacle.", flush=True)
        for v in halt.detail:
            print(f"  {v}", flush=True)
        write_halt_report_guard(halt.detail)


def run(ctx: "study.StudyContext"):
    """Truncation check, both premise tests at the registered timing and
    the execution-lag-1 sensitivity; writes the report and the JSON.
    Returns the summary dict, or None if the truncation check halted."""
    entry_dates = ctx.entry_dates
    print("Running real-data truncation-invariance check...", flush=True)
    full_panel = ctx.carry_panel
    truncated_panel = pipeline.truncation_invariant_carry_panel(ctx.carry, TRUNCATION_MONTHS, entry_dates=entry_dates)
    try:
        pd.testing.assert_frame_equal(full_panel.loc[truncated_panel.index], truncated_panel, check_exact=True)
        print("  PASSED -- bit-identical.", flush=True)
    except AssertionError as e:
        print(f"  FAILED: {e}", flush=True)
        write_halt_report_truncation(str(e))
        return None

    month_end_index = full_panel.index
    returns = ctx.returns[1.0]
    results = {}
    for lag in (config.EXECUTION_LAG_PRIMARY, config.EXECUTION_LAG_SENSITIVITY):
        return_panel = pipeline.month_end_next_month_return_panel(
            returns, month_end_index, entry_dates=entry_dates, execution_lag=lag)
        print(f"Running XS and TS premise tests (execution_lag={lag})...", flush=True)
        results[lag] = (premise.xs_premise_test(full_panel, return_panel),
                        premise.ts_premise_test(full_panel, return_panel))
    xs_result, ts_result = results[config.EXECUTION_LAG_PRIMARY]

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "code_version": study.code_version(),
        "execution_lag": config.EXECUTION_LAG_PRIMARY,
        "months": len(full_panel),
        "month_end_first": str(full_panel.index.min().date()),
        "month_end_last": str(full_panel.index.max().date()),
        "trading_days_by_symbol": ctx.n_bars,
        "statistics_diagnostics": ctx.statistics_diagnostics,
        "xs": _xs_json(xs_result),
        "ts": _ts_json(ts_result),
        "sensitivity_execution_lag_1": {
            "xs": _xs_json(results[config.EXECUTION_LAG_SENSITIVITY][0]),
            "ts": _ts_json(results[config.EXECUTION_LAG_SENSITIVITY][1]),
        },
        "gate": {"H1": bool(xs_result["gate_passes"]), "H2": bool(ts_result["gate_passes"])},
    }
    study.write_json(RESULTS_PATH, summary)
    write_report(full_panel, xs_result, ts_result, results[config.EXECUTION_LAG_SENSITIVITY], ctx.n_filled,
                 ctx.n_bars, ctx.graze_disclosures, ctx.statistics_diagnostics, summary["code_version"])
    print(f"Done. See {REPORT_PATH} and {RESULTS_PATH}", flush=True)
    return summary


def _xs_json(r):
    return {"mean_ic": r["mean_ic"], "tstat": r["tstat"], "pvalue": r["pvalue"], "n_months": r["n_months"],
            "nw_lags": r["nw_lags"], "gate_passes": bool(r["gate_passes"])}


def _ts_json(r):
    return {"coefficient": r["coefficient"], "tstat": r["tstat"], "pvalue": r["pvalue"], "n_obs": r["n_obs"],
            "gate_passes": bool(r["gate_passes"])}


def write_halt_report_stuck_front(symbol, disclosure):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Premise Report -- HALTED (unexpected stuck front)",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "**The permanent tripwire (`pipeline.assert_front_not_past_expiry`) "
        "fired on a violation that does NOT match a user-pre-authorized "
        f"transient graze** (known set: {sorted(study.KNOWN_ALLOWED_TRANSIENT_GRAZES)!r}). "
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


def write_report(full_panel, xs_result, ts_result, lag1_results, n_filled_by_symbol, n_bars_by_symbol,
                  known_graze_disclosures=None, statistics_diagnostics=None, code_version="unknown"):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    statistics_diagnostics = statistics_diagnostics or {}

    def gate_label(passes):
        return "**PROCEEDS to Phase 1c**" if passes else "**CLOSES at premise (no backtest)**"

    total_filled = sum(n_filled_by_symbol.values())
    total_bars = sum(n_bars_by_symbol.values())

    lines = [
        "# Premise Report",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()} · code `{code_version}`",
        "",
        ("Runner-generated (`scripts/phase1b_premise_test.py`). PREREGISTRATION.md "
         "Sec 7. This run follows the 2026-09-27 corrections "
         "(`reports/ADDENDUM_2026-09-27.md`: trade-date calendar, open-interest "
         "field, execution timing). Run 4's published report, "
         "`reports/PREMISE_REPORT.md`, stays unchanged as the pre-correction record."),
        "",
        "## Run-history disclosure",
        "",
        ("Runs 1-3 were invalidated, each by an integrity anomaly caught before "
         "any premise number was trusted -- never by a result direction. Run 4 "
         "(commit 543d271) was the first valid premise computation; it keyed "
         "statistics on the delivery file's UTC date (Sunday rows) and read "
         "CLEARED_VOLUME as open interest, and is superseded by this run."),
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
        ("| 4 | Published 2026-07-16; not invalidated by an anomaly in its own "
         "output | Statistics keyed on the file's UTC date (Sunday re-sends "
         "became trading days, ~313 rows/yr) and `stat_type` 6 "
         "(CLEARED_VOLUME) used as open interest | Trade-date (`ts_ref`) "
         "keying, session calendar, `StatType.OPEN_INTEREST` "
         "(`reports/ADDENDUM_2026-09-27.md`) |"),
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
        ("- **Trade-date keying (2026-09-27):** every settlement/OI value keyed "
         "on its `ts_ref` trade date; a symbol's calendar is the trade dates "
         "with at least one published settlement or OI. Statistics diagnostics: "
         f"{statistics_diagnostics.get('n_weekend_trade_date_dropped', 'n/a')} "
         "weekend-dated records dropped, "
         f"{statistics_diagnostics.get('n_undefined_ts_ref', 'n/a')} records "
         "without a `ts_ref` dropped, "
         f"{statistics_diagnostics.get('n_deleted', 'n/a')} DELETE records "
         "applied. Open interest = `StatType.OPEN_INTEREST`."),
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
        ("- Timing: execution_lag = 0 (registered; month-end t's outcome window "
         "starts with settle(t) -> settle(t+1), "
         "`preregistration/AMENDMENT_2026-09-27.md`)."),
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
    lag1_xs, lag1_ts = lag1_results
    lines += [
        "## Sensitivity: execution one trading day after the signal (non-gating)",
        "",
        ("Registered by `preregistration/AMENDMENT_2026-09-27.md`: the same tests "
         "with each month's outcome window shifted one trading row (first "
         "return settle(t+1) -> settle(t+2)). Reported beside the registered "
         "result; the gate above is decided at execution_lag = 0 only."),
        "",
        "| Arm | Point estimate | t-statistic | p-value |",
        "|---|---|---|---|",
        f"| H1 (XS) mean IC | {lag1_xs['mean_ic']:.6f} | {lag1_xs['tstat']:.4f} | {lag1_xs['pvalue']:.4f} |",
        f"| H2 (TS) coefficient | {lag1_ts['coefficient']:.6f} | {lag1_ts['tstat']:.4f} | {lag1_ts['pvalue']:.4f} |",
        "",
    ]
    if not xs_result["gate_passes"] and not ts_result["gate_passes"]:
        lines += [
            "**Both arms close at the premise stage.** Per Sec 7 and the "
            "governing prompt: *\"a premise-stage falsification is a "
            "complete, successful outcome of this study.\"* Phase 1c and "
            "Sec 8's robustness suite do not run (`scripts/run_all.py` stops "
            "here). This report is the final quantitative output of Phase 1.",
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
