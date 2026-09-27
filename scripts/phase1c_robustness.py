"""
Phase 1c robustness suite runner. PREREGISTRATION.md Sec 8 (all 10 items),
the F7 ex-PA/PL diagnostic (`DEVIATIONS.md`, 2026-07-11), the Sec 8 item 7
day-count specification (`DEVIATIONS.md`, 2026-07-16) and the
execution-lag-1 sensitivity (`preregistration/AMENDMENT_2026-09-27.md`).
Writes reports/rerun/ROBUSTNESS_REPORT.md and results/robustness_variants.csv.
The published reports/ROBUSTNESS_REPORT.md is immutable and never written.

Every item is reported with sign and magnitude; none gates promotion (Sec 8).
Items 8-9 are diagnostics of the already-computed primary series; the
constructed series come from src/study.py, the same objects the primary
runner used for the DSR trial dispersion. Sharpe is the point estimate
mean/std(ddof=1)*sqrt(252) (study.sharpe_point); non-gating items carry no
CI. Run alone with `python scripts/phase1c_robustness.py`, or as a stage of
`python scripts/run_all.py` (after the primary stage).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src import config, study  # noqa: E402

REPORT_PATH = config.RERUN_REPORTS_DIR / "ROBUSTNESS_REPORT.md"
PRIMARY_RESULTS_PATH = config.RESULTS_DIR / "primary_summary.json"
VARIANTS_PATH = config.RESULTS_DIR / "robustness_variants.csv"


def main():
    try:
        ctx = study.load_context(log=lambda m: print(m, flush=True))
    except study.StudyHalt as halt:
        print(f"HALTING -- {halt}", flush=True)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(f"# Robustness Report -- HALTED ({halt.kind})\n\n{halt.detail}\n", encoding="utf-8")
        sys.exit(1)
    run(ctx)


def run(ctx: "study.StudyContext") -> pd.DataFrame:
    if not PRIMARY_RESULTS_PATH.exists():
        raise FileNotFoundError(f"{PRIMARY_RESULTS_PATH} not found -- run the primary stage first.")
    primary_summary = json.loads(PRIMARY_RESULTS_PATH.read_text(encoding="utf-8"))
    open_arms = tuple(a for a in study.ARMS if primary_summary["arms"][a].get("status") != "closed at premise (Sec 7)")

    print("Registered series (cached from the primary stage when run via run_all)...", flush=True)
    series = study.registered_series(ctx, arms=open_arms)
    print("Diagnostic constructions (F7 ex-PA/PL, drop-one-sector)...", flush=True)
    diagnostics = study.diagnostic_series(ctx, arms=open_arms)

    net = {arm: series[arm]["result"]["daily_net_returns"].dropna() for arm in open_arms}
    sub_period = {arm: study.sub_period_halves(net[arm]) for arm in open_arms}
    jackknife_year = {arm: {int(y): study.sharpe_point(net[arm][net[arm].index.year != y])
                            for y in sorted(net[arm].index.year.unique())} for arm in open_arms}
    gross_sharpe = {arm: study.sharpe_point(series[arm]["result"]["daily_gross_returns"]) for arm in open_arms}

    legs = None
    if "H1" in open_arms:
        result = series["H1"]["result"]
        contrib, w = result["contributions"], result["daily_weights"]
        legs = {"long": contrib.where(w > 0, 0.0).sum(axis=1), "short": contrib.where(w < 0, 0.0).sum(axis=1)}

    roll_date_diffs = {
        s: int((ctx.front[s].reindex(ctx.daily_index).astype(object)
                != ctx.fixed_cal_front[s].reindex(ctx.daily_index).astype(object)).sum())
        for s in ctx.symbols
    }

    rows = []
    for e in list(series.values()) + list(diagnostics.values()):
        rows.append({"id": e["id"], "item": e["item"], "arm": e["arm"],
                     "kind": "primary" if e["item"] == "primary" else e["kind"],
                     "in_n_trials": e["kind"] == "registered", "description": e["description"],
                     "sharpe": e["sharpe"]})
    for arm in open_arms:
        for half in ("first_half", "second_half"):
            start, end, sh = sub_period[arm][half]
            rows.append({"id": f"subperiod_{arm}_{half.split('_')[0]}", "item": "8", "arm": arm, "kind": "diagnostic",
                         "in_n_trials": False, "description": f"Sub-period {start} to {end}", "sharpe": sh})
    variants = pd.DataFrame(rows)
    VARIANTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    variants.to_csv(VARIANTS_PATH, index=False, float_format="%.10g")

    write_report(ctx, primary_summary, open_arms, series, diagnostics, sub_period, jackknife_year, gross_sharpe,
                 legs, roll_date_diffs)
    print(f"Done. See {REPORT_PATH} and {VARIANTS_PATH}", flush=True)
    return variants


def _row(series, sid, fmt="{:.4f}"):
    return fmt.format(series[sid]["sharpe"]) if sid in series else "--"


def write_report(ctx, primary_summary, open_arms, series, diagnostics, sub_period, jackknife_year, gross_sharpe,
                 legs, roll_date_diffs):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    verdicts = ", ".join(f"{a}: {primary_summary['arms'][a]['status']}" for a in study.ARMS)
    reference = []
    for arm in open_arms:
        reported = primary_summary["arms"][arm]["net_sharpe"]
        rebuilt = series[arm]["sharpe"]
        reference.append(f"{arm} {rebuilt:.4f} ({'matches' if round(reported, 10) == round(rebuilt, 10) else 'DIFFERS FROM'} "
                         f"`results/primary_summary.json`)")
    lines = [
        "# Robustness Report",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()} · code `{study.code_version()}`",
        "",
        "Runner-generated (`scripts/phase1c_robustness.py`). PREREGISTRATION.md Sec 8, "
        "the F7 ex-PA/PL diagnostic and the execution-lag-1 sensitivity "
        "(`preregistration/AMENDMENT_2026-09-27.md`). This run follows the 2026-09-27 "
        "corrections (`reports/ADDENDUM_2026-09-27.md`); the published pre-correction "
        "report, `reports/ROBUSTNESS_REPORT.md`, stays unchanged. **Every item below is reported with "
        "sign and magnitude; none gates promotion.** The primary family's promotion "
        f"verdict (`reports/rerun/PRIMARY_REPORT.md`: {verdicts}) is unaffected by anything "
        "in this report.",
        "",
        f"Primary Sharpe for reference: {'; '.join(reference) or 'no open arm'}.",
        "",
        "## Items 1-7, 10: constructed variants (Sec 8)",
        "",
        "| Item | Description | Arm(s) | Sharpe |",
        "|---|---|---|---|",
    ]
    constructed = [e for e in series.values() if e["item"] not in ("primary", "lag-1")]
    for e in sorted(constructed, key=lambda e: (int(e["item"]), e["arm"])):
        lines.append(f"| {e['item']} | {e['description']} | {study.ARM_LABEL[e['arm']]} | {e['sharpe']:.4f} |")
    lines += [
        "",
        "## Execution-timing sensitivity (registered 2026-09-27; counted in N_trials)",
        "",
        "The primary construction with execution one trading day after the signal: "
        "entry at settle(t+1), first return settle(t+1) -> settle(t+2).",
        "",
        "| Arm | Sharpe, execution at the signal settlement (registered) | Sharpe, execution one day later |",
        "|---|---|---|",
    ]
    for arm in open_arms:
        lines.append(f"| {arm} | {series[arm]['sharpe']:.4f} | {series[f'LAG1_{arm}']['sharpe']:.4f} |")
    lines += [
        "",
        "### Item 7 detail: rule-independence cross-check for the amended (A1) roll rule",
        "",
        "Calendar-driven roll timing (last business day of the month before the "
        "front's expiry month) sharing only the existence filter with A1/A2.",
        "",
        "| Symbol | Daily dates where fixed-calendar front differs from A1's front |",
        "|---|---|",
    ]
    for s, n in sorted(roll_date_diffs.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {s} | {n:,} |")
    findings = ctx.fixed_cal_tripwire_findings
    lines += [
        "",
        f"**Fixed-calendar tripwire status:** "
        f"{'zero unexpected stuck-front findings' if not findings else str(len(findings)) + ' finding(s), detail below'} "
        "(NG's two known transient grazes are not counted as new findings).",
    ]
    if findings:
        lines += [""] + [f"- {d}" for d in findings]
    lines += [
        "",
        "## F7 ex-PA/PL diagnostic (non-gating; not counted in N_trials)",
        "",
        "| Arm | Sharpe (full universe) | Sharpe (ex-PA/PL) |",
        "|---|---|---|",
    ]
    for arm in open_arms:
        lines.append(f"| {arm} | {series[arm]['sharpe']:.4f} | {_row(diagnostics, f'exPAPL_{arm}')} |")
    lines += [
        "",
        "## Items 8-9: diagnostics of the primary series (no new construction)",
        "",
        "### Sub-period halves",
        "",
        "| Arm | First half | Sharpe | Second half | Sharpe |",
        "|---|---|---|---|---|",
    ]
    for arm in open_arms:
        fh, sh = sub_period[arm]["first_half"], sub_period[arm]["second_half"]
        lines.append(f"| {arm} | {fh[0]} to {fh[1]} | {fh[2]:.4f} | {sh[0]} to {sh[1]} | {sh[2]:.4f} |")
    lines += ["", "### Per-year Sharpe (annual returns are in `reports/rerun/PRIMARY_REPORT.md`)", ""]
    for arm in open_arms:
        net = series[arm]["result"]["daily_net_returns"].dropna()
        lines += [f"**{arm}:**", "", "| Year | Sharpe (that year's daily returns only) |", "|---|---|"]
        for year, grp in net.groupby(net.index.year):
            lines.append(f"| {int(year)} | {study.sharpe_point(grp):.4f} |")
        lines += [""]
    lines += ["### Jackknife: drop-one-year", ""]
    for arm in open_arms:
        lines += [f"**{arm}** (Sharpe with the given year's daily returns excluded):", "",
                  "| Year dropped | Sharpe |", "|---|---|"]
        for year, sh in sorted(jackknife_year[arm].items()):
            lines.append(f"| {year} | {sh:.4f} |")
        lines += [""]
    lines += ["### Jackknife: drop-one-sector", "", "| Sector dropped | Symbols dropped | H1 Sharpe | H2 Sharpe |",
              "|---|---|---|---|"]
    for sector, members in config.UNIVERSE.items():
        lines.append(f"| {sector} | {', '.join(members)} | {_row(diagnostics, f'jackknife_sector_{sector}_H1')} | "
                     f"{_row(diagnostics, f'jackknife_sector_{sector}_H2')} |")
    lines += [
        "",
        "## Attribution decompositions (of already-computed series; no new constructions)",
        "",
        "### (a) Gross-of-cost Sharpe, restated alongside net",
        "",
        "Same positions and leverage path; only the costs are removed.",
        "",
        "| Arm | Net Sharpe | Gross-of-cost Sharpe |",
        "|---|---|---|",
    ]
    for arm in open_arms:
        lines.append(f"| {arm} | {series[arm]['sharpe']:.4f} | {gross_sharpe[arm]:.4f} |")
    if legs is not None:
        per_year = config.TRADING_DAYS_PER_YEAR
        lines += [
            "",
            "### (b) H1 long-leg vs short-leg contribution split",
            "",
            "Each leg's levered daily contribution net of its own trading and roll costs.",
            "",
            f"- Long-leg annualized mean contribution: {legs['long'].mean() * per_year:.4%}",
            f"- Short-leg annualized mean contribution: {legs['short'].mean() * per_year:.4%}",
            f"- Long-leg cumulative contribution (sum of daily contributions, full sample): {legs['long'].sum():.4%}",
            f"- Short-leg cumulative contribution (sum of daily contributions, full sample): {legs['short'].sum():.4%}",
        ]
    lines += [
        "",
        "### (c) Per-year table annotated against the 2021-22 backwardation episode",
        "",
        "| Year | H1 return | H2 return | Note |",
        "|---|---|---|---|",
    ]
    annual = {arm: study.annual_returns(series[arm]["result"]["daily_net_returns"]) for arm in open_arms}
    notes = {
        2021: "2021: post-COVID demand recovery outpacing supply -- widely documented broad commodity backwardation.",
        2022: "2022: Russia/Ukraine war supply shock intensified backwardation across energy and several other "
              "commodities.",
    }

    def cell(arm, year):
        value = annual.get(arm, {}).get(year)
        return "--" if value is None else f"{value:.4%}"

    for year in sorted(set().union(*[set(a) for a in annual.values()]) if annual else []):
        lines.append(f"| {year} | {cell('H1', year)} | {cell('H2', year)} | {notes.get(year, '')} |")
    lines += [
        "",
        "No further interpretation attempted -- a factual annotation of already-computed "
        "numbers against a well-documented macro episode, not a claim about causality.",
        "",
        "Every Sharpe above: `results/robustness_variants.csv`.",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
