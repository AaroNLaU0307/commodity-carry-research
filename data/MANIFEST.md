# Data Provenance Manifest

Generated (UTC): 2026-07-11T06:03:52.995478+00:00

Raw files live in `DATA_DIR` (see `src/config.py` / README's Data storage section) -- outside this repo and outside OneDrive. Never committed. This manifest is the committed record of what was pulled, when, and its checksums.

## Request parameters (locked, PREREGISTRATION.md Sec 2)

- Dataset: `GLBX.MDP3`
- Symbols: 18 pre-registered CME symbols (parent symbology)
- Date range: `2010-06-06` (inclusive) to `2026-07-01` (exclusive) == through 2026-06-30 inclusive
- Schemas: `ohlcv-1d`, `statistics`, `definition`

## Cost

See `docs/samples/COST_LEDGER.md` for every quote and every real charge, in order.

## Files

### `ohlcv-1d`

| File | Size (bytes) | SHA-256 |
|---|---|---|
| `ohlcv-1d.dbn.zst` | 107,229,003 | `333095164e55c73a150949b654a0e4c9f15636cc01ee7c93bf625e5412c59539` |

### `definition`

Delivered as 5,031 per-day files (Databento batch-job default split_duration="day"; concatenating independently-compressed DBN streams is not valid, so they are kept as delivered -- see `scripts/phase1a_batch_poll_download.py`).

- Total files: 5,031
- Total bytes: 2,153,223,347
- Aggregate SHA-256 (of the sorted `filename:sha256` lines for every individual file, newline-joined): `76da3a39a7279ef3a3b4c03ffb2646048685f715466108ca5136aee6f7922277`
- Full per-file checksum list: `manifest_perfile_definition.json` (WORKSPACE, not committed -- reproducible from `DATA_DIR` at any time; the aggregate hash above is what's committed here as the tamper-evident record)

### `statistics`

Delivered as 5,026 per-day files (Databento batch-job default split_duration="day"; concatenating independently-compressed DBN streams is not valid, so they are kept as delivered -- see `scripts/phase1a_batch_poll_download.py`).

- Total files: 5,026
- Total bytes: 7,166,969,133
- Aggregate SHA-256 (of the sorted `filename:sha256` lines for every individual file, newline-joined): `ee7dee4dc1c2dab44df207d20d5327b0dfb7e6193c49091b8e0a52bfb489001f`
- Full per-file checksum list: `manifest_perfile_statistics.json` (WORKSPACE, not committed -- reproducible from `DATA_DIR` at any time; the aggregate hash above is what's committed here as the tamper-evident record)

Total confirmed-complete: 3 schema(s), 10,058 file(s), 9,427,421,483 bytes.

## Superseded (billed provenance, retired, not part of the working dataset)

Session 1 pulled `statistics` as ad hoc yearly chunks via synchronous streaming before the batch-job API was adopted (see `docs/DATA_QA_REPORT.md`'s addenda). The 4 confirmed-billed, complete chunks below are **retired** to `DATA_DIR/_superseded/` now that the full-range batch delivery (`GLBX-20260710-E8YMQQJMA7`) has landed and is verified complete -- moved, not deleted, since they remain real billed provenance (`docs/samples/COST_LEDGER.md` rows 46/49/51/54). `src/data_loader.py::load_dbn_partitioned()` only ever resolves `DATA_DIR/{schema}/*.dbn.zst`, never `DATA_DIR/_superseded/`, so these files cannot be silently mixed into a Phase 1b/1c computation -- single-provenance by construction, not just by convention.

| File | Size (bytes) | SHA-256 |
|---|---|---|
| `statistics_2010-06-06_2011-01-01.dbn.zst` | 114,164,811 | `e29db6e3e59448deaae2bd9e151c1b8293a4c9dcd72420b4a9b8c29f59b053f1` |
| `statistics_2012-01-01_2013-01-01.dbn.zst` | 165,856,063 | `d134fa957b1b3e21b05245390fdb4a8b66d740971e132071f7e98a6a8cbe02d5` |
| `statistics_2013-01-01_2014-01-01.dbn.zst` | 173,505,255 | `8a04d5846b7e14c4adb505e1ae74fc8e30a9cd23cb4f0423df5adf6fd44915ff` |
| `statistics_2015-01-01_2016-01-01.dbn.zst` | 231,384,865 | `6c09b9f7ef6e678818f6a90d870bfc57493eb64d804aa89c66f93f9a91901013` |

## Notes

- Raw data integrity findings (settlement/OI coverage, gaps, expiry calendar completeness, spot-checks) are in `docs/DATA_QA_REPORT.md`, not here -- this manifest is provenance only.