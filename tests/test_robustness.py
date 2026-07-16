"""
Tests for src/robustness.py -- the Phase 1c Sec 8 robustness constructions.
All synthetic, per Hard Rule 4 (tests before real data).
"""
import pandas as pd
import pytest

from src.robustness import (
    sector_neutral_xs_raw_signal, n_leg_quintile, xs_raw_signal_quintile,
    equal_weight_pre_leverage_weights, smooth_carry_panel,
    symbol_deferred_carry_series, fixed_calendar_front_series,
)
from src.carry import compute_carry


def test_sector_neutral_ranks_within_sector_and_normalizes_by_active_count():
    """2 sectors, sizes 3 and 6. Each sector gets its OWN tercile split
    (n_leg(3)=1, n_leg(6)=2), then each active symbol's signal is divided
    by its OWN sector's active-position count (2 for the 3-member sector,
    4 for the 6-member sector) -- NOT the global active count."""
    carry_snapshot = pd.Series({
        "E1": 10.0, "E2": 0.0, "E3": -10.0,  # energy-like, 3 members
        "M1": 6.0, "M2": 5.0, "M3": 1.0, "M4": -1.0, "M5": -5.0, "M6": -6.0,  # metals-like, 6 members
    })
    symbol_sector = {"E1": "energy", "E2": "energy", "E3": "energy",
                      "M1": "metals", "M2": "metals", "M3": "metals", "M4": "metals", "M5": "metals", "M6": "metals"}
    signal = sector_neutral_xs_raw_signal(carry_snapshot, symbol_sector)

    # energy: n_leg(3)=1 -> E1 top, E3 bottom, E2 neutral; 2 active -> each |signal|=1/2
    assert signal["E1"] == pytest.approx(0.5)
    assert signal["E3"] == pytest.approx(-0.5)
    assert signal["E2"] == 0.0
    # metals: n_leg(6)=2 -> M1,M2 top; M5,M6 bottom; 4 active -> each |signal|=1/4
    assert signal["M1"] == pytest.approx(0.25)
    assert signal["M2"] == pytest.approx(0.25)
    assert signal["M5"] == pytest.approx(-0.25)
    assert signal["M6"] == pytest.approx(-0.25)
    assert signal["M3"] == 0.0 and signal["M4"] == 0.0
    # each sector's total gross signal magnitude is the same (1.0 long + 1.0 short = 2.0), regardless of member count
    energy_gross = signal[["E1", "E2", "E3"]].abs().sum()
    metals_gross = signal[["M1", "M2", "M3", "M4", "M5", "M6"]].abs().sum()
    assert energy_gross == pytest.approx(metals_gross) == pytest.approx(1.0)


def test_quintile_leg_size_and_signal():
    assert n_leg_quintile(10) == 2  # 10/5 = 2 exactly
    assert n_leg_quintile(17) == 3  # 17/5 = 3.4 -> 3
    assert n_leg_quintile(20) == 4
    carry_snapshot = pd.Series({f"S{i}": float(i) for i in range(10)})  # 0..9, distinct
    signal = xs_raw_signal_quintile(carry_snapshot)
    assert (signal == 1.0).sum() == 2  # top 2 (values 8,9)
    assert (signal == -1.0).sum() == 2  # bottom 2 (values 0,1)
    assert signal["S9"] == 1.0 and signal["S8"] == 1.0
    assert signal["S0"] == -1.0 and signal["S1"] == -1.0


def test_equal_weight_legs_sum_to_one_gross_per_leg_and_are_equal_within_leg():
    months = pd.DatetimeIndex(["2020-01-31"])
    cols = ["A", "B", "C", "D", "E", "F"]
    carry_panel = pd.DataFrame({"A": [10.0], "B": [9.0], "C": [1.0], "D": [-1.0], "E": [-9.0], "F": [-10.0]}, index=months)
    entry_dates = {s: pd.Timestamp("2019-01-01") for s in cols}

    weights = equal_weight_pre_leverage_weights(carry_panel, entry_dates)
    # n_leg(6)=2 -> A,B long; E,F short
    assert weights.at[months[0], "A"] == pytest.approx(0.5)
    assert weights.at[months[0], "B"] == pytest.approx(0.5)  # EQUAL, not vol-scaled -- same weight as A regardless of any vol input
    assert weights.at[months[0], "E"] == pytest.approx(-0.5)
    assert weights.at[months[0], "F"] == pytest.approx(-0.5)
    assert weights.at[months[0], "C"] == 0.0 and weights.at[months[0], "D"] == 0.0
    assert weights.loc[months[0], ["A", "B"]].sum() == pytest.approx(1.0)
    assert weights.loc[months[0], ["E", "F"]].sum() == pytest.approx(-1.0)


def test_smooth_carry_panel_is_two_point_trailing_average_no_backfill_across_entry():
    months = pd.DatetimeIndex(["2020-01-31", "2020-02-29", "2020-03-31"])
    carry_panel = pd.DataFrame({"A": [10.0, 20.0, 30.0], "B": [float("nan"), 5.0, 7.0]}, index=months)
    smoothed = smooth_carry_panel(carry_panel, window=2)
    assert pd.isna(smoothed.at[months[0], "A"])  # no prior month yet
    assert smoothed.at[months[1], "A"] == pytest.approx((10.0 + 20.0) / 2)
    assert smoothed.at[months[2], "A"] == pytest.approx((20.0 + 30.0) / 2)
    # B enters month 2 (Feb) -- Feb's smoothed value must NOT backfill/average across the entry boundary
    assert pd.isna(smoothed.at[months[1], "B"])
    assert smoothed.at[months[2], "B"] == pytest.approx((5.0 + 7.0) / 2)


def test_deferred_carry_selects_nearest_to_defer_days_with_earlier_tie_break():
    """front expires 2020-02-01; target = front + 365d = 2021-01-31 (2020
    is a leap year, so +365d lands 1 day short of the calendar
    anniversary). C1 (2021-01-30) and C2 (2021-02-01) are DELIBERATELY
    equidistant from target (1 day on each side) -- the earlier one, C1,
    must win. C3/C4 are clearly-further decoys proving the nearest-search
    doesn't just grab an arbitrary later contract."""
    dates = pd.date_range("2020-01-01", periods=2, freq="D")
    rows = []
    stats_rows = []
    specs = [
        (100, "F1", "2020-02-01", 50.0),
        (101, "C1", "2021-01-30", 55.0),   # 1 day BEFORE target -- ties with C2, must win (earlier)
        (102, "C2", "2021-02-01", 60.0),   # 1 day AFTER target -- ties with C1, must lose
        (103, "C3", "2021-06-01", 65.0),   # clearly further -- decoy
        (104, "C4", "2022-07-20", 70.0),   # clearly further -- decoy
    ]
    for d in dates:
        for iid, sym, exp, settle in specs:
            rows.append({"date": d, "instrument_id": iid, "asset": "CL", "raw_symbol": sym,
                         "instrument_class": "F", "expiration": pd.Timestamp(exp)})
            stats_rows.append({"date": d, "instrument_id": iid, "settlement": settle, "oi": 1000})
    defn = pd.DataFrame(rows)
    stats = pd.DataFrame(stats_rows)
    from src.pipeline import build_outright_panel, symbol_listed_sequence
    outright = build_outright_panel(defn, stats)
    seq = symbol_listed_sequence(outright, "CL")
    front = pd.Series(["100__2020-02-01"] * len(dates), index=dates)

    result = symbol_deferred_carry_series(outright, front, seq, "CL", defer_days=365)
    expected = compute_carry(50.0, 55.0, pd.Timestamp("2020-02-01").date(), pd.Timestamp("2021-01-30").date())
    assert result.iloc[0] == pytest.approx(expected)


def test_fixed_calendar_roll_timing_and_existence_filter():
    """Front expires 2020-03-14 -> scheduled roll date is the last business
    day of Feb 2020 (2020-02-28, a Friday). Before that date, front must
    stay on the incumbent regardless of OI. On/after that date, front must
    roll to the first LATER candidate with positive t-1 OI, skipping a
    dead-serial (zero-OI) intermediate candidate entirely -- the same
    existence filter as A2, not the OI-crossover rule."""
    dates = pd.date_range("2020-02-25", periods=6, freq="D")  # 2/25 (Tue) .. 3/1 (Sun)
    listed_sequence = ["front", "dead_serial", "real_next"]
    expiry_by_key = {
        "front": pd.Timestamp("2020-03-14"),
        "dead_serial": pd.Timestamp("2020-04-14"),
        "real_next": pd.Timestamp("2020-05-14"),
    }
    oi_panel = pd.DataFrame({
        "front": [1000, 900, 800, 700, 600, 500],
        "dead_serial": [0, 0, 0, 0, 0, 0],           # never gains OI, ever
        "real_next": [50, 400, 500, 600, 700, 800],  # genuinely OI-bearing
    }, index=dates)

    front_series = fixed_calendar_front_series(oi_panel, listed_sequence, expiry_by_key)

    # 2020-02-25, 2020-02-26, 2020-02-27: before the scheduled roll date -> still "front"
    assert front_series.at[pd.Timestamp("2020-02-25")] == "front"
    assert front_series.at[pd.Timestamp("2020-02-26")] == "front"
    assert front_series.at[pd.Timestamp("2020-02-27")] == "front"
    # 2020-02-28 (the scheduled roll date) onward: rolls DIRECTLY to real_next,
    # skipping dead_serial entirely (existence filter, t-1 OI at 2020-02-28 is 2020-02-27's: front=800, dead_serial=0, real_next=500 -> qualifies)
    assert front_series.at[pd.Timestamp("2020-02-28")] == "real_next"
    assert front_series.at[pd.Timestamp("2020-03-01")] == "real_next"
    assert (front_series != "dead_serial").all()  # dead-serial candidate never becomes front


def test_fixed_calendar_roll_holds_if_no_existent_candidate_yet_on_scheduled_date():
    """If the scheduled roll date arrives but NO later candidate has
    positive t-1 OI yet, the rule holds at the incumbent (same
    hold-on-nonexistence principle as A2/F7) rather than rolling to a
    dead serial or raising."""
    dates = pd.date_range("2020-02-27", periods=3, freq="D")
    listed_sequence = ["front", "not_yet_liquid"]
    expiry_by_key = {"front": pd.Timestamp("2020-03-14"), "not_yet_liquid": pd.Timestamp("2020-04-14")}
    oi_panel = pd.DataFrame({"front": [800, 700, 600], "not_yet_liquid": [0, 0, 0]}, index=dates)
    front_series = fixed_calendar_front_series(oi_panel, listed_sequence, expiry_by_key)
    assert (front_series == "front").all()
