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

---

## Addendum — 2026-07-11, Phase 1a Completion (statistics landing + final QA close-out)

**Status change: PARTIAL → substantively complete.** `statistics` landed cleanly (5,026 files, zero failures) via the same per-file batch-download mechanism used for `definition`. Settlement and OI coverage, the OI roll-rule readiness table, and settlement spot-checks are now unblocked and completed below. The one item this addendum cannot close is Step 2's balance reconciliation — see that section for why.

### §0 update — corpus pull status: complete

| Schema | Status |
|---|---|
| `ohlcv-1d` | Complete (unchanged). |
| `definition` | Complete (unchanged from the prior addendum): 5,031 per-day files. |
| `statistics` | **Complete.** Batch job `GLBX-20260710-E8YMQQJMA7` reached `state="done"`; downloaded via the proven per-file retry/resume mechanism — 5,026 data files, **zero failures on the first attempt** (unlike `definition`'s bulk-download 504, no equivalent problem recurred for `statistics`). No new charge: download is free, cost was incurred at `submit_job()` time ($20.757709, already logged). |

**Single-provenance retirement (Step 1.3).** The 4 confirmed-billed, session-1 yearly `statistics` chunks (`docs/samples/COST_LEDGER.md` rows 46/49/51/54) are moved — not deleted — to `DATA_DIR/_superseded/`, checksummed before the move (`data/MANIFEST.md`'s new "Superseded" section). `src/data_loader.py` gained `load_dbn_partitioned(schema)`, which resolves only `DATA_DIR/{schema}/*.dbn.zst` — the batch-delivery directory — and never `DATA_DIR/_superseded/` or any loose `DATA_DIR/{schema}_*.dbn.zst` file. This is a structural guarantee, not a convention: the retired chunks are no longer even in a path this function's glob can reach, so mixed-provenance loading is prevented by construction, verified by inspection of the function's own restricted glob pattern.

### Settlement/OI field identification (empirical, not assumed)

The `statistics` schema's `stat_type` field is not self-documenting from the column names alone (`price`, `quantity`, `stat_type`, `update_action`, `stat_flags`). Per the same F1-ruling discipline (verify empirically, never trust memory of a vendor spec), the two `stat_type` values this study needs were identified from the data itself, not looked up:

- **Settlement price → `stat_type == 3`.** Verified conclusively: CLK0 (May 2020 WTI) on 2020-04-20 has three `stat_type=3` rows, all `price = -37.63`, the last (21:43:42 UTC, `stat_flags=3`, presumably the final/corrected publication) matching the historic, publicly-documented negative WTI settlement to the cent (see the spot-check section below for citations).
- **Open interest → `stat_type == 6`.** Identified by elimination and shape: exactly one `stat_type=6` row per instrument per day, quantity-valued (never the `price` field), and its trajectory across consecutive days is smooth and monotonic in a way consistent with pre-expiry OI decay — e.g. CLK0's `stat_type=6` quantity fell 1,122,149 → 775,120 → 785,478 → 544,797 → 350,942 → 240,628 across 2020-04-13 through 04-20 (expiry 04-21), the expected shape as holders roll out of an expiring contract. A second, superficially similar single-row-per-day quantity stat (`stat_type=9`) tracks much closer to `ohlcv-1d`'s own `volume` field for the same contract/dates and was ruled out as OI on that basis — it is very likely a cleared-volume statistic, though this study only needed to positively identify OI, not exhaustively decode every `stat_type` value.

### Step 2 — Ledger reconciliation: **NOT COMPLETED, POST_PULL_BALANCE not supplied**

This governing prompt's own REQUIRED INPUT block carried `POST_PULL_BALANCE = <Aaron fills from the portal Billing page>` verbatim — the placeholder, not a real figure. Per this project's standing rule against fabricating data, the confirmed-vs-worst-case ambiguity is **left open**, exactly where the prior addendum left it:

- Confirmed cumulative: **$93.379095**
- Worst-case cumulative (if the 3 deleted "Response ended prematurely" chunks were in fact billed): **$96.189823**
- Ambiguity: **$2.810727**, across 3 chunks: 2011–2012 ($0.790831), 2014–2015 ($0.758321), 2017–2018 ($1.261575)

**What's needed to close this:** Aaron's current Databento portal balance. $125.00 (the pull's starting balance) minus that figure is the ground-truth total spend; compared against the two figures above, it resolves the ambiguity exactly (a value near $93.38 means none of the 3 were billed; near $96.19 means all 3 were; anything between means a partial subset was). **This is a genuine open item, not a rounding formality — it is off by up to $2.81, and Aaron is the only source for the number that closes it.**

**Monthly limit.** This governing prompt states Aaron has restored the Databento monthly spending limit to $20 as his own manual action. That action was not performed by this session (never in scope) and is recorded here as stated, not independently verified — **Aaron, please confirm this was actually done**, since the $125 setting was for the corpus pull specifically and has no reason to remain elevated now that both schemas are delivered.

### §1 — Settlement coverage per outright contract: RESOLVED

Joined the corrected, date-aware outright `ohlcv-1d` population (941,928 bars) against the settlement panel on `(date, instrument_id)`:

- **9,011 bars without a matching settlement value (0.957%).**
- Concentrated in energy/metals (CL 1.62%, GC 1.70%, HG 1.49%, HO 1.33%, PA 1.86%, PL 1.89%, RB 1.50%, SI 1.71%), near-zero in grains/livestock/KE (all ≤0.24%).
- Per-contract detail (1,770 unique traded outright contracts) saved to `_carry-research-workspace/settlement_coverage_per_contract.csv` (workspace, not committed — reproducible). Worst individual contracts are all thin, far-dated PL/GC/PA listings with small sample sizes (20–140 bars, up to ~7% missing) — consistent with genuinely low trading activity on those specific contract-months, not a systematic defect.
- Availability windows: every symbol's settlement coverage spans its full `ohlcv-1d` trading window (2010-06-06/07 through 2026-06-30, KE from 2013-12-16) — no symbol has a shortened settlement window relative to its trading window.

### §2 — OI coverage → roll-rule readiness table: RESOLVED (prominent, required Phase 1b input)

**Method.** For each symbol and trading day, take the two nearest-expiry outright contracts that actually traded that day (the front/next pair the OI-crossover rule would compare) and check whether both have a matching `stat_type=6` value. Days where fewer than 2 contracts traded at all are excluded from this check (there is no roll decision to make — not an OI gap, see the PA investigation below). Remaining gap days were then cross-referenced against the same computed US holiday calendar used in F4, since CME does not republish settlement/OI on exchange holidays even when a thin electronic bar prints (confirmed: the initial gap-date list matched the holiday calendar almost exactly for the energy/metals complex).

| Symbol | First trading day (t−1 OI usable) | Holiday-explained gaps | Unexplained gaps | Last unexplained gap | Strict "zero-exceptions-ever" readiness date |
|---|---|---|---|---|---|
| CL | 2010-06-06 | 93 | 32 | 2026-01-04 | 2026-01-05 |
| GC | 2010-06-06 | 93 | 35 | 2026-01-04 | 2026-01-05 |
| GF | 2010-06-07 | 5 | 2 | 2021-06-28 | 2021-06-29 |
| HE | 2010-06-07 | 7 | 1 | 2018-02-26 | 2018-02-27 |
| HG | 2010-06-06 | 92 | 32 | 2026-01-04 | 2026-01-05 |
| HO | 2010-06-06 | 92 | 33 | 2026-01-04 | 2026-01-05 |
| KE | 2013-12-16 | 0 | 1 | 2018-02-26 | 2018-02-27 |
| LE | 2010-06-07 | 7 | 1 | 2018-02-26 | 2018-02-27 |
| NG | 2010-06-06 | 93 | 32 | 2026-01-04 | 2026-01-05 |
| PA | 2010-06-06 | 73 | 171 | 2026-02-13 | 2026-02-15 |
| PL | 2010-06-06 | 88 | 176 | 2026-06-11 | 2026-06-12 |
| RB | 2010-06-06 | 92 | 34 | 2026-01-04 | 2026-01-05 |
| SI | 2010-06-06 | 93 | 53 | 2026-01-04 | 2026-01-05 |
| ZC | 2010-06-06 | 5 | 3 | 2018-02-26 | 2018-02-27 |
| ZL | 2010-06-06 | 5 | 4 | 2021-06-28 | 2021-06-29 |
| ZM | 2010-06-06 | 5 | 4 | 2021-06-28 | 2021-06-29 |
| ZS | 2010-06-06 | 5 | 3 | 2018-02-26 | 2018-02-27 |
| ZW | 2010-06-06 | 5 | 3 | 2018-02-26 | 2018-02-27 |

**A methodological caveat, stated plainly rather than buried: the rightmost column is close to meaningless as a "readiness" signal, and is included only for literal compliance with this prompt's phrasing.** A strict "first date after which zero exceptions ever occur again" is degenerate for a recurring phenomenon — US exchange holidays recur every year for the life of the sample, so under this definition "readiness" is mechanically pinned to just after the most recent holiday, regardless of how dense and reliable coverage is in between. The far more useful numbers are the two middle columns: **holiday-explained gaps (expected, and already exactly the missing-data case the engine's `t−1` lookup already has to handle — no special-casing needed) and unexplained gaps (a real, if small, residual).** For 15 of 18 symbols the unexplained residual is 1–4 days across the entire 16-year sample. **PA (171) and GF/PL (2, 176) are the exceptions** — PL and PA specifically show a much larger unexplained residual, concentrated in their second-nearest ("next") contract not always receiving a published OI figure even on ordinary trading days. This is consistent with PA/PL being the two thinnest markets in the 18-symbol universe (smallest per-contract trading-bar counts in §1 above), not a data-delivery defect — but it is real, and larger than the other 16 symbols by roughly two orders of magnitude, so it is recorded as a new finding for adjudication (F7 below), not silently absorbed into "holiday-explained."

Full per-symbol unexplained-gap date lists saved to `_carry-research-workspace/oi_roll_rule_readiness_FINAL.csv` (workspace, not committed).

### §5 — Settlement spot-checks against a public source

1. **2020-04-20, CLK0 (May 2020 WTI) = -$37.63 — REQUIRED CHECK. MATCH, exact.** Our data's final `stat_type=3` value for this instrument/date is -37.63, matching the CME-reported settlement cited in the CFTC's own interim staff report and CME Group's public acknowledgment of the event ([CFTC Press Release 8315-20](https://www.cftc.gov/PressRoom/PressReleases/8315-20); coverage confirming -$37.63 via web search). This is also the same value already used as the ground-truth anchor to identify `stat_type=3` as settlement in the first place (see above) — the spot-check and the field-identification are the same empirical fact, which is a stronger form of verification than an independent lookup would have been, not a weaker one.
2. **Silver (SI), late April 2011 — approximate, order-of-magnitude corroboration only, not a precise match.** Public sources (web search) place spot silver's then-record high at approximately $49.50–$49.79/oz intraday around 2011-04-25 to 04-28. Our data's far-dated SI contracts (SIF2/SIF3, Jan 2012/2013) settled at $47.05–$47.55 in the same window — in the right regime (high-$40s) but not the same quantity (spot vs. a specific far futures month) and not the precise front-month figure, so this is disclosed as directional corroboration, not a verified match.
3. **Further checks attempted, honestly disclosed as not obtainable via free public tools this session:** (a) CME Group's own settlements pages return a connection error to automated fetching (`ECONNRESET`), consistent with session 1's identical finding researching the fee schedule; (b) Barchart's historical-prices page renders its data table client-side in JavaScript, so an automated fetch returns the page structure with no populated price data, also consistent with session 1's finding researching third-party fee comparisons; (c) general web search does not index precise historical point-in-time settlement tables for non-headline dates — a search for a recent (2026-06-30) gold settlement returned only current, not historical, quotes; (d) a natural gas comparison around the February 2021 Winter Storm Uri event was investigated and deliberately **not** presented as a check: the extreme prices reported publicly (Henry Hub spot/cash, up to ~$24/MMBtu, even higher at some delivery points) are a physical/cash-market phenomenon at specific delivery hubs during an acute multi-day emergency, while the NYMEX NG futures front-month contract (a monthly-delivery instrument that structurally smooths short-lived regional physical stress) is not the same quantity and would not be expected to show anything close to the same move — our data confirms this (front NG settlement rose only ~3% across the window), which is the *expected*, *correct* divergence, not a discrepancy to explain. Presenting it as a "check" would have invited a false failure reading.

**Net: 1 exact match on the mandatory check, 1 approximate corroboration, and an honest account of why a fuller ~5-check target wasn't reached — consistent with this project's standing practice of disclosing rather than papering over tooling limits (the same CME/Barchart access blocks were already documented in session 1).**

### F4 adjudication — recorded verbatim

**Ruling (dated 2026-07-11, authority: "Aaron + advisor, decided blind to results"):** the 99 residual unexplained symbol-days receive no special handling — materiality is ~0.11%, the engine's missing-data path applies, and the windows (June 2014, Sept 2014, Feb 2012 livestock) are documented and will surface naturally in the §8 per-year diagnostics. Conditional exclusion ("exclude if influential") is rejected as results-conditioned handling.

This **supersedes** the prior addendum's F4 "proposed handling" text (which had suggested conditional flag/exclude treatment) — that proposal is withdrawn, not implemented, per the ruling above.

### Consistency sweep — one denominator, used everywhere

Prior addenda used three different unique-outright-contract counts at different points (3,314 / 3,333 / 3,353), arising from different partial samples and, in one case, an incorrect dedup key. Resolved:

- **3,353 unique outright contracts is the authoritative figure**, used consistently in this addendum and superseding the other two everywhere they previously appeared.
- **A second identity hazard was found and is recorded for completeness, not correction (no prior numbers relied on the flawed version):** deduplicating by `(asset, raw_symbol)` alone — instead of the full `(asset, raw_symbol, instrument_id)` triple — collapses to only 1,936 rows, *fewer* than deduplicating by `instrument_id` alone (3,314). Reason: CME's single-digit-year `raw_symbol` shorthand (e.g. `CLZ6` = December 2016 *or* December 2026) is itself ambiguous across this dataset's 16-year span, a second, independent identity-key hazard alongside F6's `instrument_id` reuse. **Neither field is individually safe; only the full triple is.** `unique_outright_contracts_AUTHORITATIVE.csv` (the flawed asset+raw_symbol-only version) is retained in the workspace only as the evidence trail for this finding, not used anywhere as a real count.

### §7 Updated findings register

| ID | Severity | Status | Finding | Resolution / handling |
|---|---|---|---|---|
| F1 | High | RESOLVED | Parent symbology mixes outright and spread/combo instruments. | Unchanged from the prior addendum — 20.91% outright / 79.09% spread, field-based, date-aware. |
| F2 | Medium | RESOLVED | Zero/negative-close rows in the naive "outright" set. | Unchanged — 1 row (2020-04-20 CLK0), KEEP with citation, now doubly confirmed via the settlement spot-check above. |
| F3 | Low / informational | Unchanged | June 2014 degraded-quality window. | Unchanged. |
| F4 | Informational / limitation | **RESOLVED, adjudicated** | 99-symbol-day genuine residual gap. | **Adjudicated 2026-07-11 (verbatim above): no special handling — materiality ~0.11%, engine's missing-data path applies, conditional exclusion rejected.** |
| F5 | Operational | **RESOLVED** | `statistics`/`definition` did not finish pulling in session 1. | Both schemas fully delivered this session: `definition` (5,031 files), `statistics` (5,026 files), zero failures on the (revised) per-file mechanism. |
| F6 | High | RESOLVED (guarded in code) | `instrument_id` reuse (~20% of outright contracts). | Unchanged — guarded in `src/instrument_filter.py`, tests added. |
| F7 | **Medium — NEW, for adjudication** | OPEN | PA and PL show a materially larger unexplained OI-gap residual (171 and 176 symbol-days respectively) than the other 16 symbols (1–4 days each), concentrated in their second-nearest ("next") contract not always receiving a published OI figure even on days it traded. Plausibly explained by PA/PL being the thinnest markets in the universe, but not independently confirmed as benign. | **Not resolved here, per Step 4's instruction.** Options for Aaron + advisor to adjudicate: (a) treat identically to F4 (engine's missing-data path, no special handling); (b) a PA/PL-specific fallback rule if the roll rule's OI-crossover comparison hits a missing value for these two symbols specifically; (c) something else. Full date lists in `_carry-research-workspace/oi_roll_rule_readiness_FINAL.csv`. |
| F8 | **Low — NEW, informational** | Recorded, no action needed | A second `raw_symbol`-collision identity hazard (CME's single-digit-year shorthand is ambiguous across the 16-year sample) exists alongside F6's `instrument_id` reuse — see the consistency-sweep section above. | No code currently deduplicates by `raw_symbol` alone (the engine always carries `instrument_id` alongside it), so this has not caused any wrong number in this project. Recorded so any future code that's tempted to key on `raw_symbol` alone knows why not to. |
| — | Blocked | **RESOLVED** | Settlement coverage, OI coverage, settlement spot-checks required `statistics`. | Complete — see §1, §2, §5 above. |
| — | **Open, non-technical** | **RESOLVED** | Step 2 ledger reconciliation ($93.38 vs. $96.19, a $2.81 ambiguity). | **Closed 2026-07-11 — see the addendum below.** |

---

## Addendum — 2026-07-11, Phase 1b Step 0 (adjudication record + reconciliation closure)

### F7 roll-rule reading (not a deviation)

**Ruling (dated 2026-07-11, authority: "Aaron + advisor, decided blind to results"):** `PREREGISTRATION.md` §3's roll rule as registered already defines behavior under missing OI — the front switches from `c1` to `c2` at the first `t` such that the crossover condition `OI_{t−1}(c2) > OI_{t−1}(c1)` is *observed true*. Missing `t−1` OI for either contract means that condition is unobservable that day, so it cannot be observed true, and the current front is held. **This is a reading of the registered rule, not a deviation from it** — no `DEVIATIONS.md` entry applies to this point. `src/roll.py::compute_front_contract_series()` was already written this way in Phase 1a (the crossover `if` only advances `current_idx` when both lagged OI values are non-null *and* the inequality holds; any other case — including either value being `NaN` — falls through to holding the current front), independently of this ruling; this addendum confirms that existing behavior is the intended one rather than an accidental match.

Per-symbol rule forks (e.g. a volume-based OI fallback specifically for PA/PL) and universe amputation (dropping PA/PL from the study) were both considered in adjudicating F7 and rejected — see the `DEVIATIONS.md` entry dated 2026-07-11 for the rejected-alternatives record and the one diagnostic that was adopted in their place (item 11, ex-PA/PL primary-series recomputation, non-gating).

### Reconciliation closure

Aaron's Databento portal shows **$29.67 remaining credits**. Against the $125.00 pull-approval balance, **total corpus acquisition cost = $95.33**, inside the $100 `CUMULATIVE_CEILING`.

This closes the $2.81 ambiguity left open in the prior addendum: $93.379095 (confirmed) + the two premature-termination chunks (2011–2012, 2014–2015 — the client-side "Response ended prematurely" errors, as distinct from the 2017–2018 chunk's deliberate kill) billed for delivered bytes only ≈ **$1.95**, not their full quoted amounts, giving $93.379095 + $1.95 ≈ **$95.329095**, matching the balance-delta figure to the cent. The 2017–2018 chunk (killed client-side mid-transfer, not a server/network interruption) was not billed at all. **Card charged: $0.00** — this was a pre-funded credit balance, not a card transaction. **Monthly spending limit confirmed restored to $20** by Aaron.

Final, closed cost table for this project's Phase 1a corpus acquisition:

| Component | Amount (USD) |
|---|---|
| Confirmed REAL SPEND (ledger rows, unambiguous) | 93.379095 |
| 2011–2012 + 2014–2015 chunks, delivered-bytes-only billing | ≈1.95 |
| 2017–2018 chunk (client-killed, not billed) | 0.00 |
| **Total** | **95.33** (portal-confirmed) |
| Ceiling | 100.00 |
| Headroom (unused) | 4.67 |

### Spot-check relabel

The 2020-04-20 CLK0 = -$37.63 check (§5 of the prior addendum) is relabeled: it is the **field-identification anchor** for `stat_type=3`, not an independent spot-check — a value used to *identify* what a field means cannot also serve as independent confirmation *of* that identification; that would be circular. The independent corroboration for the settlement/OI extraction pipeline is: (a) `stat_type=6`'s pre-expiry OI-decay shape (a structural property unrelated to any single price value); (b) the SI, April 2011 approximate check; (c) the overall coverage-consistency results in §1/§2 (settlement and OI both present for >98% of outright trading bars, with the residual concentrated in explicable thin/holiday cases) — internal consistency across ~941,928 independent bars is itself meaningful corroboration, distinct from anchoring a single field's identity to a single famous value.

---

## Addendum — 2026-07-12, Phase 1b Step 0 continued (F9/F10 resolved; F11 opened for adjudication)

**Scope of this addendum.** Two contract-identity bugs (F9, F10) found while building the Phase 1b pipeline are recorded here as RESOLVED, code-correctness fixes — per the governing Phase 1b Riders, these are not `DEVIATIONS.md` entries (no design choice was made; the fix restores the frozen pre-registration's intended behavior on previously-corrupted input; the earlier next-settle ≤ 0 → NaN ruling remains ratified and unchanged). A third, structural finding (F11) is opened for adjudication: fixing F9/F10 did not resolve most of the roll rule's stuck-front problem, and the residual is a genuine design limitation, not a further bug. **No `roll.py` change is made in this addendum, and no premise-test run happens here** — this is characterization only.

### F9 — RESOLVED: raw_symbol format instability within a single contract's life

A single real contract's `raw_symbol` representation can itself change partway through its own listed life — not a collision between two different contracts (that is F8), but the *same* `instrument_id` reporting a different symbol string over time. Confirmed example: `instrument_id 551735` (a CL contract expiring 2019-05-21) is recorded as `raw_symbol "CLM19"` on its first 2 listed days (2010-11-04/05) and `"CLM9"` for the remaining ~9 years through expiry. Caught via an implausible ~49% held-front missing-settlement rate concentrated from 2019 onward — `raw_symbol + instrument_id` as originally keyed silently split this one real contract's settlement/OI history across two spurious `_contract_key` columns.

**Fix.** `raw_symbol` dropped from `_contract_key` entirely — the key is now `instrument_id + "__" + expiration.date()` (see F10 for why the date, not the full timestamp). `src/pipeline.py::build_outright_panel()`.

**Tests.** `test_F9_build_outright_panel_unifies_a_contract_whose_raw_symbol_format_changes` (synthetic fixture, `tests/test_pipeline.py`), asserting the unified key yields one continuous OI history across the format change.

### F10 — RESOLVED: expiration time-of-day correction fractures contract identity

A single real contract's `expiration` field can be corrected mid-life at the **time-of-day** level while the calendar date stays fixed. Confirmed example: `instrument_id 827180` (a KE contract) is recorded with `expiration "2014-09-12 18:15:00"` for its first 186 listed days (2013-12-15 to 2014-07-18) and `"2014-09-12 17:01:00"` for its remaining 48 days (2014-07-20 to 2014-09-12) — same calendar date throughout, a mid-life metadata correction to the exact time only.

Keying on the full timestamp (as the pipeline did immediately after the F9 fix, before this one) split this one contract's OI history into two fragments. The fragmentation happened to land exactly where an adjacent contract's roll should have occurred, so `roll.py`'s crossover condition — correctly implementing the F7 hold-on-missing ruling — could never observe both sides of the crossover simultaneously again: front froze permanently on the now-expired prior contract for the rest of the sample. **This is corrupted input, not a flaw in `roll.py` or the F7 ruling** — F7's hold-on-missing behavior is confirmed to have behaved exactly as specified once given a correctly-unified contract identity; it required no change.

**Confirmed via direct empirical verification before any fix was proposed:** unifying instrument_id 827180's two fragments restores 173 real, overlapping OI dates against the contract it should have rolled into.

**Fix.** `expiration` truncated to its calendar date (`.dt.date`) in `_contract_key`, dropping the time-of-day component. Verified this does not reintroduce F6 (genuine `instrument_id` reuse across different real contracts): every confirmed F6/F10 case differs in expiration by months to years, never by a same-day time-correction, so a date-level match remains a safe disambiguator.

**Tests.** `test_F10_build_outright_panel_unifies_a_contract_whose_expiration_time_of_day_is_corrected` (synthetic fixture proving the unified key yields one continuous OI history) and `test_genuine_F6_reuse_with_different_expiration_dates_does_not_unify` (the required negative-case fixture, proving a same-`instrument_id`-different-date pair stays separate) — `tests/test_pipeline.py`.

### Contract-key unification audit (required by the Phase 1b Riders)

`src/pipeline.py::audit_contract_key_unification()` groups every outright `(instrument_id, asset)` pair with more than one distinct expiration timestamp, and classifies it "unify" (all timestamps share one calendar date — F9/F10-style drift) or "keep_separate" (timestamps span different calendar dates — genuine F6 reuse). Grouped by `(instrument_id, asset)`, not `instrument_id` alone: real data surfaced `instrument_id 60` reused across two *different assets* entirely (SI and GF) — an even more extreme case of F6 than same-asset reuse, reported separately as `cross_asset` rather than forced into either bucket.

| Category | Count |
|---|---|
| `unify` (F9/F10-style same-contract drift, merged) | 25 |
| `keep_separate` (genuine F6 reuse, same asset, different dates) | 7 |
| `cross_asset` (instrument_id spans >1 asset entirely) | 27 |

Every fragment pair in `unify` was asserted to share the same `asset` (sanity check: unification never merges data across different commodities). Illustrative `unify` example beyond F9/F10 above: `instrument_id 66` (PL) shows `expiration "2021-11-26 17:05:00"` for 6 rows (2021-11-21 to 11-26) and `"2021-11-26 18:05:00"` for 84 rows (2021-08-15 to 11-19) — the same time-of-day-correction pattern as F10, recurring at the same November 2021 expiry across multiple symbols (also seen at instrument_ids 1079/PA, 1612/GC, 2303/HG, 33349/SI), consistent with a single exchange-side metadata correction batch rather than independent incidents. Illustrative `keep_separate` example: `instrument_id 335` (PA) shows two genuinely different contracts, expiring `2020-05-27` and `2023-07-27` — three years apart, correctly kept separate.

**Reproduction of the informal pre-fix estimate.** An earlier, non-audit exploratory check (grouped by `instrument_id` alone, not asset-aware) had estimated "~25 unify / ~33 keep separate." The proper audit reproduces `n_unify = 25` exactly. The non-unify side is `7 + 27 = 34` against the informal `33` — a 1-count difference, attributable to the informal check's grouping: not being asset-aware, it could not distinguish `cross_asset` reuse (27 cases, e.g. instrument_id 60 spanning SI and GF) from same-asset-different-date reuse (7 cases) — both present identically as "an instrument_id with multiple expirations" under an `instrument_id`-only grouping. Per the governing riders ("the measured 25-unify/33-keep-separate split must be reproduced by the audit or the discrepancy explained"): `n_unify` reproduces exactly, and the 1-count gap on the other side is structurally attributable to the informal check's non-asset-awareness, not a new, unexplained inconsistency.

### F11 — OPEN, for adjudication: §3's next-listed crossover deadlocks on listed-but-illiquid serials

**Summary.** Fixing F9/F10 did not resolve most of the roll rule's stuck-front problem. Of 18 symbols, 13 show at least one episode where the permanent tripwire (`assert_front_not_past_expiry`) fires; 11 of those are **permanent** (the front never moves again for the rest of the 16-year sample). This is a structural limitation of §3's roll rule as registered, not a data-corruption bug: **F7's hold-on-missing ruling is confirmed to behave correctly on this cleaned-up data and is not implicated.** The root cause is that the rule's state machine only ever compares the current front to the single immediately-next contract in `listed_sequence` — it has no mechanism to look past that contract if its own crossover never fires, even when a later contract's OI is perfectly healthy and observable throughout.

#### Dead-serial map

CME lists many more contract-months per symbol than actually carry material open interest. Peak OI by listed month, aggregated across the full 16-year sample (`_carry-research-workspace/dead_serial_map.csv`):

- **CL, HO, RB, NG** (energy): materially liquid in **all 12** listed months (peak OI in the hundreds of thousands to millions every month). No dead serials.
- **GC, SI, HG** (COMEX metals): a sharp bimonthly pattern — even months (Feb/Apr/Jun/Aug/Oct/Dec) carry hundreds of thousands of peak OI; odd months carry only thousands or less. Matches the well-known COMEX principal-vs-serial-month convention for these products.
- **PL**: only 4 genuinely liquid months (Jan/Apr/Jul/Oct, tens of thousands peak OI); the other 8 are near-zero (hundreds or less).
- **PA**: only 4 liquid months (Mar/Jun/Sep/Dec, tens of thousands); the other 8 are near-zero (~100–500).
- **Grains** (ZC/ZS/ZW/ZM/ZL/KE): only 5–8 specific months are listed **at all** — no other months appear in the registry, not even as thin serials.
- **Livestock** (LE/HE/GF): 6–8 listed months with a liquidity gradient rather than a sharp liquid/dead split; no month is literally zero.

This directly explains most of the stuck-front episodes below: the roll rule's single candidate is, for several symbols, structurally very likely to be a month the real market never trades.

#### Episode classification

Every stuck-past-expiry episode across all 18 symbols (16 total), classified per the requested taxonomy (`_carry-research-workspace/stuck_episodes_classified.csv`):

| Pattern | Definition | Count | Symbols |
|---|---|---|---|
| (a) dead-serial deadlock | next-listed contract never gains material OI | 10 | GF, HO, PA, PL, RB, ZC, ZL, ZM, ZS, ZW (1 each) |
| (b) overlap-never-crosses | both front and next observable, but next's OI never exceeds front's before next's own window ends | 1 | HE |
| (c) narrow/absent OI window | next has no overlapping OI-observation window with front at all | 0 | — |

All 11 of these episodes are **permanent** — held from first stuck date through sample end (2026-06-30), 2,706 to 5,785 days. 8 of the 10 pattern-(a) cases have the next candidate's peak OI at **exactly 0.0** ever recorded (HO, RB, ZC, ZS, ZW, ZM, ZL, GF); the remaining 2 are de minimis but not literally zero (PL: 27; PA: 2). This is a natural, not threshold-chosen, split: the single pattern-(b) case (HE) has a next-candidate peak OI of 2,314 — two orders of magnitude above the pattern-(a) cluster — so the (a)/(b) boundary falls out of the data rather than an arbitrary cutoff.

**HE detail (pattern b, "where did the market's OI go").** HE's front got stuck on the contract expiring 2011-04-14; the immediately-next candidate (expiring 2011-05-13) reached a peak OI of 2,314 but never exceeded the stuck front's own OI during their overlap window. Scanning forward through `listed_sequence`, the first later contract whose peak OI clearly exceeds the stuck front's is the one expiring **2011-12-14** — about 8 months later. HE's dead-serial map shows May is its thinnest listed month (peak OI as low as ~2,700 in some years) but not literally dead like PL/PA's off-quarter months — consistent with a genuine, if severe, liquidity trough rather than an entirely unlisted-in-practice month.

**A fourth, minor pattern found and characterized (outside the requested a/b/c taxonomy): transient single-day expiry grazes.** 5 further episodes (2 in NG, 3 in HG) trip the tripwire for **zero days past expiry** and are **not permanent** — in every case the front rolls cleanly to a high-OI successor (peak OI 1,195 to 187,328) the very next trading day. Root cause: several contracts' recorded `expiration` timestamp falls late in the trading day (17:00–19:30), so the front is technically still "current" through the calendar date immediately following before the t-1 OI crossover completes on the next available trading day — a timestamp/date-granularity artifact of the tripwire's date-only comparison, not a deadlock. Reported for completeness since the tripwire technically fires; not counted among the 11 permanent episodes and not evidence of a new bug.

#### Counterfactual "multi-candidate / OI-max roll" diagnostic (read-only; `src/roll.py` unmodified)

Standalone script (`_carry-research-workspace/step_c_counterfactual_roll.py`), never executed against `src/roll.py` and producing roll dates only — no carry, no returns. Candidate rule, strictly t-1 OI throughout (same look-ahead-safety mechanism as the production rule; "multi-candidate / OI-max," never "lookahead" — that term is reserved for temporal leakage, which is untouched):

> front(t) = argmax OI_{t-1} among outrights with expiry >= current front's expiry, ties -> earlier expiry, hold-on-missing unchanged.

**Residual stuck fronts (requested: expect zero).** 17 of 18 symbols are completely clean. The 18th (NG) technically trips the tripwire once — and it is the **identical** transient graze already characterized above (contract `192047__2010-06-28`, held through 2010-06-29, rolling cleanly to a 187,328-peak-OI successor on 2010-06-30), verified by direct inspection of the counterfactual series to resolve in exactly the same single day as under the current rule. **Zero genuine (multi-day or permanent) residual stuck fronts under the counterfactual rule.**

**Rolls/year vs known market cycles (sanity check).** The counterfactual rule's roll cadence recovers to plausible, cycle-consistent levels for every symbol that was catastrophically under-rolling under the current rule:

| Symbol | Current rule | Counterfactual | Known/implied cycle |
|---|---|---|---|
| PL | 0.12/yr (2 rolls in 16 years) | 4.11/yr | Quarterly (4 liquid months) |
| PA | 0.19/yr (3 rolls in 16 years) | 4.05/yr | Quarterly (4 liquid months) |
| HO | 1.87/yr | 11.95/yr | Monthly (12 liquid months) |
| RB | 6.41/yr | 12.01/yr | Monthly (12 liquid months) |
| HE | 0.37/yr (6 rolls in 16 years) | 7.10/yr | ~8 listed months, liquidity gradient |
| GF | 1.00/yr | 7.66/yr | ~8 listed months |
| GC, SI, HG | 6–7/yr | ~5/yr | Bimonthly (6 liquid months) |
| ZC, ZS, ZM, ZL, ZW | 0.6–1.7/yr | 4.2–5.2/yr | 5–8 listed months |
| CL, NG, KE | 12.0 / 12.0 / 5.0/yr (unchanged) | identical | Already correct under current rule |

Full per-symbol table in `_carry-research-workspace/counterfactual_roll_summary.json`.

**Roll-date diffs vs current rule, where the current rule was not stuck.** For 7 symbols (CL, HO, RB, NG, ZW, KE, HE — restricted to each symbol's own pre-deadlock window where applicable), the two rules agree **exactly**, zero differing dates. For the remaining 11, the counterfactual rule diverges even before the current rule's own eventual deadlock — because it sometimes rolls a few days earlier, and in several cases skips an intermediate thinly-traded serial contract entirely rather than briefly visiting it. Illustrative example (PL, its cleanest short window): the current rule rolls June-2010 → July-2010 (2010-06-07) → **August-2010** (2010-07-23, where it then gets permanently stuck, matching the pattern-(a) episode above); the counterfactual rolls June → July (same date) → **October-2010 directly** (2010-06-30), skipping both the near-dead August and September serials in one step — exactly matching PL's known Jan/Apr/Jul/Oct quarterly liquid cycle. This is a genuine behavioral difference from the current rule, not just a timing shift, and is a design trade-off for adjudication: the multi-candidate rule can skip a low-but-nonzero-liquidity intermediate contract entirely (as here, and similarly for GC's October 2010 contract, peak OI 39,155 vs neighboring liquid months' 600K–800K) rather than passing through it as a brief "front" state the way the current rule does.

#### Serial-settlement quality (informs whether carry.py's "next" needs the same treatment)

For every outright contract's own active window (first appearance through its own expiration), fraction of days with a settlement present and staleness evidence (zero-change run lengths), split by whether the contract's peak OI is below (`dead_serial`) or above (`liquid`) a 1,000-contract threshold (`_carry-research-workspace/serial_settlement_quality.csv`, 3,335 contracts):

| Group | n | Mean fill fraction | Median fill fraction | Mean stale fraction | Median stale fraction |
|---|---|---|---|---|---|
| liquid | 2,502 | 0.9715 | 0.9724 | 0.1903 | 0.1845 |
| dead_serial | 833 | 0.9477 | 0.9715 | 0.2061 | 0.1862 |

**The medians are nearly identical** — the typical dead-serial contract still gets settlement coverage indistinguishable from a liquid one (CME evidently still publishes a daily settlement, real or theoretical, regardless of OI). **The mean is pulled down by a real tail**: the worst dead-serial contracts have next to no settlement data at all — e.g. the four grains contracts expiring 2014-07-14 (ZC 214367, ZS 475373, ZM 537239, ZL 344868 — the same four-way cluster underlying 4 of the 10 pattern-(a) episodes above) each show only 2–3 settlements across a 1,265-day nominal window (fill fraction 0.0017–0.0024). These are already exactly the case the existing next-settle-missing-or-≤0-is-NaN ruling (`DEVIATIONS.md`, 2026-07-11) was built to handle — a "next" this sparse would produce NaN carry on nearly every date regardless of any roll-rule change.

**A distinct, separately-flagged residual: staleness, not just coverage.** ZW's dead-serial contracts show a mean stale fraction of **0.6029** (60% of day-to-day settlement changes are exactly flat) vs 0.1947 for ZW's own liquid contracts — a gap far larger than any other symbol's. A settlement that is *present* but frequently a carried-forward copy would pass the existing missing-value NaN guard untouched (it is not missing) while still feeding an economically stale price into the carry formula's denominator. This is flagged as a genuine, symbol-specific residual concern for the same adjudication, distinct from the coverage question the existing NaN ruling already addresses.

#### Proposed handling (not implemented this session)

Not resolved here, per the governing instruction. Options for Aaron + advisor to adjudicate, informed by the above:
(a) amend §3's roll rule to the multi-candidate/OI-max design characterized above (or a variant), pre-registered as a dated deviation before any re-run;
(b) keep the current single-candidate rule and instead exclude/flag the 11 permanently-affected symbols or specific date ranges;
(c) something else. Whatever is decided, the serial-settlement staleness finding (ZW in particular) suggests carry.py's "next" selection may need its own, possibly distinct, treatment even if the roll rule itself is amended — these are related but not identical questions.

### §7 Updated findings register

| ID | Severity | Status | Finding | Resolution / handling |
|---|---|---|---|---|
| F1 | High | RESOLVED | Parent symbology mixes outright and spread/combo instruments. | Unchanged — field-based, date-aware, 20.91% outright / 79.09% spread. |
| F2 | Medium | RESOLVED | Zero/negative-close rows in the naive "outright" set. | Unchanged — 1 row (2020-04-20 CLK0), KEEP with citation. |
| F3 | Low / informational | Unchanged | June 2014 degraded-quality window. | Unchanged. |
| F4 | Informational / limitation | RESOLVED, adjudicated | 99-symbol-day genuine residual gap. | Adjudicated 2026-07-11: no special handling. |
| F5 | Operational | RESOLVED | `statistics`/`definition` did not finish pulling in session 1. | Both schemas fully delivered. |
| F6 | High | RESOLVED (guarded in code) | `instrument_id` reuse across different real contracts (~20% of outright contracts). | Guarded in `src/instrument_filter.py`, tests added. |
| F7 | Medium | RESOLVED (reading, not a deviation) | PA/PL show a larger unexplained OI-gap residual. | Adjudicated 2026-07-11: existing hold-on-missing behavior is a correct reading of §3, no fork, no amputation. Confirmed in this addendum to also behave correctly on the F9/F10-corrected data. |
| F8 | Low | Recorded, no action needed | `raw_symbol`-collision identity hazard (CME single-digit-year shorthand). | No code keys on `raw_symbol` alone; recorded for future reference. |
| F9 | Medium | **RESOLVED** | `raw_symbol` format instability within a single contract's own listed life (instrument_id 551735: "CLM19" → "CLM9" after 2 days, same contract for ~9 more years). | Dropped `raw_symbol` from `_contract_key`; key is now `instrument_id + expiration.date()`. Synthetic-fixture test added. |
| F10 | High | **RESOLVED** | `expiration` time-of-day correction mid-life (instrument_id 827180, KE) fractures one contract's OI history, permanently freezing the roll rule once the fracture lands on a real crossover. F7's hold-on-missing ruling confirmed correct on cleaned-up data, not implicated. | `_contract_key` truncates expiration to calendar date. Unification audit: 25 unify / 7 keep-separate / 27 cross-asset (reproduces the informal 25-unify estimate exactly). Tests added, including the required negative-case (genuine F6 reuse does not unify). |
| F11 | High — **NEW, for adjudication** | **OPEN** | §3's roll rule structurally deadlocks whenever the next-listed contract is a listed-but-illiquid ("dead") serial month or its crossover otherwise never fires against a single fixed candidate — 11 of 18 symbols permanently stuck post-F9/F10-fix (10 dead-serial, 1 overlap-never-crosses), 5 further transient single-day grazes (benign, non-permanent). A read-only counterfactual "multi-candidate / OI-max roll" simulator resolves all permanent cases and recovers cycle-consistent roll cadences per-symbol, with zero genuine residual stuck fronts. Serial-settlement quality check finds coverage is typically adequate even for dead-serial contracts (median ≈ liquid), but flags a distinct staleness concern for ZW specifically. | Not resolved here. Dead-serial map, episode census, counterfactual diagnostic, and serial-settlement quality check all complete; full detail in this addendum and `_carry-research-workspace/`. No `roll.py` change made; no premise-test run performed. |
