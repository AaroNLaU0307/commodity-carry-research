# Data Provenance Manifest

Generated (UTC): 2026-07-09T23:40:18.052983+00:00

Raw files live in `DATA_DIR` (see `src/config.py` / README's Data storage section) -- outside this repo and outside OneDrive. Never committed. This manifest is the committed record of what was pulled, when, and its checksums.

## Request parameters (locked, PREREGISTRATION.md Sec 2)

- Dataset: `GLBX.MDP3`
- Symbols: 18 pre-registered CME symbols (parent symbology)
- Date range: `2010-06-06` (inclusive) to `2026-07-01` (exclusive) == through 2026-06-30 inclusive
- Schemas: `ohlcv-1d`, `statistics`, `definition`

## Cost

- Total quoted: see `docs/samples/COST_LEDGER.md`

- Full ledger: `docs/samples/COST_LEDGER.md` (continued from the Pass 2 session's rows 1-39)

## Files

| File | Size (bytes) | SHA-256 |
|---|---|---|
| `ohlcv-1d.dbn.zst` | 107,229,003 | `333095164e55c73a150949b654a0e4c9f15636cc01ee7c93bf625e5412c59539` |

Total confirmed-complete: 1 files, 107,229,003 bytes.

## In progress / not yet manifested

These files exist in `DATA_DIR` but are NOT yet confirmed complete (no matching REAL SPEND row in `docs/samples/COST_LEDGER.md` as of this manifest generation) and are therefore deliberately excluded above -- checksumming a file still being written to would record an unstable, meaningless hash. See `docs/DATA_QA_REPORT.md` Sec 0 for the full status.

- `statistics_2010-06-06_2011-01-01.dbn.zst` — 54,435,354 bytes as of manifest generation, size not final

## Notes

- `statistics` was split into yearly (or finer) date-range chunks after the single full-range request consistently hit a server-side gateway timeout (`504`) across multiple attempts; `ohlcv-1d` succeeded as a single request. This is a mechanical delivery detail, not a change to what was requested -- every chunk covers the same locked whitelist (dataset, schema, symbols), just a narrower date sub-range per request. See `docs/samples/COST_LEDGER.md` for every chunk's individual quote and actual cost.
- Raw data integrity findings (settlement/OI coverage, gaps, expiry calendar completeness, spot-checks) are in `docs/DATA_QA_REPORT.md`, not here -- this manifest is provenance only.