# Premise Report

Generated (UTC): 2026-09-28T15:45:07.057070+00:00 · code `70d1e0392f7112042d5855d57df9ca3e54bfda1a`

Runner-generated (`scripts/phase1b_premise_test.py`). PREREGISTRATION.md Sec 7. This run follows the 2026-09-27 corrections (`reports/ADDENDUM_2026-09-27.md`: trade-date calendar, open-interest field, execution timing). Run 4's published report, `reports/PREMISE_REPORT.md`, stays unchanged as the pre-correction record.

## Run-history disclosure

Runs 1-3 were invalidated, each by an integrity anomaly caught before any premise number was trusted -- never by a result direction. Run 4 (commit 543d271) was the first valid premise computation; it keyed statistics on the delivery file's UTC date (Sunday rows) and read CLEARED_VOLUME as open interest, and is superseded by this run.

| Run | Trigger anomaly | Root cause | Fix |
|---|---|---|---|
| 1 | `RuntimeWarning: divide by zero` inside `carry.compute_carry()` (GC, SI, PA) | 8,635 outright rows (0.31%, all 18 symbols) with `statistics` settlement <= 0 -- far-dated, not-yet-traded contracts reported as 0.00 rather than omitted | Next-contract settlement <= 0 treated as NaN, symmetric with missing-settlement handling (`DEVIATIONS.md`, 2026-07-11) |
| 2 | Implausible ~49% held-front missing-settlement rate, concentrated from 2019 onward | F9: a single real contract's `raw_symbol` format drifts mid-life (instrument_id 551735: "CLM19" for 2 days, "CLM9" for ~9 more years), silently splitting one contract's OI/settlement history across two spurious `_contract_key` columns | Dropped `raw_symbol` from `_contract_key`; key is now `instrument_id + expiration.date()` |
| 3 | Implausible 63.504% held-front missing-settlement rate; permanent-tripwire dead-front discovery on 13 of 18 symbols | F10: an `expiration` time-of-day correction mid-life (instrument_id 827180, KE) fractured one contract's OI history, freezing the roll rule's crossover exactly where an adjacent contract's roll should have occurred -- and even after that identity fix, 11 of 18 symbols remained permanently stuck for a structurally different reason (F11): the single-candidate roll rule deadlocks whenever the immediately-next contract is a listed-but-illiquid ("dead") serial month | A1 (multi-candidate OI-max roll rule) + A2 (next-OI-bearing carry-next), adjudicated 2026-07-15 (`DEVIATIONS.md`) |
| 4 | Published 2026-07-16; not invalidated by an anomaly in its own output | Statistics keyed on the file's UTC date (Sunday re-sends became trading days, ~313 rows/yr) and `stat_type` 6 (CLEARED_VOLUME) used as open interest | Trade-date (`ts_ref`) keying, session calendar, `StatType.OPEN_INTEREST` (`reports/ADDENDUM_2026-09-27.md`) |

**F12 mechanism note, for the fill-count table below.** The t-1 look-ahead discipline (Sec 3, unchanged by A1/A2) means the roll rule can only ever detect a real-market liquidity shift one day after it happens -- official OI is published T+1, so the roll always trails the market by exactly one day. When that shift is abrupt rather than gradual, the day this pipeline is still nominally holding the old contract for the return calculation is already a day the real market has moved on from it entirely, and CME may not publish anything for it that day -- confirmed absent from both `statistics` and `ohlcv-1d`, not lost anywhere in this pipeline. This is the cost of the look-ahead-safe design, not a defect: found 8 times, all on CL, against CL's own ~193 rolls in the sample (~4%), zero times on any other symbol (`F12`, `docs/DATA_QA_REPORT.md`).

**Tripwire firings this run.** The permanent tripwire (`assert_front_not_past_expiry`) is checked for every symbol before its carry is computed. Any firing that does not exactly match the one user-pre-authorized transient graze below would have halted this run before reaching this report.

- None -- zero tripwire firings of any kind this run.

## Pipeline integrity checks

- **Trade-date keying (2026-09-27):** every settlement/OI value keyed on its `ts_ref` trade date; a symbol's calendar is the trade dates with at least one published settlement or OI. Statistics diagnostics: 8 weekend-dated records dropped (no weekend trade date in the kept calendar; 2011-08-07 instrument_id=197210 stat_type=3; 2011-10-02 instrument_id=66128 stat_type=3; 2011-10-02 instrument_id=66130 stat_type=3; 2011-10-02 instrument_id=1208 stat_type=3; 2011-10-02 instrument_id=66134 stat_type=3; 2011-10-02 instrument_id=66137 stat_type=3; 2011-10-02 instrument_id=66138 stat_type=3; 2014-02-23 instrument_id=819161 stat_type=3), 1649822 open-interest records without a `ts_ref` dated to the instrument's latest settlement trade date received before them (2026-09-27 DATA_FIX), 3 records still without a trade date dropped, 0 DELETE records applied. Open interest = `StatType.OPEN_INTEREST`.
- **Late-record rule (DATA_FIX, 2026-09-27; `reports/ADDENDUM_2026-09-27.md` §10):** a record for trade date d received after the same instrument's record of the same stat type for a later trade date is ignored. Dropped: 2966 settlement records, 2116 open-interest records.
- **Roll rule and carry-next selection:** A1 (multi-candidate OI-max roll rule) and A2 (next-OI-bearing carry-next), per `DEVIATIONS.md` 2026-07-15 -- this run uses the amended pipeline throughout, verified against the validated read-only counterfactual before this run (`docs/DATA_QA_REPORT.md`, 2026-07-16 addendum, Gates 1-4).
- **Zero-price guard (Step 0 spec):** silent -- no held-front settlement <= 0 was encountered across all 18 symbols' full history. (F2's confirmed negative CLK0 settlement on 2020-04-20 was correctly not the OI-determined front that day.)
- **Next-contract settlement <= 0 in the carry formula (found and adjudicated this session, DEVIATIONS.md 2026-07-11):** treated as NaN (not computable), symmetric with missing-settlement handling. 8,635 outright rows (0.31%) were affected across all 18 symbols before this fix, overwhelmingly far-dated not-yet-traded contracts; carry is NaN on the affected symbol-days rather than an undefined (inf/nan-from-division) value.
- **Truncation-invariance check (Step 1.2):** PASSED -- the month-end carry panel recomputed with the final 6 months of raw data removed is bit-identical to the full panel up to the truncation date.
- **Held-front missing-settlement fills (Step 0 spec, mark-to-last + zero return, counted precisely per returns.count_held_front_missing_settlement() -- only the cells chain_returns() actually reads, not every column in the wide panel):** 306 occurrences across 72,296 trading days (0.423%).

| Symbol | Trading days | Missing-settlement fills |
|---|---|---|
| CL | 4,066 | 17 |
| HO | 4,066 | 17 |
| RB | 4,066 | 17 |
| NG | 4,066 | 17 |
| GC | 4,066 | 17 |
| SI | 4,066 | 17 |
| HG | 4,066 | 17 |
| PL | 4,066 | 17 |
| PA | 4,066 | 17 |
| ZC | 4,069 | 17 |
| ZS | 4,069 | 17 |
| ZW | 4,069 | 17 |
| ZM | 4,069 | 17 |
| ZL | 4,069 | 17 |
| KE | 3,174 | 17 |
| LE | 4,061 | 17 |
| HE | 4,061 | 17 |
| GF | 4,061 | 17 |

## Universe and entry dates

Per Sec 2 (no backfill); entry dates per config.py's frozen constants (dataset floor 2010-06-07 for 17 symbols, KE's confirmed 2013-12-16 entry).

- Month-end panel: 193 months, 2010-06-30 to 2026-06-30
- Symbols with data: 18 / 18
- Timing: execution_lag = 0 (registered; month-end t's outcome window starts with settle(t) -> settle(t+1), `preregistration/AMENDMENT_2026-09-27.md`).

## XS premise (Sec 7)

Monthly cross-sectional Spearman rank IC between carry_i(t) and symbol i's next-month excess return, Newey-West(3)-adjusted t-statistic (lag fixed per DEVIATIONS.md 2026-07-11).

- Mean IC: **0.028270**
- NW(3) t-statistic: 1.3721
- p-value: 0.1700
- Months used: 192
- **Gate verdict:** **PROCEEDS to Phase 1c** (point estimate > 0 required to proceed; Sec 7's gate is mechanical on the sign of the point estimate alone, not significance)

## TS premise (Sec 7)

Pooled panel regression of next-month excess return on sign(carry_i(t)), standard errors clustered by month.

- Coefficient: **-0.000143**
- Clustered t-statistic: -0.0690
- p-value: 0.9450
- N (symbol-month observations): 3,414
- **Gate verdict:** **CLOSES at premise (no backtest)**

## Summary

| Arm | Point estimate | Gate verdict |
|---|---|---|
| H1 (XS) | 0.028270 | **PROCEEDS to Phase 1c** |
| H2 (TS) | -0.000143 | **CLOSES at premise (no backtest)** |

## Sensitivity: execution one trading day after the signal (non-gating)

Registered by `preregistration/AMENDMENT_2026-09-27.md`: the same tests with each month's outcome window shifted one trading row (first return settle(t+1) -> settle(t+2)). Reported beside the registered result; the gate above is decided at execution_lag = 0 only.

| Arm | Point estimate | t-statistic | p-value |
|---|---|---|---|
| H1 (XS) mean IC | 0.029179 | 1.3966 | 0.1625 |
| H2 (TS) coefficient | -0.000275 | -0.1336 | 0.8937 |

**Surviving arm(s) proceeding to Phase 1c: H1 (XS).**