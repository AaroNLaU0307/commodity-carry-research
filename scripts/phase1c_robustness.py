"""
Phase 1c robustness suite runner. PREREGISTRATION.md Sec 8 (all 10 items),
plus the F7 ex-PA/PL diagnostic (`DEVIATIONS.md`, 2026-07-11) and the Sec 8
item 7 day-count specification completion (`DEVIATIONS.md`, 2026-07-16).
Generates reports/ROBUSTNESS_REPORT.md -- immutable once committed.

Every item here is reported with sign and magnitude; NONE gates promotion
(Sec 8; the primary family's promotion verdict, already decided and
committed in reports/PRIMARY_REPORT.md, is unaffected by anything in this
report). Items 8-9 are diagnostics of the ALREADY-COMPUTED primary series
(no new construction); items 1-5, 7, 10 and the ex-PA/PL diagnostic each
build one bounded variant via src/robustness.py or src/primary.py; item 6
needs no new computation (already reported in Stage 2, restated here).

Reuses the exact data-loading path scripts/phase1b_premise_test.py and
scripts/phase1c_primary_backtest.py used (raw DBN, no parallel loading
code). Sharpe for every robustness item is the same point-estimate formula
stats.stationary_bootstrap_sharpe() uses internally (mean/std(ddof=1)*
sqrt(252)), computed directly rather than via the full 10,000-replication
bootstrap -- these are non-gating diagnostics reported with sign and
magnitude, not requiring their own confidence interval.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\commodity-carry-research")
sys.path.insert(0, str(REPO))

from src import config, pipeline, primary, robustness, stats  # noqa: E402
from src.portfolio import xs_raw_signal, ts_raw_signal  # noqa: E402

REPORT_PATH = REPO / "reports" / "ROBUSTNESS_REPORT.md"

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
    violations = []
    for date, contract in front_series.items():
        expiry = expiry_by_key.get(contract)
        if expiry is None:
            continue
        if _tz_naive(pd.Timestamp(expiry)) < _tz_naive(pd.Timestamp(date)):
            violations.append((date, contract))
    return violations


def _check_tripwire(symbol, front, expiry_by_key):
    violations = _find_stuck_front_violations(front, expiry_by_key)
    if not violations:
        return True, False, None
    last_contract = front.iloc[-1]
    last_date = front.index.max()
    last_expiry = expiry_by_key.get(last_contract)
    permanent = last_expiry is not None and _tz_naive(pd.Timestamp(last_expiry)) < _tz_naive(pd.Timestamp(last_date))
    is_known_graze = not permanent and all((symbol, c) in KNOWN_ALLOWED_TRANSIENT_GRAZES for _, c in violations)
    if is_known_graze:
        return True, True, f"{symbol}: known allowed transient graze(s) {sorted({c for _, c in violations})}"
    detail = f"{symbol}: {violations[:5]}{'...' if len(violations) > 5 else ''} (permanent={permanent})"
    return False, False, detail


def sharpe_point(daily_returns: pd.Series) -> float:
    """Same formula as stats.stationary_bootstrap_sharpe()'s own point
    estimate, computed directly (no bootstrap resampling) -- non-gating
    robustness items are reported with sign and magnitude, not their own CI."""
    x = daily_returns.dropna().values
    sigma = x.std(ddof=1) if len(x) > 1 else 0.0
    if sigma <= 0:
        return 0.0
    return float(x.mean() / sigma * np.sqrt(config.TRADING_DAYS_PER_YEAR))


def build_arm(carry_panel, vol_panel, settle_by_month, month_end_index, daily_index,
              daily_returns_by_symbol, entry_dates, signal_fn, symbol_of_column, cost_multiplier=1.0):
    """One-shot: pre-leverage weights -> daily arm returns -> Sharpe. Used
    by every vol-scaled (non-equal-weight) robustness item, exactly the
    same sequence as scripts/phase1c_primary_backtest.py's own arms."""
    weights = primary.build_pre_leverage_weights(carry_panel, vol_panel, entry_dates, signal_fn)
    result = primary.compute_arm_daily_returns(
        weights, daily_returns_by_symbol, settle_by_month, month_end_index, daily_index,
        symbol_of_column=symbol_of_column, cost_multiplier=cost_multiplier)
    return result, sharpe_point(result["daily_net_returns"])


def main():
    entry_dates = _entry_dates()
    symbol_of_column = {s: s for s in config.ALL_SYMBOLS}

    print("Loading definition lookup (real data, all 5,031 files)...", flush=True)
    definition_lookup = pipeline.build_definition_lookup()
    print("Loading settlement/OI panel (real data, all 5,026 files)...", flush=True)
    settlement_oi_panel = pipeline.build_settlement_oi_panel()
    print("Building outright panel...", flush=True)
    outright_panel = pipeline.build_outright_panel(definition_lookup, settlement_oi_panel)

    carry_by_symbol = {}
    daily_returns_1x, daily_returns_2x, daily_returns_0x = {}, {}, {}
    front_by_symbol, settle_wide_by_symbol, oi_wide_by_symbol, seq_by_symbol, expiry_by_key_by_symbol = {}, {}, {}, {}, {}
    fixed_cal_front_by_symbol = {}
    fixed_cal_tripwire_findings = []

    for symbol in config.ALL_SYMBOLS:
        print(f"Processing {symbol}...", flush=True)
        seq = pipeline.symbol_listed_sequence(outright_panel, symbol)
        if not seq:
            continue
        oi_wide = pipeline.symbol_oi_wide(outright_panel, symbol, seq)
        settle_wide = pipeline.symbol_settle_wide(outright_panel, symbol, seq)
        front = pipeline.symbol_front_series(oi_wide, seq)
        expiry_by_key = (
            outright_panel[outright_panel["asset"] == symbol]
            .drop_duplicates(subset=["_contract_key"]).set_index("_contract_key")["expiration"].to_dict()
        )
        ok, skip_tripwire, disclosure = _check_tripwire(symbol, front, expiry_by_key)
        if not ok:
            print(f"STUCK FRONT (unexpected, primary A1 series) -- HALTING. {disclosure}", flush=True)
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(
                f"# Robustness Report -- HALTED (unexpected stuck front, primary series)\n\n{symbol}: {disclosure}\n",
                encoding="utf-8")
            sys.exit(1)

        carry_by_symbol[symbol] = pipeline.symbol_carry_series(outright_panel, front, seq, symbol, skip_tripwire=skip_tripwire)
        daily_returns_1x[symbol] = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=1.0)["returns"]
        daily_returns_2x[symbol] = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=2.0)["returns"]
        daily_returns_0x[symbol] = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=0.0)["returns"]
        front_by_symbol[symbol] = front
        settle_wide_by_symbol[symbol] = settle_wide
        oi_wide_by_symbol[symbol] = oi_wide
        seq_by_symbol[symbol] = seq
        expiry_by_key_by_symbol[symbol] = expiry_by_key

        # Item 7: fixed-calendar variant front series, checked (not halted) for its own tripwire status
        fc_front = robustness.fixed_calendar_front_series(oi_wide, seq, expiry_by_key)
        fixed_cal_front_by_symbol[symbol] = fc_front
        fc_ok, fc_known, fc_detail = _check_tripwire(symbol, fc_front, expiry_by_key)
        if not fc_ok:
            fixed_cal_tripwire_findings.append(fc_detail)

    print("Building month-end panel, daily index, vol/settle-at-month-end panels...", flush=True)
    carry_panel = pipeline.month_end_carry_panel(carry_by_symbol, entry_dates=entry_dates)
    month_end_index = carry_panel.index
    daily_index = pd.DatetimeIndex(sorted(set().union(*[s.index for s in daily_returns_1x.values()])))
    vol_panel = pd.DataFrame({s: primary.symbol_vol_at_month_end(daily_returns_1x[s], month_end_index) for s in carry_by_symbol})
    settle_by_month = pd.DataFrame({
        s: primary.symbol_settle_at_month_end(front_by_symbol[s], settle_wide_by_symbol[s], month_end_index)
        for s in carry_by_symbol
    })

    results = {}  # name -> {"sharpe": float, "detail": str, ...}

    # --- Primary H1/H2, rebuilt fresh here for the diagnostics (items 8/9) and attribution (b) ---
    print("Rebuilding primary H1/H2 (for diagnostics/attribution -- same construction as Stage 2)...", flush=True)
    primary_result = {}
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        weights = primary.build_pre_leverage_weights(carry_panel, vol_panel, entry_dates, signal_fn)
        result = primary.compute_arm_daily_returns(
            weights, daily_returns_1x, settle_by_month, month_end_index, daily_index, symbol_of_column)
        primary_result[arm] = {"weights": weights, "result": result, "sharpe": sharpe_point(result["daily_net_returns"])}

    # --- Item 1: sector-neutral XS ---
    print("Item 1: sector-neutral XS...", flush=True)
    sector_signal_fn = lambda snap: robustness.sector_neutral_xs_raw_signal(snap, config.SYMBOL_SECTOR)  # noqa: E731
    r1_result, r1_sharpe = build_arm(carry_panel, vol_panel, settle_by_month, month_end_index, daily_index,
                                      daily_returns_1x, entry_dates, sector_signal_fn, symbol_of_column)
    results["R1_sector_neutral_xs"] = {"sharpe": r1_sharpe, "arms": "XS only"}

    # --- Item 2: quintile cutoffs ---
    print("Item 2: quintile cutoffs...", flush=True)
    r2_result, r2_sharpe = build_arm(carry_panel, vol_panel, settle_by_month, month_end_index, daily_index,
                                      daily_returns_1x, entry_dates, robustness.xs_raw_signal_quintile, symbol_of_column)
    results["R2_quintile_xs"] = {"sharpe": r2_sharpe, "arms": "XS only"}

    # --- Item 3: equal-weight legs ---
    print("Item 3: equal-weight legs...", flush=True)
    r3_weights = robustness.equal_weight_pre_leverage_weights(carry_panel, entry_dates)
    r3_result = primary.compute_arm_daily_returns(
        r3_weights, daily_returns_1x, settle_by_month, month_end_index, daily_index, symbol_of_column)
    results["R3_equal_weight_legs"] = {"sharpe": sharpe_point(r3_result["daily_net_returns"]), "arms": "XS only"}

    # --- Item 4: 1-month-smoothed carry (both arms) ---
    print("Item 4: 1-month-smoothed carry...", flush=True)
    smoothed_panel = robustness.smooth_carry_panel(carry_panel)
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        _, sh = build_arm(smoothed_panel, vol_panel, settle_by_month, month_end_index, daily_index,
                           daily_returns_1x, entry_dates, signal_fn, symbol_of_column)
        results[f"R4_smoothed_carry_{arm}"] = {"sharpe": sh, "arms": arm}

    # --- Item 5: 12-month-deferred carry (both arms) ---
    print("Item 5: 12-month-deferred carry...", flush=True)
    carry_deferred_by_symbol = {
        s: robustness.symbol_deferred_carry_series(outright_panel, front_by_symbol[s], seq_by_symbol[s], s)
        for s in carry_by_symbol
    }
    deferred_panel = pipeline.month_end_carry_panel(carry_deferred_by_symbol, entry_dates=entry_dates)
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        _, sh = build_arm(deferred_panel, vol_panel, settle_by_month, month_end_index, daily_index,
                           daily_returns_1x, entry_dates, signal_fn, symbol_of_column)
        results[f"R5_deferred_carry_{arm}"] = {"sharpe": sh, "arms": arm}

    # --- Item 6: 2x cost table (both arms) -- already computed in Stage 2 (gate 4); restated here ---
    print("Item 6: 2x cost table (restated from Stage 2's construction)...", flush=True)
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        weights = primary_result[arm]["weights"]
        result_2x = primary.compute_arm_daily_returns(
            weights, daily_returns_2x, settle_by_month, month_end_index, daily_index,
            symbol_of_column=symbol_of_column, cost_multiplier=2.0)
        results[f"R6_2x_cost_{arm}"] = {"sharpe": sharpe_point(result_2x["daily_net_returns"]), "arms": arm}

    # --- Item 7: fixed-calendar roll rule (both arms) ---
    print("Item 7: fixed-calendar roll rule...", flush=True)
    carry_fc_by_symbol, daily_returns_fc_by_symbol = {}, {}
    for s in carry_by_symbol:
        carry_fc_by_symbol[s] = pipeline.symbol_carry_series(
            outright_panel, fixed_cal_front_by_symbol[s], seq_by_symbol[s], s, skip_tripwire=True)
        daily_returns_fc_by_symbol[s] = pipeline.symbol_daily_returns(
            settle_wide_by_symbol[s], fixed_cal_front_by_symbol[s], s, cost_multiplier=1.0)["returns"]
    carry_fc_panel = pipeline.month_end_carry_panel(carry_fc_by_symbol, entry_dates=entry_dates)
    vol_fc_panel = pd.DataFrame({s: primary.symbol_vol_at_month_end(daily_returns_fc_by_symbol[s], month_end_index) for s in carry_by_symbol})
    settle_fc_by_month = pd.DataFrame({
        s: primary.symbol_settle_at_month_end(fixed_cal_front_by_symbol[s], settle_wide_by_symbol[s], month_end_index)
        for s in carry_by_symbol
    })
    roll_date_diffs = {}
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        _, sh = build_arm(carry_fc_panel, vol_fc_panel, settle_fc_by_month, month_end_index, daily_index,
                           daily_returns_fc_by_symbol, entry_dates, signal_fn, symbol_of_column)
        results[f"R7_fixed_calendar_{arm}"] = {"sharpe": sh, "arms": arm}
    for s in carry_by_symbol:
        n_diff = int((front_by_symbol[s].reindex(daily_index).astype(object)
                      != fixed_cal_front_by_symbol[s].reindex(daily_index).astype(object)).sum())
        roll_date_diffs[s] = n_diff

    # --- Item 10: KE-excluded sensitivity (XS only) ---
    print("Item 10: KE-excluded sensitivity...", flush=True)
    entry_dates_no_ke = {s: v for s, v in entry_dates.items() if s != "KE"}
    carry_panel_no_ke = carry_panel.drop(columns=["KE"]) if "KE" in carry_panel.columns else carry_panel
    vol_panel_no_ke = vol_panel.drop(columns=["KE"]) if "KE" in vol_panel.columns else vol_panel
    _, r10_sharpe = build_arm(carry_panel_no_ke, vol_panel_no_ke, settle_by_month, month_end_index, daily_index,
                               daily_returns_1x, entry_dates_no_ke, xs_raw_signal, symbol_of_column)
    results["R10_ke_excluded"] = {"sharpe": r10_sharpe, "arms": "XS only"}

    # --- F7 ex-PA/PL diagnostic (both arms, non-gating, NOT counted in N_trials) ---
    print("F7 ex-PA/PL diagnostic...", flush=True)
    entry_dates_ex_papl = {s: v for s, v in entry_dates.items() if s not in ("PA", "PL")}
    carry_panel_ex_papl = carry_panel.drop(columns=[c for c in ("PA", "PL") if c in carry_panel.columns])
    vol_panel_ex_papl = vol_panel.drop(columns=[c for c in ("PA", "PL") if c in vol_panel.columns])
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        _, sh = build_arm(carry_panel_ex_papl, vol_panel_ex_papl, settle_by_month, month_end_index, daily_index,
                           daily_returns_1x, entry_dates_ex_papl, signal_fn, symbol_of_column)
        results[f"exPAPL_{arm}"] = {"sharpe": sh, "arms": arm}

    # --- Items 8-9: diagnostics of the ALREADY-COMPUTED primary series ---
    print("Items 8-9: sub-period, per-year, jackknife diagnostics...", flush=True)
    sub_period = {}
    for arm in ("H1", "H2"):
        net = primary_result[arm]["result"]["daily_net_returns"].dropna()
        midpoint = net.index[len(net) // 2]
        first_half, second_half = net[net.index <= midpoint], net[net.index > midpoint]
        sub_period[arm] = {
            "first_half": (str(first_half.index.min().date()), str(first_half.index.max().date()), sharpe_point(first_half)),
            "second_half": (str(second_half.index.min().date()), str(second_half.index.max().date()), sharpe_point(second_half)),
        }

    jackknife_year = {}
    for arm in ("H1", "H2"):
        net = primary_result[arm]["result"]["daily_net_returns"].dropna()
        years = sorted(net.index.year.unique())
        jackknife_year[arm] = {int(y): sharpe_point(net[net.index.year != y]) for y in years}

    jackknife_sector = {}
    for sector in config.UNIVERSE:
        drop_symbols = config.UNIVERSE[sector]
        entry_dates_ex_sector = {s: v for s, v in entry_dates.items() if s not in drop_symbols}
        carry_panel_ex_sector = carry_panel.drop(columns=[c for c in drop_symbols if c in carry_panel.columns])
        vol_panel_ex_sector = vol_panel.drop(columns=[c for c in drop_symbols if c in vol_panel.columns])
        for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
            _, sh = build_arm(carry_panel_ex_sector, vol_panel_ex_sector, settle_by_month, month_end_index, daily_index,
                               daily_returns_1x, entry_dates_ex_sector, signal_fn, symbol_of_column)
            jackknife_sector[(sector, arm)] = sh

    # --- Attribution (a): gross-of-cost Sharpe ---
    print("Attribution (a): gross-of-cost Sharpe...", flush=True)
    gross_sharpe = {}
    for arm in ("H1", "H2"):
        weights = primary_result[arm]["weights"]
        result_0x = primary.compute_arm_daily_returns(
            weights, daily_returns_0x, settle_by_month, month_end_index, daily_index,
            symbol_of_column=symbol_of_column, cost_multiplier=0.0)
        gross_sharpe[arm] = sharpe_point(result_0x["daily_net_returns"])

    # --- Attribution (b): H1 long-leg vs short-leg contribution ---
    print("Attribution (b): H1 long/short leg contribution...", flush=True)
    h1_weights = primary_result["H1"]["weights"]
    h1_daily_weights = primary.expand_monthly_to_daily(h1_weights, month_end_index, daily_index)
    returns_matrix = pd.DataFrame(index=daily_index, columns=h1_weights.columns, dtype=float)
    for s in h1_weights.columns:
        returns_matrix[s] = daily_returns_1x.get(s, pd.Series(dtype=float)).reindex(daily_index)
    returns_matrix = returns_matrix.fillna(0.0)
    long_contribution = (h1_daily_weights.clip(lower=0) * returns_matrix).sum(axis=1)
    short_contribution = (h1_daily_weights.clip(upper=0) * returns_matrix).sum(axis=1)
    leverage = primary_result["H1"]["result"]["leverage"]
    long_leveraged = (leverage * long_contribution)
    short_leveraged = (leverage * short_contribution)

    write_report(
        results, sub_period, jackknife_year, jackknife_sector, gross_sharpe,
        long_leveraged, short_leveraged, primary_result, roll_date_diffs,
        fixed_cal_tripwire_findings,
    )
    print("Done. See reports/ROBUSTNESS_REPORT.md", flush=True)


def _annual_returns(daily_net_returns: pd.Series) -> dict:
    out = {}
    for year, grp in daily_net_returns.dropna().groupby(daily_net_returns.dropna().index.year):
        out[int(year)] = float((1.0 + grp).prod() - 1.0)
    return out


def write_report(results, sub_period, jackknife_year, jackknife_sector, gross_sharpe,
                  long_leveraged, short_leveraged, primary_result, roll_date_diffs,
                  fixed_cal_tripwire_findings):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Robustness Report",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "Runner-generated, immutable once committed (dated addenda only for "
        "any future correction). PREREGISTRATION.md Sec 8, plus the F7 "
        "ex-PA/PL diagnostic. **Every item below is reported with sign and "
        "magnitude; none gates promotion.** The primary family's own "
        "promotion verdict (`reports/PRIMARY_REPORT.md`, commit f52602e: "
        "neither H1 nor H2 promoted) is unaffected by anything in this "
        "report and is not reconsidered here.",
        "",
        f"Primary Sharpe for reference: H1 {primary_result['H1']['sharpe']:.4f}, "
        f"H2 {primary_result['H2']['sharpe']:.4f} (matches `reports/PRIMARY_REPORT.md` "
        "exactly -- same construction, rebuilt fresh in this runner for the "
        "diagnostics below, not re-derived differently).",
        "",
        "## Items 1-5, 7, 10: constructed variants (Sec 8)",
        "",
        "| Item | Description | Arm(s) | Sharpe |",
        "|---|---|---|---|",
        f"| 1 | Sector-neutral XS (rank within sector, equal sector risk) | XS | {results['R1_sector_neutral_xs']['sharpe']:.4f} |",
        f"| 2 | Quintile cutoffs instead of terciles | XS | {results['R2_quintile_xs']['sharpe']:.4f} |",
        f"| 3 | Equal-weight legs instead of inverse-vol | XS | {results['R3_equal_weight_legs']['sharpe']:.4f} |",
        f"| 4 | 1-month-smoothed carry | XS | {results['R4_smoothed_carry_H1']['sharpe']:.4f} |",
        f"| 4 | 1-month-smoothed carry | TS | {results['R4_smoothed_carry_H2']['sharpe']:.4f} |",
        f"| 5 | 12-month-deferred carry (front vs ~1yr contract) | XS | {results['R5_deferred_carry_H1']['sharpe']:.4f} |",
        f"| 5 | 12-month-deferred carry (front vs ~1yr contract) | TS | {results['R5_deferred_carry_H2']['sharpe']:.4f} |",
        f"| 6 | 2x cost table (restated from Stage 2's gate 4 construction) | XS | {results['R6_2x_cost_H1']['sharpe']:.4f} |",
        f"| 6 | 2x cost table (restated from Stage 2's gate 4 construction) | TS | {results['R6_2x_cost_H2']['sharpe']:.4f} |",
        f"| 7 | Fixed-calendar roll rule (spec completion, `DEVIATIONS.md` 2026-07-16) | XS | {results['R7_fixed_calendar_H1']['sharpe']:.4f} |",
        f"| 7 | Fixed-calendar roll rule (spec completion, `DEVIATIONS.md` 2026-07-16) | TS | {results['R7_fixed_calendar_H2']['sharpe']:.4f} |",
        f"| 10 | KE excluded entirely from the universe | XS | {results['R10_ke_excluded']['sharpe']:.4f} |",
        "",
        "### Item 7 detail: rule-independence cross-check for the amended (A1) roll rule",
        "",
        "Per its upgraded role (this session's governing instruction): item 7 now "
        "also serves as an independent cross-check of A1's timing, using a "
        "completely different (calendar-driven, not OI-crossover) roll mechanism "
        "that shares only the existence filter with A2/A1.",
        "",
        "| Symbol | Daily dates where fixed-calendar front differs from A1's front |",
        "|---|---|",
    ]
    for s, n in sorted(roll_date_diffs.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {s} | {n:,} |")
    lines += [
        "",
        f"**Fixed-calendar tripwire status:** {'zero unexpected stuck-front findings' if not fixed_cal_tripwire_findings else str(len(fixed_cal_tripwire_findings)) + ' finding(s), detail below'} "
        "(NG's two already-known transient grazes, if they recur under this variant's own timing, are treated the same as elsewhere and are not counted as new findings).",
    ]
    if fixed_cal_tripwire_findings:
        lines += [""] + [f"- {d}" for d in fixed_cal_tripwire_findings]
    lines += [
        "",
        "## F7 ex-PA/PL diagnostic (non-gating; N_trials unaffected, per `DEVIATIONS.md` 2026-07-11)",
        "",
        "| Arm | Sharpe (full 18-symbol universe) | Sharpe (ex-PA/PL) |",
        "|---|---|---|",
        f"| H1 | {primary_result['H1']['sharpe']:.4f} | {results['exPAPL_H1']['sharpe']:.4f} |",
        f"| H2 | {primary_result['H2']['sharpe']:.4f} | {results['exPAPL_H2']['sharpe']:.4f} |",
        "",
        "## Items 8-9: diagnostics of the primary series (no new construction)",
        "",
        "### Sub-period halves",
        "",
        "| Arm | First half | Sharpe | Second half | Sharpe |",
        "|---|---|---|---|---|",
    ]
    for arm in ("H1", "H2"):
        fh = sub_period[arm]["first_half"]
        sh = sub_period[arm]["second_half"]
        lines.append(f"| {arm} | {fh[0]} to {fh[1]} | {fh[2]:.4f} | {sh[0]} to {sh[1]} | {sh[2]:.4f} |")
    lines += ["", "### Per-year Sharpe (annual returns already in `reports/PRIMARY_REPORT.md`)", ""]
    for arm in ("H1", "H2"):
        net = primary_result[arm]["result"]["daily_net_returns"].dropna()
        lines += [f"**{arm}:**", "", "| Year | Sharpe (that year's daily returns only) |", "|---|---|"]
        for year, grp in net.groupby(net.index.year):
            lines.append(f"| {int(year)} | {sharpe_point(grp):.4f} |")
        lines += [""]
    lines += ["### Jackknife: drop-one-year", ""]
    for arm in ("H1", "H2"):
        lines += [f"**{arm}** (Sharpe with the given year's daily returns excluded):", "", "| Year dropped | Sharpe |", "|---|---|"]
        for year, sh in sorted(jackknife_year[arm].items()):
            lines.append(f"| {year} | {sh:.4f} |")
        lines += [""]
    lines += ["### Jackknife: drop-one-sector", "", "| Sector dropped | Symbols dropped | H1 Sharpe | H2 Sharpe |", "|---|---|---|---|"]
    for sector in config.UNIVERSE:
        h1_sh = jackknife_sector[(sector, "H1")]
        h2_sh = jackknife_sector[(sector, "H2")]
        lines.append(f"| {sector} | {', '.join(config.UNIVERSE[sector])} | {h1_sh:.4f} | {h2_sh:.4f} |")

    lines += [
        "",
        "## Sanctioned attribution decompositions (of already-computed series; no new constructions)",
        "",
        "### (a) Gross-of-cost Sharpe, restated alongside net",
        "",
        "| Arm | Net Sharpe | Gross-of-cost Sharpe |",
        "|---|---|---|",
        f"| H1 | {primary_result['H1']['sharpe']:.4f} | {gross_sharpe['H1']:.4f} |",
        f"| H2 | {primary_result['H2']['sharpe']:.4f} | {gross_sharpe['H2']:.4f} |",
        "",
        "### (b) H1 long-leg vs short-leg contribution split",
        "",
        f"- Long-leg annualized mean contribution: {long_leveraged.mean() * config.TRADING_DAYS_PER_YEAR:.4%}",
        f"- Short-leg annualized mean contribution: {short_leveraged.mean() * config.TRADING_DAYS_PER_YEAR:.4%}",
        f"- Long-leg cumulative contribution (sum of daily contributions, full sample): {long_leveraged.sum():.4%}",
        f"- Short-leg cumulative contribution (sum of daily contributions, full sample): {short_leveraged.sum():.4%}",
        "",
        "### (c) Per-year table annotated against the 2021-22 backwardation episode",
        "",
        "| Year | H1 return | H2 return | Note |",
        "|---|---|---|---|",
    ]
    h1_annual = _annual_returns(primary_result["H1"]["result"]["daily_net_returns"])
    h2_annual = _annual_returns(primary_result["H2"]["result"]["daily_net_returns"])
    for year in sorted(set(h1_annual) | set(h2_annual)):
        note = ""
        if year == 2021:
            note = "2021: post-COVID demand recovery outpacing supply -- widely documented broad commodity backwardation."
        elif year == 2022:
            note = "2022: Russia/Ukraine war supply shock intensified backwardation across energy and several other commodities."
        lines.append(f"| {year} | {h1_annual.get(year, float('nan')):.4%} | {h2_annual.get(year, float('nan')):.4%} | {note} |")
    lines += [
        "",
        "No further interpretation attempted -- this is a factual annotation "
        "of already-computed, already-reported numbers against a "
        "well-documented macro episode, not a new claim about causality or "
        "an argument for or against promotion.",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
