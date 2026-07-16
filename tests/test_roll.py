"""Tests for src/roll.py -- all on synthetic fixtures, per Phase 1a Hard Rule 1."""
import pandas as pd

from src.roll import compute_front_contract_series


def test_roll_uses_strictly_t_minus_1_oi_not_same_day():
    """Fixture where SAME-DAY OI would already show c2 > c1 on day T, but
    T-1's OI does not yet show the crossover. Correct (look-ahead-safe)
    behavior: front stays c1 through day T, rolls to c2 only on T+1 (using
    T's OI, now available as T+1's t-1)."""
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 80, 75],   # day0=T-1: 100, day1=T: 80, day2=T+1: 75
            "c2": [90, 95, 98],    # day0=T-1: 90,  day1=T: 95, day2=T+1: 98
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2"])

    # Day0 (T-1): no t-1 data at all (nothing before it) -> stays at initial front c1.
    assert front.iloc[0] == "c1"
    # Day1 (T): t-1 OI is day0's (c1=100 > c2=90) -> still c1. A same-day-OI
    # implementation would incorrectly roll here, since day1's OWN OI already
    # has c2=95 > c1=80.
    assert front.iloc[1] == "c1"
    # Day2 (T+1): t-1 OI is day1's (c1=80 < c2=95) -> NOW rolls to c2.
    assert front.iloc[2] == "c2"


def test_roll_is_monotonic_no_roll_back_on_oscillating_oi():
    """Once front has moved from c1 to c2, OI later favoring c1 again must
    NOT roll it back."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 80, 120, 130, 140],  # c1 OI recovers above c2 at day3-4
            "c2": [90, 95, 90, 85, 80],
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2"])

    assert front.iloc[0] == "c1"
    assert front.iloc[1] == "c1"   # t-1 (day0) still favors c1
    assert front.iloc[2] == "c2"   # t-1 (day1): c2=95 > c1=80 -> rolled
    # From here on, even though c1's OI recovers above c2's, front must stay c2.
    assert front.iloc[3] == "c2"
    assert front.iloc[4] == "c2"


def test_roll_truncation_invariance_future_oi_rows_do_not_change_past_front():
    """Appending future rows must leave every already-computed front-contract
    decision unchanged -- the state machine only ever looks at t-1, never
    forward, so truncating (or extending) the series should not alter the
    front assignment for any date already covered."""
    dates = pd.date_range("2020-01-01", periods=6, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 80, 60, 40, 20, 10],
            "c2": [90, 95, 96, 97, 98, 99],
        },
        index=dates,
    )
    front_full = compute_front_contract_series(oi, ["c1", "c2"])

    front_truncated = compute_front_contract_series(oi.iloc[:3], ["c1", "c2"])
    pd.testing.assert_series_equal(front_truncated, front_full.iloc[:3])


def test_roll_with_three_contracts_progresses_sequentially_when_crossovers_are_sequential():
    """Under A1 (multi-candidate OI-max, DEVIATIONS.md 2026-07-15), the
    front is the argmax over ALL candidates >= the incumbent's expiration,
    not just the single next-listed one -- so a direct c1 -> c3 jump
    (skipping c2 entirely) is possible in principle (see the skip-ahead
    test below). This fixture's OI happens to cross over sequentially
    (c2 overtakes c1 before c3 ever overtakes c2), so A1 still lands on c2
    first, then c3 -- proving A1 does not force a jump when a sequential
    path is what the OI data actually shows."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 50, 40, 30],
            "c2": [90, 95, 96, 20],
            "c3": [10, 15, 97, 98],
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2", "c3"])
    assert front.iloc[0] == "c1"
    assert front.iloc[1] == "c1"   # t-1 (day0): c1=100 is the max among {c1,c2,c3} -> stays c1
    assert front.iloc[2] == "c2"   # t-1 (day1): c2=95 is the max among {c1,c2,c3} -> rolls to c2
    assert front.iloc[3] == "c3"   # t-1 (day2): c3=97 is the max among {c2,c3} -> rolls to c3


def test_A1_dead_serial_deadlock_regression():
    """The F11 regression test: under the pre-A1 single-candidate rule, a
    front stuck comparing only against an immediately-next contract that
    NEVER gains OI (a "dead serial" month) would freeze permanently, even
    though a later, real, liquid contract is fully observable throughout
    (docs/DATA_QA_REPORT.md finding F11 -- 11 permanent stuck fronts across
    13 symbols under the pre-A1 rule). A1 must instead roll directly from
    c1 to c3, skipping the permanently-dead c2, once c3's t-1 OI exceeds
    c1's -- exactly the "multi-candidate OI-max" behavior A1 exists for."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [1000, 900, 800, 700, 600],
            "c2": [0, 0, 0, 0, 0],          # dead serial -- never gains ANY open interest, ever
            "c3": [50, 400, 850, 900, 950],  # the real, later, liquid contract
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2", "c3"])
    assert (front != "c2").all()  # c2 is never front -- dead-serial candidates are correctly skippable
    assert front.iloc[0] == "c1"
    # t-1 (day1): c1=900 > c2=0, c3=400 -> still c1
    assert front.iloc[2] == "c1"
    # t-1 (day2): c3=850 > c1=800, c2=0 -> rolls DIRECTLY c1 -> c3, skipping c2 entirely
    assert front.iloc[3] == "c3"
    assert front.iloc[4] == "c3"


def test_A1_multi_candidate_skip_ahead_in_a_single_date():
    """A direct, unambiguous multi-step jump in one date: c3's t-1 OI
    already exceeds c1's while c2's does not, so front must skip straight
    from c1 to c3 in a single date evaluation -- never briefly landing on
    c2 (contrast with the sequential-crossover fixture above, where the
    data itself does not support a skip)."""
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 50, 40],
            "c2": [90, 60, 55],    # c2 never leads c1, ever
            "c3": [10, 200, 210],  # c3 overtakes c1 directly
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2", "c3"])
    assert front.iloc[0] == "c1"
    assert front.iloc[1] == "c1"  # t-1 (day0): c1=100 is still the max
    assert front.iloc[2] == "c3"  # t-1 (day1): c3=200 is the max -> direct c1 -> c3, c2 never visited


def test_A1_oi_max_tie_break_retains_incumbent():
    """Ties break toward the earlier expiration -- i.e. the incumbent wins
    a tie against a later-expiration candidate with EQUAL t-1 OI, rather
    than switching for no economic reason."""
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 500, 500],  # ties c2 exactly on day1's t-1 (day1 itself)
            "c2": [90, 200, 500],
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2"])
    assert front.iloc[0] == "c1"
    assert front.iloc[1] == "c1"  # t-1 (day0): c1=100 > c2=90
    # t-1 (day1): c1=500 == c2=500 -- exact tie -> incumbent (c1, earlier expiration) retained
    assert front.iloc[2] == "c1"


def test_A1_monotonicity_holds_even_when_an_earlier_expiration_spikes_after_rolling_past_it():
    """Once front has advanced past c1 (to c2), c1 is no longer even in the
    eligible candidate set -- so no OI value c1 could possibly take,
    including one far exceeding every current candidate, can pull front
    back to it. This is the ping-pong-attempt case: c1's OI spikes to the
    highest value in the whole table AFTER front has already left it."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 80, 50, 99999],  # day3: c1 spikes far above both c2 and c3 -- must NOT pull front back
            "c2": [90, 95, 40, 200],
            "c3": [10, 15, 96, 300],
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2", "c3"])
    assert front.iloc[0] == "c1"
    assert front.iloc[1] == "c1"  # t-1 (day0): c1=100 max
    assert front.iloc[2] == "c2"  # t-1 (day1): c2=95 max -> rolls to c2
    assert front.iloc[3] == "c3"  # t-1 (day2): c3=96 max among {c2,c3} (c1 no longer eligible) -> rolls to c3
    # front is now c3; day3's own t-1 OI (day2's row, already consumed above)
    # never even considers c1's day3 spike, since c1 was never in the day3
    # eligible set (current_idx already past it) -- proven by front staying
    # c3 and never reverting, regardless of how large c1's OI becomes later.


def test_A1_hold_on_missing_when_every_eligible_candidate_is_unobserved():
    """F7's hold-on-missing ruling, unchanged by A1: if EVERY eligible
    candidate's t-1 OI is NaN (not just the incumbent's), front holds --
    even after having already advanced past position 0, proving this isn't
    just the day-0 initialization case."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    oi = pd.DataFrame(
        {
            "c1": [100, 500, 40, 30],
            "c2": [90, 600, None, None],  # goes fully dark (NaN) after rolling onto it
        },
        index=dates,
    )
    front = compute_front_contract_series(oi, ["c1", "c2"])
    assert front.iloc[0] == "c1"
    assert front.iloc[1] == "c1"  # t-1 (day0): c1=100 > c2=90
    assert front.iloc[2] == "c2"  # t-1 (day1): c2=600 > c1=500 -> rolls to c2
    # day3: t-1 (day2) is NaN for the only eligible candidate (c2, since
    # current_idx is now past c1) -> hold at c2, not an error, not a revert.
    assert front.iloc[3] == "c2"
