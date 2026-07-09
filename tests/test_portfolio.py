"""Tests for src/portfolio.py -- n_leg rounding, symbol-entry no-backfill,
rebalance cost charging -- all synthetic, per Phase 1a Hard Rule 1."""
import pandas as pd
import pytest

from src.portfolio import n_leg, xs_raw_signal, ts_raw_signal, apply_rebalance_costs
from src.data_loader import apply_entry_rule, live_symbols_at


def test_n_leg_rounding_matches_preregistration_worked_examples():
    """PREREGISTRATION.md Sec 4: "N=17 gives n_leg=6; N=18 gives n_leg=6"."""
    assert n_leg(17) == 6
    assert n_leg(18) == 6


def test_n_leg_general_rounding():
    assert n_leg(9) == 3
    assert n_leg(10) == 3  # round(3.333) = 3
    assert n_leg(12) == 4  # round(4.0) = 4


def test_xs_raw_signal_top_and_bottom_tercile():
    carry = pd.Series({"A": 0.10, "B": 0.05, "C": 0.02, "D": -0.01, "E": -0.03, "F": -0.08})
    # N=6, n_leg = round(2.0) = 2
    sig = xs_raw_signal(carry)
    assert sig["A"] == 1.0 and sig["B"] == 1.0          # top 2 (highest carry)
    assert sig["E"] == -1.0 and sig["F"] == -1.0         # bottom 2 (lowest carry)
    assert sig["C"] == 0.0 and sig["D"] == 0.0           # middle, untouched


def test_ts_raw_signal_is_sign_of_carry():
    carry = pd.Series({"A": 0.05, "B": -0.02, "C": 0.0})
    sig = ts_raw_signal(carry)
    assert sig["A"] == 1.0
    assert sig["B"] == -1.0
    assert sig["C"] == 0.0


def test_symbol_entry_rule_no_backfill():
    """Sec 2: a symbol enters at its first live month-end; no backfill
    before that date."""
    months = pd.date_range("2013-01-31", periods=15, freq="ME")
    carry = pd.DataFrame(
        {"CL": [0.01] * 15, "KE": [0.02] * 15},  # KE has values for ALL months upstream...
        index=months,
    )
    entry_dates = {"CL": months[0], "KE": pd.Timestamp("2013-12-16")}
    result = apply_entry_rule(carry, entry_dates)

    # ...but apply_entry_rule must null out KE before its true entry date,
    # regardless of what upstream data happened to contain -- this is the
    # "no backfill" guarantee, defended even against accidental upstream leakage.
    pre_entry_ke = result.loc[result.index < entry_dates["KE"], "KE"]
    assert pre_entry_ke.isna().all()

    post_entry_ke = result.loc[result.index >= entry_dates["KE"], "KE"]
    assert (post_entry_ke == 0.02).all()

    # CL, entered from month 0, is untouched throughout.
    assert (result["CL"] == 0.01).all()


def test_live_symbols_at_reflects_17_then_18():
    entry_dates = {"CL": pd.Timestamp("2010-06-07"), "KE": pd.Timestamp("2013-12-16")}
    before = live_symbols_at(pd.Timestamp("2013-11-30"), entry_dates)
    after = live_symbols_at(pd.Timestamp("2013-12-31"), entry_dates)
    assert "KE" not in before
    assert "KE" in after
    assert "CL" in before and "CL" in after


def test_rebalance_cost_charged_only_on_weight_change():
    months = pd.date_range("2020-01-31", periods=3, freq="ME")
    weights = pd.DataFrame({"CL": [1.0, 1.0, -1.0]}, index=months)  # unchanged, then flips
    settles = pd.DataFrame({"CL": [80.0, 82.0, 83.0]}, index=months)
    cost = apply_rebalance_costs(weights, settles, symbol_of_column={"CL": "CL"})

    # Month 0: weights_prev is NaN->filled to 0, so delta = |1.0 - 0| = 1.0 -> cost charged
    assert cost.iloc[0] > 0
    # Month 1: no change (1.0 -> 1.0) -> zero cost
    assert cost.iloc[1] == pytest.approx(0.0)
    # Month 2: full flip (1.0 -> -1.0), delta = 2.0 -> double the "per unit" cost of month0
    from src.costs import cost_per_side_pct
    expected_month2 = 2.0 * cost_per_side_pct("CL", 83.0)
    assert cost.iloc[2] == pytest.approx(expected_month2)


def test_rebalance_cost_2x_multiplier():
    months = pd.date_range("2020-01-31", periods=2, freq="ME")
    weights = pd.DataFrame({"CL": [1.0, -1.0]}, index=months)
    settles = pd.DataFrame({"CL": [80.0, 81.0]}, index=months)
    cost1 = apply_rebalance_costs(weights, settles, {"CL": "CL"}, cost_multiplier=1.0)
    cost2 = apply_rebalance_costs(weights, settles, {"CL": "CL"}, cost_multiplier=2.0)
    assert cost2.iloc[1] == pytest.approx(2 * cost1.iloc[1])
