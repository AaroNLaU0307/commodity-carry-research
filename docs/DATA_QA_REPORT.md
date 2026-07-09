# Data QA Report — Phase 1a

**Status: PARTIAL, honestly reported.** `ohlcv-1d` was fully pulled, checksummed, and audited. `statistics` and `definition` did not finish pulling within this session — see §0 for exactly why, and the findings register (§7) for what that blocks. This is a data-delivery mechanics problem, not a cost, guardrail, or design issue. **No carry value, return, ranking, or portfolio weight was computed anywhere in this audit** — every check below is a count, a coverage window, a checksum, or a flag, per Hard Rule 1.

Immutable snapshot once written; corrections go in a dated addendum at the bottom, never silent edits.

---

## 0. Corpus pull status (why this report is partial)

| Schema | Status | Detail |
|---|---|---|
| `ohlcv-1d` | **Complete** | Single request, all 18 symbols, full 2010-06-06→2026-07-01(excl) range. Succeeded in ~3 minutes. 107,229,003 bytes. SHA-256 in `data/MANIFEST.md`. |
| `statistics` | **Incomplete** | A single full-range request timed out (`504 gateway timeout`) on 4 consecutive attempts (1 initial + 3 retries). Re-quoted and split into 17 yearly chunks (mechanical batching change only — same locked dataset/schema/symbols/date range, per the pull's own "batch or streaming per your judgment" latitude). The first chunk (2010-06-06 to 2011-01-01, ~7 months) was still transferring after 45+ minutes and had not completed when this report was written. At that rate, the remaining 16 chunks are not practical to finish within this session. |
| `definition` | **Not obtained** | One unchunked attempt also hit a `504` timeout. Not re-attempted given the time already spent on `statistics`. |

**Root cause (best assessment, not certain):** `ohlcv-1d` generation is evidently far cheaper for Databento's backend to serve than `statistics` or `definition` for the same symbol/date scope — the size difference alone doesn't explain a 45-minute partial transfer for a 7-month slice. **Recommended fix for the follow-up session:** use Databento's asynchronous batch-job API (`client.batch.submit_job()`, poll `list_jobs()`, then `download()`) instead of synchronous streaming (`timeseries.get_range()`). Batch jobs are specifically designed for large historical requests and are not bound by a synchronous gateway's response-time window — this should sidestep the timeout entirely rather than working around it with ever-smaller chunks. This is a delivery-mechanism change only; it does not touch the locked whitelist (dataset, schemas, symbols, date range) in any way.

**Cost impact of the incomplete pull:** none beyond what's already logged. `metadata.get_cost` is never billed regardless of outcome; the only real spend logged is for data that was actually, successfully delivered (`ohlcv-1d`, $44.643947, plus the one `statistics` chunk if it completes — see `docs/samples/COST_LEDGER.md` for the exact, current cumulative). No guardrail was breached; the ceiling was never approached.

---

## 1. Settlement coverage (`statistics` schema) — **BLOCKED, schema not yet obtained**

Cannot be completed until `statistics` data is available. Nothing asserted here.

## 2. Open-interest coverage (`statistics` schema) — **BLOCKED, schema not yet obtained**

Cannot be completed until `statistics` data is available. This is the check that matters most for the roll rule (§3 of `PREREGISTRATION.md` depends on OI at t-1) — it is a hard prerequisite for Phase 1b, not an optional nicety.

## 3. Gap audit (`ohlcv-1d` — completed; full gap audit including `statistics` — pending)

**June 2014 degraded-quality window.** Databento's own API surfaces a warning for 2014-06-11 through 2014-06-13 ("reduced quality"). Confirmed: data **is present** for all three dates — 432 outright rows across all 18 root symbols, not missing — consistent with "quality-flagged," not "absent." No further interpretation attempted here (per the no-alpha-peeking bright line, "flag only" for divergence-type checks).

**Pooled trading-day counts per year** (all 18 roots, union of dates with ≥1 outright row): 2010 shows 179 days (partial year, data starts 2010-06-06/07 — expected) and 2026 shows 154 days (partial year through 2026-06-30 — expected). Every full year (2011–2025) shows 308–313 days — higher than a naive 252-weekday count, plausibly reflecting Sunday-evening electronic session dating on CME Globex's near-24-hour schedule across 18 different products with slightly different holiday calendars (a union across products is always ≥ any single product's own trading-day count). **This is an observation, not a verified explanation** — a proper *per-symbol* gap audit against each product's actual CME holiday calendar was not done this session (an eyeball pooled check is not a substitute) and is noted as a limitation for Phase 1b prep, not asserted as "no gaps exist."

**No exchange-side anomalies found in `ohlcv-1d` beyond the zero/negative-close finding below** — no duplicate rows detected in the per-instrument row-count summary, no price-scale jump investigation was performed this session (would require the kind of longitudinal per-instrument price series review that risks drifting into signal-adjacent territory; deferred).

## 4. Expiry calendar (`definition` schema) — **BLOCKED, schema not yet obtained**

Cannot be completed until `definition` data is available. This is a hard prerequisite for `D` (calendar days between consecutive expiries) in the carry formula (§3) — nothing about expiry-calendar completeness can be asserted here.

## 5. Spot-checks against a public source — **BLOCKED, schema not yet obtained**

The pre-registered spot-check is specifically against **settlement** prices (the mandatory, carry-relevant price per `PREREGISTRATION.md` §3), which live in the `statistics` schema. `ohlcv-1d`'s "close" field is a different, non-equivalent quantity (last trade/quote in the session vs. the exchange's official settlement algorithm) and was deliberately not used as a stand-in — substituting one for the other here would misrepresent what was actually checked. **Zero settlement values have been checked against any public source this session.**

## 6. KE entry date confirmation — **partially confirmed (ohlcv-1d only)**

**Confirmed:** KE's first outright `ohlcv-1d` record is **2013-12-16**, exactly matching the load-bearing claim in `PREREGISTRATION.md` §2 and the Phase 0 probe (`per_symbol_probe_results.json`). Verified twice independently in this session (once on the unfiltered symbol set, once after excluding spread/combo instruments per §7 finding F1 below — same answer both times).

**Not yet confirmed:** whether KE's `statistics` (settlement/OI) and `definition` (expiry) records begin on the same date, or diverge from it — cannot be checked until those schemas are available.

## 7. Findings register

| ID | Severity | Finding | Proposed handling (not implemented this session) |
|---|---|---|---|
| F1 | **High** | Parent symbology returns spread and combination instruments alongside outright single-month contracts, and they vastly outnumber the outrights: of 4,505,270 `ohlcv-1d` rows, only 953,766 (21.2%) are outright; 3,551,504 (78.8%) are spreads/combos. Two distinct non-outright symbol formats observed so far: hyphenated calendar spreads (e.g. `NGV0-NGX0`) and `":CF"`-suffixed multi-leg combos (e.g. `ZS:CF N1Q1U1X1`) — a simple symbol-string heuristic catches the first but not the second, so **symbol-string pattern matching is not a reliable filter**. | Filter to outright-only instruments using the `definition` schema's actual instrument-classification field (not obtained yet) before any roll-rule or carry computation. Re-verify no third non-outright format exists once `definition` is available. |
| F2 | Medium | Of the 953,766 apparent "outright" rows (after the hyphen-only filter), 3,490 (0.37%) have zero/negative close. 97.3% of these cluster in five grain/oilseed roots (ZS 1,442; ZM 893; ZW 426; ZC 410; ZL 224) and the sample rows show the `":CF"` combo notation from F1 — i.e., most of this residual is **F1 leaking through an incomplete filter**, not a second, independent data-quality problem. | Re-run this check after F1's proper instrument-class filter is applied; expect the residual to drop sharply. Any genuinely-outright zero/negative-close rows still remaining after that should be individually inspected. |
| F3 | Low / informational | The known June 2014 degraded-quality window (2014-06-11 to 13) has data present, not missing, consistent with Databento's own "reduced quality" flag rather than an outage. | Treat these 3 dates with caution in any settlement-based computation in Phase 1c; consider flagging or excluding if they prove influential on any roll/carry calculation touching them. |
| F4 | Informational / limitation | Pooled (18-root-union) trading-day counts run 308–313/year for full years — plausible given Sunday-session dating on a 24-hour multi-product calendar, but not verified against each product's actual CME holiday calendar. | A proper per-symbol gap audit against real CME trading calendars, before Phase 1b relies on any implicit "no gaps" assumption. |
| F5 | Operational (blocks Phase 1a completion, not a design/guardrail issue) | `statistics` and `definition` did not finish pulling this session — see §0. | Resume the pull in a follow-up session using Databento's batch-job API instead of synchronous streaming (see §0's recommendation). Re-quote before resuming, per the same guardrails as this session. |
| — | Confirmed (not an anomaly) | All 18 pre-registered root symbols present in `ohlcv-1d`, outright coverage spanning the full locked date range for each. KE's outright entry date confirmed at exactly 2013-12-16, matching `PREREGISTRATION.md` §2 and the Phase 0 probe. | N/A — no action needed, stated for completeness of the register. |

---

## Ledger / balance reconciliation

Pending final ledger state once the currently-running `statistics` chunk resolves (success or failure) and Aaron reads the post-session portal balance into `POST_PULL_BALANCE`. Real spend logged so far this session: $44.643947 (`ohlcv-1d`) plus whatever the in-progress `statistics` chunk logs if it completes — see `docs/samples/COST_LEDGER.md` for the authoritative, current running total. **Reminder for Aaron, per guardrail 4: restore the Databento portal's monthly spending limit to $20 once the corpus pull work is actually finished** — the $125 setting was for this pull only, and is not lowered automatically.

---

## Addendum log

*(none yet)*
