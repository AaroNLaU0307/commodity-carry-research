"""
Tests for src/repro_gate.py -- the figure-generation reproduction gate.
Synthetic only, per Hard Rule 4 (tests before real data).
"""
import pytest

from src.repro_gate import ReproductionGate, ReproductionGateError


def test_matching_numbers_pass_silently():
    gate = ReproductionGate()
    gate.check("H1 net Sharpe", expected=-0.0031, actual=-0.0031, decimals=4)
    gate.check("H1 CI low", expected=-0.4417, actual=-0.441703, decimals=4)  # rounds to same 4dp
    gate.check("H2 net Sharpe", expected=-0.1255, actual=-0.12546, decimals=4)  # rounds to -0.1255
    gate.finalize()  # must not raise


def test_perturbed_number_raises_with_label_and_values():
    gate = ReproductionGate()
    gate.check("H1 net Sharpe", expected=-0.0031, actual=-0.0031, decimals=4)
    gate.check("H2 net Sharpe", expected=-0.1255, actual=-0.1300, decimals=4)  # genuine mismatch
    with pytest.raises(ReproductionGateError) as excinfo:
        gate.finalize()
    message = str(excinfo.value)
    assert "H2 net Sharpe" in message
    assert "-0.1255" in message
    assert "-0.1300" in message
    assert "H1 net Sharpe" not in message  # only the failing check is reported


def test_multiple_mismatches_all_reported_together():
    gate = ReproductionGate()
    gate.check("A", expected=1.0, actual=2.0, decimals=4)
    gate.check("B", expected=3.0, actual=3.0, decimals=4)
    gate.check("C", expected=5.0, actual=6.0, decimals=4)
    with pytest.raises(ReproductionGateError) as excinfo:
        gate.finalize()
    message = str(excinfo.value)
    assert "2 mismatch" in message
    assert "A:" in message and "C:" in message
    assert "B:" not in message
