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

## Addendum — 2026-07-10, Phase 1a Follow-up (corpus completion + QA continuation)

**Status change: PARTIAL → PARTIAL (materially advanced).** `ohlcv-1d` and `definition` are now both complete and checksummed. `statistics` is submitted, billed, and processing server-side via Databento's batch-job API (fixing the session-1 mechanism problem), but has not finished as of this writing — see §0 below for the honest ETA assessment. Settlement/OI-dependent checks (§1, §2, spot-checks in §5) remain blocked for that reason alone, not a design or guardrail issue. No carry value, return, ranking, or portfolio weight was computed anywhere in this addendum, per Hard Rule 1.

### §0 update — corpus pull status

| Schema | Status | Detail |
|---|---|---|
| `ohlcv-1d` | Complete (unchanged) | 107,229,003 bytes, SHA-256 in `data/MANIFEST.md`. |
| `definition` | **Complete** | Delivered via Databento batch job `GLBX-20260710-BN6B8WQRWH` as 5,031 per-day files (44,312,422 rows total), zero download failures across all files. Aggregate SHA-256 in `data/MANIFEST.md`; full per-file list in `_carry-research-workspace/manifest_perfile_definition.json` (not committed, reproducible from `DATA_DIR`). |
| `statistics` | **Still processing server-side** | Batch job `GLBX-20260710-E8YMQQJMA7`, submitted and billed 2026-07-10T05:44:47 UTC ($20.757709, logged as REAL SPEND at submission per the SDK's own billing model). Processing started 05:46:15 UTC. Progress readings taken across the session: 8%, 8% again, 10%, 12% — roughly 12% after ~7 hours of server-side processing. **Honest assessment: at anything resembling this rate, this job is very unlikely to reach `state="done"` within this session, and plausibly not within the next 24–48 hours either** — the progress metric's own non-linearity (identical readings across some checks) makes a firm ETA impossible to state responsibly. This is an acknowledged limitation of this addendum, not glossed over. No further cost is incurred by continuing to wait — the job is fully billed regardless of how long server-side processing takes. |

**Root-cause note (mechanism, resolved).** The batch-job API sidesteps the synchronous-streaming 504 timeouts that blocked `statistics`/`definition` in session 1 — `definition` completed cleanly this way. `statistics` is simply a much heavier job server-side (likely far more per-instrument-per-day settlement+OI records across thousands of listed instruments, vs. `definition`'s lighter per-instrument reference-data records); its processing time is outside this project's control once submitted.

**A second, unrelated mechanism problem surfaced and was fixed this session.** Downloading the completed `definition` job via the SDK's bulk `client.batch.download()` (all 5,031 files in one call) itself hit a `504 gateway timeout` — the same failure mode relocated one step later in the pipeline. Fixed by downloading files individually via the SDK's documented `filename_to_download` parameter, with a small thread pool and per-file retry/resume logic (`scripts/phase1a_batch_poll_download.py`, revised this session) — the same "break a large transfer into small, independently-retriable pieces" principle already used for `statistics` in session 1's yearly-chunk workaround, applied one level lower. Zero failures across all 5,031 files on this revised approach. Downloading is not a separate charge regardless of attempt count.

### F1 — RESOLVED: outright/spread classification, empirically verified

The `definition` schema's `instrument_class` field takes **exactly two values across the complete corpus** (44,312,422 rows, all 5,031 days, all 18 symbols): `F` (2,816,198 rows, 6.36%) and `S` (41,496,224 rows, 93.64%). Zero other values found anywhere. `":CF"`-suffixed multi-leg combo instruments (e.g. `ZC:CF H1K1N1U1`, `ZS:CF N1Q1U1X1`) are classified `S` alongside ordinary hyphenated calendar spreads — Databento does not give combos a distinct third class in this dataset. Spot-checked directly across 2010, 2011, 2015, 2020, and 2025 samples before confirming against the full corpus; no unexpected class or red-herring case found anywhere.

`OUTRIGHT_INSTRUMENT_CLASS = "F"` in `src/instrument_filter.py` (committed pending this evidence) is confirmed correct and left unchanged.

**3,353 unique outright contracts** across all 18 symbols (by `asset` + `raw_symbol` + `instrument_id`), zero missing roots, **zero null `activation`**:

| Symbol | Contracts | Earliest expiry | Latest expiry |
|---|---|---|---|
| CL | 328 | 2010-06-22 | 2037-01-20 |
| GC | 227 | 2010-06-28 | 2032-06-28 |
| GF | 137 | 2010-08-26 | 2027-08-26 |
| HE | 141 | 2010-06-14 | 2027-12-14 |
| HG | 241 | 2010-06-28 | 2031-09-26 |
| HO | 237 | 2010-06-30 | 2029-12-31 |
| KE | 78 | 2014-03-14 | 2029-07-13 |
| LE | 107 | 2010-06-30 | 2028-02-29 |
| NG | 342 | 2010-06-28 | 2038-11-26 |
| PA | 207 | 2010-06-28 | 2029-06-27 |
| PL | 207 | 2010-06-28 | 2029-04-26 |
| RB | 236 | 2010-06-30 | 2029-12-31 |
| SI | 224 | 2010-06-28 | 2030-12-27 |
| ZC | 96 | 2010-07-14 | 2029-12-14 |
| ZL | 153 | 2010-07-14 | 2029-12-14 |
| ZM | 159 | 2010-07-14 | 2029-12-14 |
| ZS | 133 | 2010-07-14 | 2029-11-14 |
| ZW | 100 | 2010-07-14 | 2029-07-13 |

The `asset` field (`definition` schema) gives a clean, field-based root-symbol mapping with zero missing/unexpected roots — a better alternative to `ohlcv-1d`'s symbol-string-prefix heuristic (still necessary there, since `ohlcv-1d` has no `asset` field of its own).

**Final, date-aware cross-reference against the already-complete `ohlcv-1d`:** joining on `(date, instrument_id)` — every one of `ohlcv-1d`'s 4,505,270 rows matched a same-day `definition` record (100% match rate, zero unmatched). Result: **941,928 outright rows (20.91%)**, 3,563,342 spread/combo rows (79.09%). All 18 roots present, zero missing. This is now the authoritative figure, superseding session 1's string-heuristic estimate of 953,766 (21.2%) — close in aggregate (the two differ by only ~0.3 percentage points) but the string heuristic remains methodologically unsound regardless (proven by the `:CF` red-herring case in `tests/test_instrument_filter.py`), so the closeness of the aggregate numbers is a coincidence of this particular dataset, not a vindication of the method.

### F6 — NEW, High severity: `instrument_id` is not a globally-stable key

While building the date-aware cross-reference above, a first-pass version of this analysis used a simpler (and, it turned out, incorrect) approach: build a static set of "every `instrument_id` ever seen with `instrument_class == 'F'`" from the full `definition` corpus, then filter `ohlcv-1d` by membership in that set. This produced a plausible-looking but **wrong** result (962,504 rows, 21.4%) that included genuine spread rows — e.g. `ZLV0-ZLZ0`, `GCQ0-GCM1`, `LEM0-LEG1` (all hyphenated spreads) appeared inside the supposedly outright-only set.

**Root cause, confirmed.** Databento/CME recycle numeric `instrument_id` values once an instrument is delisted. Confirmed example — `instrument_id 4948` was, at different points across this dataset's 16-year history:

| Observed as | `raw_symbol` | `asset` | `instrument_class` |
|---|---|---|---|
| earliest observed | `ZLV0-ZLZ0` | ZL | S (spread) |
| later | `PLU4-PLN5` | PL | S (spread) |
| activation 2015-06-26, expiry 2015-09-28 | `PLU5` | PL | **F (outright)** |
| later still | `PLX0-PLJ1` | PL | S (spread) |

**Scope.** Of the 3,353 outright instrument_ids, **668 (~20%) were also assigned to at least one other, usually non-outright, instrument at a different point in time.** Not a rare edge case.

**Fix, applied this session:**
- `src/instrument_filter.py`'s `outright_instrument_ids()` now raises `ValueError` if given a `definition_df` spanning more than one distinct date (detected via a `DatetimeIndex` or a `ts_recv`/`date`/`ts_event` column) — a caller who unions this function's output across multiple days and then filters a multi-day `ohlcv-1d`/`statistics` frame by static membership will silently misclassify recycled-ID rows; this guard makes that mistake fail loudly instead of shipping a wrong number. `filter_outright_only()` itself was never affected (it classifies rows in place, row-by-row, never materializing a cross-date ID set).
- Tests added: `test_outright_instrument_ids_raises_on_multiple_dates_via_datetime_index`, `..._via_ts_recv_column`, plus passing-case tests for legitimate single-day usage (`tests/test_instrument_filter.py`).
- The F1/F2 numbers reported in this addendum use a proper date-aware join (`(date, instrument_id) → instrument_class`, matched against `ohlcv-1d`'s own date per row), not the flawed static-set approach.

**Implication for Phase 1b/1c.** Any future code that joins `definition` to `ohlcv-1d`/`statistics` (the roll rule, the carry formula, anything using `instrument_id` as a cross-schema key) must be date-aware. This is now enforced at the API boundary in `src/instrument_filter.py`, not just documented in prose.

### F2 — RESOLVED: zero/negative-close re-audit under the proper filter

Under the corrected, date-aware outright filter (941,928 rows): **exactly one row has `close <= 0`** in the entire 16-year, 18-symbol outright universe:

| Date | Symbol | Close | Volume |
|---|---|---|---|
| 2020-04-20 | CLK0 (May 2020 WTI) | -2.67 | 102,083 |

This matches the well-documented historic episode in which May 2020 WTI crude oil futures traded and settled negative for the first time in history (2020-04-20), driven by a COVID-19 demand collapse colliding with Cushing, OK storage-capacity constraints as the May contract approached expiry. CME's own reported settlement that day was -$37.63 — `ohlcv-1d`'s `close` field is the session's last trade/quote, a different (and, on that specific day, far less extreme) quantity than the official settlement price, consistent with this report's own earlier note (§5) that `close` and settlement are not interchangeable. Same episode, different quantity — not a discrepancy requiring further explanation.

**Verdict: KEEP, with citation** (above). Session 1's naive-filter estimate of 3,490 (0.37%) "outright" zero/negative-close rows is now understood as almost entirely spread/combo contamination leaking through an imperfect string-based filter (as F2's original text already suspected) — confirmed and closed by the properly-filtered result above.

### §4 (expiry calendar) — RESOLVED

Every one of the 3,353 unique outright contracts has a non-null `expiration` (0 exceptions). `D` (calendar days between consecutive expiries, needed by the carry formula) is computable for every outright contract in the corpus.

### F4 — RESOLVED (materially deeper than session 1's pooled eyeball check): per-symbol gap audit

**Method.** For each symbol, compute its own set of outright trading days (via the corrected field-based filter) and compare against the pooled (any-symbol) trading calendar. Classify every "missing" day into one of three buckets, in order: (1) **Sunday-session difference** — a day of the week (Sunday) on which the pooled calendar has activity from some other symbol's CME Globex near-24-hour session, but this particular symbol does not trade a Sunday-evening session at all; (2) **US federal holiday** — computed analytically (New Year's Day, MLK Day, Presidents Day, Good Friday, Memorial Day, Juneteenth from 2021, Independence Day, Labor Day, Thanksgiving, Christmas; standard weekend-observance shifting), not looked up from an external calendar source; (3) **genuine residual** — whatever is left.

**Finding 1 (confirms and quantifies session 1's own hypothesis).** Energy and metals trade nearly every pooled Sunday (e.g. CL: 823/823 pooled Sundays); grains trade very few (ZC: 106/823); livestock trades almost none (LE: 1/823). A real, confirmed cross-sector difference in CME Globex session participation, not a data defect — it explains the large majority of the raw "missing vs. pooled" gap for grains and livestock that session 1's pooled-only view had flagged as an open question.

**Finding 2.** After both adjustments, the **total genuine residual across all 18 symbols over the full 16-year sample is 99 symbol-days** (roughly 0.11% of symbol-trading-days) — and it clusters into a small number of identifiable events, not scattered noise:

| Window | Symbols affected | Days | Note |
|---|---|---|---|
| 2014-06-11 to 06-13 | Energy, metals, grains | 3 | **Matches F3's already-known "reduced quality" window exactly** — independent cross-validation via a completely different method (gap audit vs. Databento's own quality flag). |
| 2014-09-23 to 09-25 | Energy, metals, grains | 3 | **New.** Data present and normal-looking (volume from the tens of thousands to hundreds of thousands for liquid contracts) on 2014-09-22 and 2014-09-26, the trading days immediately before and after — the 3-day absence is total and real, not a partial/degraded-quality issue like F3. Cause not established. |
| 2014-12-31 | Metals only | 1 | New Year's Eve; plausibly a metals-specific closure, not independently confirmed. |
| 2020-02-28 | Nearly all symbols | 1 | New. Immediately precedes the March 2020 COVID volatility period; noted, not interpreted further. |
| 2012-02-06 to 02-10 | **Livestock only (LE, HE, GF)** | 5 | **New, largest single finding.** A full trading week — confirmed via direct inspection that zero `ohlcv-1d` rows exist for any of the three livestock roots across this entire window, while energy/metals/grains traded normally throughout. Livestock-specific, total, and the longest gap found. Cause not established. |
| 2014-06-12 | Livestock only | 1 | Livestock's own version of the June 2014 window, one day offset from the 06-11/06-13 window seen elsewhere. |

**Proposed handling (not implemented this session, per scope).** The 2014-09-23/09-25 and 2012-02-06/02-10 windows are new, real, and unexplained — Phase 1b should treat them the same way F3's window is already flagged to be treated (caution in any settlement-based computation touching them; consider flagging or excluding if influential on a specific roll/carry calculation), pending further investigation into cause. Method and full per-symbol counts saved to `_carry-research-workspace/f4_gap_audit_final.csv` (workspace, not committed).

### KE entry-date cross-check (via `definition`, a fourth independent method)

`definition`'s own `activation` field shows KE contracts existing in CME's systems as early as **2012-04-26** — well before any KE contract actually traded. This is expected and is a different concept from the pre-registration's symbol-entry rule: `activation` marks when an instrument is *creatable/listed*, not when it has real, tradeable price data. `ohlcv-1d`'s first real KE outright record remains **2013-12-16**, now confirmed a fourth time (Phase 0 probe, session 1's `ohlcv-1d` audit twice, and now cross-checked against the date-aware `definition` join) — this is the correct entry date under `PREREGISTRATION.md` §2 ("the first month-end where its carry signal is computable from available data"), and is unaffected by this finding. Noted for completeness, not a new open item.

### §1, §2, §5 (settlement coverage, OI coverage, settlement spot-checks) — still BLOCKED

Unchanged from the original report's reasoning: these require the `statistics` schema (settlement price, open interest), which has not finished processing server-side (see §0 above). No settlement value, open-interest figure, or spot-check has been performed against real data in this addendum.

### §7 Updated findings register

| ID | Severity | Status | Finding | Resolution / handling |
|---|---|---|---|---|
| F1 | High | **RESOLVED** | Parent symbology mixes outright and spread/combo instruments. | Field-based filter (`instrument_class`) confirmed correct across the complete corpus; final date-aware split is 20.91% outright / 79.09% spread. |
| F2 | Medium | **RESOLVED** | Zero/negative-close rows in the naive "outright" set. | Under the corrected filter, exactly 1 row remains (2020-04-20, CLK0, the well-known May-2020-WTI negative-price episode). Verdict: KEEP with citation. |
| F3 | Low / informational | Unchanged (confirmed, not an anomaly) | June 2014 degraded-quality window (2014-06-11 to 13) has data present, not missing. | Independently cross-validated by this session's F4 gap audit (same window falls out as a residual cluster). Treat with caution in Phase 1c settlement-based computation, as originally proposed. |
| F4 | Informational / limitation | **RESOLVED (materially deeper)** | Pooled trading-day gap analysis was an eyeball check only. | Proper per-symbol layered audit (Sunday-session difference, then US holiday calendar) leaves a 99-symbol-day genuine residual, clustering into 6 identifiable windows. Two windows (2014-09-23/25, 2012-02-06/10) are newly identified and unexplained; proposed handling: flag/exclude if influential in Phase 1c, same treatment as F3. |
| F5 | Operational | **Partially resolved** | `statistics`/`definition` did not finish pulling in session 1. | Mechanism fixed (batch-job API replaces synchronous streaming): `definition` now fully delivered (5,031 files, zero failures). `statistics` submitted and billed, still processing server-side; ETA cannot be responsibly stated (see §0). A second, unrelated mechanism problem (bulk download of the completed `definition` job itself hit a 504) was found and fixed this session (per-file download with retry/resume). |
| F6 | **High** | **RESOLVED (guarded in code)** | `instrument_id` is reused across this dataset's 16-year history — ~20% of outright instrument_ids (668/3,353) were also assigned to a different, usually non-outright, instrument at another point in time. A static cross-schema join by instrument_id silently misclassifies rows. | `src/instrument_filter.py::outright_instrument_ids()` now raises `ValueError` on multi-date input; tests added. All F1/F2 numbers in this addendum use a proper date-aware join. Confirmed example: instrument_id 4948 (ZL spread → PL spread → PL outright PLU5 → PL spread). |
| — | Confirmed (not an anomaly) | Unchanged | KE's outright entry date confirmed a 4th time (via `definition`'s date-aware join), exactly 2013-12-16. `definition`'s `activation` field (2012-04-26 for KE's earliest contract) is a distinct, earlier concept (contract existence, not tradeable data) and does not change the entry-rule date. | N/A. |
| — | Blocked (not a design/guardrail issue) | Unchanged | Settlement coverage (§1), OI coverage (§2), settlement spot-checks (§5) require `statistics`, still processing server-side. | Resume in the next session: poll `GLBX-20260710-E8YMQQJMA7` via `scripts/phase1a_batch_poll_download.py` (already updated with resumable, per-file download logic this session, ready to use as soon as the job reaches `state="done"`). |

---

## Ledger / balance reconciliation (this addendum)

No new REAL SPEND this session beyond the batch-job submissions already logged (`docs/samples/COST_LEDGER.md`, "Phase 1a follow-up — batch job submission" section): confirmed cumulative $93.379095 (ohlcv-1d $44.643947 + 4 confirmed statistics chunks $2.720535 + statistics batch $20.757709 + definition batch $25.256725), worst-case $96.189822 if the 3 deleted ambiguous partial-transfer chunks were in fact separately billed. Both figures remain comfortably under the $100 `CUMULATIVE_CEILING`. Downloading the completed `definition` job (5,031 files, multiple attempts due to the bulk-download 504) incurred no additional charge — download is free regardless of attempt count, per the SDK's own billing model.

**POST_PULL_BALANCE is still pending Aaron's manual portal check** — deferred again, since `statistics` has not finished and a true "post-pull" balance read is only meaningful once both schemas are fully delivered. **Reminder, unchanged from the original report: restore the Databento portal's monthly spending limit to $20 once the corpus pull work is actually finished** — not yet, since `statistics` is still in flight.
