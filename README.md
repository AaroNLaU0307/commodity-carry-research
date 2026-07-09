# Commodity Carry Research

[![tests](https://github.com/AaroNLaU0307/commodity-carry-research/actions/workflows/tests.yml/badge.svg)](https://github.com/AaroNLaU0307/commodity-carry-research/actions/workflows/tests.yml)

A pre-registered research project testing whether the commodity carry risk premium (basis / roll yield on futures term structure) is exploitable across a multi-sector CME futures universe, under a falsification-first protocol consistent with the sibling repos in this research program.

> **Status:** Phase 0 complete — data feasibility passed; pre-registration pending.

Phase 0 verified that Databento's `GLBX.MDP3` dataset delivers 18 CME futures across 4 sectors (energy, metals, grains, livestock), each with individual contract-month history sufficient for term-structure construction, settlement prices, open interest, and an expiry calendar, at a verified cost well within the available free credit. Full findings: [`docs/DATA_FEASIBILITY_REPORT.md`](docs/DATA_FEASIBILITY_REPORT.md), [`docs/DECISION_MEMO.md`](docs/DECISION_MEMO.md), [`docs/SAMPLE_AUDIT.md`](docs/SAMPLE_AUDIT.md).

No hypothesis has been tested. No signal has been designed. No return has been computed. This repository currently contains a data-feasibility record and a pre-registration skeleton, nothing else — see [`preregistration/PREREGISTRATION_TEMPLATE.md`](preregistration/PREREGISTRATION_TEMPLATE.md) for what comes next.

## Repository layout

- `docs/` — immutable Phase 0 snapshots (data feasibility report, decision memo, sample audit).
- `preregistration/` — pre-registration skeleton, to be filled in a dedicated session before any signal work begins.
- `data/` — provenance conventions for data once acquired. Raw data is never committed here; see `data/README.md`.
- `tests/` — currently a scaffold placeholder; real tests arrive with the pre-registration.
