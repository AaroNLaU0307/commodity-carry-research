# Deviations Log

Per [`preregistration/PREREGISTRATION.md`](preregistration/PREREGISTRATION.md) §11: any deviation from the frozen pre-registration — a changed parameter, an added or removed robustness variant, a different inference method, anything at all — gets a dated entry here, written **before** the deviating computation runs. Evidence standards are never weakened by a deviation, only re-instrumented in response to a genuine error (e.g., a coding bug), and no adaptation may be motivated by an observed result.

No entries yet — this file is created alongside the frozen pre-registration, ready to receive them if and when they occur.

## Log

### 2026-07-11 — Phase 1b Step 0: one additional diagnostic, three specification completions, two rejected alternatives

Written before any real-data signal computation in this project's history — no carry, return, ranking, or portfolio weight had been computed from real data at the time this entry was made. Authority: "Aaron + advisor, decided blind to results," per the F7 adjudication recorded in `docs/DATA_QA_REPORT.md`'s 2026-07-11 addendum.

**1. Additional non-gating diagnostic (item 11 of §8's robustness suite): ex-PA/PL primary series.**
Motivated by QA finding F7 (PA and PL show a materially larger unexplained OI-gap residual than the other 16 symbols). The primary H1/H2 series are recomputed with PA and PL excluded from the universe entirely, reported alongside the full-18-symbol primary result with no gating consequence — exactly the same treatment as §8's existing ten items. **`N_trials` is unchanged at 14** per §10's own diagnostics-exclusion rule (item 8–9 precedent: a diagnostic of the primary series is not a new constructed strategy-return series for DSR-deflation purposes, and this one is the same kind of diagnostic, just keyed on a QA finding rather than a jackknife fold).

**2. Newey–West lag for the XS premise t-statistic, fixed at 3.**
`PREREGISTRATION.md` §7 specifies a Newey–West-adjusted t-statistic for the XS premise's mean Spearman IC but does not pin down the lag order. `src/stats.py::newey_west_tstat()` has always had a default auto-lag (the Newey-West 1994 plug-in rule, `floor(4*(n/100)^(2/9))`), which was appropriate as a general-purpose default when that function was built in Phase 1a (synthetic tests only, no real n). For the actual premise test, the lag is fixed at a pre-declared constant, **3**, rather than left to the data-dependent auto-formula — a monthly IC series with roughly 190 months of history and no expectation of long-memory dependence does not need the auto-formula's larger data-dependent lag, and a fixed constant declared before seeing the real series removes any possibility of the lag choice being tuned to the outcome.

**3. Held-front missing-settlement handling: mark-to-last-settlement, zero return that day, counted and reported, no gate.**
`PREREGISTRATION.md` §3 defines returns as `r_t = F_front(t) / F_front(t−1) − 1` but does not specify behavior when the held front contract's settlement is missing on a given date (QA §1 found 0.957% of outright bars lack a matching settlement value). Specification: on such a day, the held front's price is marked to its last available settlement (i.e. no return is recorded — the position is treated as flat that day rather than the return being left undefined or backfilled from a different contract), the return for that day is exactly 0.0, and every occurrence is counted and reported in `reports/PREMISE_REPORT.md` / `reports/PRIMARY_REPORT.md`. This is not a gate — it is a data-handling convention needed to make the return series computable at all, declared before running it on real data.

**4. Zero-price guard: HALT on any held-front settlement ≤ 0.**
If the currently-held front contract's settlement is ≤ 0 on any date, the pipeline halts immediately and reports the event as a finding rather than computing a return through it. This is expected to be silent in practice — CLK0 (the one confirmed negative-settlement instrument in this corpus, F2) was not the OI-determined front on 2020-04-20 (by that date by the roll rule should have already crossed to the next contract ahead of May-contract expiry) — but the guard is real and will actually halt the run if this expectation is wrong. If it fires, that is a discovery about this dataset, not an obstacle to route around.

**Rejected alternatives (considered, not adopted):**
- **Per-symbol rule forks** (e.g. a volume-based OI fallback specifically for PA/PL, to paper over F7's residual gap) — rejected. A per-symbol special case in the roll rule is exactly the kind of silent, symbol-specific tuning this project's falsification-first discipline exists to prevent, and F7's residual is small enough (171–176 symbol-days out of ~4,990 trading days per symbol, ~3.5%) that the existing hold-on-missing behavior (item 1 above) is adequate without a fork.
- **Universe amputation** (dropping PA/PL from the study entirely) — rejected. F7 does not rise to a severity that justifies silently shrinking the pre-registered 18-symbol universe; the ex-PA/PL diagnostic (item 1 above) gives the same information as a non-gating, fully-disclosed comparison instead.

### 2026-07-11 — Next-contract settlement ≤ 0 in the carry formula: treated as NaN

Discovered mid-session, not pre-declared: the pipeline's first real-data run produced `RuntimeWarning: divide by zero` inside `carry.compute_carry()` for GC, SI, and PA. Investigation found 8,635 outright rows (0.31% of the outright panel, present across all 18 symbols) where the `statistics` schema's settlement is exactly 0 or negative — overwhelmingly far-dated contracts CME lists years ahead of any real trading activity, reported with a settlement of 0.00 rather than omitted (unlike `ohlcv-1d`, which simply has no bar at all for a not-yet-traded contract — this is why F2's exhaustive zero/negative-close check on `ohlcv-1d` found only the one genuine CLK0 case and did not surface this).

This was not covered by Step 0's zero-price guard, which is explicitly scoped to the *held-front* settlement (for the return calculation) — Sec 3's carry formula additionally divides by the *next* contract's settlement, and nothing in the frozen pre-registration or Step 0 addressed that denominator's validity. Per Hard Rule 1 ("you never choose"), this was flagged rather than silently patched, without first forming or disclosing any view on which direction a fix would move the premise-test numbers.

**Ruling (authority: Aaron + advisor):** a next-contract settlement ≤ 0 is treated identically to a missing (NaN) one — carry is not computable that day, exactly the same handling `pipeline.py::symbol_carry_series()` already applies to a genuinely absent settlement. This is the symmetric, minimal extension of an existing convention, not a new threshold or parameter: a reported 0.00 for a dormant, not-yet-traded contract is no more economically meaningful than an absent value. Implemented in `src/pipeline.py::symbol_carry_series()`; `src/carry.py::compute_carry()` itself is unchanged (still a pure function assuming valid positive inputs, now always called guarded). Tests added (`tests/test_pipeline.py`) proving both the NaN outcome and that no RuntimeWarning is raised.

The premise-test run that first surfaced this (which produced `RuntimeWarning`s and was never committed) is superseded by a clean re-run under this ruling.

### 2026-07-15 — F11 Amendment A1: roll rule (§3) amended, single-candidate next-listed crossover → multi-candidate OI-max

**Authority:** Aaron + advisor.

**Amended definition.** At each date `t`, the front for a symbol is the outright contract (date-aware registry, per the F9/F10 `_contract_key` fix) that maximizes OI at `t−1` among candidates whose expiration is ≥ the incumbent front's expiration; ties break toward the earlier expiration (so the incumbent is retained on ties); if OI at `t−1` is unobserved for every candidate, the incumbent is held (the F7 ruling, unchanged). Initialization on a symbol's first evaluable day: argmax OI at `t−1` over all live outrights, ties to the earlier expiration. Monotonicity holds by construction (the candidate set never includes earlier expirations than the incumbent's).

**Why this is a legitimate amendment and not result-fitting:**
1. No valid result has ever existed — all three prior runs (Runs 1–3) were invalidated by identity-resolution bugs before any premise number was trusted, and Run 4 has not run; the amendment is made under zero result temptation.
2. The registered rule fails structurally on documented market structure — exchange-listed month cycles include serial months that never bear open interest (census: `docs/DATA_QA_REPORT.md` finding F11 — 11 permanent deadlocks across 13 symbols; PL frozen since a contract expired Aug 2010).
3. The replacement was validated read-only before adoption: the standalone counterfactual (`_carry-research-workspace/step_c_counterfactual_roll.py`, never executed against `src/roll.py` until this amendment) found zero genuine residual stuck fronts, and roll cadences matching known liquid cycles (e.g. PL: 0.12 → 4.11 rolls/yr against its quarterly cycle).
4. Lower-DOF than the alternatives — liquidity-cycle lookup tables and per-symbol rule forks were considered and rejected as researcher degrees of freedom.

**F7 note.** F7's hold-on-missing ruling behaved correctly throughout and is retained verbatim, unchanged by this amendment — only the candidate set considered at each date changed (single next-listed contract → every contract with expiration ≥ the incumbent's), never the hold-on-missing fallback or the t−1 temporal lag.

**N_trials.** Unaffected — still 14 per §10. This amendment changes how the front/next series is *constructed*, not the count of constructed strategy-return series.

**Implementation.** `src/roll.py::compute_front_contract_series()` — the state machine itself is replaced in place (same function name/signature, so every existing caller is unaffected); `src/pipeline.py::assert_front_not_past_expiry()` (the permanent tripwire) is retained unchanged and re-verified against the amended output.

### 2026-07-15 — F11 Amendment A2: carry "next" (§3) amended, next-listed → next OI-bearing

**Authority:** Aaron + advisor.

**Amended definition.** `next(t)` is the earliest-expiration outright with expiration strictly greater than the front's AND OI at `t−1` strictly positive; if none exists, carry is undefined (NaN) that date, under the existing missing-data handling (§3's return convention; the 2026-07-11 next-settle-≤0-is-NaN ruling above). The annualization denominator `D` remains the actual calendar-day gap between the two contracts' expirations — unchanged by this amendment, only which contract fills the "next" role changes.

**Justification.** The census's serial-settlement quality check (`docs/DATA_QA_REPORT.md` finding F11) — ZW's dead-serial months show 60% flat settlements vs 19% for liquid months, plus a real low-coverage tail concentrated in specific never-traded serial contracts — demonstrates that listed-curve marks on never-traded serials are exchange-algorithm artifacts unfit for signal measurement, not genuine market-clearing prices. Carry must measure the slope of the *traded* curve; this also matches the nearby-contract convention of the carry literature. The `OI > 0` condition is an existence threshold, not a tuned one — no magnitude parameter is introduced, and no threshold beyond strict positivity is used anywhere in this amendment.

**Interaction with A1.** Independent of A1's roll-rule amendment — A2 only changes which contract's settlement fills the carry formula's denominator/next-price role; it does not change which contract is held as the front position. A symbol's front (A1) and its carry "next" (A2) can therefore legitimately differ from the single-candidate next-listed contract in different, independently-motivated ways on the same date.

**N_trials.** Unaffected — still 14 per §10, for the same reason as A1.

**Implementation.** `src/pipeline.py::symbol_carry_series()` — the next-contract selection step is replaced; `src/carry.py::compute_carry()` itself is unchanged (still a pure function taking an already-selected front/next pair and their prices/expiries).
