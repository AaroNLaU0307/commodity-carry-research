"""End-to-end smoke test of scripts/run_all.py on a synthetic corpus.

The two DBN readers are replaced by synthetic definition and settlement/OI
tables (six symbols, monthly contracts, a planted carry premium so both
premise gates open); every other line -- src/study.py, the four stage
scripts, the report writers and the results artifacts -- runs as it would
on the licensed corpus. Also checks data/MANIFEST.md parsing and the
aggregate-checksum rule `check-data` relies on."""
import hashlib
import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import config, pipeline

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
SYMBOLS = {"CL": 1.0, "NG": -1.0, "GC": 1.0, "ZC": -1.0, "ZS": 1.0, "LE": -1.0}  # sign of carry


def _synthetic_corpus(start="2010-06-07", end="2012-06-29", seed=11):
    rng = np.random.default_rng(seed)
    weekdays = pd.bdate_range(start, end)
    all_days = pd.DatetimeIndex([d for d in pd.date_range(start, end, freq="D") if d.dayofweek != 5])
    expiries = pd.date_range("2010-05-01", "2013-06-01", freq="MS") + np.timedelta64(19, "D")
    definition_rows, stat_rows = [], []
    iid = 1000
    for s_i, (symbol, carry_sign) in enumerate(SYMBOLS.items()):
        k = -0.08 * carry_sign  # S_c = P * exp(k * DTE / 365): k < 0 -> backwardation
        drift = 0.0006 * carry_sign  # planted premium: backwardated symbols rise
        spot = 50.0 * np.exp(np.cumsum(rng.normal(drift, 0.012, len(weekdays))))
        spot = pd.Series(spot, index=weekdays)
        for expiry in expiries:
            iid += 1
            listed = expiry - np.timedelta64(200, "D")
            for d in all_days[(all_days >= listed) & (all_days <= expiry)]:
                definition_rows.append({"date": d, "instrument_id": iid, "asset": symbol,
                                        "raw_symbol": f"{symbol}{expiry:%m%y}", "instrument_class": "F",
                                        "expiration": expiry})
            for d in weekdays[(weekdays >= listed) & (weekdays <= expiry)]:
                dte = (expiry - d).days
                oi = 1000.0 * max(0.0, 1.0 - abs(dte - 40) / 40.0)
                stat_rows.append({"date": d, "instrument_id": iid,
                                  "settlement": float(spot.at[d] * np.exp(k * dte / 365.0)),
                                  "oi": oi})
    definition = pd.DataFrame(definition_rows)
    stats = pd.DataFrame(stat_rows)
    stats.attrs["diagnostics"] = {"n_weekend_trade_date_dropped": 0, "n_undefined_ts_ref": 0, "n_deleted": 0}
    return definition, stats


@pytest.fixture
def isolated_run(tmp_path, monkeypatch):
    definition, stats = _synthetic_corpus()
    monkeypatch.setattr(pipeline, "build_definition_lookup", lambda data_dir=None: definition)
    monkeypatch.setattr(pipeline, "build_settlement_oi_panel", lambda data_dir=None: stats)
    monkeypatch.setattr(config, "BOOTSTRAP_N_REPLICATIONS", 200)
    monkeypatch.setattr(config, "WORKSPACE", tmp_path / "workspace")
    monkeypatch.syspath_prepend(str(SCRIPTS))
    modules = {}
    for name in ("run_all", "phase1b_premise_test", "phase1c_primary_backtest", "phase1c_robustness",
                 "generate_readme_figures"):
        modules[name] = importlib.import_module(name)
    for mod in modules.values():
        for attr, value in list(vars(mod).items()):
            if isinstance(value, Path) and value.is_relative_to(REPO) and attr.isupper() and attr not in (
                    "REPO", "SCRIPTS", "MANIFEST_PATH"):
                monkeypatch.setattr(mod, attr, tmp_path / value.relative_to(REPO))
    yield tmp_path, modules
    for name in modules:
        sys.modules.pop(name, None)


# pandas 2.3 with numpy 2.5 warns inside pd.Timedelta(days=...), which the
# pre-existing item-5 construction calls once per date.
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_run_all_end_to_end_on_a_synthetic_corpus(isolated_run):
    tmp, modules = isolated_run
    assert modules["run_all"].main(["all"]) == 0

    premise = json.loads((tmp / "results" / "premise_summary.json").read_text())
    assert premise["gate"] == {"H1": True, "H2": True}
    assert set(premise["sensitivity_execution_lag_1"]) == {"xs", "ts"}

    primary = json.loads((tmp / "results" / "primary_summary.json").read_text())
    assert primary["n_trials"] == config.N_TRIALS == 16
    assert len(primary["trial_sharpes"]) == config.N_TRIALS  # 2 primaries + 12 Sec 8 series + 2 lag-1
    assert {"LAG1_H1", "LAG1_H2", "R6_2x_cost_H1", "R10_ke_excluded"} <= set(primary["trial_sharpes"])
    for arm in ("H1", "H2"):
        a = primary["arms"][arm]
        assert a["dsr_inputs"]["sharpe_std_across_trials"] == pytest.approx(
            np.std(list(primary["trial_sharpes"].values()), ddof=1))
        assert a["dsr_inputs"]["n_trials"] == 16
        assert a["dsr_sharpe_threshold"] > 0
        assert a["cost_drag_annualized"]["total"] > 0

    monthly = pd.read_csv(tmp / "results" / "primary_monthly_returns.csv", index_col="month")
    assert list(monthly.columns) == ["H1_net", "H1_gross", "H2_net", "H2_gross"]
    assert (monthly["H1_gross"] - monthly["H1_net"]).sum() > 0  # costs are a drag

    variants = pd.read_csv(tmp / "results" / "robustness_variants.csv")
    assert int(variants["in_n_trials"].sum()) == config.N_TRIALS  # primaries + registered variants
    assert variants.loc[variants["kind"] == "primary", "id"].tolist() == ["H1", "H2"]
    h1 = variants.set_index("id").at["H1", "sharpe"]
    assert h1 == pytest.approx(primary["arms"]["H1"]["net_sharpe"])

    for name in ("PREMISE_REPORT.md", "PRIMARY_REPORT.md", "ROBUSTNESS_REPORT.md"):
        text = (tmp / "reports" / "rerun" / name).read_text()
        assert "HALTED" not in text and "2026-09-27" in text
    for name in ("gates_forest.png", "equity_curves.png", "per_year_returns.png"):
        assert (tmp / "reports" / "rerun" / "figures" / name).stat().st_size > 10_000
    # the published reports/*.md and reports/figures/*.png are never written
    assert not list((tmp / "reports").glob("*.md"))
    assert not (tmp / "reports" / "figures").exists()


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_primary_stage_skips_an_arm_closed_at_the_premise(isolated_run):
    tmp, modules = isolated_run
    assert modules["run_all"].main(["premise"]) == 0
    path = tmp / "results" / "premise_summary.json"
    premise = json.loads(path.read_text())
    premise["gate"]["H2"] = False
    path.write_text(json.dumps(premise))
    assert modules["run_all"].main(["primary"]) == 0
    primary = json.loads((tmp / "results" / "primary_summary.json").read_text())
    assert primary["arms"]["H2"] == {"status": "closed at premise (Sec 7)"}
    assert not any(k.endswith("H2") for k in primary["trial_sharpes"])
    assert "CLOSED AT PREMISE" in (tmp / "reports" / "rerun" / "PRIMARY_REPORT.md").read_text()


def test_no_stage_writes_the_published_reports(monkeypatch):
    """reports/*.md and reports/figures/*.png are the immutable published
    record; every stage of the corrected pipeline writes under reports/rerun/."""
    monkeypatch.syspath_prepend(str(SCRIPTS))
    published = REPO / "reports"
    rerun = published / "rerun"
    assert config.RERUN_REPORTS_DIR == rerun and config.RERUN_FIGURES_DIR == rerun / "figures"
    for name in ("phase1b_premise_test", "phase1c_primary_backtest", "phase1c_robustness"):
        assert importlib.import_module(name).REPORT_PATH.parent == rerun
    assert importlib.import_module("generate_readme_figures").FIGURES_DIR == rerun / "figures"
    for name in ("phase1b_premise_test", "phase1c_primary_backtest", "phase1c_robustness", "generate_readme_figures"):
        sys.modules.pop(name, None)


def test_manifest_parsing_and_aggregate_checksum(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    run_all = importlib.import_module("run_all")
    spec = run_all.parse_manifest((REPO / "data" / "MANIFEST.md").read_text(encoding="utf-8"))
    assert set(spec) == {"ohlcv-1d", "definition", "statistics"}
    assert spec["definition"]["n_files"] == 5031 and spec["statistics"]["n_files"] == 5026
    assert spec["ohlcv-1d"]["files"][0][0] == "ohlcv-1d.dbn.zst"
    assert spec["statistics"]["aggregate_sha256"].startswith("ee7dee4d")

    files = []
    for name, payload in (("b.dbn.zst", b"two"), ("a.dbn.zst", b"one")):
        (tmp_path / name).write_bytes(payload)
        files.append(tmp_path / name)
    lines = [f"a.dbn.zst:{hashlib.sha256(b'one').hexdigest()}", f"b.dbn.zst:{hashlib.sha256(b'two').hexdigest()}"]
    assert run_all.aggregate_sha256(files) == hashlib.sha256("\n".join(lines).encode()).hexdigest()
    sys.modules.pop("run_all", None)


def test_check_data_prints_both_quantity_stats_and_the_sunday_resend(tmp_path, monkeypatch, capsys):
    """The pre-run data check reads the raw statistics files: it must show
    CLEARED_VOLUME and OPEN_INTEREST side by side per trade date, and list a
    Friday settlement from both its Friday file and its Sunday-dated re-send."""
    from tests.test_statistics_calendar import (
        CLEARED_VOLUME,
        OPEN_INTEREST,
        SETTLE,
        _stat,
        _write_statistics_files,
    )

    _write_statistics_files(tmp_path, [
        _stat(5, SETTLE, "2020-04-17 18:30", "2020-04-17", price=18.27),
        _stat(5, SETTLE, "2020-04-19 22:00", "2020-04-17", price=18.27),
        _stat(5, CLEARED_VOLUME, "2020-04-19 22:00:01", "2020-04-17", quantity=222),
        _stat(5, OPEN_INTEREST, "2020-04-19 22:00:02", "2020-04-17", quantity=777),
    ])
    monkeypatch.syspath_prepend(str(SCRIPTS))
    run_all = importlib.import_module("run_all")
    monkeypatch.setattr(run_all, "_instrument_ids", lambda data_dir, raw, day: ([5], None))
    run_all.check_open_interest_field(tmp_path, "CLK0", "2020-04-13", "2020-04-20")
    run_all.spot_check_settlements(tmp_path, [("CLK0", "2020-04-17")])
    out = capsys.readouterr().out
    row = next(line for line in out.splitlines() if line.startswith("2020-04-17"))
    assert "222" in row and "777" in row and "18.27" in row
    assert "glbx-mdp3-20200419.statistics.dbn.zst" in out and "(Sunday)" in out
    assert "pipeline value (last received): 18.27" in out
    sys.modules.pop("run_all", None)


def test_run_all_pins_the_code_version_before_the_first_stage(monkeypatch):
    """Stages rewrite tracked files under reports/rerun/; the stamp must be
    taken once, before the first stage, so later stages are not stamped
    "-dirty" by the run's own output (addendum §10, 2026-09-28). Git is
    faked: clean at the first status call, a modified tracked file after."""
    import types
    from src import study
    status_calls = []

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "rev-parse"]:
            return types.SimpleNamespace(stdout="abc123\n")
        status_calls.append(cmd)
        return types.SimpleNamespace(stdout="" if len(status_calls) == 1 else " M reports/rerun/PREMISE_REPORT.md\n")

    monkeypatch.setattr(study.subprocess, "run", fake_run)
    monkeypatch.setattr(study, "_PINNED_CODE_VERSION", None)
    assert study.pin_code_version() == "abc123"
    assert study.code_version() == "abc123"          # pinned: no further git call
    assert len(status_calls) == 1
    monkeypatch.setattr(study, "_PINNED_CODE_VERSION", None)
    assert study.code_version() == "abc123-dirty"    # unpinned, the run's own output would read dirty
