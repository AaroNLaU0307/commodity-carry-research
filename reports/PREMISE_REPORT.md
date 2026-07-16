# Premise Report

Generated (UTC): 2026-07-16T08:12:05.533233+00:00

Runner-generated, immutable once committed (dated addenda only for any future correction). PREREGISTRATION.md Sec 7. First real-data carry/return computation in this project's history.

## Run-history disclosure

Three prior pipeline runs were invalidated before this one, each by an integrity anomaly caught before any premise number was trusted -- never by a result direction. No directional memory of any invalidated run's numbers -- premise, primary, or otherwise -- informs anything below. This is the first valid premise computation in this project's history.

| Run | Trigger anomaly | Root cause | Fix |
|---|---|---|---|
| 1 | `RuntimeWarning: divide by zero` inside `carry.compute_carry()` (GC, SI, PA) | 8,635 outright rows (0.31%, all 18 symbols) with `statistics` settlement <= 0 -- far-dated, not-yet-traded contracts reported as 0.00 rather than omitted | Next-contract settlement <= 0 treated as NaN, symmetric with missing-settlement handling (`DEVIATIONS.md`, 2026-07-11) |
| 2 | Implausible ~49% held-front missing-settlement rate, concentrated from 2019 onward | F9: a single real contract's `raw_symbol` format drifts mid-life (instrument_id 551735: "CLM19" for 2 days, "CLM9" for ~9 more years), silently splitting one contract's OI/settlement history across two spurious `_contract_key` columns | Dropped `raw_symbol` from `_contract_key`; key is now `instrument_id + expiration.date()` |
| 3 | Implausible 63.504% held-front missing-settlement rate; permanent-tripwire dead-front discovery on 13 of 18 symbols | F10: an `expiration` time-of-day correction mid-life (instrument_id 827180, KE) fractured one contract's OI history, freezing the roll rule's crossover exactly where an adjacent contract's roll should have occurred -- and even after that identity fix, 11 of 18 symbols remained permanently stuck for a structurally different reason (F11): the single-candidate roll rule deadlocks whenever the immediately-next contract is a listed-but-illiquid ("dead") serial month | A1 (multi-candidate OI-max roll rule) + A2 (next-OI-bearing carry-next), adjudicated 2026-07-15 (`DEVIATIONS.md`) |

**F12 mechanism note, for the fill-count table below.** The t-1 look-ahead discipline (Sec 3, unchanged by A1/A2) means the roll rule can only ever detect a real-market liquidity shift one day after it happens -- official OI is published T+1, so the roll always trails the market by exactly one day. When that shift is abrupt rather than gradual, the day this pipeline is still nominally holding the old contract for the return calculation is already a day the real market has moved on from it entirely, and CME may not publish anything for it that day -- confirmed absent from both `statistics` and `ohlcv-1d`, not lost anywhere in this pipeline. This is the cost of the look-ahead-safe design, not a defect: found 8 times, all on CL, against CL's own ~193 rolls in the sample (~4%), zero times on any other symbol (`F12`, `docs/DATA_QA_REPORT.md`).

**Tripwire firings this run.** The permanent tripwire (`assert_front_not_past_expiry`) is checked for every symbol before its carry is computed. Any firing that does not exactly match the one user-pre-authorized transient graze below would have halted this run before reaching this report.

- NG: known allowed transient graze(s), contract(s) ['192047__2010-06-28', '192053__2010-12-28'], held on ['2010-06-29 00:00:00', '2010-12-29 00:00:00'] -- non-permanent, resolves the next trading day (F11 amendment record). Not a new anomaly; continuing with skip_tripwire=True for this symbol's carry computation only.

## Pipeline integrity checks

- **Roll rule and carry-next selection:** A1 (multi-candidate OI-max roll rule) and A2 (next-OI-bearing carry-next), per `DEVIATIONS.md` 2026-07-15 -- this run uses the amended pipeline throughout, verified against the validated read-only counterfactual before this run (`docs/DATA_QA_REPORT.md`, 2026-07-16 addendum, Gates 1-4).
- **Zero-price guard (Step 0 spec):** silent -- no held-front settlement <= 0 was encountered across all 18 symbols' full history. (F2's confirmed negative CLK0 settlement on 2020-04-20 was correctly not the OI-determined front that day.)
- **Next-contract settlement <= 0 in the carry formula (found and adjudicated this session, DEVIATIONS.md 2026-07-11):** treated as NaN (not computable), symmetric with missing-settlement handling. 8,635 outright rows (0.31%) were affected across all 18 symbols before this fix, overwhelmingly far-dated not-yet-traded contracts; carry is NaN on the affected symbol-days rather than an undefined (inf/nan-from-division) value.
- **Truncation-invariance check (Step 1.2):** PASSED -- the month-end carry panel recomputed with the final 6 months of raw data removed is bit-identical to the full panel up to the truncation date.
- **Held-front missing-settlement fills (Step 0 spec, mark-to-last + zero return, counted precisely per returns.count_held_front_missing_settlement() -- only the cells chain_returns() actually reads, not every column in the wide panel):** 2,440 occurrences across 89,436 trading days (2.728%).

| Symbol | Trading days | Missing-settlement fills |
|---|---|---|
| CL | 5,031 | 159 |
| HO | 5,031 | 134 |
| RB | 5,031 | 134 |
| NG | 5,031 | 152 |
| GC | 5,031 | 135 |
| SI | 5,031 | 136 |
| HG | 5,031 | 135 |
| PL | 5,031 | 135 |
| PA | 5,031 | 135 |
| ZC | 5,031 | 133 |
| ZS | 5,031 | 133 |
| ZW | 5,031 | 133 |
| ZM | 5,031 | 133 |
| ZL | 5,031 | 133 |
| KE | 3,927 | 109 |
| LE | 5,025 | 137 |
| HE | 5,025 | 137 |
| GF | 5,025 | 137 |

## Universe and entry dates

Per Sec 2 (no backfill); entry dates per config.py's frozen constants (dataset floor 2010-06-07 for 17 symbols, KE's confirmed 2013-12-16 entry).

- Month-end panel: 193 months, 2010-06-30 to 2026-06-30
- Symbols with data: 18 / 18

## XS premise (Sec 7)

Monthly cross-sectional Spearman rank IC between carry_i(t) and symbol i's next-month excess return, Newey-West(3)-adjusted t-statistic (lag fixed per DEVIATIONS.md 2026-07-11).

- Mean IC: **0.028489**
- NW(3) t-statistic: 1.4650
- p-value: 0.1429
- Months used: 192
- **Gate verdict:** **PROCEEDS to Phase 1c** (point estimate > 0 required to proceed; Sec 7's gate is mechanical on the sign of the point estimate alone, not significance)

## TS premise (Sec 7)

Pooled panel regression of next-month excess return on sign(carry_i(t)), standard errors clustered by month.

- Coefficient: **0.000672**
- Clustered t-statistic: 0.3000
- p-value: 0.7642
- N (symbol-month observations): 3,414
- **Gate verdict:** **PROCEEDS to Phase 1c**

## Summary

| Arm | Point estimate | Gate verdict |
|---|---|---|
| H1 (XS) | 0.028489 | **PROCEEDS to Phase 1c** |
| H2 (TS) | 0.000672 | **PROCEEDS to Phase 1c** |

**Surviving arm(s) proceeding to Phase 1c: H1 (XS), H2 (TS).**