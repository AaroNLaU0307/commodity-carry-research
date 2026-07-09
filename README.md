# Commodity Carry Research

[![tests](https://github.com/AaroNLaU0307/commodity-carry-research/actions/workflows/tests.yml/badge.svg)](https://github.com/AaroNLaU0307/commodity-carry-research/actions/workflows/tests.yml)

A pre-registered research project testing whether the commodity carry risk premium (basis / roll yield on futures term structure) is exploitable across a multi-sector CME futures universe, under a falsification-first protocol consistent with the sibling repos in this research program.

> **Status:** pre-registration frozen — see [`preregistration/PREREGISTRATION.md`](preregistration/PREREGISTRATION.md).

Phase 0 verified that Databento's `GLBX.MDP3` dataset delivers 18 CME futures across 4 sectors (energy, metals, grains, livestock), each with individual contract-month history sufficient for term-structure construction, settlement prices, open interest, and an expiry calendar, at a verified cost well within the available free credit. Full findings: [`docs/DATA_FEASIBILITY_REPORT.md`](docs/DATA_FEASIBILITY_REPORT.md), [`docs/DECISION_MEMO.md`](docs/DECISION_MEMO.md), [`docs/SAMPLE_AUDIT.md`](docs/SAMPLE_AUDIT.md).

The pre-registration is now frozen: hypotheses, data lock, locked definitions, portfolio construction, cost model, statistical gates, premise test, robustness suite, and NOT-testing list are all fixed before any computation touches the data — see [`preregistration/PREREGISTRATION.md`](preregistration/PREREGISTRATION.md). **Frozen design is not a result.** No hypothesis has been tested. No signal has been computed. No return has been computed. The corpus itself has not been downloaded — that requires a separate written approval, after this repo is pushed, per the pre-registration's own ordering (§12).

## Repository layout

- `docs/` — immutable Phase 0 snapshots (data feasibility report, decision memo, sample audit).
- `preregistration/` — the frozen pre-registration. Deviations from it are logged in [`DEVIATIONS.md`](DEVIATIONS.md), never made silently.
- `data/` — provenance conventions for data once acquired. Raw data is never committed here; see `data/README.md`.
- `tests/` — currently a scaffold placeholder; real tests arrive with Phase 1 implementation.
