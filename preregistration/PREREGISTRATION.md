# Pre-Registration — Commodity Carry Research

**Status: FROZEN as of 2026-07-10.** This document supersedes `PREREGISTRATION_TEMPLATE.md` (deleted in the same commit that adds this file). Every design decision below was specified before any computation, data download, signal code, or notebook existed for this project — see the no-alpha-peeking bright line carried over from Phase 0. Deviations from this document follow the protocol in §11 and are logged in `DEVIATIONS.md`, never made silently.

Two `[OPEN]` items surfaced while formalizing this document — genuine mismatches between the governing spec's assumptions and what was actually found in source material, not left for me to resolve. See [`WORKSPACE/PREREG_OPEN_ITEMS.md`](../../_carry-research-workspace/PREREG_OPEN_ITEMS.md) for both, referenced inline at §6 and §5 below.

---

## 1. Hypotheses and economic mechanism

**H1 (cross-sectional carry).** Among the 18 CME commodity futures in the frozen universe (§2), commodities in backwardation (positive carry) outperform commodities in contango (negative carry) on a risk-adjusted basis, net of transaction costs, when ranked and traded cross-sectionally each month. Mechanism: the theory of storage (convenience yield accruing to holders of the physical commodity, which shows up as backwardation when inventories are scarce) and the hedging-pressure / normal-backwardation view (commercial hedgers who are net short pay a risk premium to the speculators who take the other side of that position) both predict that the carry signal proxies for a compensated risk or scarcity premium, not a random cross-sectional split. This study takes no position on which of the two mechanisms dominates — both predict the same sign, and disentangling them is out of scope (see §9).

**H2 (time-series carry).** For a given commodity, the sign of its own carry predicts the sign of its own excess return over the following month, net of costs — the same mechanism restated in absolute rather than relative form: a commodity in backwardation is expected to earn a positive expected excess return on its own terms, independent of how it ranks against the other 17.

Both hypotheses are stated as priors only — no results, in-sample or otherwise, are referenced or have been computed at the time of writing. General literature background, cited generically per the governing brief's instruction (no results quoted): Koijen, Moskowitz, Pedersen & Vrugt, "Carry," *Journal of Financial Economics* (2018), for the empirical carry-premium framework spanning currencies, equities, bonds, and commodities; the broader theory-of-storage and hedging-pressure/normal-backwardation literature (Keynes 1930; Working 1949; Kaldor 1939 on the theory of storage more generally) for the economic mechanism.

---

## 2. Data lock

- **Source:** Databento, dataset `GLBX.MDP3` (CME Globex MDP 3.0).
- **Schemas:** `ohlcv-1d` (daily bars), `statistics` (settlement price, open interest), `definition` (contract expiries, tick size, contract multiplier).
- **Symbology:** individual contract months, parent symbology (`stype_in=parent`) — not a continuous/spliced series.
- **Universe (18 symbols, 4 sectors, frozen from Phase 0):**

  | Sector | Symbols |
  |---|---|
  | Energy (4) | CL, HO, RB, NG |
  | Metals (5) | GC, SI, HG, PL, PA |
  | Grains (6) | ZC, ZS, ZW, ZM, ZL, KE |
  | Livestock (3) | LE, HE, GF |

  Source: `DECISION_MEMO.md`, Pass 2 addendum, final Track A verdict table.

- **Sample window: 2010-06-07 through 2026-06-30** (dataset floor to last complete month at the time of freezing). Cross-checked against the Phase 0 probe: 14 symbols (CL, HO, RB, NG, GC, SI, HG, PL, PA, ZC, ZS, ZW, ZM, ZL) show a first record of 2010-06-06, and 3 symbols (LE, HE, GF) show 2010-06-07 — source: `samples/per_symbol_probe_results.json`, `per_symbol_probe` object. 2010-06-07 is correctly the later of the two dates, i.e. the first date on which **all 17** non-KE symbols have data simultaneously — consistent with the symbol entry rule below.
- **Projected acquisition cost: $90.658381** (`ohlcv-1d` $44.643947 + `statistics` $20.757709 + `definition` $25.256725) for the full candidate corpus, full history, all 18 symbols — source: `samples/COST_LEDGER.md` rows 1–3 and `samples/per_symbol_probe_results.json`, field `full_corpus_projection_usd`. Not yet spent; awaiting Aaron's written approval per §12 step 2.
- **Symbol entry rule:** a symbol enters the cross-section (H1) or the traded set (H2) at the first month-end where its carry signal is computable from available data (i.e., both a front and a next contract have settlement prices) — no backfill to before that date, and no exclusion of the symbol once it has entered. Per the probe results (`samples/per_symbol_probe_results.json`), 17 symbols are available from the dataset floor (2010-06-06/07) and KE enters on **2013-12-16**. Consequence: the H1 cross-section is **17 names before KE's entry, 18 names from 2013-12-16 onward**. `n_leg` in §4 is computed from whichever count is live in a given month.
- **Rebalance frequency:** monthly. Daily settlement data is used for signal construction, the volatility estimator (§4), and daily P&L reconstruction; the trading decision itself is monthly (§3, Signal timing).

---

## 3. Locked definitions

**Carry.**
```
carry_i(t) = [F_front(t) − F_next(t)] / F_next(t) × 365 / D
```
where `F_front(t)` and `F_next(t)` are same-date settlement prices (Databento `statistics` schema) for the front and next contract respectively, and `D` is the number of calendar days between the two contracts' expiry dates (Databento `definition` schema). Positive carry = backwardation (front trades above next, annualized).

**Front contract — roll rule (OI-crossover, look-ahead-safe).** At date `t`, the front contract switches from `c1` to the next-listed contract `c2` at the first `t` such that `OI_{t−1}(c2) > OI_{t−1}(c1)` — open interest **as of the prior trading day only**. Rationale (this is the reason, not a hedge on the rule): CME publishes official open interest on a T+1 basis, so using same-day OI to decide a same-day roll would embed look-ahead bias — the roll decision would be conditioned on information not actually available until the next trading day. Using `t−1` OI is therefore the latest OI figure that is genuinely known before trading on day `t`. Rolls are monotonic: once the front has switched from `c1` to `c2`, it cannot switch back to `c1`.

**Next contract.** The contract immediately following the front in the exchange-listed expiry sequence, per the `definition` schema.

**Returns.** Daily excess return of the held (front) contract:
```
r_t = F_front(t) / F_front(t−1) − 1
```
settlement-to-settlement. Futures returns are excess returns by construction (no financing leg — a futures position requires no funding of the notional). On a roll date, the old front position is closed and the new front position opened at that day's settlement prices, with a transaction cost charged on both legs (§5); there is no price splicing across the roll — the return series is chained per **held** contract, not per a synthetic continuous price.

**Signal timing.** Carry signals are computed using data available through month-end `t`. Positions implied by that signal are established at the first trading day of month `t+1`, at that day's settlement price. There is no same-day signal-to-trade — a full trading day separates signal observation from position entry, consistent with `positions = weights.shift(1)` convention used in `multi-asset-tsmom-research` (`STUDY_SUMMARY.md`, line 72; see §4 for the full convention-inheritance discussion).

---

## 4. Portfolio construction

**H1 (cross-sectional).** At each month-end, rank the live cross-section (17 or 18 names, per §2) by `carry_i(t)`. Long the top tercile, short the bottom tercile, `n_leg = round(N/3)` per leg (`N`=17 gives `n_leg=6`; `N`=18 gives `n_leg=6`). Within each leg, weight constituents inversely to their individual volatility (§ vol estimator below). Scale the resulting long/short book to the portfolio-level volatility target.

**H2 (time-series).** For each symbol independently, `position_i = sign(carry_i(t))`, scaled by that symbol's individual volatility estimate, then aggregated equal-risk across all live symbols and scaled to the portfolio-level volatility target.

**Convention inheritance (mandatory, per governing brief §4).** The volatility estimator, vol target, leverage cap, and dynamic-deleveraging rule are inherited **verbatim** from `multi-asset-tsmom-research` (read-only reference; nothing in that repo was modified). Located and cited exactly, not paraphrased from memory:

| Element | Value | TSMOM citation |
|---|---|---|
| Per-asset vol estimator | 60-trading-day rolling standard deviation (`ddof=1`) of daily simple returns, `min_periods=window` (no partial windows — NaN until a full 60-day history exists, so no look-ahead), annualized by ×√252 | `config.py` L168 (`VOL_WINDOW_DAYS = 60`), L171 (`TRADING_DAYS_PER_YEAR = 252`); implementation `src/sizing.py`, function `rolling_volatility()`, L51–63 |
| Portfolio-level vol estimator | Same method, same 60-day window, applied to the portfolio's own daily return series | `config.py` L183 (`PORT_VOL_WINDOW_DAYS = 60`); implementation `src/portfolio.py`, function `realized_portfolio_vol()`, L156–165 |
| Per-asset annualized vol target | 10% | `config.py` L169 (`TARGET_VOL_ANNUAL = 0.10`) |
| Portfolio annualized vol target | 10% | `config.py` L182 (`PORT_TARGET_VOL_ANNUAL = 0.10`) |
| Per-asset weight cap | \|weight\| ≤ 2.0 (leverage guardrail on any single name) | `config.py` L170 (`MAX_ASSET_WEIGHT = 2.0`); implementation `src/sizing.py`, function `target_weights()`, L93 (`raw.clip(lower=-max_weight, upper=max_weight)`) |
| Portfolio gross-leverage cap | sum\|weights\| ≤ 3.0 (safety valve) | `config.py` L184 (`MAX_GROSS_LEVERAGE = 3.0`); implementation `src/portfolio.py`, function `leverage()`, L171–189 |
| Dynamic deleveraging rule | The leverage scalar **is** the deleveraging mechanism: `L = target_vol / realized_portfolio_vol`, so the book automatically shrinks when trailing realized vol rises and grows when it falls, subject to the 3.0× cap above. There is no separate/additional deleveraging layer beyond this scalar. | `src/portfolio.py` module docstring L21–26; formula at `leverage()` L184 (`l_raw = target_vol / port_vol.where(port_vol > 0)`) |

**No-trade band: explicitly not inherited, and this is a positive design choice, not an omission.** TSMOM defines a no-trade band parameter (`config.py` L207, `NO_TRADE_BAND = 0.05`, implemented in `src/portfolio.py::apply_no_trade_band()`, L202–229) but **does not apply it** in its main/adopted pipeline — `run_backtest.py` (the live strategy) never calls `apply_no_trade_band()`; the only caller is `cost_analysis.py`, where it was run as a standalone control experiment and rejected: turnover fell only 17.6×→16.0× annual (a 9% reduction) while net Sharpe was *slightly lower at every cost level tested* (`output/COST_AND_TURNOVER_REPORT.md` L32, L66: *"No-trade band did NOT help — honest negative result... the band is not adopted"*). Per the governing brief's own instruction ("if TSMOM applies a no-trade band... inherit it likewise") — TSMOM's applied answer is *no* — so this project inherits that same applied answer: **no no-trade band.** TSMOM's own monthly rebalance frequency (`config.py` L154, `SIGNAL_RESAMPLE = "ME"`) already matches this project's, so no frequency-translation was needed to reach this conclusion.

**Stated purpose (per governing brief, restated here as instructed).** These conventions are inherited rather than independently chosen so that parameter degrees of freedom are eliminated by reusing frozen infrastructure already in production elsewhere in this research program, and so that a later trend-vs-carry comparison (Project B) is a clean like-for-like — any difference in results between that project and this one will not be attributable to different vol-targeting or leverage machinery.

---

## 5. Cost model (frozen before any computation)

Per-side cost formula (fixed, applied identically to every rebalance trade and every roll leg):
```
cost_per_side_$ = max(1 tick value, conservative half-spread) + exchange fee + clearing fee
cost_per_side_pct = cost_per_side_$ / (settlement_price_t × contract_multiplier)
```
The dollar-denominated inputs (tick value, fee estimates) are frozen now, in the table below. The **percentage** cost is not a single frozen number — it is computed from the formula above using the actual settlement price on the actual date of each trade or roll during Phase 1c, since notional value (price × multiplier) changes daily. Freezing the formula, not a stale point-in-time percentage, is what "frozen cost model" means here.

**Conservative half-spread:** no systematic per-product bid-ask spread data was found via public search for all 18 products (see below); the formula's own `max(1 tick, ...)` structure means the 1-tick value is the operative floor throughout this table — this is a documented consequence of the formula as specified, not a new assumption.

**Exchange + clearing fee:** a genuine sourcing limitation, logged as `[OPEN]` item 2 in `WORKSPACE/PREREG_OPEN_ITEMS.md`. CME Group's own fee-schedule pages and PDFs blocked automated access this session (multiple `WebFetch` attempts failed with connection resets/timeouts — no Databento or other API call was made; this is public-documentation research only, consistent with Hard Rule 1). The one concrete, dated figure found: CBOT non-member agricultural futures exchange fee = **$2.13/contract**, effective 2025-02-01, plus a **$0.02/contract** non-member NFA regulatory fee — summing to **$2.15/side**. This figure is applied **uniformly as a conservative proxy** across all 18 rows below, pending Aaron's direct verification via CME's own Non-Member Fee Finder tool (a manual, browser-based lookup — not automatable from this session). Source: CME fee-schedule change coverage found via web search (AMP Futures fee-change notice, referencing the CME fee schedule effective 2025-02-01) and NFA's published non-member regulatory fee.

| Symbol | Sector | Multiplier | Tick size | Tick value | Exch.+clearing fee/side (proxy) | Source (tick/multiplier) |
|---|---|---|---|---|---|---|
| CL | Energy | 1,000 bbl | $0.01/bbl | $10.00 | $2.15 | CME Group contract specs |
| HO | Energy | 42,000 gal | $0.0001/gal | $4.20 | $2.15 | CME Group contract specs |
| RB | Energy | 42,000 gal | $0.0001/gal | $4.20 | $2.15 | CME Group contract specs |
| NG | Energy | 10,000 MMBtu | $0.001/MMBtu | $10.00 | $2.15 | CME Group contract specs |
| GC | Metals | 100 troy oz | $0.10/oz | $10.00 | $2.15 | CME Group contract specs |
| SI | Metals | 5,000 troy oz | $0.005/oz | $25.00 | $2.15 | CME Group contract specs |
| HG | Metals | 25,000 lb | $0.0005/lb | $12.50 | $2.15 | Ironbeam contract-spec page (cross-checked; an initial secondary source had this off by 10×) |
| PL | Metals | 50 troy oz | $0.10/oz | $5.00 | $2.15 | CME Group contract specs |
| PA | Metals | 100 troy oz | $0.50/oz | $50.00 | $2.15 | Barchart contract-spec page (cross-checked against conflicting secondary sources that cited $10 — CME-adjacent sources and Barchart agree on $50) |
| ZC | Grains | 5,000 bu | $0.0025/bu (¼¢) | $12.50 | $2.15 | CME Group contract specs |
| ZS | Grains | 5,000 bu | $0.0025/bu (¼¢) | $12.50 | $2.15 | CME Group contract specs |
| ZW | Grains | 5,000 bu | $0.0025/bu (¼¢) | $12.50 | $2.15 | Standard CBOT grain contract structure — not independently fetched this session, inferred from the identical, independently-confirmed structure of ZC/ZS/KE. Flag if this project ever needs certainty beyond "standard CBOT convention." |
| ZM | Grains | 100 short tons | $0.10/ton | $10.00 | $2.15 | CME Group contract specs |
| ZL | Grains | 60,000 lb | $0.0001/lb | $6.00 | $2.15 | CME Group contract specs |
| KE | Grains | 5,000 bu | $0.0025/bu (¼¢) | $12.50 | $2.15 | Barchart contract-spec page |
| LE | Livestock | 40,000 lb | $0.00025/lb | $10.00 | $2.15 | Cross-checked via the GF/HE consistency pattern (40,000 lb × $0.00025 = $10.00); an initial secondary source had this off by 100× |
| HE | Livestock | 40,000 lb | $0.00025/lb | $10.00 | $2.15 | CME Group contract specs |
| GF | Livestock | 50,000 lb | $0.00025/lb | $12.50 | $2.15 | Web search, resolving an initial conflicting secondary source |

The 2× cost table required by robustness item 6 (§8) is this table with every fee/tick-floor dollar figure doubled — computed at Phase 1c time, not a second frozen table.

---

## 6. Primary family and statistical gates

**Primary family: exactly {H1, H2}, m = 2.** Benjamini–Hochberg FDR control at **q = 0.10** across these two primary p-values.

**Primary statistic:** annualized net Sharpe ratio.

**Inference method — `[OPEN]` item 1, see `WORKSPACE/PREREG_OPEN_ITEMS.md`.** The governing brief specifies "stationary block bootstrap on daily net returns — mirror the TSMOM repo's bootstrap convention... verbatim with citation; fallback if absent: stationary bootstrap, expected block length 21 trading days, 10,000 replications, 3 recorded seeds." A full search of `multi-asset-tsmom-research` (`src/validation.py`, `config.py`, `src/seasonality.py`, `src/xsmom_stats.py`, and every `research/*/PREREGISTRATION.md`) found **no stationary bootstrap anywhere in that repo** — zero hits for "stationary" or "circular" block-bootstrap terminology. What actually exists:
- The convention that produces TSMOM's own headline Sharpe/return confidence interval is an **ordinary (IID) bootstrap** — no block structure at all (`src/validation.py::bootstrap_ci()`, L20–57; docstring L27: *"IID bootstrap of monthly returns"*), n=10,000 (`config.py` L198, `BOOTSTRAP_N=10000`), 95% CI (`config.py` L200, `CI_LEVEL=95`), single fixed seed 7 (`config.py` L142, `RANDOM_SEED=7`).
- A **moving-block bootstrap** (a different, named method from "stationary") exists but only in three *secondary/robustness* studies, each with its own block length: seasonality (10 trading days, `config.py` L323), XSMOM decomposition (12 months, `src/xsmom_stats.py`), yield-spread (the forward horizon `h`). None of these compute the core promotion-gate Sharpe CI in their respective studies.

Since a stationary block bootstrap is genuinely absent (not merely under-documented), this triggers the governing brief's own pre-written fallback exactly as specified, rather than a decision made here: **stationary bootstrap, expected block length 21 trading days, 10,000 replications, 3 recorded seeds** on daily net returns for each of H1 and H2. The 3 seeds and their outcomes will be individually recorded in the Phase 1c output, not just their average. `[OPEN]` item 1 flags this for Aaron in case the actual intent was to mirror TSMOM's moving-block convention instead (and if so, which of its three block-length variants) — the fallback stands as written in this document unless and until that is revisited, since revisiting it now, mid-formalization, based on which result "looks better" is exactly what §11's deviations protocol exists to prevent.

**Promotion gate per hypothesis — ALL must hold:**
1. BH-FDR-adjusted bootstrap p-value passes at q = 0.10.
2. 95% bootstrap CI of net Sharpe excludes 0.
3. Net Sharpe ≥ 0.30.
4. Net Sharpe remains > 0 under the 2× cost table (§5).
5. DSR ≥ 0.95, with `N_trials` set to the exact enumerated count from §10 (= 14).

**No OOS lockbox.** Rationale, per the governing brief, stated here as instructed: a lockbox exists to guard against discovery-phase contamination — this study freezes its entire design (universe, definitions, construction, costs, gates, robustness suite) before any computation touches the data, so there is no discovery phase to guard against. Separately, a 2022–2026 holdout would be dominated by a single macro episode (the 2022 commodity/inflation shock) rather than providing a representative, independent test window. Full-sample confirmation via the §8 robustness suite is used instead, per the house convention already established in `multi-asset-tsmom-research`.

---

## 7. Premise test (Phase 1 gate, before any portfolio backtest)

- **XS premise:** monthly cross-sectional Spearman rank IC between `carry_i(t)` and symbol `i`'s next-month excess return; report the mean IC with a Newey–West-adjusted t-statistic.
- **TS premise:** pooled panel regression of next-month excess return on `sign(carry_i(t))`, standard errors clustered by month.
- **Gate:** if an arm's premise point estimate is ≤ 0 (wrong sign), that arm **closes at the premise stage** — no portfolio backtest is run for it. This is the cheapest possible gate and is deliberately checked first. A positive-but-insignificant premise estimate is not a gate failure — it proceeds to the portfolio backtest, where the bootstrap (§6) is the primary evidence, not the premise test. **Both premise results are reported regardless of outcome** — a closed arm is reported as closed with its point estimate, not omitted.

---

## 8. Robustness suite (direction-consistency checks — reported in full, never gating)

1. Sector-neutral XS (rank within sector, equal sector risk).
2. Quintile cutoffs instead of terciles (XS).
3. Equal-weight legs instead of inverse-vol weighting (XS).
4. Carry smoothed over 1 month (both arms).
5. 12-month-deferred carry definition — front vs. ~1-year contract instead of front vs. next (both arms).
6. 2× cost table, per §5 (both arms).
7. Fixed-calendar roll rule instead of OI-crossover (both arms).
8. Sub-period halves and per-year returns — diagnostic of the primary series, not an alternative strategy.
9. Jackknife: drop-one-sector and drop-one-year — diagnostic of the primary series, not an alternative strategy.
10. KE-entry sensitivity: results with KE excluded entirely from the universe (XS).

Items 8–9 are excluded from the trial count in §10 because they diagnose the *same* primary return series rather than constructing a new one. A robustness sign flip anywhere in 1–7 or 10 does **not** veto promotion — the promotion gate is §6 alone — but every robustness result is reported and discussed in the final report regardless of direction.

---

## 9. NOT-testing list (locked)

Basis-momentum · carry×momentum interaction · COT/hedging-pressure signals (reserved for a future, separate pre-registration) · seasonality conditioning · curve curvature or far-end-of-curve slopes · volatility-managed overlays · any cutoff/threshold optimization · dynamic or learned weighting schemes · any regime filtering · anything intraday · any parameter search.

---

## 10. Computation ledger and N_trials

Every distinct constructed strategy-return series this study will compute, with arm counts (items 8–9 from §8 excluded as diagnostics of the primary series, per that section):

| Series | Arms | Count |
|---|---|---|
| Primary H1 (XS) | 1 | 1 |
| Primary H2 (TS) | 1 | 1 |
| Robustness 1 — sector-neutral XS | XS only | 1 |
| Robustness 2 — quintile cutoffs | XS only | 1 |
| Robustness 3 — equal-weight legs | XS only | 1 |
| Robustness 4 — 1-month-smoothed carry | XS + TS | 2 |
| Robustness 5 — 12-month-deferred carry | XS + TS | 2 |
| Robustness 6 — 2× cost table | XS + TS | 2 |
| Robustness 7 — fixed-calendar roll | XS + TS | 2 |
| Robustness 10 — KE excluded | XS only | 1 |

Arithmetic: primary = 1 + 1 = **2**. Robustness = 1 + 1 + 1 + 2 + 2 + 2 + 2 + 1 = **12**. Total **N_trials = 2 + 12 = 14**.

This is the exact figure used as the `N_trials` input to the DSR gate (§6, promotion criterion 5). It is frozen at this value; if a future deviation (§11) adds or removes a constructed series, `N_trials` changes and every already-computed DSR must be recomputed under the new count — this is exactly the kind of consequence §11 exists to force into the open rather than let slide.

---

## 11. Deviations protocol

Any deviation from this document — a changed parameter, an added or removed robustness variant, a different inference method, anything — requires a dated entry in [`DEVIATIONS.md`](../DEVIATIONS.md) (repo root), written **before** the deviating computation runs. Evidence standards (the gate in §6, the bootstrap method, the DSR threshold) are never weakened by a deviation, only re-instrumented if a genuine error is found (e.g., a coding bug in the vol estimator) — and no adaptation may ever be motivated by an observed result. `DEVIATIONS.md` is created alongside this document, currently empty, ready to receive entries if and when they occur.

---

## 12. Phase 1 order of operations

1. **This document is committed and the repo is pushed to a public GitHub remote.** The public timestamp on that push must precede any data entering the repo — this is what makes the freeze verifiable by anyone, not just asserted in a local commit message. See `PUSH_CHECKLIST.md`.
2. **Only then** does Aaron give written approval for the $90.66 corpus pull (§2) — the Databento portal's monthly spending limit has already been raised to $125 for this specific purpose, per the governing brief.
3. **Phase 1a — data QA only.** Checksums on every retrieved file, a per-contract settlement/open-interest coverage audit, a gap audit, and a spot-check of approximately 5 settlement values against publicly published CME settlement prices. No signal computation of any kind occurs in this phase.
4. **Phase 1b — premise test**, §7, with its own gate applied before proceeding.
5. **Phase 1c — primary family backtests and gates** (§6), then the full robustness suite (§8).

No step in this ordering may be reordered or skipped without a §11 deviation entry.

---

## Traceability index

Every cross-referenced source used in this document, gathered in one place:

- `DECISION_MEMO.md` (this repo, `docs/`) — universe, sectors, final Track A verdict.
- `samples/per_symbol_probe_results.json` (this repo, `docs/samples/`) — per-symbol first-available dates, full-corpus cost projection.
- `samples/COST_LEDGER.md` (this repo, `docs/samples/`) — the 39 logged Databento API calls behind the cost figures above.
- `multi-asset-tsmom-research/config.py`, `src/sizing.py`, `src/portfolio.py`, `src/validation.py`, `src/seasonality.py`, `src/xsmom_stats.py`, `STUDY_SUMMARY.md`, `output/COST_AND_TURNOVER_REPORT.md` — every inherited convention in §4 and §6, read-only, unmodified.
- CME Group contract-specification pages, Ironbeam and Barchart contract-spec pages (per-row citations in §5) — tick sizes and contract multipliers.
- Koijen, Moskowitz, Pedersen & Vrugt (2018), "Carry," *Journal of Financial Economics* — economic-mechanism citation only, no results referenced (§1).
