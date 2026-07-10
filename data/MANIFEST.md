# Data Provenance Manifest

Generated (UTC): 2026-07-10T13:10:42.870366+00:00

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

Total confirmed-complete: 2 schema(s), 5,032 file(s), 2,260,452,350 bytes.

## Not yet manifested

- `statistics` -- submitted as a Databento batch job (`GLBX-20260710-E8YMQQJMA7`), billed at submission, still processing server-side as of this manifest generation. See `docs/DATA_QA_REPORT.md`'s addendum Sec 0 for the current progress reading and honest ETA assessment.
- 4 pre-batch `statistics` yearly-chunk files remain in `DATA_DIR` (`statistics_2010-06-06_2011-01-01.dbn.zst` and 3 others) -- confirmed billed (`docs/samples/COST_LEDGER.md` rows 46/49/51/54) but superseded by the pending full-range batch job per the Step 1 reconciliation plan; kept until that job completes and is verified, then removed as redundant. Not manifested here since they cover only partial date ranges, not the full locked window.

## Notes

- Raw data integrity findings (settlement/OI coverage, gaps, expiry calendar completeness, spot-checks) are in `docs/DATA_QA_REPORT.md`, not here -- this manifest is provenance only.