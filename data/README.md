# Data provenance conventions

Raw data is never committed to this repository (see `.gitignore`: `data/raw/` is excluded entirely). What lives here instead, once data acquisition begins:

- **`manifest.json`** (or similar) — one entry per retrieved file/request: source, exact request specification (dataset, schema, symbols, date range), SHA-256 checksum of the retrieved file, retrieval date (UTC), and the tool/script version used to fetch it.
- **Checksums** for every file actually pulled, so integrity can be verified without needing to re-fetch or without needing write access to the vendor account that pulled it originally.
- **No vendor "signals" or "analytics" fields** — only raw price/volume/OI/reference data as licensed, consistent with the no-alpha-peeking discipline carried over from Phase 0.

## Phase 0 provenance (for reference, not yet a real pull)

Phase 0 verified feasibility via Databento's `metadata.get_cost` (quotes only) and 18 real single-row `timeseries.get_range` probes against `GLBX.MDP3` — never a bulk pull. Full record of every call made, including exact parameters and cost: `docs/DATA_FEASIBILITY_REPORT.md`'s addendum, `docs/SAMPLE_AUDIT.md`, and the Phase 0 workspace's `samples/COST_LEDGER.md` (not part of this repo — the workspace is a separate, non-repo scratch directory used for the feasibility gate).

## Source

- **Dataset:** Databento `GLBX.MDP3` (CME Globex MDP 3.0).
- **Universe:** 18 CME futures, 4 sectors — see `docs/DECISION_MEMO.md` for the full symbol list and per-symbol history windows.
- **Schemas:** `ohlcv-1d` (daily bars), `statistics` (settlement price, open interest), `definition` (expiry calendar).
