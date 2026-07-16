"""
Phase 1c primary-family backtest runner. PREREGISTRATION.md Sec 4 (H1/H2
construction), Sec 5 (cost model), Sec 6 (inference + promotion gates),
Sec 10 (N_trials). Generates reports/PRIMARY_REPORT.md -- immutable once
committed (dated addenda only for any future correction).

Reuses the EXACT data-loading path scripts/phase1b_premise_test.py used
(pipeline.build_definition_lookup/build_settlement_oi_panel/build_outright_panel,
raw DBN files, all 5,031/5,026 files) -- no parallel loading code. The
per-symbol tripwire handling (including the one user-pre-authorized "NG
single-day graze," DEVIATIONS.md/F11 amendment record) is duplicated from
that runner rather than imported, since scripts/ are not unit-tested
real-data-only code by established convention (data_loader.py's own
docstring) and this keeps each runner independently readable.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\commodity-carry-research")
sys.path.insert(0, str(REPO))

from src import config, pipeline, primary, stats  # noqa: E402
from src.portfolio import xs_raw_signal, ts_raw_signal  # noqa: E402

REPORT_PATH = REPO / "reports" / "PRIMARY_REPORT.md"
WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")

# Same user-pre-authorized transient grazes as Phase 1b's runner (F11
# amendment record; PREREGISTRATION.md's own wording: "the NG single-day
# graze is the one known allowed artifact"). Both of NG's two
# already-characterized instances -- see docs/DATA_QA_REPORT.md's F11 census.
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


def main():
    entry_dates = _entry_dates()
    symbol_of_column = {s: s for s in config.ALL_SYMBOLS}

    print("Loading definition lookup (real data, all 5,031 files)...", flush=True)
    definition_lookup = pipeline.build_definition_lookup()
    print(f"  {len(definition_lookup):,} rows", flush=True)

    print("Loading settlement/OI panel (real data, all 5,026 files)...", flush=True)
    settlement_oi_panel = pipeline.build_settlement_oi_panel()
    print(f"  {len(settlement_oi_panel):,} rows", flush=True)

    print("Building outright panel...", flush=True)
    outright_panel = pipeline.build_outright_panel(definition_lookup, settlement_oi_panel)
    print(f"  {len(outright_panel):,} outright rows", flush=True)

    carry_by_symbol = {}
    daily_returns_1x, daily_returns_2x, daily_returns_0x = {}, {}, {}
    front_by_symbol, settle_wide_by_symbol = {}, {}
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
        ret_1x = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=1.0)["returns"]
        ret_2x = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=2.0)["returns"]
        ret_0x = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=0.0)["returns"]

        carry_by_symbol[symbol] = carry
        daily_returns_1x[symbol] = ret_1x
        daily_returns_2x[symbol] = ret_2x
        daily_returns_0x[symbol] = ret_0x
        front_by_symbol[symbol] = front
        settle_wide_by_symbol[symbol] = settle_wide

    print("Building month-end carry panel and daily index...", flush=True)
    carry_panel = pipeline.month_end_carry_panel(carry_by_symbol, entry_dates=entry_dates)
    month_end_index = carry_panel.index
    all_daily_dates = sorted(set().union(*[s.index for s in daily_returns_1x.values()]))
    daily_index = pd.DatetimeIndex(all_daily_dates)
    print(f"  {len(month_end_index)} months, {len(daily_index):,} daily dates", flush=True)

    print("Building per-symbol vol-at-month-end and settle-at-month-end panels...", flush=True)
    vol_panel = pd.DataFrame({
        s: primary.symbol_vol_at_month_end(daily_returns_1x[s], month_end_index) for s in carry_by_symbol
    })
    settle_by_month = pd.DataFrame({
        s: primary.symbol_settle_at_month_end(front_by_symbol[s], settle_wide_by_symbol[s], month_end_index)
        for s in carry_by_symbol
    })

    arms = {"H1": xs_raw_signal, "H2": ts_raw_signal}
    weights_by_arm, results_by_arm = {}, {}
    results_2x_by_arm, results_0x_by_arm = {}, {}

    for arm, signal_fn in arms.items():
        print(f"Building {arm} pre-leverage weights and daily returns...", flush=True)
        weights = primary.build_pre_leverage_weights(carry_panel, vol_panel, entry_dates, signal_fn)
        weights_by_arm[arm] = weights
        results_by_arm[arm] = primary.compute_arm_daily_returns(
            weights, daily_returns_1x, settle_by_month, month_end_index, daily_index,
            symbol_of_column=symbol_of_column, cost_multiplier=1.0)
        results_2x_by_arm[arm] = primary.compute_arm_daily_returns(
            weights, daily_returns_2x, settle_by_month, month_end_index, daily_index,
            symbol_of_column=symbol_of_column, cost_multiplier=2.0)
        results_0x_by_arm[arm] = primary.compute_arm_daily_returns(
            weights, daily_returns_0x, settle_by_month, month_end_index, daily_index,
            symbol_of_column=symbol_of_column, cost_multiplier=0.0)

    print("Running stationary bootstrap (3 seeds, 10,000 replications each) per arm...", flush=True)
    bootstrap_by_arm, sharpe_2x_by_arm = {}, {}
    for arm in arms:
        net = results_by_arm[arm]["daily_net_returns"].dropna().values
        bootstrap_by_arm[arm] = stats.stationary_bootstrap_multi_seed(net)
        net_2x = results_2x_by_arm[arm]["daily_net_returns"].dropna().values
        sharpe_2x_by_arm[arm] = stats.stationary_bootstrap_sharpe(net_2x, seed=config.BOOTSTRAP_SEEDS[0])["point_estimate"]

    print("Computing BH-FDR and DSR, evaluating the five gates per arm...", flush=True)
    primary_seed = config.BOOTSTRAP_SEEDS[0]
    pvalues = []
    gate_data = {}
    for arm in arms:
        primary_result = bootstrap_by_arm[arm][0]  # seed[0] == config.BOOTSTRAP_SEEDS[0], the gate-deciding result
        assert primary_result["seed"] == primary_seed
        pvalue = float((primary_result["bootstrap_distribution"] <= 0).mean())
        pvalues.append(pvalue)
        n_obs = len(results_by_arm[arm]["daily_net_returns"].dropna())
        dsr = stats.deflated_sharpe_ratio(
            observed_sharpe=primary_result["point_estimate"], n_trials=config.N_TRIALS, n_obs=n_obs)
        gate_data[arm] = {"primary_result": primary_result, "pvalue": pvalue, "dsr": dsr, "n_obs": n_obs}

    bh_pass = stats.benjamini_hochberg(pvalues, q=config.BH_FDR_Q)
    for i, arm in enumerate(arms):
        gate_data[arm]["bh_pass"] = bh_pass[i]

    for arm in arms:
        gd = gate_data[arm]
        pr = gd["primary_result"]
        g1 = gd["bh_pass"]
        g2 = pr["excludes_zero"]
        g3 = pr["point_estimate"] >= config.SHARPE_GATE_MIN
        g4 = sharpe_2x_by_arm[arm] > 0
        g5 = gd["dsr"] >= config.DSR_GATE_MIN
        gd["gates"] = {"bh_fdr": g1, "ci_excludes_zero": g2, "sharpe_min": g3, "positive_2x_cost": g4, "dsr_min": g5}
        gd["promoted"] = all(gd["gates"].values())

    write_report(
        arms, weights_by_arm, results_by_arm, results_2x_by_arm, results_0x_by_arm,
        bootstrap_by_arm, sharpe_2x_by_arm, gate_data, known_graze_disclosures, daily_index,
    )
    print("Done. See reports/PRIMARY_REPORT.md", flush=True)


def write_halt_report_stuck_front(symbol, disclosure):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Primary Report -- HALTED (unexpected stuck front)",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "**The permanent tripwire fired on a violation that does NOT match "
        "a user-pre-authorized transient graze** (known set: "
        f"{sorted(KNOWN_ALLOWED_TRANSIENT_GRAZES)!r}). This requires its own "
        "check before any further computation. No primary backtest was computed.",
        "",
        f"- Symbol: {symbol}",
        f"- {disclosure}",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def _annual_returns(daily_net_returns: pd.Series) -> dict:
    out = {}
    for year, grp in daily_net_returns.dropna().groupby(daily_net_returns.dropna().index.year):
        out[int(year)] = float((1.0 + grp).prod() - 1.0)
    return out


def _annualized_turnover(weights_by_month: pd.DataFrame, n_years: float) -> float:
    delta = (weights_by_month - weights_by_month.shift(1).fillna(0.0)).abs().sum(axis=1)
    return float(delta.sum() / n_years) if n_years > 0 else float("nan")


def write_report(arms, weights_by_arm, results_by_arm, results_2x_by_arm, results_0x_by_arm,
                  bootstrap_by_arm, sharpe_2x_by_arm, gate_data, known_graze_disclosures, daily_index):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_years = (daily_index.max() - daily_index.min()).days / 365.25

    lines = [
        "# Primary Report",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "Runner-generated, immutable once committed (dated addenda only for "
        "any future correction). PREREGISTRATION.md Sec 4/Sec 6. First "
        "real-data primary-family backtest in this project's history -- "
        "both arms passed Sec 7's premise gate (`reports/PREMISE_REPORT.md`, "
        "commit 543d271): XS mean IC +0.028489 (NW(3) t=1.4650), TS "
        "coefficient +0.000672 (t=0.3000). No design reaction to those "
        "numbers occurred; they are quoted here only for the run record.",
        "",
        f"**Pipeline confirmation:** amended pipeline throughout (A1 "
        "multi-candidate OI-max roll rule, A2 next-OI-bearing carry-next, "
        "`DEVIATIONS.md` 2026-07-15). **N_trials used for DSR: "
        f"{config.N_TRIALS}** (Sec 10's frozen computation ledger, cited "
        "directly, never locally recomputed). Bootstrap: expected block "
        f"{config.BOOTSTRAP_EXPECTED_BLOCK_LENGTH} trading days, "
        f"{config.BOOTSTRAP_N_REPLICATIONS:,} replications, seeds "
        f"{config.BOOTSTRAP_SEEDS} -- seed {config.BOOTSTRAP_SEEDS[0]} (the "
        "stats.py default) decides the gate verdicts below; all 3 seeds' "
        "individual outcomes are reported per Sec 6 (\"not just their average\").",
        "",
    ]

    if known_graze_disclosures:
        lines += ["**Tripwire firings this run** (same known, non-permanent NG grazes as Phase 1b):", ""]
        lines += [f"- {d}" for d in known_graze_disclosures]
    else:
        lines += ["**Tripwire firings this run:** none."]
    lines += [""]

    for arm in arms:
        gd = gate_data[arm]
        pr = gd["primary_result"]
        weights = weights_by_arm[arm]
        result = results_by_arm[arm]
        net = result["daily_net_returns"].dropna()
        turnover = _annualized_turnover(weights, n_years)
        rebal_cost_annual = float(result["rebalance_cost"].sum() / n_years) if n_years > 0 else float("nan")
        gross_mean_daily = results_0x_by_arm[arm]["daily_net_returns"].dropna().mean()
        net_mean_daily = net.mean()
        total_cost_drag_annual = float((gross_mean_daily - net_mean_daily) * config.TRADING_DAYS_PER_YEAR)

        arm_label = "H1 (XS, cross-sectional tercile)" if arm == "H1" else "H2 (TS, time-series sign)"
        lines += [
            f"## {arm_label}",
            "",
            f"- N (daily observations): {gd['n_obs']:,}",
            f"- Annualized net Sharpe (seed {pr['seed']}, point estimate): **{pr['point_estimate']:.4f}**",
            f"- 95% bootstrap CI: [{pr['ci_low']:.4f}, {pr['ci_high']:.4f}]  (excludes zero: {pr['excludes_zero']})",
            f"- Bootstrap p-value (one-sided, P[Sharpe <= 0]): {gd['pvalue']:.4f}",
            f"- Net Sharpe under 2x cost table: {sharpe_2x_by_arm[arm]:.4f}",
            f"- Deflated Sharpe Ratio (N_trials={config.N_TRIALS}): {gd['dsr']:.4f}",
            f"- Annualized turnover (sum |monthly weight delta| / years): {turnover:.2f}",
            f"- Rebalance cost drag (annualized): {rebal_cost_annual:.6%}",
            f"- Total cost drag, rebalance + roll (annualized, gross-vs-net mean daily return): {total_cost_drag_annual:.6%}",
            "",
            "**All 3 recorded seeds (Sec 6: \"not just their average\"):**",
            "",
            "| Seed | Point estimate | CI low | CI high | Excludes zero |",
            "|---|---|---|---|---|",
        ]
        for r in bootstrap_by_arm[arm]:
            lines.append(f"| {r['seed']} | {r['point_estimate']:.4f} | {r['ci_low']:.4f} | {r['ci_high']:.4f} | {r['excludes_zero']} |")
        lines += [
            "",
            "**Five promotion gates (Sec 6, verbatim, all must pass):**",
            "",
            "| Gate | Requirement | Value | Verdict |",
            "|---|---|---|---|",
            f"| 1. BH-FDR | q={config.BH_FDR_Q}, m=2 | p={gd['pvalue']:.4f} | {'PASS' if gd['gates']['bh_fdr'] else 'FAIL'} |",
            f"| 2. CI excludes 0 | 95% bootstrap CI | [{pr['ci_low']:.4f}, {pr['ci_high']:.4f}] | {'PASS' if gd['gates']['ci_excludes_zero'] else 'FAIL'} |",
            f"| 3. Net Sharpe >= {config.SHARPE_GATE_MIN} | | {pr['point_estimate']:.4f} | {'PASS' if gd['gates']['sharpe_min'] else 'FAIL'} |",
            f"| 4. Net Sharpe > 0 under 2x cost | | {sharpe_2x_by_arm[arm]:.4f} | {'PASS' if gd['gates']['positive_2x_cost'] else 'FAIL'} |",
            f"| 5. DSR >= {config.DSR_GATE_MIN} | N_trials={config.N_TRIALS} | {gd['dsr']:.4f} | {'PASS' if gd['gates']['dsr_min'] else 'FAIL'} |",
            "",
            f"**Promotion verdict: {'PROMOTED' if gd['promoted'] else 'NOT PROMOTED'}**",
            "",
            "### Annual returns",
            "",
            "| Year | Net return |",
            "|---|---|",
        ]
        for year, r in sorted(_annual_returns(net).items()):
            lines.append(f"| {year} | {r:.4%} |")
        lines += [""]

        # save full daily equity curve to the workspace for later charting
        equity = (1.0 + net).cumprod()
        equity.to_csv(WORKSPACE / f"phase1c_equity_curve_{arm}.csv", header=["equity"])
        lines += [f"Full daily equity curve saved to `_carry-research-workspace/phase1c_equity_curve_{arm}.csv` (not committed, reproducible).", ""]

    lines += [
        "## Summary",
        "",
        "| Arm | Sharpe | CI | DSR | BH-FDR | Sharpe>=0.30 | 2x cost>0 | DSR>=0.95 | Promoted |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for arm in arms:
        gd = gate_data[arm]
        pr = gd["primary_result"]
        g = gd["gates"]
        lines.append(
            f"| {arm} | {pr['point_estimate']:.4f} | [{pr['ci_low']:.4f}, {pr['ci_high']:.4f}] | {gd['dsr']:.4f} | "
            f"{'PASS' if g['bh_fdr'] else 'FAIL'} | {'PASS' if g['sharpe_min'] else 'FAIL'} | "
            f"{'PASS' if g['positive_2x_cost'] else 'FAIL'} | {'PASS' if g['dsr_min'] else 'FAIL'} | "
            f"{'YES' if gd['promoted'] else 'NO'} |"
        )
    lines += [""]

    any_promoted = any(gate_data[arm]["promoted"] for arm in arms)
    if any_promoted:
        promoted = [arm for arm in arms if gate_data[arm]["promoted"]]
        lines += [f"**Arm(s) promoted, proceeding to Sec 8 robustness suite: {', '.join(promoted)}.**"]
    else:
        lines += ["**No arm promoted.** Per Sec 6, promotion requires all five gates. Sec 8's robustness suite is still run "
                   "as diagnostics of the primary series regardless of promotion (robustness never gates promotion either way)."]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
