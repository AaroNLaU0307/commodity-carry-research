# Commodity Carry Premium — A Falsification Study Across 18 CME Futures

[![tests](https://github.com/AaroNLaU0307/commodity-carry-research/actions/workflows/tests.yml/badge.svg)](https://github.com/AaroNLaU0307/commodity-carry-research/actions/workflows/tests.yml)

**Verdict: no confirmable edge in this sample, net of costs.** A pre-registered, falsification-first
test of the commodity carry premium — cross-sectional (H1) and time-series (H2) — on 18 CME futures
across 4 sectors, 2010–2026. Design (universe, definitions, gates, robustness suite) was frozen and
publicly timestamped before any data entered the repo. 0 of 2 primary arms promoted; none of ~30
registered variants approach the gates either.

> 18 CME futures / 4 sectors · 2010-06-07 to 2026-06-30 · settlement-based signals · frozen conservative
> cost table · stationary block bootstrap + DSR + BH-FDR · H1 net Sharpe **−0.003** (95% CI
> **[−0.44, 0.43]**), H2 net Sharpe **−0.126** (95% CI **[−0.56, 0.32]**) · 136 passing tests, synthetic
> fixtures only.

## TL;DR

- **What was tested.** Cross-sectional (H1: rank carry, long top tercile / short bottom tercile) and
  time-series (H2: `sign(carry)` per symbol) commodity carry — 18 CME futures, 4 sectors (energy,
  metals, grains, livestock), 2010-06-07 through 2026-06-30, settlement-price-based signals (never
  last-trade), monthly rebalance, inverse-vol leg weighting and portfolio-level vol targeting inherited
  from a sibling study, and a deliberately conservative frozen cost table (max(1 tick, unavailable
  half-spread) + $2.50/side all-in fee) — `preregistration/PREREGISTRATION.md` §2–§5.
- **Verdicts table:**

  | Arm | Premise (point est.) | Sharpe | 95% CI | BH-FDR | CI excl. 0 | Sharpe≥0.30 | 2×cost>0 | DSR≥0.95 | Promotion |
  |---|---|---|---|---|---|---|---|---|---|
  | H1 (XS) | +0.028489 (NW(3) t=1.465, p=0.143) | −0.0031 | [−0.4417, 0.4287] | FAIL | FAIL | FAIL | FAIL | FAIL | **NOT PROMOTED** |
  | H2 (TS) | +0.000672 (t=0.300, p=0.764) | −0.1255 | [−0.5580, 0.3227] | FAIL | FAIL | FAIL | FAIL | FAIL | **NOT PROMOTED** |

  (`reports/PREMISE_REPORT.md` §"XS premise"/"TS premise"; `reports/PRIMARY_REPORT.md` §"Summary")

- **Headline stats with CIs.** Both arms' 95% bootstrap confidence intervals span zero by a wide margin
  — H1 [−0.44, 0.43], H2 [−0.56, 0.32] (`reports/PRIMARY_REPORT.md`) — and both Deflated Sharpe Ratios
  sit near zero (H1 0.0399, H2 0.0107 against the 0.95 gate, N_trials=14 per `PREREGISTRATION.md` §10).
- **Public timestamp.** The pre-registration was committed and pushed to a public remote before any
  data entered the repository — `PREREGISTRATION.md` §12 step 1, `PUSH_CHECKLIST.md` — the freeze is
  independently verifiable, not merely asserted in a local commit message.

## The arc, short

**Pre-registration** (universe, locked definitions, cost model, gates, robustness suite, NOT-testing
list — `preregistration/PREREGISTRATION.md`) → **data acquisition** (Databento `GLBX.MDP3`, full
checksummed corpus, `data/MANIFEST.md`) → **three invalidated runs**, each caught by an integrity
anomaly and never a result direction (`reports/PREMISE_REPORT.md` §"Run-history disclosure" has the
full trigger/root-cause/fix table for all three) → the **F11 amendment**, adopted under a legitimacy
test explained in full in [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md) → **Run 4**, the
project's first valid computation → **falsification**, evaluated against gates fixed before Run 4 ever
executed.

## Mechanism: why no edge, when the literature finds one

Five candidate mechanisms, each checked against evidence already sitting in the committed reports —
sample-period decay, cost drag, universe width, curve point, and construction choice — plus a
long-leg-vs-short-leg symmetry check. Full table, citations, and verdicts:
**[`docs/MECHANISM_NOTES.md`](docs/MECHANISM_NOTES.md).**

Short version: cost drag and construction choice are directly **contradicted** by the gross-of-cost and
quintile/equal-weight restatements; the curve-point question is **weakly, narrowly suggestive** for H1
alone (the 12-month-deferred variant, `reports/ROBUSTNESS_REPORT.md` item 5); sample-period decay and
universe width remain **genuinely open** — this corpus cannot settle them either way.

## War stories: four exchange-data identity traps, plus the price of look-ahead safety

Full detail, evidence, and fixes in [`docs/DATA_QA_REPORT.md`](docs/DATA_QA_REPORT.md)'s findings
register. Compact version:

- **F1 — spreads hiding in the parent symbology.** Of 4,505,270 raw `ohlcv-1d` rows returned under
  parent symbology, only 20.91% were genuine single-month outrights — the rest were calendar spreads
  and multi-leg combos sharing the same symbol namespace. A naive string filter misses one of the two
  observed combo formats entirely; the fix uses the `definition` schema's own `instrument_class` field.
- **F6 — `instrument_id` is not a stable key.** ~20% of outright `instrument_id`s (668 of 3,353) were
  reused for a *different* real contract at another point in this dataset's 16-year history — including
  one case spanning two different commodities entirely. Any join must be date-aware; never join on
  `instrument_id` alone across dates.
- **F9 — a single contract's own symbol string can drift mid-life.** One real CL contract
  (`instrument_id` 551735) reported as `"CLM19"` for its first 2 listed days and `"CLM9"` for the
  remaining ~9 years — the same contract, not a collision. Caught via an implausible ~49% held-front
  missing-settlement rate before it was understood.
- **F10 — an expiration *timestamp* can be corrected mid-life → F11, a structural roll deadlock.** One
  KE contract's recorded expiration time-of-day changed mid-life (same calendar date). Keying on the
  full timestamp fractured its OI history and froze the roll rule permanently. Fixing the identity key
  exposed a *deeper*, non-bug problem — the registered single-candidate roll rule deadlocks whenever the
  next-listed contract is a real but illiquid ("dead serial") month, affecting 11 of 18 symbols. Resolved
  by a pre-registered amendment (A1/A2, `DEVIATIONS.md` 2026-07-15), validated read-only before adoption.
- **F12 — the one-day tax of never looking ahead.** Because open interest is only known T+1, the roll
  rule always trails the real market's shift by exactly one day. When that shift is abrupt, the just-
  abandoned contract can go completely dark — in *both* `statistics` and `ohlcv-1d` — on the very first
  day it's no longer front. Found 8 times, all on CL, against CL's own ~193 rolls (~4%) — the cost of the
  look-ahead-safe design, not a defect (`docs/DATA_QA_REPORT.md` finding F12).

## Limitations

- **The sample is entirely post-publication / post-financialization (2010–2026).** Every well-known
  early carry papers' sample predates this window; if the premium's strongest years were earlier and it
  has since been arbitraged down or crowded out, this sample cannot see that — see
  `docs/MECHANISM_NOTES.md` row 1.
- **18 CME markets — ICE-listed softs excluded, pre-declared.** Sugar, coffee, cocoa, and cotton were
  excluded before any computation because ICE's history via Databento begins only 2018-12-23 (~7.6
  years), failing this study's 10-year minimum (`docs/DATA_FEASIBILITY_REPORT.md` line 35;
  `docs/DECISION_MEMO.md`: "softs excluded as a pre-declared scope limitation"). LME base metals were
  never in scope. A wider universe (the literature commonly runs 24–35 markets) was not tested — see
  `docs/MECHANISM_NOTES.md` row 3.
- **Front-slope carry definition; the 12-month curve point was tested only as a robustness variant, not
  primary.** `PREREGISTRATION.md` §3 locks the carry definition to front-vs-next; a further-out curve
  point was pre-registered as §8 item 5 specifically so it could be checked without becoming a second
  primary hypothesis — see `docs/MECHANISM_NOTES.md` row 4 for what it showed.
- **Power statement.** From each arm's bootstrap standard error (≈ half the 95% CI width ÷ 1.96: H1 SE
  ≈ 0.222, H2 SE ≈ 0.225 — `reports/PRIMARY_REPORT.md`), and the standard two-sided-5%/80%-power minimum
  detectable effect (SE × 2.8), **this design could reliably confirm a true annualized net Sharpe of
  roughly 0.6 or larger — not the 0.30 the gate itself required.** Put plainly: even a strategy sitting
  exactly at this study's own promotion threshold would have had well under even odds of producing a
  significant result at this sample size. This is a limitation stated with numbers, not an apology — the
  design was powered to catch a large edge, and a large edge is not what commodity carry, on this
  construction, in this sample, turned out to be.

## Read this repo in 5 minutes

1. [`preregistration/PREREGISTRATION.md`](preregistration/PREREGISTRATION.md) (+ its Amendments log at
   the end) — the frozen design, and the two post-freeze amendments (A1, A2).
2. [`reports/PREMISE_REPORT.md`](reports/PREMISE_REPORT.md) — the cheap sign-only gate, and the full
   run-history disclosure (three invalidated runs, why each was invalidated, why none was
   result-motivated).
3. [`reports/PRIMARY_REPORT.md`](reports/PRIMARY_REPORT.md) — the five promotion gates, evaluated.
4. [`reports/ROBUSTNESS_REPORT.md`](reports/ROBUSTNESS_REPORT.md) — all ~30 variants, none gating,
   all reported.
5. [`DEVIATIONS.md`](DEVIATIONS.md) — every departure from the frozen design, dated, before the
   deviating computation ran, with authority and rationale recorded for each.

## Related research

Part of a falsification-first research series applying the same protocol across asset classes and
strategy families:

- [`multi-asset-tsmom-research`](https://github.com/AaroNLaU0307/multi-asset-tsmom-research) - time-series momentum across asset classes, **confirmed** (net Sharpe 0.75, 95% bootstrap CI [0.29, 1.23] excludes zero); XSMOM and four overlay studies falsified under the same gates.
- [`quant-backtest-framework`](https://github.com/AaroNLaU0307/quant-backtest-framework) - multi-instrument SMC price-action study, **falsified** (0/210 cross-instrument BH-FDR across 5 instruments x 42 configs).
- [`orderflow-research-engine`](https://github.com/AaroNLaU0307/orderflow-research-engine) - order-flow footprint signals on BTC/ETH perps, **falsified/null** (0/20 cells survive BH-FDR; 18-month OOS never opened).
- [`spot-mfi-btc-perp-research`](https://github.com/AaroNLaU0307/spot-mfi-btc-perp-research) - spot money-flow signals for BTC perps, base study **falsified** (0/42 BH-FDR); funding-divergence follow-up **inconclusive, leaning falsified**.

The series' base rate is the point: confirmations are earned against the same gates that falsify
everything else.

## Repository layout

- `docs/` — immutable Phase 0/1 snapshots (data feasibility, decision memo, sample audit, data QA
  report and findings register, mechanism notes, design decisions).
- `preregistration/` — the frozen pre-registration and its post-freeze amendments log. Every deviation
  is logged in [`DEVIATIONS.md`](DEVIATIONS.md), never made silently.
- `data/` — provenance conventions and the manifest (checksums, request parameters). Raw data is never
  committed here — see `data/README.md`.
- `src/` — the computation engine (data loading, roll rule, carry, returns, costs, vol targeting,
  portfolio construction, statistics, robustness constructions), one module per
  `PREREGISTRATION.md` section, cited in each module's docstring.
- `tests/` — unit tests for every `src/` module, exclusively on synthetic fixtures (no real data in the
  test suite, by design).
- `scripts/` — the corpus pull, QA, and Phase 1b/1c runner scripts. Real-data-only, not unit-tested
  (same convention as `data_loader.py`'s own DBN-reading functions), exercised manually and their
  output is the immutable `reports/` this study is built on.
- `reports/` — runner-generated, immutable once committed (`PREMISE_REPORT.md`, `PRIMARY_REPORT.md`,
  `ROBUSTNESS_REPORT.md`). Corrections happen via dated addenda, never silent edits.

## Data storage

Raw pulled data lives outside this repository and outside OneDrive, at the path in
`src/config.py`'s `DATA_DIR` — default `C:\Users\Aaron\quant-data\commodity-carry`, overridable via the
`DATA_DIR` environment variable. The repo itself only ever holds a provenance manifest
(`data/MANIFEST.md`: request parameters, timestamps, SHA-256 per file) and the reports above — never
the raw files themselves.
