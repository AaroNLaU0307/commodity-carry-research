# Pre-Registration — Commodity Carry Research

**Status: TEMPLATE. Not yet a pre-registration.** This is a skeleton created at the end of Phase 0 (data feasibility) to carry forward what Phase 0 actually determined. Family parameters, decision thresholds, and everything else marked `TBD` are filled in a dedicated pre-registration session — deliberately not here, and deliberately not by extrapolating from the feasibility data. Writing this before any PnL, return, or carry value has been computed is the point.

---

## Hypothesis & economic mechanism

TBD. One paragraph, written before any data is touched for signal purposes. State the specific economic mechanism (e.g., hedging pressure / insurance premium, storage cost, risk transfer from producers to speculators) being tested, not just "carry predicts returns."

## Universe & data lock

Filled from [`../docs/DECISION_MEMO.md`](../docs/DECISION_MEMO.md)'s final Track A verdict — this part is not TBD, it's a fact Phase 0 already established:

- **Dataset:** Databento `GLBX.MDP3` (CME Globex MDP 3.0).
- **Universe:** 18 CME futures across 4 sectors:
  - Energy: CL, HO, RB, NG
  - Metals: GC, SI, HG, PL, PA
  - Grains: ZC, ZS, ZW, ZM, ZL, KE
  - Livestock: LE, HE, GF
- **History:** 2010-06-06 through present for 17 of 18 symbols; KE from 2013-12-16. **TBD (pre-registration decision, not a feasibility question):** whether the study uses a universe-wide common start date (forces all 17 others down to 2013-12-16) or a staggered per-symbol window with KE joining later.
- **Frequency:** daily.
- **Price field:** settlement price (`statistics` schema) — not last trade, not a continuous-series "close."
- **Term structure form:** individual contract months via parent symbology (form (a) in the feasibility spec — the strongest of the three acceptable forms).
- **Expiry calendar source:** `definition` schema, same dataset.
- **Softs (SB, KC, CC, CT):** excluded. Databento's ICE Futures US coverage only starts 2018-12-23, failing the 10-year minimum. Pre-declared scope limitation, not an oversight.

## Primary family table (bounded; cell count TBD)

TBD. Must be bounded and declared before any signal computation — no post-hoc expansion. Cell count, exact carry/roll-yield construction, sorting/weighting scheme, and rebalance frequency all TBD here, not inferred from what "looks like it worked" later.

## Decision rule & gates

TBD. Should mirror the falsification standard used across the sibling repos in this research program: net of costs, no look-ahead, out-of-sample, beats a random/naive control — a claimed edge must survive all of these simultaneously, not just the best-looking one.

## Economic materiality bar

TBD. A minimum effect size relative to realistic transaction costs for CME futures (commissions + slippage + any roll cost), fixed before results are seen.

## Robustness plan matched to effect frequency

TBD. Given daily data on ~18 symbols with what's likely a low-frequency (monthly-or-slower rebalanced) carry signal, the robustness plan should be scaled to the actual number of independent observations this produces — not borrowed wholesale from a higher-frequency sibling study.

## NOT-testing list

Pre-seeded per the governing Phase 0 brief; extend during pre-registration if needed, but do not shrink this list without a logged reason:

- No seasonality interactions.
- No regime/macro conditioning.
- No intraday variants.
- No volatility-managed overlay variants.
- No post-hoc threshold search.

## Adaptation declarations

TBD. Log here, not silently in code, if any parameter drifts from what's declared above once real work starts (e.g., if KE ends up excluded after all, or the universe-wide start date changes).

## OOS lockbox definition

TBD. Exact date range or fraction of history that is locked out of all exploratory work until the pre-registered analysis is complete, per this research program's established practice.
