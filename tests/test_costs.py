"""Tests for src/costs.py -- frozen cost table values and the 2x switch."""
import pytest

from src import config
from src.costs import cost_per_side_usd, cost_per_side_pct


def test_frozen_table_values_all_18_symbols():
    """Every symbol's cost = tick_value + $2.50 all-in fee (Sec 5, advisor
    ruling 2026-07-10)."""
    for symbol, spec in config.CONTRACT_SPECS.items():
        expected = spec["tick_value"] + config.ALL_IN_FEE_PER_SIDE_USD
        assert cost_per_side_usd(symbol) == pytest.approx(expected)


def test_specific_frozen_values_match_preregistration_table():
    # Spot-check a few rows directly against PREREGISTRATION.md Sec 5's table.
    assert cost_per_side_usd("CL") == pytest.approx(10.00 + 2.50)
    assert cost_per_side_usd("PA") == pytest.approx(50.00 + 2.50)
    assert cost_per_side_usd("HO") == pytest.approx(4.20 + 2.50)
    assert cost_per_side_usd("ZL") == pytest.approx(6.00 + 2.50)


def test_2x_cost_switch_doubles_every_row():
    """Sec 8 item 6 robustness variant: the whole table doubled, not just
    the fee or just the tick value."""
    for symbol in config.CONTRACT_SPECS:
        base = cost_per_side_usd(symbol, cost_multiplier=1.0)
        doubled = cost_per_side_usd(symbol, cost_multiplier=2.0)
        assert doubled == pytest.approx(2 * base)


def test_cost_per_side_pct_conversion():
    # CL: tick_value+fee = 12.50, multiplier=1000, settle=80.00 ->
    # notional = 80,000; pct = 12.50 / 80000
    pct = cost_per_side_pct("CL", settle_price=80.00)
    assert pct == pytest.approx(12.50 / (80.00 * 1000))


def test_cost_per_side_pct_raises_on_non_positive_price():
    with pytest.raises(ValueError):
        cost_per_side_pct("CL", settle_price=0.0)
    with pytest.raises(ValueError):
        cost_per_side_pct("CL", settle_price=-5.0)


def test_all_18_symbols_present_in_contract_specs():
    assert set(config.CONTRACT_SPECS) == set(config.ALL_SYMBOLS)
    assert len(config.CONTRACT_SPECS) == 18
