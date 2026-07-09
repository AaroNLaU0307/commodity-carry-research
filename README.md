# Commodity Carry Research

[![tests](https://github.com/AaroNLaU0307/commodity-carry-research/actions/workflows/tests.yml/badge.svg)](https://github.com/AaroNLaU0307/commodity-carry-research/actions/workflows/tests.yml)

A pre-registered research project testing whether the commodity carry risk premium (basis / roll yield on futures term structure) is exploitable across a multi-sector CME futures universe, under a falsification-first protocol consistent with the sibling repos in this research program.

> **Status:** pre-registration frozen — see [`preregistration/PREREGISTRATION.md`](preregistration/PREREGISTRATION.md).

Phase 0 verified that Databento's `GLBX.MDP3` dataset delivers 18 CME futures across 4 sectors (energy, metals, grains, livestock), each with individual contract-month history sufficient for term-structure construction, settlement prices, open interest, and an expiry calendar, at a verified cost well within the available free credit. Full findings: [`docs/DATA_FEASIBILITY_REPORT.md`](docs/DATA_FEASIBILITY_REPORT.md), [`docs/DECISION_MEMO.md`](docs/DECISION_MEMO.md), [`docs/SAMPLE_AUDIT.md`](docs/SAMPLE_AUDIT.md).

The pre-registration is now frozen: hypotheses, data lock, locked definitions, portfolio construction, cost model, statistical gates, premise test, robustness suite, and NOT-testing list are all fixed before any computation touches the data — see [`preregistration/PREREGISTRATION.md`](preregistration/PREREGISTRATION.md). **Frozen design is not a result.** No hypothesis has been tested. No return-signal relationship has been computed on real data. Real data may be loaded, counted, checksummed, and audited for integrity (Phase 1a); it may not flow through the signal path until Aaron and his advisor review the data QA report.

## Repository layout

- `docs/` — immutable Phase 0/1 snapshots (data feasibility report, decision memo, sample audit, data QA report).
- `preregistration/` — the frozen pre-registration. Deviations from it are logged in [`DEVIATIONS.md`](DEVIATIONS.md), never made silently.
- `data/` — provenance conventions and the manifest (checksums, request parameters) for data once acquired. Raw data is never committed here — see `data/README.md`.
- `src/` — the computation engine (data loading, roll rule, carry, returns, costs, vol targeting, portfolio construction, statistics), one module per `PREREGISTRATION.md` section, cited in each module's docstring.
- `tests/` — unit tests for every `src/` module, exclusively on synthetic fixtures (no real data in the test suite, by design — see Phase 1a's data-QA-vs-signal-path separation above).
- `scripts/` — one-off operational scripts (the Phase 1a corpus pull, Pass 2 verification) — not part of the importable engine.

## Data storage

Raw pulled data lives outside this repository and outside OneDrive, at the path in `src/config.py`'s `DATA_DIR` — default `C:\Users\Aaron\quant-data\commodity-carry`, overridable via the `DATA_DIR` environment variable. The repo itself only ever holds a provenance manifest (`data/MANIFEST.md`: request parameters, timestamps, SHA-256 per file) and reports — never the raw files themselves.
