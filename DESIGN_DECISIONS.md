# Design Decisions — pre-answered objections

The obvious questions a skeptical reader would ask, answered once, here, with citations, rather than
scattered across commit messages. Nothing below is new reasoning — every answer condenses something
already recorded in `preregistration/PREREGISTRATION.md`, `DEVIATIONS.md`, or the reports.

## Why a sign-only premise gate?

`PREREGISTRATION.md` §7 gates Phase 1c on the *sign* of the premise point estimate alone, not its
significance: "if an arm's premise point estimate is ≤ 0 (wrong sign), that arm closes at the premise
stage... A positive-but-insignificant premise estimate is not a gate failure." This is deliberate, not
an oversight. The premise test is the cheapest possible check — a monthly rank correlation, no
portfolio, no costs, no leverage — and its only job is to reject arms with the *wrong-signed* relationship
before spending the much more expensive primary-family machinery on them. Both arms here passed that
cheap gate (H1 mean IC +0.028489, NW(3) t=1.465; H2 coefficient +0.000672, t=0.300 —
`reports/PREMISE_REPORT.md`) precisely because a positive-but-weak estimate is what the gate is
*designed* to let through, so the bootstrap — the actual evidence bar (§6) — gets to make the real call.
Gating on significance at the premise stage would have meant deciding the outcome twice with two
different, weaker tools instead of once with the right one.

## Why BH-FDR at m=2, always — never recomputed after seeing results?

`PREREGISTRATION.md` §10 fixes the primary family at exactly {H1, H2}, m=2, frozen before any
computation. The alternative — declaring m after seeing which arms "still look interesting" — is
exactly the kind of researcher degree of freedom multiple-testing correction exists to close off. m=2
was true when the pre-registration was written and remains true regardless of the outcome; changing it
post hoc, even in a direction that looks more conservative, would itself be a result-motivated
adaptation of the kind `DEVIATIONS.md`'s own protocol (§11) exists to prevent.

## Why no out-of-sample lockbox?

`PREREGISTRATION.md` §6: a lockbox exists to guard against discovery-phase contamination — iterating on
a model until an OOS slice validates it. This study never had a discovery phase to guard against: the
entire design (universe, definitions, construction, costs, gates, robustness suite) was frozen and
publicly pushed *before* any data entered the repo (§12 step 1; `PUSH_CHECKLIST.md`). A held-out slice
adds protection against a failure mode (in-sample overfitting via iterative tuning) that structurally
cannot have occurred here, at the cost of a real one: a 2022–2026 holdout would be dominated by a single
macro episode (the commodity/inflation shock) rather than a representative test window. Full-sample
confirmation via the §8 robustness suite was used instead, per the same house convention already
established in `multi-asset-tsmom-research`.

## Why were the F11 amendments (A1, A2) legitimate, and not post hoc rationalization?

Condensed from the full argument in `DEVIATIONS.md`'s 2026-07-15 entries — three pillars, each
independently checkable:

1. **Zero result temptation.** All three prior runs were invalidated by *identity-resolution bugs*
   before any premise number was ever trusted (`reports/PREMISE_REPORT.md`'s run-history table) — no
   valid result existed anywhere in this project's history at the point the amendment was adopted, and
   none was computed under the old rule afterward for comparison. There was nothing to protect or chase.
2. **Structural necessity, validated read-only before adoption.** The registered single-candidate roll
   rule fails on documented, verifiable market structure (11 of 18 symbols permanently deadlocked on
   real, listed-but-illiquid serial months — `docs/DATA_QA_REPORT.md` finding F11) — not a hunch, a
   census. The replacement was built and validated as a **read-only counterfactual**, against real data,
   *before* it ever touched the production pipeline (`docs/DATA_QA_REPORT.md`'s Gates 1–4; the
   counterfactual script never called `src/roll.py`).
3. **Lower researcher degrees of freedom than the alternatives.** A liquidity-cycle lookup table or a
   per-symbol rule fork were both considered and rejected (`DEVIATIONS.md`) as introducing more tunable
   parameters, not fewer, than the multi-candidate OI-max rule actually adopted, which uses the same t−1
   look-ahead discipline as before and adds no new threshold beyond existence (`OI > 0`).

## Why 12 registered variants, and not more? What about [some other construction]?

The ten §8 robustness items build 12 registered variant series (items 1–7 and 10; §10's ledger) and all
12 were run. Items 8–9 and the F7 ex-PA/PL series are diagnostic slices of the primary series, not
variants. `PREREGISTRATION.md` §9 locks a NOT-testing list *before* any computation: basis-momentum,
carry×momentum interaction, COT/hedging-pressure signals, seasonality conditioning, curve curvature,
volatility-managed overlays, any cutoff/threshold optimization, dynamic or learned weighting, regime
filtering, intraday signals, and any parameter search. Anything not in the registered ten robustness
items (§8) plus the one F7 diagnostic is, by construction, on that list — the honest answer to "did you
try X" for any X outside that set is "it was pre-declared out of scope specifically so that a
disappointing result couldn't be followed by an ad hoc eleventh variant that happened to work." The ten
items that *were* registered were chosen before Run 4 existed, not selected afterward as the ones worth
trying; the exact specifications of items 1, 4 and 5 were fixed when the code was written and were not
logged (recorded retroactively in `reports/ADDENDUM_2026-09-27.md` §6). One sensitivity was added on
2026-09-27, before the corrected re-run: execution one trading day after the signal, for both arms
(`preregistration/AMENDMENT_2026-09-27.md`), which raises N_trials from 14 to 16.

## Why report a confidence interval this wide instead of a tighter, more flattering one?

Because the bootstrap CI is a function of the achieved sample size and realized return volatility, not
a design choice — `reports/PRIMARY_REPORT.md`'s CIs ([−0.44, 0.43] for H1, [−0.56, 0.32] for H2) are
what 10,000 stationary-block resamples of the actual daily return series produce. Narrowing them would
require either more data (not available) or a less conservative method (not permitted — the stationary
bootstrap was the pre-registered, advisor-affirmed primary inference method, §6). The width is itself
informative: see the power statement in `README.md`'s Limitations section, computed directly from these
two CIs, not asserted separately.

## Why ship a negative result with the same rigor as `multi-asset-tsmom-research`'s supported result?

Because the gates don't know in advance which answer they're going to give. `multi-asset-tsmom-research`'s
core result is labelled *supported, not independently confirmed*: its bootstrap CI excludes zero, and that
repository records that its core was not pre-registered. This study was pre-registered and gated from the
start, and it reports `NOT PROMOTED` with the same completeness a favorable answer would have had. A
research program that only publishes when the answer is favorable isn't running a falsification test at
all — it's running a publication filter. A supported result elsewhere in this series is only as credible
as the completeness with which the failed ones are reported.

## Why does F12 (the one-day tax) get its own note instead of being quietly absorbed?

Because it is a genuine, if small, consequence of a design choice (strict t−1 look-ahead safety) that
a reader could otherwise mistake for a data gap or a bug if it surfaced unexplained. Documenting it
precisely — 8 instances, all on CL, ~4% of that symbol's own rolls, confirmed absent at the raw source
in both schemas, not lost in this pipeline (`docs/DATA_QA_REPORT.md` finding F12) — turns "we found
something odd and moved on" into "we found it, quantified it, and can show you exactly why it has to
exist given the look-ahead discipline this whole study depends on." A falsification-first project
should be at least as rigorous about its own mechanics as it is about the hypothesis under test.
