# Mechanism Notes — why no edge, when the literature finds one

Linked from [`README.md`](../README.md). Five candidate mechanisms, each evaluated against evidence
already sitting in the committed, immutable reports — no new computation performed for this document
beyond reading numbers off those reports. Verdict per row: **supported** / **contradicted** /
**undischarged** (the evidence in this corpus cannot settle it either way).

Every cell below cites a specific report and line/section — nothing here is asserted without a
traceable source.

**Re-run (2026-09-28).** Every number below is from the corrected re-run (`reports/rerun/`, code
`70d1e03`); published → corrected values are in
[`reports/ADDENDUM_2026-09-27.md`](../reports/ADDENDUM_2026-09-27.md) §10. H2 closed at the premise gate in
the re-run, so only H1 has backtest evidence. Each verdict was re-read against the corrected numbers.

| # | Candidate mechanism | Prediction if true | Evidence from our reports | Verdict |
|---|---|---|---|---|
| 1 | **Sample period + post-publication decay.** The carry premium was real but has decayed since being published/arbitraged (this study's sample, 2010–2026, is entirely post-publication — see `README.md` Limitations). | The strategy should still show up in a well-documented backwardation episode (2021–22) even if the average Sharpe over the full sample is weak or negative from decay in other years. | Per-year returns (`reports/rerun/ROBUSTNESS_REPORT.md`, "(c) Per-year table annotated against the 2021-22 backwardation episode"): H1 2021 **+0.70%**, 2022 **+2.97%**; H2 closed at the premise gate and has no series. H1 is positive in both years but only slightly, far below its best years (2013 +16.47%, 2010 +15.71%, 2017 +14.71%). Sub-period halves (`reports/rerun/ROBUSTNESS_REPORT.md`, "Sub-period halves") show H1 *worse* in the second half (0.1173 → 0.0016), directionally consistent with decay, but neither half is itself close to the gates. | **Undischarged.** Directionally consistent with mild decay, but the strategy did not clearly work even in its own best-case macro backdrop — too weak a signal in either direction to confirm or rule out decay specifically. |
| 2 | **Costs / implementation drag.** The signal is real gross of costs; the frozen conservative cost table (tick-floor + $2.50/side, `PREREGISTRATION.md` §5) is what kills it. | Gross-of-cost Sharpe should be meaningfully higher than net, ideally clearing or approaching the gates. | Gross-vs-net restatement with the same positions and leverage path (`reports/rerun/ROBUSTNESS_REPORT.md`, "(a) Gross-of-cost Sharpe"): H1 net **0.0591** vs. gross **0.0860**. H2 closed at the premise gate. | **Contradicted.** Gross is only a fraction of a Sharpe point above net, and nowhere near the 0.30 gate. There is no economically meaningful edge being eaten by frictions, because there is no meaningful edge gross of costs either. |
| 3 | **Universe width** (18 CME markets here vs. the literature's typical 24–35 including ICE softs and LME base metals). | Cannot be tested directly without pulling the missing markets (out of scope this session, and ICE softs were pre-declared excluded on data-history grounds — `docs/DATA_FEASIBILITY_REPORT.md` line 35). | Marked **honestly undischarged** — not testable with this corpus. Partial context only: drop-one-sector jackknife (`reports/rerun/ROBUSTNESS_REPORT.md`, "Jackknife: drop-one-sector") shows H1's Sharpe swinging from **−0.2194** (grains dropped) to **+0.1848** (livestock dropped) depending on which sector is excluded — sector composition clearly matters to the sign and magnitude of the result, which is at least consistent with (not proof of) universe-composition sensitivity being a live issue. | **Undischarged.** The sector-jackknife swing shows composition matters; it says nothing about whether adding softs/LME specifically would help. Selecting sectors after seeing this table would be exactly the post-hoc search the NOT-testing list prohibits — the jackknife is a diagnostic, not a menu. |
| 4 | **Curve point:** the literature's edge lives further out the term structure than the front-vs-next slope this study's primary definition uses (`PREREGISTRATION.md` §3). | The 12-month-deferred carry variant (§8 item 5) should show a meaningfully better Sharpe than the front-slope primary. | 12-month-deferred variant (`reports/rerun/ROBUSTNESS_REPORT.md`, item 5): H1 **0.1750** vs. primary **0.0591** (an improvement). H2 closed at the premise gate, so its item-5 variant was not built. Neither comes close to the 0.30 gate. | **Weakly supported for H1 only.** A mechanism-consistent improvement worth flagging plainly, but H1's item-5 Sharpe is still below the 0.30 gate and H2 offers no comparison. Suggestive, not decisive — and a legitimate candidate for a future, separate pre-registration; this study's NOT-testing list binds this study, not follow-on work. |
| 5 | **Construction choice** (terciles / inverse-vol weighting / vol-targeting here vs. the literature's more common equal-weighted quintiles). | The quintile and equal-weight-leg variants should show a meaningfully better Sharpe than the primary tercile/inverse-vol construction. | Quintile cutoffs (`reports/rerun/ROBUSTNESS_REPORT.md`, item 2): **0.0584** vs. primary 0.0591. Equal-weight legs (item 3): **0.0520** vs. primary 0.0591. Both slightly *below* the primary. | **Contradicted.** Construction choice is not concealing a real edge — every alternate construction tested lands in the same near-zero neighborhood as the primary. |

Row 1's per-year evidence, in full:

![Bar chart of H1's annual net returns from 2010 to 2026, with the 2021-22 backwardation window shaded; H1 is slightly positive in 2021 and 2022, far below its best years, and has negative years both before and after the shaded window.](../reports/rerun/figures/per_year_returns.png)

*H1's annual net returns, 2021–22 backwardation window shaded. H1 is positive in 2021 (+0.70%) and 2022
(+2.97%), but far below its best years — 2013 (+16.47%), 2010 (+15.71%) and 2017 (+14.71%). H2 closed at
the premise gate and has no series. Source: `reports/rerun/ROBUSTNESS_REPORT.md` §"(c) Per-year table
annotated against the 2021-22 backwardation episode". The pre-correction figure stays at
`reports/figures/per_year_returns.png`.*

## Cross-cutting: where did H1's P&L come from?

**Long-leg vs. short-leg contribution** (`reports/rerun/ROBUSTNESS_REPORT.md`, "(b) H1 long-leg vs
short-leg contribution split"; each leg net of its own trading and roll costs). The long leg's gains
(**+1.96%/yr** annualized mean contribution, +31.6817% cumulative) outweigh the short leg's losses
(**−1.31%/yr**, −21.1022% cumulative). The long leg made money and the short leg lost less, which is
where H1's small positive net Sharpe comes from. The split is an exploratory attribution, not a
pre-registered §8 item, and it has no confidence interval.

## What the evidence actually discriminates

Two mechanisms are **ruled out** by the corrected evidence: costs/implementation drag (row 2) and
construction choice (row 5) — neither the gross restatement nor either alternate construction moves the
needle. One mechanism is **weakly, narrowly suggestive** — the curve-point
question (row 4), on H1 alone, and still far short of the gate. Two remain **genuinely open** because
this corpus cannot settle them — sample-period decay (row 1) and universe width (row 3). No forced
conclusion: this study answers "does this specific, pre-registered construction show a confirmable edge
in this sample" (no), not "does a commodity carry premium exist anywhere, under any construction, in any
universe" — a materially broader question this corpus was never built to answer.
