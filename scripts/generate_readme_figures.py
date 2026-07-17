"""
README figure generator. Docs addendum only -- the study is closed and its
verdict is frozen: no new analysis, no verdict-language changes, no edits to
any committed generated report. This script is the SOLE producer of
reports/figures/*.png.

Reproduction gate: before any figure is written, every headline number this
script regenerates (H1/H2 net Sharpe + all-3-seed CIs, gross Sharpe, the
~28 registered robustness/diagnostic point estimates, and both arms' 17-year
annual-return tables) must match reports/PRIMARY_REPORT.md and
reports/ROBUSTNESS_REPORT.md to their reported precision. Any mismatch halts
before any figure is written (src/repro_gate.py).

Net daily-return series: loaded from the persisted workspace equity curves
(_carry-research-workspace/phase1c_equity_curve_H{1,2}.csv, referenced in
PRIMARY_REPORT.md) where available, as an independent check alongside the
freshly-regenerated net series below -- both must agree with the committed
report. Gross series and the ~28 variant point estimates were never
persisted, so they are regenerated via the EXACT data-loading path and
construction sequence scripts/phase1c_robustness.py used (raw DBN, same
src/ modules, same KNOWN_ALLOWED_TRANSIENT_GRAZES) -- no parallel or new
analysis path. Items intentionally not recomputed here (not needed by any
figure): attribution (b)'s long/short-leg split, and the drop-one-year
jackknife (34 near-duplicate perturbations of the same construction; the
sub-period halves and per-year table already cover temporal stability for
these figures' purposes).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\commodity-carry-research")
sys.path.insert(0, str(REPO))

from src import config, pipeline, primary, robustness, stats  # noqa: E402
from src.portfolio import xs_raw_signal, ts_raw_signal  # noqa: E402
from src.repro_gate import ReproductionGate, ReproductionGateError  # noqa: E402

WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")
FIGURES_DIR = REPO / "reports" / "figures"

KNOWN_ALLOWED_TRANSIENT_GRAZES = {
    ("NG", "192047__2010-06-28"),
    ("NG", "192053__2010-12-28"),
}

# Okabe-Ito colorblind-safe palette: two hues only, plus neutral gray/dark-gray.
H1_COLOR = "#0072B2"   # blue
H2_COLOR = "#D55E00"   # vermillion
GRAY = "#8A8A8A"
DARK = "#333333"

FIG_W_IN, DPI = 8.0, 150  # ~1200px wide

# ---------------------------------------------------------------------------
# Committed-report values (hand-transcribed from reports/PRIMARY_REPORT.md
# and reports/ROBUSTNESS_REPORT.md as committed; the reproduction gate below
# checks freshly-regenerated numbers against these, not the other way round).
# ---------------------------------------------------------------------------
EXPECTED_CI = {
    "H1": {7: (-0.4417, 0.4287), 13: (-0.4463, 0.4241), 31: (-0.4423, 0.4263)},
    "H2": {7: (-0.5580, 0.3227), 13: (-0.5784, 0.3215), 31: (-0.5665, 0.3104)},
}
EXPECTED_NET_SHARPE = {"H1": -0.0031, "H2": -0.1255}
EXPECTED_GROSS_SHARPE = {"H1": 0.0061, "H2": -0.1288}

EXPECTED_VARIANTS = {
    "R1_sector_neutral_xs": 0.0365,
    "R2_quintile_xs": 0.0154,
    "R3_equal_weight_legs": 0.0139,
    "R4_smoothed_carry_H1": 0.1648,
    "R4_smoothed_carry_H2": -0.0562,
    "R5_deferred_carry_H1": 0.1829,
    "R5_deferred_carry_H2": -0.0058,
    "R6_2x_cost_H1": -0.0122,
    "R6_2x_cost_H2": -0.1223,
    "R7_fixed_calendar_H1": 0.1248,
    "R7_fixed_calendar_H2": -0.0628,
    "R10_ke_excluded": -0.0271,
    "exPAPL_H1": -0.0092,
    "exPAPL_H2": -0.2677,
    "subperiod_H1_first": 0.0435,
    "subperiod_H1_second": -0.0485,
    "subperiod_H2_first": -0.0747,
    "subperiod_H2_second": -0.1765,
    "jackknife_sector_energy_H1": 0.2186,
    "jackknife_sector_energy_H2": -0.0718,
    "jackknife_sector_metals_H1": -0.0671,
    "jackknife_sector_metals_H2": -0.2108,
    "jackknife_sector_grains_H1": -0.1927,
    "jackknife_sector_grains_H2": -0.1787,
    "jackknife_sector_livestock_H1": 0.1024,
    "jackknife_sector_livestock_H2": -0.0514,
}

EXPECTED_ANNUAL = {
    "H1": {2010: 16.0005, 2011: -0.4649, 2012: -6.1675, 2013: 7.9970, 2014: -30.6974,
           2015: 12.6742, 2016: -4.6247, 2017: 14.9351, 2018: -18.0362, 2019: 5.4445,
           2020: -3.8141, 2021: -2.4298, 2022: 5.6852, 2023: -8.9908, 2024: -4.3636,
           2025: 6.7596, 2026: 11.3038},
    "H2": {2010: -21.5977, 2011: 6.1813, 2012: -7.2463, 2013: 10.8094, 2014: -10.7015,
           2015: 28.6642, 2016: -13.0592, 2017: 0.9654, 2018: 0.6746, 2019: -1.0311,
           2020: -11.1862, 2021: 1.7054, 2022: 5.1026, 2023: 1.5285, 2024: -4.3676,
           2025: -15.5766, 2026: 2.6519},
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
    x = daily_returns.dropna().values
    sigma = x.std(ddof=1) if len(x) > 1 else 0.0
    if sigma <= 0:
        return 0.0
    return float(x.mean() / sigma * np.sqrt(config.TRADING_DAYS_PER_YEAR))


def build_arm(carry_panel, vol_panel, settle_by_month, month_end_index, daily_index,
              daily_returns_by_symbol, entry_dates, signal_fn, symbol_of_column, cost_multiplier=1.0):
    weights = primary.build_pre_leverage_weights(carry_panel, vol_panel, entry_dates, signal_fn)
    result = primary.compute_arm_daily_returns(
        weights, daily_returns_by_symbol, settle_by_month, month_end_index, daily_index,
        symbol_of_column=symbol_of_column, cost_multiplier=cost_multiplier)
    return result, sharpe_point(result["daily_net_returns"])


def _annual_returns(daily_net_returns: pd.Series) -> dict:
    out = {}
    for year, grp in daily_net_returns.dropna().groupby(daily_net_returns.dropna().index.year):
        out[int(year)] = float((1.0 + grp).prod() - 1.0)
    return out


# ---------------------------------------------------------------------------
# Full-pipeline regeneration (raw DBN, same path as scripts/phase1c_robustness.py)
# ---------------------------------------------------------------------------
def run_full_pipeline():
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
    front_by_symbol, settle_wide_by_symbol, oi_wide_by_symbol, seq_by_symbol = {}, {}, {}, {}
    fixed_cal_front_by_symbol = {}

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
            raise RuntimeError(f"STUCK FRONT (unexpected): {disclosure}")

        carry_by_symbol[symbol] = pipeline.symbol_carry_series(outright_panel, front, seq, symbol, skip_tripwire=skip_tripwire)
        daily_returns_1x[symbol] = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=1.0)["returns"]
        daily_returns_2x[symbol] = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=2.0)["returns"]
        daily_returns_0x[symbol] = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=0.0)["returns"]
        front_by_symbol[symbol] = front
        settle_wide_by_symbol[symbol] = settle_wide
        oi_wide_by_symbol[symbol] = oi_wide
        seq_by_symbol[symbol] = seq

        fc_front = robustness.fixed_calendar_front_series(oi_wide, seq, expiry_by_key)
        fixed_cal_front_by_symbol[symbol] = fc_front

    print("Building month-end panel, daily index, vol/settle-at-month-end panels...", flush=True)
    carry_panel = pipeline.month_end_carry_panel(carry_by_symbol, entry_dates=entry_dates)
    month_end_index = carry_panel.index
    daily_index = pd.DatetimeIndex(sorted(set().union(*[s.index for s in daily_returns_1x.values()])))
    vol_panel = pd.DataFrame({s: primary.symbol_vol_at_month_end(daily_returns_1x[s], month_end_index) for s in carry_by_symbol})
    settle_by_month = pd.DataFrame({
        s: primary.symbol_settle_at_month_end(front_by_symbol[s], settle_wide_by_symbol[s], month_end_index)
        for s in carry_by_symbol
    })

    results = {}
    primary_result = {}
    print("Rebuilding primary H1/H2 (net + gross)...", flush=True)
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        weights = primary.build_pre_leverage_weights(carry_panel, vol_panel, entry_dates, signal_fn)
        net_result = primary.compute_arm_daily_returns(
            weights, daily_returns_1x, settle_by_month, month_end_index, daily_index, symbol_of_column)
        gross_result = primary.compute_arm_daily_returns(
            weights, daily_returns_0x, settle_by_month, month_end_index, daily_index,
            symbol_of_column=symbol_of_column, cost_multiplier=0.0)
        primary_result[arm] = {
            "weights": weights,
            "net_returns": net_result["daily_net_returns"],
            "gross_returns": gross_result["daily_net_returns"],
            "net_sharpe": sharpe_point(net_result["daily_net_returns"]),
            "gross_sharpe": sharpe_point(gross_result["daily_net_returns"]),
            "annual": _annual_returns(net_result["daily_net_returns"]),
        }

    print("Running stationary bootstrap (3 seeds) on regenerated net series...", flush=True)
    bootstrap_by_arm = {}
    for arm in ("H1", "H2"):
        net = primary_result[arm]["net_returns"].dropna().values
        bootstrap_by_arm[arm] = stats.stationary_bootstrap_multi_seed(net)
    primary_result["bootstrap"] = bootstrap_by_arm

    print("Item 1: sector-neutral XS...", flush=True)
    sector_signal_fn = lambda snap: robustness.sector_neutral_xs_raw_signal(snap, config.SYMBOL_SECTOR)  # noqa: E731
    _, sh = build_arm(carry_panel, vol_panel, settle_by_month, month_end_index, daily_index,
                       daily_returns_1x, entry_dates, sector_signal_fn, symbol_of_column)
    results["R1_sector_neutral_xs"] = sh

    print("Item 2: quintile cutoffs...", flush=True)
    _, sh = build_arm(carry_panel, vol_panel, settle_by_month, month_end_index, daily_index,
                       daily_returns_1x, entry_dates, robustness.xs_raw_signal_quintile, symbol_of_column)
    results["R2_quintile_xs"] = sh

    print("Item 3: equal-weight legs...", flush=True)
    r3_weights = robustness.equal_weight_pre_leverage_weights(carry_panel, entry_dates)
    r3_result = primary.compute_arm_daily_returns(
        r3_weights, daily_returns_1x, settle_by_month, month_end_index, daily_index, symbol_of_column)
    results["R3_equal_weight_legs"] = sharpe_point(r3_result["daily_net_returns"])

    print("Item 4: 1-month-smoothed carry...", flush=True)
    smoothed_panel = robustness.smooth_carry_panel(carry_panel)
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        _, sh = build_arm(smoothed_panel, vol_panel, settle_by_month, month_end_index, daily_index,
                           daily_returns_1x, entry_dates, signal_fn, symbol_of_column)
        results[f"R4_smoothed_carry_{arm}"] = sh

    print("Item 5: 12-month-deferred carry...", flush=True)
    carry_deferred_by_symbol = {
        s: robustness.symbol_deferred_carry_series(outright_panel, front_by_symbol[s], seq_by_symbol[s], s)
        for s in carry_by_symbol
    }
    deferred_panel = pipeline.month_end_carry_panel(carry_deferred_by_symbol, entry_dates=entry_dates)
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        _, sh = build_arm(deferred_panel, vol_panel, settle_by_month, month_end_index, daily_index,
                           daily_returns_1x, entry_dates, signal_fn, symbol_of_column)
        results[f"R5_deferred_carry_{arm}"] = sh

    print("Item 6: 2x cost table...", flush=True)
    for arm in ("H1", "H2"):
        weights = primary_result[arm]["weights"]
        result_2x = primary.compute_arm_daily_returns(
            weights, daily_returns_2x, settle_by_month, month_end_index, daily_index,
            symbol_of_column=symbol_of_column, cost_multiplier=2.0)
        results[f"R6_2x_cost_{arm}"] = sharpe_point(result_2x["daily_net_returns"])

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
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        _, sh = build_arm(carry_fc_panel, vol_fc_panel, settle_fc_by_month, month_end_index, daily_index,
                           daily_returns_fc_by_symbol, entry_dates, signal_fn, symbol_of_column)
        results[f"R7_fixed_calendar_{arm}"] = sh

    print("Item 10: KE-excluded sensitivity...", flush=True)
    entry_dates_no_ke = {s: v for s, v in entry_dates.items() if s != "KE"}
    carry_panel_no_ke = carry_panel.drop(columns=["KE"]) if "KE" in carry_panel.columns else carry_panel
    vol_panel_no_ke = vol_panel.drop(columns=["KE"]) if "KE" in vol_panel.columns else vol_panel
    _, sh = build_arm(carry_panel_no_ke, vol_panel_no_ke, settle_by_month, month_end_index, daily_index,
                       daily_returns_1x, entry_dates_no_ke, xs_raw_signal, symbol_of_column)
    results["R10_ke_excluded"] = sh

    print("F7 ex-PA/PL diagnostic...", flush=True)
    entry_dates_ex_papl = {s: v for s, v in entry_dates.items() if s not in ("PA", "PL")}
    carry_panel_ex_papl = carry_panel.drop(columns=[c for c in ("PA", "PL") if c in carry_panel.columns])
    vol_panel_ex_papl = vol_panel.drop(columns=[c for c in ("PA", "PL") if c in vol_panel.columns])
    for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
        _, sh = build_arm(carry_panel_ex_papl, vol_panel_ex_papl, settle_by_month, month_end_index, daily_index,
                           daily_returns_1x, entry_dates_ex_papl, signal_fn, symbol_of_column)
        results[f"exPAPL_{arm}"] = sh

    print("Items 8-9: sub-period + jackknife-sector diagnostics...", flush=True)
    for arm in ("H1", "H2"):
        net = primary_result[arm]["net_returns"].dropna()
        midpoint = net.index[len(net) // 2]
        first_half, second_half = net[net.index <= midpoint], net[net.index > midpoint]
        results[f"subperiod_{arm}_first"] = sharpe_point(first_half)
        results[f"subperiod_{arm}_second"] = sharpe_point(second_half)

    for sector in config.UNIVERSE:
        drop_symbols = config.UNIVERSE[sector]
        entry_dates_ex_sector = {s: v for s, v in entry_dates.items() if s not in drop_symbols}
        carry_panel_ex_sector = carry_panel.drop(columns=[c for c in drop_symbols if c in carry_panel.columns])
        vol_panel_ex_sector = vol_panel.drop(columns=[c for c in drop_symbols if c in vol_panel.columns])
        for arm, signal_fn in (("H1", xs_raw_signal), ("H2", ts_raw_signal)):
            _, sh = build_arm(carry_panel_ex_sector, vol_panel_ex_sector, settle_by_month, month_end_index, daily_index,
                               daily_returns_1x, entry_dates_ex_sector, signal_fn, symbol_of_column)
            results[f"jackknife_sector_{sector}_{arm}"] = sh

    return {"primary": primary_result, "variants": results}


def load_persisted_net(arm: str) -> pd.Series | None:
    """Independent check: derive daily returns from the persisted workspace
    equity curve (referenced in reports/PRIMARY_REPORT.md), if it exists."""
    path = WORKSPACE / f"phase1c_equity_curve_{arm}.csv"
    if not path.exists():
        return None
    equity = pd.read_csv(path, index_col=0, parse_dates=True)["equity"]
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0] - 1.0
    return returns


def verify_reproduction(pipeline_out) -> None:
    gate = ReproductionGate()
    primary_result = pipeline_out["primary"]
    variants = pipeline_out["variants"]

    for arm in ("H1", "H2"):
        gate.check(f"{arm} net Sharpe (fresh pipeline)", EXPECTED_NET_SHARPE[arm], primary_result[arm]["net_sharpe"])
        gate.check(f"{arm} gross Sharpe", EXPECTED_GROSS_SHARPE[arm], primary_result[arm]["gross_sharpe"])
        for r in primary_result["bootstrap"][arm]:
            seed = r["seed"]
            exp_lo, exp_hi = EXPECTED_CI[arm][seed]
            gate.check(f"{arm} seed {seed} CI low", exp_lo, r["ci_low"])
            gate.check(f"{arm} seed {seed} CI high", exp_hi, r["ci_high"])
            if seed == config.BOOTSTRAP_SEEDS[0]:
                gate.check(f"{arm} seed {seed} point estimate", EXPECTED_NET_SHARPE[arm], r["point_estimate"])
        for year, expected_pct in EXPECTED_ANNUAL[arm].items():
            actual_frac = primary_result[arm]["annual"].get(year)
            if actual_frac is None:
                gate.check(f"{arm} {year} annual return (MISSING)", expected_pct, float("nan"))
                continue
            gate.check(f"{arm} {year} annual return", expected_pct, actual_frac * 100.0)

        persisted = load_persisted_net(arm)
        if persisted is not None:
            persisted_sharpe = sharpe_point(persisted)
            gate.check(f"{arm} net Sharpe (persisted equity curve)", EXPECTED_NET_SHARPE[arm], persisted_sharpe)

    for name, expected in EXPECTED_VARIANTS.items():
        actual = variants.get(name)
        if actual is None:
            gate.check(f"variant {name} (MISSING)", expected, float("nan"))
            continue
        gate.check(f"variant {name}", expected, actual)

    gate.finalize()


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def fig1_gates_forest(pipeline_out, out_path: Path):
    primary_result = pipeline_out["primary"]
    variants = pipeline_out["variants"]
    fig, ax = plt.subplots(figsize=(FIG_W_IN, 6.0), dpi=DPI)

    # Row layout: each row gets its own vertical band (label above, data below)
    # so the label text never overlaps the error-bar whiskers.
    y_h1, y_h2, y_strip = 3.6, 2.0, 0.5
    ax.axvline(0, color=DARK, linewidth=1.2, zorder=1)
    ax.text(0, 4.55, "0", ha="center", va="bottom", fontsize=8, color=DARK)
    ax.axvline(config.SHARPE_GATE_MIN, color=DARK, linewidth=1.2, linestyle="--", zorder=1)
    ax.text(config.SHARPE_GATE_MIN, 4.55, "0.30 gate", ha="center", va="bottom", fontsize=8, color=DARK)

    for arm, y in (("H1", y_h1), ("H2", y_h2)):
        r = primary_result["bootstrap"][arm][0]  # seed[0], the gate-deciding seed
        color = H1_COLOR if arm == "H1" else H2_COLOR
        ax.errorbar(r["point_estimate"], y, xerr=[[r["point_estimate"] - r["ci_low"]], [r["ci_high"] - r["point_estimate"]]],
                    fmt="o", markersize=9, color=color, ecolor=color, elinewidth=2.2, capsize=4, zorder=3)
        label = "H1 (XS)" if arm == "H1" else "H2 (TS)"
        ax.text(-0.98, y + 0.55, f"{label}   net Sharpe {r['point_estimate']:.4f}   95% CI [{r['ci_low']:.2f}, {r['ci_high']:.2f}]",
                ha="left", va="bottom", fontsize=9.5, fontweight="bold", color=color)

    variant_values = list(variants.values())
    ax.scatter(variant_values, [y_strip] * len(variant_values), color=GRAY, s=22, alpha=0.55, zorder=2,
               edgecolors="none")
    ax.text(-0.98, y_strip + 0.55, f"registered variants — point estimates, non-gating (n={len(variant_values)})",
            ha="left", va="bottom", fontsize=8.5, color=GRAY, style="italic")

    ax.set_xlim(-1.0, 0.7)
    ax.set_ylim(-0.3, 4.85)
    ax.set_yticks([])
    ax.set_xlabel("Annualized Sharpe ratio")
    ax.set_title("Neither arm approaches the gate; the null is uniform across ~30 registered variants",
                  fontsize=10.5)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig2_equity_curves(pipeline_out, out_path: Path):
    primary_result = pipeline_out["primary"]
    fig, ax = plt.subplots(figsize=(FIG_W_IN, 4.5), dpi=DPI)

    for arm, color in (("H1", H1_COLOR), ("H2", H2_COLOR)):
        net_equity = (1.0 + primary_result[arm]["net_returns"].dropna()).cumprod()
        gross_equity = (1.0 + primary_result[arm]["gross_returns"].dropna()).cumprod()
        label = "H1 (XS)" if arm == "H1" else "H2 (TS)"
        ax.plot(net_equity.index, net_equity.values, color=color, linewidth=1.6, linestyle="-",
                label=f"{label} net")
        ax.plot(gross_equity.index, gross_equity.values, color=color, linewidth=1.3, linestyle=":",
                label=f"{label} gross")

    ax.axhline(1.0, color=DARK, linewidth=1.3, zorder=1)
    ax.set_ylabel("Cumulative growth of $1")
    ax.set_xlabel("")
    ax.set_title("Gross lines track the net lines closely — costs are not what killed this", fontsize=10.5)
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=2)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig3_per_year_returns(pipeline_out, out_path: Path):
    primary_result = pipeline_out["primary"]
    years = sorted(primary_result["H1"]["annual"].keys())
    h1_vals = [primary_result["H1"]["annual"][y] * 100.0 for y in years]
    h2_vals = [primary_result["H2"]["annual"][y] * 100.0 for y in years]

    fig, ax = plt.subplots(figsize=(FIG_W_IN, 4.5), dpi=DPI)
    x = np.arange(len(years))
    width = 0.38

    if 2021 in years and 2022 in years:
        i21, i22 = years.index(2021), years.index(2022)
        ax.axvspan(i21 - 0.5, i22 + 0.5, color=GRAY, alpha=0.15, zorder=0)

    ax.bar(x - width / 2, h1_vals, width, color=H1_COLOR, label="H1 (XS)")
    ax.bar(x + width / 2, h2_vals, width, color=H2_COLOR, label="H2 (TS)")
    ax.axhline(0, color=DARK, linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], fontsize=8, rotation=45, ha="right")
    ax.set_ylabel("Annual net return (%)")
    ax.set_title("2022 positive but not either arm's best year — decay stays undischarged", fontsize=10.5)
    if 2021 in years and 2022 in years:
        ymax = ax.get_ylim()[1]
        ax.text((i21 + i22) / 2, ymax * 0.96, "2021–22\nbackwardation", ha="center", va="top", fontsize=7.5,
                color=DARK, style="italic")
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig4_f11_deadlock(out_path: Path) -> bool:
    """Optional. Uses only the already-generated F11 census artifact; skips
    silently (returns False) if it isn't readily loadable. Never re-runs
    the census and never touches src/roll.py's current (post-amendment) logic."""
    census_path = WORKSPACE / "stuck_episodes_full.csv"
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

    print("Running full regeneration pipeline (raw DBN, same path as phase1c_robustness.py)...", flush=True)
    pipeline_out = run_full_pipeline()

    print("Verifying reproduction gate against committed reports...", flush=True)
    try:
        verify_reproduction(pipeline_out)
    except ReproductionGateError as e:
        print(str(e), flush=True)
        print("HALTED. No figures written.", flush=True)
        sys.exit(1)
    print("Reproduction gate passed (bit-consistent with committed reports).", flush=True)

    print("Writing fig 1 (gates forest)...", flush=True)
    fig1_gates_forest(pipeline_out, FIGURES_DIR / "gates_forest.png")
    print("Writing fig 2 (equity curves)...", flush=True)
    fig2_equity_curves(pipeline_out, FIGURES_DIR / "equity_curves.png")
    print("Writing fig 3 (per-year returns)...", flush=True)
    fig3_per_year_returns(pipeline_out, FIGURES_DIR / "per_year_returns.png")
    print("Attempting fig 4 (F11 deadlock, optional)...", flush=True)
    made_fig4 = fig4_f11_deadlock(FIGURES_DIR / "f11_deadlock.png")
    print(f"  fig 4 {'written' if made_fig4 else 'skipped (census artifact not readily loadable)'}", flush=True)

    print("Done. See reports/figures/", flush=True)


if __name__ == "__main__":
    main()
