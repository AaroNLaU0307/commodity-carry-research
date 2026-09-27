"""
README figure generator for the corrected pipeline: writes
reports/rerun/figures/*.png. The committed reports/figures/*.png are the
published 2026-07-16 figures and are never overwritten.

Renders from the committed machine-readable results the runners write --
results/primary_summary.json (H1/H2 net Sharpe and the three seeds' CIs),
results/robustness_variants.csv (the registered variants and the diagnostic
slices) and results/primary_monthly_returns.csv (net and gross monthly
returns) -- so every plotted number is the one in those files and in the
reports generated alongside them. No data access and no recomputation; run
after the primary and robustness stages (`python scripts/run_all.py` does).

Figure 4 (the pre-amendment F11 deadlock) is optional: it reads the F11
census CSV from config.WORKSPACE and is skipped when that file is absent.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src import config  # noqa: E402

PRIMARY_RESULTS_PATH = config.RESULTS_DIR / "primary_summary.json"
VARIANTS_PATH = config.RESULTS_DIR / "robustness_variants.csv"
MONTHLY_PATH = config.RESULTS_DIR / "primary_monthly_returns.csv"
FIGURES_DIR = config.RERUN_FIGURES_DIR

# Okabe-Ito colorblind-safe palette: two hues only, plus neutral gray/dark-gray.
H1_COLOR = "#0072B2"   # blue
H2_COLOR = "#D55E00"   # vermillion
GRAY = "#8A8A8A"
DARK = "#333333"
ARM_COLOR = {"H1": H1_COLOR, "H2": H2_COLOR}
ARM_LABEL = {"H1": "H1 (XS)", "H2": "H2 (TS)"}

FIG_W_IN, DPI = 8.0, 150  # ~1200px wide


def load_results() -> dict:
    missing = [p for p in (PRIMARY_RESULTS_PATH, VARIANTS_PATH, MONTHLY_PATH) if not p.exists()]
    if missing:
        raise FileNotFoundError(f"missing results artifact(s) {missing} -- run the primary and robustness stages first")
    summary = json.loads(PRIMARY_RESULTS_PATH.read_text(encoding="utf-8"))
    variants = pd.read_csv(VARIANTS_PATH)
    monthly = pd.read_csv(MONTHLY_PATH, index_col="month")
    monthly.index = pd.PeriodIndex(monthly.index, freq="M").to_timestamp(how="end").normalize()
    arms = [a for a in ("H1", "H2") if "net_sharpe" in summary["arms"][a]]
    return {"summary": summary, "variants": variants, "monthly": monthly, "arms": arms}


def fig1_gates_forest(res: dict, out_path: Path):
    summary, variants = res["summary"], res["variants"]
    fig, ax = plt.subplots(figsize=(FIG_W_IN, 6.0), dpi=DPI)
    rows = {"H1": 4.2, "H2": 2.8}
    y_registered, y_diagnostic = 1.5, 0.5
    ax.axvline(0, color=DARK, linewidth=1.2, zorder=1)
    ax.axvline(config.SHARPE_GATE_MIN, color=DARK, linewidth=1.2, linestyle="--", zorder=1)
    ax.text(config.SHARPE_GATE_MIN, 5.05, f"{config.SHARPE_GATE_MIN:.2f} gate", ha="center", va="bottom",
            fontsize=8, color=DARK)

    for arm in res["arms"]:
        r = summary["arms"][arm]["ci_by_seed"][0]  # seed[0], the gate-deciding seed
        y, color = rows[arm], ARM_COLOR[arm]
        ax.errorbar(r["point_estimate"], y,
                    xerr=[[r["point_estimate"] - r["ci_low"]], [r["ci_high"] - r["point_estimate"]]],
                    fmt="o", markersize=9, color=color, ecolor=color, elinewidth=2.2, capsize=4, zorder=3)
        ax.text(0.01, y + 0.45, f"{ARM_LABEL[arm]}   net Sharpe {r['point_estimate']:.4f}   "
                f"95% CI [{r['ci_low']:.2f}, {r['ci_high']:.2f}]",
                ha="left", va="bottom", fontsize=9.5, fontweight="bold", color=color,
                transform=ax.get_yaxis_transform())

    strips = (
        (variants[variants["kind"] == "registered"], y_registered, "o",
         "registered variants (Sec 8 items 1-7, 10; execution-lag-1)"),
        (variants[variants["kind"] == "diagnostic"], y_diagnostic, "D",
         "diagnostic slices (F7 ex-PA/PL, sub-period halves, drop-one-sector)"),
    )
    for rows_df, y, marker, label in strips:
        ax.scatter(rows_df["sharpe"], [y] * len(rows_df), color=GRAY, s=22, alpha=0.6, marker=marker, zorder=2,
                   edgecolors="none")
        ax.text(0.01, y + 0.3, f"{label} -- point estimates, non-gating (n={len(rows_df)})",
                ha="left", va="bottom", fontsize=8.5, color=GRAY, style="italic", transform=ax.get_yaxis_transform())

    lows = [summary["arms"][a]["ci_by_seed"][0]["ci_low"] for a in res["arms"]] + variants["sharpe"].tolist()
    highs = [summary["arms"][a]["ci_by_seed"][0]["ci_high"] for a in res["arms"]] + variants["sharpe"].tolist()
    ax.set_xlim(min(-1.0, min(lows) - 0.1), max(0.8, max(highs) + 0.1))
    ax.set_ylim(0.0, 5.4)
    ax.set_yticks([])
    ax.set_xlabel("Annualized Sharpe ratio")
    ax.set_title("Net Sharpe with 95% bootstrap CI against the promotion gate; variants and diagnostics below",
                 fontsize=10.5)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig2_equity_curves(res: dict, out_path: Path):
    monthly = res["monthly"]
    fig, ax = plt.subplots(figsize=(FIG_W_IN, 4.5), dpi=DPI)
    for arm in res["arms"]:
        color = ARM_COLOR[arm]
        ax.plot(monthly.index, (1.0 + monthly[f"{arm}_net"]).cumprod(), color=color, linewidth=1.6,
                label=f"{ARM_LABEL[arm]} net")
        ax.plot(monthly.index, (1.0 + monthly[f"{arm}_gross"]).cumprod(), color=color, linewidth=1.3,
                linestyle=":", label=f"{ARM_LABEL[arm]} gross of costs")
    ax.axhline(1.0, color=DARK, linewidth=1.3, zorder=1)
    ax.set_ylabel("Cumulative growth of $1 (month-end)")
    ax.set_title("Cumulative growth of $1, net and gross of costs (same positions and leverage)", fontsize=10.5)
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=2)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig3_per_year_returns(res: dict, out_path: Path):
    summary = res["summary"]
    years = sorted({int(y) for arm in res["arms"] for y in summary["arms"][arm]["annual_returns"]})
    fig, ax = plt.subplots(figsize=(FIG_W_IN, 4.5), dpi=DPI)
    x = np.arange(len(years))
    width = 0.38
    if 2021 in years and 2022 in years:
        i21, i22 = years.index(2021), years.index(2022)
        ax.axvspan(i21 - 0.5, i22 + 0.5, color=GRAY, alpha=0.15, zorder=0)
    for k, arm in enumerate(res["arms"]):
        annual = summary["arms"][arm]["annual_returns"]
        values = [100.0 * annual.get(str(y), float("nan")) for y in years]
        ax.bar(x + (k - 0.5) * width, values, width, color=ARM_COLOR[arm], label=ARM_LABEL[arm])
    ax.axhline(0, color=DARK, linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], fontsize=8, rotation=45, ha="right")
    ax.set_ylabel("Annual net return (%)")
    ax.set_title("Annual net returns per arm, 2021-22 backwardation window shaded", fontsize=10.5)
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig4_f11_deadlock(out_path: Path) -> bool:
    """Optional. Uses only the already-generated F11 census artifact; skips
    (returns False) if it isn't readily loadable. Never re-runs the census
    and never touches src/roll.py's current (post-amendment) logic."""
    census_path = config.WORKSPACE / "stuck_episodes_full.csv"
    if not census_path.exists():
        return False
    try:
        df = pd.read_csv(census_path)
        row = df[df["symbol"] == "PL"].iloc[0]
        expiry = pd.Timestamp(row["expiry"]).normalize()
        last_held = pd.Timestamp(row["last_date_held"]).normalize()
    except (KeyError, IndexError, ValueError):
        return False

    fig, ax = plt.subplots(figsize=(FIG_W_IN, 4.0), dpi=DPI)
    ax.plot([expiry, last_held], [expiry, expiry], color=H1_COLOR, linewidth=2.4,
            label="PL held-front expiration (pre-amendment rule)", zorder=3)
    ax.plot([expiry, last_held], [expiry, last_held], color=GRAY, linewidth=1.2, linestyle="--",
            label="expiration keeping pace with calendar (normal)", zorder=2)
    ax.set_xlabel("Calendar date")
    ax.set_ylabel("Held front's expiration date")
    ax.set_title("PL: the pre-amendment roll rule never advanced past this contract's expiry", fontsize=10.5)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return True


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    res = load_results()
    print("Writing fig 1 (gates forest)...", flush=True)
    fig1_gates_forest(res, FIGURES_DIR / "gates_forest.png")
    print("Writing fig 2 (equity curves)...", flush=True)
    fig2_equity_curves(res, FIGURES_DIR / "equity_curves.png")
    print("Writing fig 3 (per-year returns)...", flush=True)
    fig3_per_year_returns(res, FIGURES_DIR / "per_year_returns.png")
    made_fig4 = fig4_f11_deadlock(FIGURES_DIR / "f11_deadlock.png")
    print(f"fig 4 {'written' if made_fig4 else 'skipped (F11 census CSV not in WORKSPACE)'}", flush=True)
    print(f"Done. See {FIGURES_DIR}", flush=True)


if __name__ == "__main__":
    main()
