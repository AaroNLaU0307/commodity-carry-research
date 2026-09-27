# Mechanism Notes — why no edge, when the literature finds one

Linked from [`README.md`](../README.md). Five candidate mechanisms, each evaluated against evidence
already sitting in the committed, immutable reports — no new computation performed for this document
beyond reading numbers off those reports. Verdict per row: **supported** / **contradicted** /
**undischarged** (the evidence in this corpus cannot settle it either way).

Every cell below cites a specific report and line/section — nothing here is asserted without a
traceable source.

**Correction (2026-09-27).** Every number below comes from the reports of 2026-07-16. Those reports
predate the trade-date calendar, open-interest field, execution-timing and cost/leverage corrections in
[`reports/ADDENDUM_2026-09-27.md`](../reports/ADDENDUM_2026-09-27.md). The verdicts will be re-checked
against the corrected re-run. Row 2's gross-vs-net comparison is directly affected: the published gross
and net series used different leverage paths, and the net series credited roll costs to short positions
(addendum §4).

| # | Candidate mechanism | Prediction if true | Evidence from our reports | Verdict |
|---|---|---|---|---|
| 1 | **Sample period + post-publication decay.** The carry premium was real but has decayed since being published/arbitraged (this study's sample, 2010–2026, is entirely post-publication — see `README.md` Limitations). | The strategy should still show up in a well-documented backwardation episode (2021–22) even if the average Sharpe over the full sample is weak or negative from decay in other years. | Per-year returns (`reports/ROBUSTNESS_REPORT.md`, "(c) Per-year table annotated against the 2021-22 backwardation episode"): H1 2021 **−2.43%**, 2022 **+5.69%**; H2 2021 **+1.71%**, 2022 **+5.10%**. Both arms are modestly positive in 2022 but H1 is negative in 2021, and neither 2022 figure is that arm's best year (H1's best years are 2010 +16.00%, 2017 +14.94%, 2026 +11.30% — all larger than its 2022 print). Sub-period halves (`reports/ROBUSTNESS_REPORT.md`, "Sub-period halves") show both arms *worse* in the second half of the sample (H1: 0.0435 → −0.0485; H2: −0.0747 → −0.1765), directionally consistent with decay, but neither half is itself close to the gates. | **Undischarged.** Directionally consistent with mild decay, but the strategy did not clearly work even in its own best-case macro backdrop — too weak a signal in either direction to confirm or rule out decay specifically. |
| 2 | **Costs / implementation drag.** The signal is real gross of costs; the frozen conservative cost table (tick-floor + $2.50/side, `PREREGISTRATION.md` §5) is what kills it. | Gross-of-cost Sharpe should be meaningfully higher than net, ideally clearing or approaching the gates. | Gross-vs-net restatement (`reports/ROBUSTNESS_REPORT.md`, "(a) Gross-of-cost Sharpe"): H1 net **−0.0031** vs. gross **+0.0061**; H2 net **−0.1255** vs. gross **−0.1288** (gross is *not* better for H2 — a cost-model defect, not a property of the strategy: costs fed the leverage estimate and roll costs were credited to short positions; `reports/ADDENDUM_2026-09-27.md` §4). | **Contradicted.** The gross-net gap is a fraction of a Sharpe point in both arms. There is no economically meaningful edge being eaten by frictions, because there is no meaningful edge gross of costs either. |
| 3 | **Universe width** (18 CME markets here vs. the literature's typical 24–35 including ICE softs and LME base metals). | Cannot be tested directly without pulling the missing markets (out of scope this session, and ICE softs were pre-declared excluded on data-history grounds — `docs/DATA_FEASIBILITY_REPORT.md` line 35). | Marked **honestly undischarged** — not testable with this corpus. Partial context only: drop-one-sector jackknife (`reports/ROBUSTNESS_REPORT.md`, "Jackknife: drop-one-sector") shows H1's Sharpe swinging from **−0.1927** (grains dropped) to **+0.2186** (energy dropped) depending on which sector is excluded — sector composition clearly matters to the sign and magnitude of the result, which is at least consistent with (not proof of) universe-composition sensitivity being a live issue. | **Undischarged.** The sector-jackknife swing shows composition matters; it says nothing about whether adding softs/LME specifically would help. Selecting sectors after seeing this table would be exactly the post-hoc search the NOT-testing list prohibits — the jackknife is a diagnostic, not a menu. |
| 4 | **Curve point:** the literature's edge lives further out the term structure than the front-vs-next slope this study's primary definition uses (`PREREGISTRATION.md` §3). | The 12-month-deferred carry variant (§8 item 5) should show a meaningfully better Sharpe than the front-slope primary. | 12-month-deferred variant (`reports/ROBUSTNESS_REPORT.md`, item 5): H1 **+0.1829** vs. primary **−0.0031** (a real improvement); H2 **−0.0058** vs. primary **−0.1255** (also improved, but still negative-ish/near-zero). Neither comes close to the 0.30 gate. | **Weakly supported for H1 only.** The single most interesting mechanism-consistent result in the whole suite — worth flagging plainly — but H1's improved Sharpe is still roughly 61% of the way to the gate threshold, and H2 shows no comparable improvement. Suggestive, not decisive — and a legitimate candidate for a future, separate pre-registration; this study's NOT-testing list binds this study, not follow-on work. |
| 5 | **Construction choice** (terciles / inverse-vol weighting / vol-targeting here vs. the literature's more common equal-weighted quintiles). | The quintile and equal-weight-leg variants should show a meaningfully better Sharpe than the primary tercile/inverse-vol construction. | Quintile cutoffs (`reports/ROBUSTNESS_REPORT.md`, item 2): **+0.0154** vs. primary −0.0031. Equal-weight legs (item 3): **+0.0139** vs. primary −0.0031. Both marginally better, neither meaningfully so. | **Contradicted.** Construction choice is not concealing a real edge — every alternate construction tested lands in the same near-zero neighborhood as the primary. |

Row 1's per-year evidence, in full:

![Grouped bar chart of H1 and H2 annual net returns from 2010 to 2026, with the 2021-22 backwardation window shaded; both arms are positive in 2022 but it is not either arm's best year, and both arms show negative years both before and after the shaded window.](../reports/figures/per_year_returns.png)

*Annual net returns per arm, 2021–22 backwardation window shaded. 2022 is positive for both arms
(H1 +5.69%, H2 +5.10%) but is not either arm's best year — H1's best years are 2010, 2017, and 2026, all
larger than its 2022 print. Source: `reports/ROBUSTNESS_REPORT.md` §"(c) Per-year table annotated
against the 2021-22 backwardation episode" · rendered before the 2026-09-27 corrections; re-rendered from
`results/` by `scripts/generate_readme_figures.py` at the re-run.*

## Cross-cutting: where did H1's P&L come from?

**Long-leg vs. short-leg contribution** (`reports/ROBUSTNESS_REPORT.md`, "(b) H1 long-leg vs short-leg
contribution split"). The long leg's gains (**+1.87%/yr** annualized mean contribution, +37.2562%
cumulative) offset the short leg's losses (**−1.82%/yr**, −36.2883% cumulative). The long leg made money
and the short leg lost about as much, so the long-minus-short book earned **no spread premium**. The
split is an exploratory attribution, not a pre-registered §8 item. It has
no confidence interval, and it predates the 2026-09-27 cost corrections (the published split credited
roll costs to the short leg).

## What the evidence actually discriminates

Two mechanisms are **ruled out** by the published, pre-correction evidence: costs/implementation drag
(row 2) and construction choice (row 5) — neither the gross restatement nor either alternate
construction moves the needle. Row 2 in particular is re-checked at the re-run (correction note above). One mechanism is **weakly, narrowly suggestive** — the curve-point
question (row 4), on H1 alone, and still far short of the gate. Two remain **genuinely open** because
this corpus cannot settle them — sample-period decay (row 1) and universe width (row 3). No forced
conclusion: this study answers "does this specific, pre-registered construction show a confirmable edge
in this sample" (no), not "does a commodity carry premium exist anywhere, under any construction, in any
universe" — a materially broader question this corpus was never built to answer.
