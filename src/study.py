"""
Real-data study assembly shared by the runners (scripts/phase1b_premise_test.py,
scripts/phase1c_primary_backtest.py, scripts/phase1c_robustness.py) and the
single entry point scripts/run_all.py.

load_context() reads the corpus once, builds every symbol's front / carry /
return series behind the permanent stuck-front tripwire and the zero-price
guard, and assembles the month-end panels. registered_series() constructs
every registered strategy-return series (PREREGISTRATION.md Sec 8/10 and
preregistration/AMENDMENT_2026-09-27.md) and diagnostic_series() the
non-gating diagnostic slices. Formulas live in pipeline / primary /
robustness / portfolio; this module only sequences them, so each runner
reads the same objects instead of carrying its own copy of the loop.

Real-data only in normal use; tests/test_run_all.py drives it end to end on a
synthetic corpus by replacing the two DBN readers.
"""
import json
import subprocess
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config, pipeline, primary, robustness
from .portfolio import ts_raw_signal, xs_raw_signal

# NG's two already-characterised, non-permanent single-day grazes (F11
# amendment record; docs/DATA_QA_REPORT.md F11 census). Any other tripwire
# firing halts the run for its own diagnosis.
KNOWN_ALLOWED_TRANSIENT_GRAZES = {
    ("NG", "192047__2010-06-28"),
    ("NG", "192053__2010-12-28"),
}

ARMS = ("H1", "H2")
SIGNAL_FN = {"H1": xs_raw_signal, "H2": ts_raw_signal}
ARM_LABEL = {"H1": "XS", "H2": "TS"}


class StudyHalt(RuntimeError):
    """A pipeline integrity check fired. kind is "stuck_front" (detail: the
    symbol and its violations) or "zero_price_guard" (detail: list of
    (symbol, date, contract, price))."""

    def __init__(self, kind: str, detail):
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


def entry_dates() -> dict:
    entry = {s: pd.Timestamp(config.SAMPLE_START) for s in config.ALL_SYMBOLS}
    entry["KE"] = pd.Timestamp(config.KE_ENTRY_DATE)
    return entry


def _tz_naive(ts):
    return ts.tz_localize(None) if ts.tzinfo is not None else ts


def find_stuck_front_violations(front_series: pd.Series, expiry_by_key: dict) -> list:
    """Same tz-safe comparison as pipeline.assert_front_not_past_expiry(),
    collecting every violation instead of raising on the first."""
    violations = []
    for date, contract in front_series.items():
        expiry = expiry_by_key.get(contract)
        if expiry is None:
            continue
        if _tz_naive(pd.Timestamp(expiry)) < _tz_naive(pd.Timestamp(date)):
            violations.append((date, contract))
    return violations


def check_tripwire(symbol: str, front: pd.Series, expiry_by_key: dict) -> tuple:
    """(ok_to_proceed, skip_tripwire_for_carry, disclosure). ok=False means
    halt. skip=True only for the known, non-permanent NG grazes."""
    violations = find_stuck_front_violations(front, expiry_by_key)
    if not violations:
        return True, False, None
    last_expiry = expiry_by_key.get(front.iloc[-1])
    permanent = last_expiry is not None and _tz_naive(pd.Timestamp(last_expiry)) < _tz_naive(
        pd.Timestamp(front.index.max()))
    if not permanent and all((symbol, c) in KNOWN_ALLOWED_TRANSIENT_GRAZES for _, c in violations):
        disclosure = (
            f"{symbol}: known allowed transient graze(s), contract(s) "
            f"{sorted({c for _, c in violations})!r}, held on {[str(d) for d, _ in violations]} "
            f"-- non-permanent, resolves the next trading day (F11 amendment record)."
        )
        return True, True, disclosure
    detail = f"{symbol}: {violations[:5]}{'...' if len(violations) > 5 else ''} (permanent={permanent})"
    return False, False, detail


def sharpe_point(daily_returns: pd.Series) -> float:
    """Annualized Sharpe, mean / std(ddof=1) * sqrt(252) -- the same point
    estimate stats.stationary_bootstrap_sharpe() reports."""
    x = pd.Series(daily_returns).dropna().to_numpy(dtype=float)
    sigma = x.std(ddof=1) if len(x) > 1 else 0.0
    if sigma <= 0:
        return 0.0
    return float(x.mean() / sigma * np.sqrt(config.TRADING_DAYS_PER_YEAR))


def annual_returns(daily_returns: pd.Series) -> dict:
    s = pd.Series(daily_returns).dropna()
    return {int(year): float((1.0 + grp).prod() - 1.0) for year, grp in s.groupby(s.index.year)}


def monthly_returns(daily_returns: pd.Series) -> pd.Series:
    s = pd.Series(daily_returns).dropna()
    return (1.0 + s).groupby(s.index.to_period("M")).prod() - 1.0


_PINNED_CODE_VERSION = None


def pin_code_version() -> str:
    """Fix the stamp for the rest of this process to the checkout's state
    now. scripts/run_all.py calls it before its first stage: each stage
    rewrites tracked report files under reports/rerun/, so a stamp read
    after the first stage would see its own output as an uncommitted change
    and read "-dirty" (addendum §10, 2026-09-28)."""
    global _PINNED_CODE_VERSION
    _PINNED_CODE_VERSION = None
    _PINNED_CODE_VERSION = code_version()
    return _PINNED_CODE_VERSION


def code_version() -> str:
    """git HEAD of this checkout (+ "-dirty" if uncommitted changes), or
    "unknown" outside a git checkout -- stamped on every report and result.
    Returns the pinned stamp when pin_code_version() has been called."""
    if _PINNED_CODE_VERSION is not None:
        return _PINNED_CODE_VERSION
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.REPO_ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=config.REPO_ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_json(path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False, default=_json_default) + "\n", encoding="utf-8")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    raise TypeError(f"not JSON serialisable: {type(o)}")


@dataclass
class StudyContext:
    outright_panel: pd.DataFrame
    entry_dates: dict
    statistics_diagnostics: dict
    seq: dict = field(default_factory=dict)
    oi_wide: dict = field(default_factory=dict)
    settle_wide: dict = field(default_factory=dict)
    front: dict = field(default_factory=dict)
    expiry_by_key: dict = field(default_factory=dict)
    carry: dict = field(default_factory=dict)
    returns: dict = field(default_factory=lambda: {1.0: {}, 2.0: {}, 0.0: {}})
    n_filled: dict = field(default_factory=dict)
    n_bars: dict = field(default_factory=dict)
    fixed_cal_front: dict = field(default_factory=dict)
    fixed_cal_tripwire_findings: list = field(default_factory=list)
    graze_disclosures: list = field(default_factory=list)
    carry_panel: pd.DataFrame = None
    month_end_index: pd.DatetimeIndex = None
    daily_index: pd.DatetimeIndex = None
    vol_panel: pd.DataFrame = None
    settle_by_month: pd.DataFrame = None
    cache: dict = field(default_factory=dict)

    @property
    def symbols(self) -> list:
        return list(self.carry)

    @property
    def symbol_of_column(self) -> dict:
        return {s: s for s in config.ALL_SYMBOLS}


def load_context(log=print) -> StudyContext:
    """Reads DATA_DIR and returns the assembled StudyContext. Raises
    StudyHalt when the tripwire or the zero-price guard fires."""
    log("Loading definition lookup (every definition file)...")
    definition_lookup = pipeline.build_definition_lookup()
    log(f"  {len(definition_lookup):,} rows")
    log("Loading settlement/OI panel (trade-date keyed, StatType-selected)...")
    settlement_oi_panel = pipeline.build_settlement_oi_panel()
    diagnostics = dict(settlement_oi_panel.attrs.get("diagnostics", {}))
    log(f"  {len(settlement_oi_panel):,} rows; diagnostics {diagnostics}")
    log("Building outright panel (session calendar)...")
    outright_panel = pipeline.build_outright_panel(definition_lookup, settlement_oi_panel)
    log(f"  {len(outright_panel):,} outright rows")
    return build_context(outright_panel, diagnostics, log=log)


def build_context(outright_panel: pd.DataFrame, statistics_diagnostics: dict | None = None,
                  log=print) -> StudyContext:
    ctx = StudyContext(outright_panel=outright_panel, entry_dates=entry_dates(),
                       statistics_diagnostics=dict(statistics_diagnostics or {}))
    guard_violations = []
    for symbol in config.ALL_SYMBOLS:
        log(f"Processing {symbol}...")
        seq = pipeline.symbol_listed_sequence(outright_panel, symbol)
        if not seq:
            log(f"  WARNING: no outright contracts found for {symbol}, skipping")
            continue
        oi_wide = pipeline.symbol_oi_wide(outright_panel, symbol, seq)
        settle_wide = pipeline.symbol_settle_wide(outright_panel, symbol, seq)
        front = pipeline.symbol_front_series(oi_wide, seq)
        expiry_by_key = (
            outright_panel[outright_panel["asset"] == symbol]
            .drop_duplicates(subset=["_contract_key"]).set_index("_contract_key")["expiration"].to_dict()
        )
        ok, skip_tripwire, disclosure = check_tripwire(symbol, front, expiry_by_key)
        if not ok:
            raise StudyHalt("stuck_front", {"symbol": symbol, "detail": disclosure})
        if skip_tripwire:
            log(f"  {disclosure}")
            ctx.graze_disclosures.append(disclosure)

        ctx.seq[symbol], ctx.oi_wide[symbol], ctx.settle_wide[symbol] = seq, oi_wide, settle_wide
        ctx.front[symbol], ctx.expiry_by_key[symbol] = front, expiry_by_key
        ctx.carry[symbol] = pipeline.symbol_carry_series(outright_panel, front, seq, symbol,
                                                         skip_tripwire=skip_tripwire)
        for mult in (1.0, 2.0, 0.0):
            r = pipeline.symbol_daily_returns(settle_wide, front, symbol, cost_multiplier=mult)
            ctx.returns[mult][symbol] = r["returns"]
            if mult == 1.0:
                ctx.n_filled[symbol] = r["n_filled"]
                guard_violations += [(symbol,) + v for v in r["guard_violations"]]
        ctx.n_bars[symbol] = len(settle_wide)

        fc_front = robustness.fixed_calendar_front_series(oi_wide, seq, expiry_by_key)
        ctx.fixed_cal_front[symbol] = fc_front
        fc_ok, _, fc_detail = check_tripwire(symbol, fc_front, expiry_by_key)
        if not fc_ok:
            ctx.fixed_cal_tripwire_findings.append(fc_detail)

    if guard_violations:
        raise StudyHalt("zero_price_guard", guard_violations)
    if not ctx.carry:
        raise FileNotFoundError("no symbol produced any outright contracts -- is DATA_DIR the right corpus?")

    log("Building month-end panels and the daily index...")
    ctx.carry_panel = pipeline.month_end_carry_panel(ctx.carry, entry_dates=ctx.entry_dates)
    ctx.month_end_index = ctx.carry_panel.index
    ctx.daily_index = pd.DatetimeIndex(sorted(set().union(*[s.index for s in ctx.returns[1.0].values()])))
    ctx.vol_panel = build_vol_panel(ctx.returns[0.0], ctx.month_end_index)
    ctx.settle_by_month = build_settle_by_month(ctx.front, ctx.settle_wide, ctx.month_end_index)
    log(f"  {len(ctx.month_end_index)} months, {len(ctx.daily_index):,} daily dates")
    return ctx


def build_vol_panel(returns_by_symbol: dict, month_end_index) -> pd.DataFrame:
    """Per-asset 60-day vol at each month-end, from cost-free returns
    (costs never feed a vol estimator; primary module docstring)."""
    return pd.DataFrame({s: primary.symbol_vol_at_month_end(r, month_end_index) for s, r in returns_by_symbol.items()})


def build_settle_by_month(front_by_symbol: dict, settle_wide_by_symbol: dict, month_end_index) -> pd.DataFrame:
    return pd.DataFrame({
        s: primary.symbol_settle_at_month_end(front_by_symbol[s], settle_wide_by_symbol[s], month_end_index)
        for s in front_by_symbol
    })


def run_arm(ctx: StudyContext, weights: pd.DataFrame, cost_multiplier: float = 1.0, execution_lag: int = 0,
            returns: dict | None = None, gross_returns: dict | None = None,
            settle: pd.DataFrame | None = None) -> dict:
    """primary.compute_arm_daily_returns() on the context's series: net
    returns at `cost_multiplier` with their cost-free counterpart, so roll
    costs are charged on |position| and leverage is sized pre-cost."""
    result = primary.compute_arm_daily_returns(
        weights,
        ctx.returns[cost_multiplier] if returns is None else returns,
        ctx.settle_by_month if settle is None else settle,
        ctx.month_end_index, ctx.daily_index,
        symbol_of_column=ctx.symbol_of_column, cost_multiplier=cost_multiplier,
        gross_returns_by_symbol=ctx.returns[0.0] if gross_returns is None else gross_returns,
        execution_lag=execution_lag,
    )
    result["weights_by_month"] = weights
    return result


def arm_weights(ctx: StudyContext, arm: str, carry_panel: pd.DataFrame | None = None,
                vol: pd.DataFrame | None = None, entry: dict | None = None, signal_fn=None) -> pd.DataFrame:
    return primary.build_pre_leverage_weights(
        ctx.carry_panel if carry_panel is None else carry_panel,
        ctx.vol_panel if vol is None else vol,
        ctx.entry_dates if entry is None else entry,
        SIGNAL_FN[arm] if signal_fn is None else signal_fn,
    )


def _drop(ctx: StudyContext, symbols) -> tuple:
    symbols = set(symbols)
    carry = ctx.carry_panel.drop(columns=[c for c in ctx.carry_panel.columns if c in symbols])
    vol = ctx.vol_panel.drop(columns=[c for c in ctx.vol_panel.columns if c in symbols])
    entry = {s: v for s, v in ctx.entry_dates.items() if s not in symbols}
    return carry, vol, entry


def _entry(series_id, item, arm, description, result, kind="registered"):
    return {"id": series_id, "item": item, "arm": arm, "description": description, "kind": kind,
            "result": result, "sharpe": sharpe_point(result["daily_net_returns"])}


def _fixed_calendar_inputs(ctx: StudyContext) -> dict:
    if "fixed_calendar" not in ctx.cache:
        carry, r1, r0 = {}, {}, {}
        for s in ctx.symbols:
            fc = ctx.fixed_cal_front[s]
            carry[s] = pipeline.symbol_carry_series(ctx.outright_panel, fc, ctx.seq[s], s, skip_tripwire=True)
            r1[s] = pipeline.symbol_daily_returns(ctx.settle_wide[s], fc, s, cost_multiplier=1.0)["returns"]
            r0[s] = pipeline.symbol_daily_returns(ctx.settle_wide[s], fc, s, cost_multiplier=0.0)["returns"]
        ctx.cache["fixed_calendar"] = {
            "carry_panel": pipeline.month_end_carry_panel(carry, entry_dates=ctx.entry_dates),
            "vol_panel": build_vol_panel(r0, ctx.month_end_index),
            "settle_by_month": build_settle_by_month(ctx.fixed_cal_front, ctx.settle_wide, ctx.month_end_index),
            "returns_1x": r1, "returns_0x": r0,
        }
    return ctx.cache["fixed_calendar"]


def registered_series(ctx: StudyContext, arms=ARMS) -> dict:
    """Every registered strategy-return series for the open arms, in ledger
    order: the 2 primaries, the 12 Sec 8 robustness series (Sec 10) and the
    2 execution-lag-1 series (AMENDMENT_2026-09-27) -- config.N_TRIALS in
    total when both arms are open. {id: {"id", "item", "arm",
    "description", "kind", "result", "sharpe"}}. Memoised on ctx."""
    key = ("registered", tuple(arms))
    if key in ctx.cache:
        return ctx.cache[key]
    out = {}
    base_weights = {arm: arm_weights(ctx, arm) for arm in arms}
    for arm in arms:
        out[arm] = _entry(arm, "primary", arm, f"Primary {arm} ({ARM_LABEL[arm]})", run_arm(ctx, base_weights[arm]))

    if "H1" in arms:
        def sector_fn(snap):
            return robustness.sector_neutral_xs_raw_signal(snap, config.SYMBOL_SECTOR)
        out["R1_sector_neutral_xs"] = _entry(
            "R1_sector_neutral_xs", "1", "H1", "Sector-neutral XS (rank within sector, equal sector risk)",
            run_arm(ctx, arm_weights(ctx, "H1", signal_fn=sector_fn)))
        out["R2_quintile_xs"] = _entry(
            "R2_quintile_xs", "2", "H1", "Quintile cutoffs instead of terciles",
            run_arm(ctx, arm_weights(ctx, "H1", signal_fn=robustness.xs_raw_signal_quintile)))
        out["R3_equal_weight_legs"] = _entry(
            "R3_equal_weight_legs", "3", "H1", "Equal-weight legs instead of inverse-vol",
            run_arm(ctx, robustness.equal_weight_pre_leverage_weights(ctx.carry_panel, ctx.entry_dates)))

    smoothed = robustness.smooth_carry_panel(ctx.carry_panel)
    deferred = pipeline.month_end_carry_panel(
        {s: robustness.symbol_deferred_carry_series(ctx.outright_panel, ctx.front[s], ctx.seq[s], s)
         for s in ctx.symbols},
        entry_dates=ctx.entry_dates)
    fc = _fixed_calendar_inputs(ctx)
    for arm in arms:
        out[f"R4_smoothed_carry_{arm}"] = _entry(
            f"R4_smoothed_carry_{arm}", "4", arm, "1-month-smoothed carry",
            run_arm(ctx, arm_weights(ctx, arm, carry_panel=smoothed)))
        out[f"R5_deferred_carry_{arm}"] = _entry(
            f"R5_deferred_carry_{arm}", "5", arm, "12-month-deferred carry (front vs ~1yr contract)",
            run_arm(ctx, arm_weights(ctx, arm, carry_panel=deferred)))
        out[f"R6_2x_cost_{arm}"] = _entry(
            f"R6_2x_cost_{arm}", "6", arm, "2x cost table",
            run_arm(ctx, base_weights[arm], cost_multiplier=2.0))
        out[f"R7_fixed_calendar_{arm}"] = _entry(
            f"R7_fixed_calendar_{arm}", "7", arm, "Fixed-calendar roll rule",
            run_arm(ctx, arm_weights(ctx, arm, carry_panel=fc["carry_panel"], vol=fc["vol_panel"]),
                    returns=fc["returns_1x"], gross_returns=fc["returns_0x"], settle=fc["settle_by_month"]))

    if "H1" in arms:
        carry, vol, entry = _drop(ctx, ["KE"])
        out["R10_ke_excluded"] = _entry(
            "R10_ke_excluded", "10", "H1", "KE excluded entirely from the universe",
            run_arm(ctx, arm_weights(ctx, "H1", carry_panel=carry, vol=vol, entry=entry)))

    for arm in arms:
        out[f"LAG1_{arm}"] = _entry(
            f"LAG1_{arm}", "lag-1", arm, "Execution one trading day after the signal (AMENDMENT_2026-09-27)",
            run_arm(ctx, base_weights[arm], execution_lag=config.EXECUTION_LAG_SENSITIVITY))

    ctx.cache[key] = out
    return out


def diagnostic_series(ctx: StudyContext, arms=ARMS) -> dict:
    """Non-gating constructed diagnostics, not counted in N_trials: the F7
    ex-PA/PL universe and the drop-one-sector jackknife."""
    key = ("diagnostic", tuple(arms))
    if key in ctx.cache:
        return ctx.cache[key]
    out = {}
    carry, vol, entry = _drop(ctx, ["PA", "PL"])
    for arm in arms:
        out[f"exPAPL_{arm}"] = _entry(f"exPAPL_{arm}", "F7", arm, "PA and PL excluded (F7 diagnostic)",
                                      run_arm(ctx, arm_weights(ctx, arm, carry_panel=carry, vol=vol, entry=entry)),
                                      kind="diagnostic")
    for sector, members in config.UNIVERSE.items():
        carry, vol, entry = _drop(ctx, members)
        for arm in arms:
            sid = f"jackknife_sector_{sector}_{arm}"
            out[sid] = _entry(sid, "9", arm, f"{sector} dropped (drop-one-sector jackknife)",
                              run_arm(ctx, arm_weights(ctx, arm, carry_panel=carry, vol=vol, entry=entry)),
                              kind="diagnostic")
    ctx.cache[key] = out
    return out


def sub_period_halves(net: pd.Series) -> dict:
    net = net.dropna()
    midpoint = net.index[len(net) // 2]
    first, second = net[net.index <= midpoint], net[net.index > midpoint]
    return {
        "first_half": (str(first.index.min().date()), str(first.index.max().date()), sharpe_point(first)),
        "second_half": (str(second.index.min().date()), str(second.index.max().date()), sharpe_point(second)),
    }
