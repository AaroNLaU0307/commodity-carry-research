"""
Frozen parameters for the commodity carry study.

Every constant here is fixed by preregistration/PREREGISTRATION.md (as
amended by preregistration/AMENDMENT_2026-09-27.md) and must not change
without a dated record under Sec 11, written before any deviating
computation runs -- not silently edited here.
"""
import os
from pathlib import Path

DATASET = "GLBX.MDP3"
SCHEMAS = ("ohlcv-1d", "statistics", "definition")

# Paths. Everything defaults to a location inside this checkout; the raw
# corpus is licensed and never committed (data/raw/ and data/workspace/ are
# git-ignored), so point DATA_DIR at wherever it actually lives.
REPO_ROOT = Path(__file__).resolve().parent.parent
# Raw Databento delivery: DATA_DIR/ohlcv-1d.dbn.zst, DATA_DIR/definition/,
# DATA_DIR/statistics/ (data/MANIFEST.md).
DATA_DIR = Path(os.environ.get("DATA_DIR", REPO_ROOT / "data" / "raw"))
# Uncommitted intermediate files (pull logs, per-file checksum lists, the
# F11 census CSV read by the optional Figure 4).
WORKSPACE = Path(os.environ.get("WORKSPACE", REPO_ROOT / "data" / "workspace"))
# reports/*.md and reports/figures/*.png are the published 2026-07-16 record:
# immutable, corrected only by dated addenda. The corrected pipeline writes
# its reports and figures to reports/rerun/ instead.
REPORTS_DIR = REPO_ROOT / "reports"
RERUN_REPORTS_DIR = REPORTS_DIR / "rerun"
RERUN_FIGURES_DIR = RERUN_REPORTS_DIR / "figures"
# Small, committed, machine-readable results written by the runners.
RESULTS_DIR = REPO_ROOT / "results"

# Sec 2 -- universe, 18 symbols, 4 sectors, frozen from Phase 0
UNIVERSE = {
    "energy": ["CL", "HO", "RB", "NG"],
    "metals": ["GC", "SI", "HG", "PL", "PA"],
    "grains": ["ZC", "ZS", "ZW", "ZM", "ZL", "KE"],
    "livestock": ["LE", "HE", "GF"],
}
ALL_SYMBOLS = [s for syms in UNIVERSE.values() for s in syms]
SYMBOL_SECTOR = {s: sector for sector, syms in UNIVERSE.items() for s in syms}
N_SYMBOLS = len(ALL_SYMBOLS)  # 18

# Sec 2 -- sample window. 2010-06-07 is the later of the two dataset-floor
# dates (14 symbols at 2010-06-06, 3 at 2010-06-07), i.e. the first date all
# 17 non-KE symbols are simultaneously live -- see per_symbol_probe_results.json.
SAMPLE_START = "2010-06-07"
SAMPLE_END = "2026-06-30"        # inclusive. Databento's own end= is exclusive;
                                  # callers pulling from the API must add one day.
KE_ENTRY_DATE = "2013-12-16"     # Sec 2 symbol entry rule -- load-bearing, verify
                                  # against delivered data in Phase 1a QA.

# Sec 4 -- TSMOM-inherited construction parameters. See PREREGISTRATION.md Sec 4
# for the exact multi-asset-tsmom-research file+line citations; restated here as
# plain constants for the engine to consume.
VOL_WINDOW_DAYS = 60
TRADING_DAYS_PER_YEAR = 252
ASSET_VOL_TARGET_ANNUAL = 0.10
PORTFOLIO_VOL_TARGET_ANNUAL = 0.10
MAX_ASSET_WEIGHT = 2.0
MAX_GROSS_LEVERAGE = 3.0
# Deliberately absent: no no-trade band. TSMOM defines one but does not apply
# it in its adopted pipeline (tested, rejected -- see PREREGISTRATION Sec 4).

# Sec 6 -- statistical gates
BOOTSTRAP_METHOD = "stationary"
BOOTSTRAP_EXPECTED_BLOCK_LENGTH = 21    # trading days
BOOTSTRAP_N_REPLICATIONS = 10_000
BOOTSTRAP_SEEDS = (7, 13, 31)           # 3 recorded seeds, fixed before any computation
BOOTSTRAP_CI_LEVEL = 0.95
BH_FDR_Q = 0.10
SHARPE_GATE_MIN = 0.30
DSR_GATE_MIN = 0.95

# Sec 10 -- computation ledger: 2 primary + 12 robustness series (items 8-9
# excluded as diagnostics) = 14, plus the two execution-lag-1 series
# registered by preregistration/AMENDMENT_2026-09-27.md = 16. This is the
# N_trials input to the DSR gate everywhere in this codebase -- never a
# locally-recomputed count. (The DSRs published before 2026-09-27 used 14.)
N_TRIALS = 16

# Execution timing (Sec 3 as amended 2026-09-27): 0 = the registered
# primary convention (entry at the signal's own month-end settlement);
# the lag-1 variant is a registered sensitivity.
EXECUTION_LAG_PRIMARY = 0
EXECUTION_LAG_SENSITIVITY = 1

# Sec 5 -- cost model. Advisor ruling, 2026-07-10 (WORKSPACE/PREREG_OPEN_ITEMS.md
# item 2): a uniform, deliberately conservative all-in per-side fee allowance
# (exchange + clearing + NFA + brokerage), NOT a per-product figure.
ALL_IN_FEE_PER_SIDE_USD = 2.50

# Contract specs: multiplier and tick value (USD value of ONE minimum price
# fluctuation for the full contract), PREREGISTRATION.md Sec 5 table.
CONTRACT_SPECS = {
    "CL": {"multiplier": 1000,    "tick_size": 0.01,    "tick_value": 10.00},
    "HO": {"multiplier": 42000,   "tick_size": 0.0001,  "tick_value": 4.20},
    "RB": {"multiplier": 42000,   "tick_size": 0.0001,  "tick_value": 4.20},
    "NG": {"multiplier": 10000,   "tick_size": 0.001,   "tick_value": 10.00},
    "GC": {"multiplier": 100,     "tick_size": 0.10,    "tick_value": 10.00},
    "SI": {"multiplier": 5000,    "tick_size": 0.005,   "tick_value": 25.00},
    "HG": {"multiplier": 25000,   "tick_size": 0.0005,  "tick_value": 12.50},
    "PL": {"multiplier": 50,      "tick_size": 0.10,    "tick_value": 5.00},
    "PA": {"multiplier": 100,     "tick_size": 0.50,    "tick_value": 50.00},
    "ZC": {"multiplier": 5000,    "tick_size": 0.0025,  "tick_value": 12.50},
    "ZS": {"multiplier": 5000,    "tick_size": 0.0025,  "tick_value": 12.50},
    "ZW": {"multiplier": 5000,    "tick_size": 0.0025,  "tick_value": 12.50},
    "ZM": {"multiplier": 100,     "tick_size": 0.10,    "tick_value": 10.00},
    "ZL": {"multiplier": 60000,   "tick_size": 0.0001,  "tick_value": 6.00},
    "KE": {"multiplier": 5000,    "tick_size": 0.0025,  "tick_value": 12.50},
    "LE": {"multiplier": 40000,   "tick_size": 0.00025, "tick_value": 10.00},
    "HE": {"multiplier": 40000,   "tick_size": 0.00025, "tick_value": 10.00},
    "GF": {"multiplier": 50000,   "tick_size": 0.00025, "tick_value": 12.50},
}

assert set(CONTRACT_SPECS) == set(ALL_SYMBOLS), "CONTRACT_SPECS must cover exactly the 18 pre-registered symbols"
