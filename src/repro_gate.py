"""
Reproduction-gate helper for scripts/generate_readme_figures.py. Not part of
the frozen study design (no PREREGISTRATION.md section) -- a docs-addendum
utility that asserts regenerated numbers match the already-committed,
immutable reports before any figure is allowed to be written.

Collects every discrepancy before raising, rather than stopping at the
first, so a full-pipeline reproduction run surfaces all mismatches at once.
"""


class ReproductionGateError(Exception):
    """Raised when regenerated numbers disagree with a committed report."""


class ReproductionGate:
    def __init__(self):
        self._failures = []

    def check(self, label: str, expected: float, actual: float, decimals: int = 4) -> None:
        """Compare expected (from a committed report) against actual (freshly
        regenerated), both rounded to `decimals` places -- the precision the
        reports themselves are printed to. Records a failure; does not raise."""
        if round(float(expected), decimals) != round(float(actual), decimals):
            self._failures.append(
                f"{label}: expected {expected:.{decimals}f}, got {actual:.{decimals}f} "
                f"(diff {actual - expected:+.{decimals}f})"
            )

    def finalize(self) -> None:
        """Raise ReproductionGateError listing every recorded discrepancy, if any."""
        if self._failures:
            detail = "\n".join(f"  - {f}" for f in self._failures)
            raise ReproductionGateError(
                f"Reproduction gate FAILED ({len(self._failures)} mismatch(es) "
                f"against committed reports -- no figures written):\n{detail}"
            )
