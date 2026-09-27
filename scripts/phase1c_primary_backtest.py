"""
Phase 1c primary-family backtest runner. PREREGISTRATION.md Sec 4 (H1/H2
construction), Sec 5 (cost model), Sec 6 (inference + promotion gates),
Sec 10 (N_trials), as amended by preregistration/AMENDMENT_2026-09-27.md.
Writes reports/rerun/PRIMARY_REPORT.md, results/primary_summary.json and
results/primary_monthly_returns.csv. The published reports/PRIMARY_REPORT.md
is immutable and never written.

Needs results/premise_summary.json from the premise stage: an arm whose
premise point estimate is <= 0 closes there (Sec 7) and is not backtested.
Loads the corpus through src/study.py (shared with every runner). Run alone
with `python scripts/phase1c_primary_backtest.py`, or as a stage of
`python scripts/run_all.py`.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src import config, stats, study  # noqa: E402

REPORT_PATH = config.RERUN_REPORTS_DIR / "PRIMARY_REPORT.md"
PREMISE_RESULTS_PATH = config.RESULTS_DIR / "premise_summary.json"
RESULTS_PATH = config.RESULTS_DIR / "primary_summary.json"
MONTHLY_PATH = config.RESULTS_DIR / "primary_monthly_returns.csv"


def main():
    try:
        ctx = study.load_context(log=lambda m: print(m, flush=True))
    except study.StudyHalt as halt:
        print(f"HALTING -- {halt}", flush=True)
        write_halt_report(halt)
        sys.exit(1)
    run(ctx)


def load_premise() -> dict:
    if not PREMISE_RESULTS_PATH.exists():
        raise FileNotFoundError(
            f"{PREMISE_RESULTS_PATH} not found -- run the premise stage first "
            f"(python scripts/run_all.py, or scripts/phase1b_premise_test.py).")
    return json.loads(PREMISE_RESULTS_PATH.read_text(encoding="utf-8"))


def run(ctx: "study.StudyContext") -> dict:
    premise = load_premise()
    open_arms = tuple(arm for arm in study.ARMS if premise["gate"][arm])
    closed_arms = tuple(arm for arm in study.ARMS if arm not in open_arms)
    print(f"Open arms after the Sec 7 premise gate: {open_arms or 'none'}", flush=True)

    print("Building every registered series (primaries, Sec 8 items, execution-lag-1)...", flush=True)
    series = study.registered_series(ctx, arms=open_arms) if open_arms else {}
    trial_sharpes = {sid: e["sharpe"] for sid, e in series.items()}
    trial_std = stats.trial_sharpe_std(trial_sharpes.values()) if len(trial_sharpes) >= 2 else float("nan")

    print(f"Running stationary bootstrap ({len(config.BOOTSTRAP_SEEDS)} seeds, "
          f"{config.BOOTSTRAP_N_REPLICATIONS:,} replications each) per open arm...", flush=True)
    gate_data = {}
    for arm in open_arms:
        result = series[arm]["result"]
        net = result["daily_net_returns"].dropna()
        boots = stats.stationary_bootstrap_multi_seed(net.values)
        pr = boots[0]  # seed config.BOOTSTRAP_SEEDS[0] decides the gates
        assert pr["seed"] == config.BOOTSTRAP_SEEDS[0]
        moments = stats.sample_moments(net.values)
        dsr_inputs = {"n_trials": config.N_TRIALS, "n_obs": len(net), **moments,
                      "sharpe_std_across_trials": trial_std}
        gate_data[arm] = {
            "result": result, "bootstrap": boots, "primary_result": pr,
            "pvalue": float((pr["bootstrap_distribution"] <= 0).mean()),
            "sharpe_2x": series[f"R6_2x_cost_{arm}"]["sharpe"],
            "dsr": stats.deflated_sharpe_ratio(pr["point_estimate"], **dsr_inputs),
            "dsr_threshold": stats.dsr_sharpe_threshold(**dsr_inputs),
            "dsr_inputs": dsr_inputs, "n_obs": len(net),
            "gross_sharpe": study.sharpe_point(result["daily_gross_returns"]),
            "lag1_sharpe": series[f"LAG1_{arm}"]["sharpe"],
        }

    # BH across the registered family m=2; an arm closed at the premise has
    # no bootstrap p-value and enters as p=1 (never rejected).
    pvalues = [gate_data[arm]["pvalue"] if arm in gate_data else 1.0 for arm in study.ARMS]
    bh_pass = dict(zip(study.ARMS, stats.benjamini_hochberg(pvalues, q=config.BH_FDR_Q)))
    for arm, gd in gate_data.items():
        pr = gd["primary_result"]
        gd["gates"] = {
            "bh_fdr": bool(bh_pass[arm]),
            "ci_excludes_zero": bool(pr["excludes_zero"]),
            "sharpe_min": bool(pr["point_estimate"] >= config.SHARPE_GATE_MIN),
            "positive_2x_cost": bool(gd["sharpe_2x"] > 0),
            "dsr_min": bool(gd["dsr"] >= config.DSR_GATE_MIN),
        }
        gd["promoted"] = all(gd["gates"].values())

    version = study.code_version()
    summary = write_results(ctx, premise, open_arms, closed_arms, gate_data, trial_sharpes, trial_std, version)
    write_report(ctx, premise, open_arms, closed_arms, gate_data, trial_sharpes, trial_std, version)
    print(f"Done. See {REPORT_PATH} and {RESULTS_PATH}", flush=True)
    return summary


def write_results(ctx, premise, open_arms, closed_arms, gate_data, trial_sharpes, trial_std, version) -> dict:
    arms = {}
    for arm in study.ARMS:
        if arm in closed_arms:
            arms[arm] = {"status": "closed at premise (Sec 7)"}
            continue
        gd = gate_data[arm]
        pr = gd["primary_result"]
        arms[arm] = {
            "status": "PROMOTED" if gd["promoted"] else "NOT PROMOTED",
            "n_obs": gd["n_obs"],
            "net_sharpe": pr["point_estimate"],
            "ci_by_seed": [{"seed": r["seed"], "point_estimate": r["point_estimate"], "ci_low": r["ci_low"],
                            "ci_high": r["ci_high"], "excludes_zero": bool(r["excludes_zero"])}
                           for r in gd["bootstrap"]],
            "bootstrap_pvalue": gd["pvalue"],
            "net_sharpe_2x_cost": gd["sharpe_2x"],
            "gross_sharpe": gd["gross_sharpe"],
            "net_sharpe_execution_lag_1": gd["lag1_sharpe"],
            "dsr": gd["dsr"],
            "dsr_inputs": gd["dsr_inputs"],
            "dsr_sharpe_threshold": gd["dsr_threshold"],
            "gates": gd["gates"],
            "annual_returns": study.annual_returns(gd["result"]["daily_net_returns"]),
            "cost_drag_annualized": _cost_drags(gd["result"]),
        }
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "code_version": version,
        "execution_lag": config.EXECUTION_LAG_PRIMARY,
        "n_trials": config.N_TRIALS,
        "trial_sharpes": trial_sharpes,
        "trial_sharpe_std": trial_std,
        "premise_gate": premise["gate"],
        "daily_index_first": str(ctx.daily_index.min().date()),
        "daily_index_last": str(ctx.daily_index.max().date()),
        "arms": arms,
    }
    study.write_json(RESULTS_PATH, summary)

    columns = {}
    for arm in open_arms:
        result = gate_data[arm]["result"]
        columns[f"{arm}_net"] = study.monthly_returns(result["daily_net_returns"])
        columns[f"{arm}_gross"] = study.monthly_returns(result["daily_gross_returns"])
    monthly = pd.DataFrame(columns)
    monthly.index = monthly.index.astype(str)
    monthly.index.name = "month"
    MONTHLY_PATH.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(MONTHLY_PATH, float_format="%.10g")
    return summary


def _cost_drags(result) -> dict:
    per_year = config.TRADING_DAYS_PER_YEAR
    trading = float(result["trading_cost"].mean() * per_year)
    roll = float(result["roll_cost"].mean() * per_year)
    return {"trading": trading, "roll": roll, "total": trading + roll}


def write_halt_report(halt: "study.StudyHalt") -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Primary Report -- HALTED ({halt.kind})",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        ("**An integrity check fired while assembling the corpus** (the permanent "
         "stuck-front tripwire -- known allowed set "
         f"{sorted(study.KNOWN_ALLOWED_TRANSIENT_GRAZES)!r} -- or the zero-price "
         "guard). This requires its own check before any further computation. "
         "No primary backtest was computed."),
        "",
        f"- {halt.detail}",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def _annualized_turnover(weights_by_month: pd.DataFrame, n_years: float) -> float:
    delta = (weights_by_month - weights_by_month.shift(1).fillna(0.0)).abs().sum(axis=1)
    return float(delta.sum() / n_years) if n_years > 0 else float("nan")


def _pf(flag: bool) -> str:
    return "PASS" if flag else "FAIL"


def write_report(ctx, premise, open_arms, closed_arms, gate_data, trial_sharpes, trial_std, version):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_years = (ctx.daily_index.max() - ctx.daily_index.min()).days / 365.25
    xs, ts = premise["xs"], premise["ts"]
    lines = [
        "# Primary Report",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()} · code `{version}`",
        "",
        ("Runner-generated (`scripts/phase1c_primary_backtest.py`). PREREGISTRATION.md "
         "Sec 4/Sec 6, as amended by `preregistration/AMENDMENT_2026-09-27.md`. This "
         "run follows the 2026-09-27 corrections (`reports/ADDENDUM_2026-09-27.md`); "
         "the published pre-correction report, `reports/PRIMARY_REPORT.md`, stays unchanged."),
        "",
        (f"**Premise gate (Sec 7, `results/premise_summary.json`):** XS mean IC "
         f"{xs['mean_ic']:+.6f} (NW({xs['nw_lags']}) t={xs['tstat']:.4f}), TS coefficient "
         f"{ts['coefficient']:+.6f} (t={ts['tstat']:.4f}). Open arms: "
         f"{', '.join(open_arms) or 'none'}; closed at the premise: {', '.join(closed_arms) or 'none'}."),
        "",
        ("**Pipeline:** A1 roll rule and A2 carry-next (`DEVIATIONS.md` 2026-07-15); "
         "trade-date calendar and `StatType.OPEN_INTEREST` (2026-09-27); execution_lag = "
         f"{config.EXECUTION_LAG_PRIMARY} (entry at the signal's own month-end settlement, "
         "the registered primary timing); leverage sized from the pre-cost series; every "
         "change in the levered position (monthly rebalance and daily leverage resize) and "
         "every roll leg charged on |position|. "
         f"**N_trials for DSR: {config.N_TRIALS}** (Sec 10's 14 plus the two "
         "execution-lag-1 series registered 2026-09-27). DSR inputs: each arm's sample "
         "skewness and excess kurtosis, and the empirical standard deviation of the "
         f"{len(trial_sharpes)} registered series' Sharpes ({trial_std:.4f}). Bootstrap: expected block "
         f"{config.BOOTSTRAP_EXPECTED_BLOCK_LENGTH} trading days, "
         f"{config.BOOTSTRAP_N_REPLICATIONS:,} replications, seeds {config.BOOTSTRAP_SEEDS} -- "
         f"seed {config.BOOTSTRAP_SEEDS[0]} decides the gates; all 3 seeds are reported (Sec 6)."),
        "",
    ]
    if ctx.graze_disclosures:
        lines += ["**Tripwire firings this run** (known, non-permanent NG grazes only):", ""]
        lines += [f"- {d}" for d in ctx.graze_disclosures]
    else:
        lines += ["**Tripwire firings this run:** none."]
    lines += [""]

    for arm in study.ARMS:
        label = "H1 (XS, cross-sectional tercile)" if arm == "H1" else "H2 (TS, time-series sign)"
        if arm in closed_arms:
            lines += [f"## {label}", "", ("**Closed at the premise stage (Sec 7): point estimate <= 0. "
                                          "No backtest run.**"), ""]
            continue
        gd = gate_data[arm]
        pr, result, di = gd["primary_result"], gd["result"], gd["dsr_inputs"]
        drags = _cost_drags(result)
        lines += [
            f"## {label}",
            "",
            f"- N (daily observations): {gd['n_obs']:,}",
            f"- Annualized net Sharpe (seed {pr['seed']}, point estimate): **{pr['point_estimate']:.4f}**",
            f"- 95% bootstrap CI: [{pr['ci_low']:.4f}, {pr['ci_high']:.4f}]  (excludes zero: {pr['excludes_zero']})",
            f"- Bootstrap p-value (one-sided, P[Sharpe <= 0]): {gd['pvalue']:.4f}",
            f"- Net Sharpe under 2x cost table: {gd['sharpe_2x']:.4f}",
            f"- Gross-of-cost Sharpe (same leverage path): {gd['gross_sharpe']:.4f}",
            f"- Net Sharpe with execution one trading day after the signal (sensitivity): {gd['lag1_sharpe']:.4f}",
            (f"- Deflated Sharpe Ratio (N_trials={di['n_trials']}, skew={di['skew']:.3f}, excess kurtosis="
             f"{di['excess_kurtosis']:.3f}, trial Sharpe std={di['sharpe_std_across_trials']:.4f}): {gd['dsr']:.4f}"),
            (f"- Annualized net Sharpe needed for DSR >= {config.DSR_GATE_MIN} under these inputs: "
             f"{gd['dsr_threshold']:.4f}"),
            (f"- Annualized turnover (sum |monthly pre-leverage weight delta| / years): "
             f"{_annualized_turnover(result['weights_by_month'], n_years):.2f}"),
            f"- Trading cost drag, rebalance + daily leverage resize (annualized): {drags['trading']:.6%}",
            f"- Roll cost drag (annualized): {drags['roll']:.6%}",
            f"- Total cost drag (annualized; equals gross minus net mean daily return x 252): {drags['total']:.6%}",
            "",
            "**All 3 recorded seeds (Sec 6: \"not just their average\"):**",
            "",
            "| Seed | Point estimate | CI low | CI high | Excludes zero |",
            "|---|---|---|---|---|",
        ]
        for r in gd["bootstrap"]:
            lines.append(f"| {r['seed']} | {r['point_estimate']:.4f} | {r['ci_low']:.4f} | {r['ci_high']:.4f} | "
                         f"{r['excludes_zero']} |")
        g = gd["gates"]
        lines += [
            "",
            "**Five promotion gates (Sec 6, all must pass):**",
            "",
            "| Gate | Requirement | Value | Verdict |",
            "|---|---|---|---|",
            f"| 1. BH-FDR | q={config.BH_FDR_Q}, m=2 | p={gd['pvalue']:.4f} | {_pf(g['bh_fdr'])} |",
            (f"| 2. CI excludes 0 | 95% bootstrap CI | [{pr['ci_low']:.4f}, {pr['ci_high']:.4f}] | "
             f"{_pf(g['ci_excludes_zero'])} |"),
            f"| 3. Net Sharpe >= {config.SHARPE_GATE_MIN} | | {pr['point_estimate']:.4f} | {_pf(g['sharpe_min'])} |",
            f"| 4. Net Sharpe > 0 under 2x cost | | {gd['sharpe_2x']:.4f} | {_pf(g['positive_2x_cost'])} |",
            f"| 5. DSR >= {config.DSR_GATE_MIN} | N_trials={config.N_TRIALS} | {gd['dsr']:.4f} | {_pf(g['dsr_min'])} |",
            "",
            f"**Promotion verdict: {'PROMOTED' if gd['promoted'] else 'NOT PROMOTED'}**",
            "",
            "### Annual returns",
            "",
            "| Year | Net return |",
            "|---|---|",
        ]
        for year, r in sorted(study.annual_returns(result["daily_net_returns"]).items()):
            lines.append(f"| {year} | {r:.4%} |")
        lines += ["", "Monthly net and gross returns: `results/primary_monthly_returns.csv`.", ""]

    lines += [
        "## Summary",
        "",
        "| Arm | Sharpe | CI | DSR | BH-FDR | Sharpe>=0.30 | 2x cost>0 | DSR>=0.95 | Promoted |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for arm in study.ARMS:
        if arm in closed_arms:
            lines.append(f"| {arm} | -- | -- | -- | -- | -- | -- | -- | CLOSED AT PREMISE |")
            continue
        gd = gate_data[arm]
        pr, g = gd["primary_result"], gd["gates"]
        lines.append(
            f"| {arm} | {pr['point_estimate']:.4f} | [{pr['ci_low']:.4f}, {pr['ci_high']:.4f}] | {gd['dsr']:.4f} | "
            f"{_pf(g['bh_fdr'])} | {_pf(g['sharpe_min'])} | {_pf(g['positive_2x_cost'])} | {_pf(g['dsr_min'])} | "
            f"{'YES' if gd['promoted'] else 'NO'} |"
        )
    lines += [""]
    promoted = [arm for arm in open_arms if gate_data[arm]["promoted"]]
    if promoted:
        lines += [f"**Arm(s) promoted: {', '.join(promoted)}.** Sec 8's robustness suite follows."]
    else:
        lines += [("**No arm promoted.** Per Sec 6, promotion requires all five gates. Sec 8's robustness suite "
                   "is still run as diagnostics of the primary series (robustness never gates promotion).")]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
