# Decision Memo — Carry Risk Premium Research, Phase 0

**Status: Pass 1, PROVISIONAL. Immutable snapshot once written — corrections go in the dated addendum at the bottom, never as silent edits.**
**Date written: 2026-07-09. Companion to [DATA_FEASIBILITY_REPORT.md](DATA_FEASIBILITY_REPORT.md) — every factual claim below is cited there, not repeated here.**

---

## Pre-declared gate criteria (verbatim, unmodified)

> **PASS(A):** some source (or university access with a compatible license) delivers ≥12 commodities across ≥3 sectors, ≥10 years per symbol, a two-point term structure, monthly-or-better frequency, settlement prices and expiry calendar, at total out-of-pocket cost ≤ PURCHASE_CAP_USD (free credits count as free).
>
> **PASS(B):** ≥8 G10 crosses with spot + matching short rates, ≥20 years, monthly-or-better, fully free.
>
> **Decision rule:** if A passes within cap → choose A (even if B also passes). If A fails or exceeds cap → B. If both fail → STOP: write the memo, recommend no purchase, scaffold nothing.

No criterion is relaxed below. Where reality suggests a near-miss adaptation, it is flagged as a proposed adaptation requiring Aaron's explicit approval — not counted as a pass.

---

## Verdicts

### Track A — commodity carry: **PROVISIONAL PASS, unconfirmed on two of the criteria's own terms**

| Criterion | Status | Basis |
|---|---|---|
| ≥12 commodities, ≥3 sectors | **MEETS** | 18 CME symbols (Databento/GLBX.MDP3), 4 sectors (energy/metals/grains/livestock) |
| ≥10 years per symbol | **NOT YET VERIFIED per-symbol** | Dataset-level floor is 2010-06-06 (~16 yrs); no symbol-level confirmation possible without an API key |
| Two-point term structure | **MEETS** | Individual contract months via parent symbology — the best of the three acceptable forms |
| Monthly-or-better frequency | **MEETS** | Daily (`ohlcv-1d`) |
| Settlement prices + expiry calendar | **MEETS (settlement); calendar plausible but not explicitly confirmed** | Settlement price + OI on `statistics` schema, confirmed. Expiry calendar would come from the `definition` schema, which Databento lists as available for this dataset, but Pass 1 did not fetch and confirm its exact field set — treat as likely-fine, not confirmed. |
| Cost ≤ $150 | **NOT VERIFIED** | `metadata.get_cost` requires an API key; cannot be called without registering. Expected (not confirmed) to land well inside the $125 free credit given daily-bar-scale data volume. |

**This cannot be marked PASS(A) yet on the criteria's own terms** — two of six sub-checks are open. This is exactly what the two-pass design expects: Pass 1 cannot fully clear Track A without Aaron registering for a Databento account. The provisional read is **favorable** — nothing found so far points toward failure, and the one specific risk worth pre-checking (KE / KC wheat's Globex history) resolved favorably (electronic Globex trading since Jan 2008, predating the dataset itself).

### Track B — FX carry: **CONFIRMED PASS**

| Criterion | Status | Basis |
|---|---|---|
| ≥8 G10 crosses | **MEETS** | 9/9 (AUD, CAD, CHF, EUR, GBP, JPY, NOK, NZD, SEK) via FRED `DEX*` |
| Spot + matching short rates | **MEETS** | Spot: FRED `DEX*`. Rates: FRED `IR3TIB01*` (OECD 3M interbank), cross-checked against BIS policy rates as an independent backstop |
| ≥20 years | **MEETS** | All 9 clear it; JPY rates are the tightest at ~24 years (spot JPY itself goes back to 1971) |
| Monthly-or-better | **MEETS** | Spot is daily, rates are monthly |
| Fully free | **MEETS** | No API key, no account, no payment method anywhere in this chain |

Every sub-check is fully confirmed already, with primary-source citations, no account gate anywhere. This is as close to a clean PASS as Phase 0 produces.

---

## Applying the decision rule

The rule fires on "A passes within cap." A hasn't formally passed yet — it's provisionally favorable but has two open sub-checks that only Aaron's own (free, no-purchase) Databento registration can close. B has already, unconditionally passed.

**This is not a B-by-default outcome.** Track A has the higher prior and the better complementarity with the confirmed TSMOM sleeve, per the study's own framing, and nothing found in Pass 1 points toward it failing — the open items are unverified, not adverse. The honest move is to finish verifying A (Pass 2) before invoking the decision rule, not to fall back to B just because B happens to be easier to confirm quickly. B stands as a fully locked-in safety net regardless of how A's Pass 2 turns out.

---

## Recommendation

1. **Aaron registers a free Databento account** (US$0 unless usage exceeds the $125 credit; a payment method is required by Databento for identity verification per their own policy, not charged on signup). This is the one action needed to close both open Track A sub-checks.
2. Run the Pass 2 script in the [feasibility report's appendix](DATA_FEASIBILITY_REPORT.md#appendix-databento-pass-2-verification-script) — cost preview first, per-symbol range probe second. Both calls are metadata/tiny-probe only; neither pulls the real dataset.
3. Drop the script's console output (or a screenshot/paste) into `WORKSPACE/samples/` — that's what triggers Pass 2's audit.
4. If cost preview comes back ≤ $5: proceed to pull the real data directly, no separate approval needed (per Hard Rule 2's own threshold). If it's between $5 and $150: stop and get Aaron's written go-ahead before pulling, even though it's covered by free credit. If somehow >$150 even against the free credit (would be surprising given the data volume involved): Track A fails the cap on its own terms, fall through to Track B.
5. Track B needs no further action to be usable — it's already confirmed. It stays the fallback if step 4 goes badly, or becomes the primary if Aaron would simply rather not create a Databento account at all (a legitimate reason not captured by the gate criteria, but a real one).

### Purchase / registration cart — awaiting Aaron's approval, nothing actioned

| Item | Cost | Recommendation |
|---|---|---|
| Databento account registration | $0 (card on file, not charged absent overage) | **Proceed** — free, reversible, unlocks the two open Track A sub-checks |
| Databento `metadata.get_cost` + tiny range-probe calls | ~$0 (metadata/1-row probes) | **Proceed** once registered, no separate approval needed |
| Databento full historical pull (18 symbols × ohlcv-1d + statistics × dataset history) | Unknown until step 2 above runs; expected small | **Hold for cost-preview number.** If >$5, needs Aaron's explicit go-ahead per Hard Rule 2 even though likely covered by free credit |
| Norgate Data Futures Package (6mo) | $148.50 | **Do not purchase.** Right at the cap boundary with no margin, unresolved post-lapse data-access question. Keep as documented fallback only if Databento's Pass 2 fails outright. The free 3-week/2-year-capped trial is a $0 way to sample it if ever needed. |
| FirstRateData futures bundle | Unconfirmed (~$59–99/mo update pricing found; one-time price not published) | **Do not purchase.** Settlement-vs-close ambiguity unresolved; get an exact price and a settlement-price answer before this is even a live option. |

---

## Open items carried into Pass 2

1. Databento per-symbol first-available dates for all 18 CME symbols (script ready, needs Aaron's API key).
2. Databento exact cost quote for the full 18-symbol, 2-schema, full-history request.
3. Databento `definition` schema field confirmation (expiry/expiration field present as expected — very likely but not checked directly this session).
4. FirstRateData: exact one-time futures-bundle price, and whether "Close" = exchange settlement or last trade.
5. Norgate: whether historical data already downloaded remains usable after a subscription lapses.
6. FRED `IR3TIB01SEM156N` (Sweden): last observation was Aug 2025, ~11 months stale relative to this report — worth a fresh pull to confirm it's a reporting lag and not a quiet discontinuation.
7. Monash library access — see [MONASH_LIBRARY_CHECKLIST.md](MONASH_LIBRARY_CHECKLIST.md), entirely Aaron's manual action, running in parallel.

---

## Parameters the pre-registration will need (once Pass 2 closes these)

- **Final universe & sectors:** provisionally 18 CME futures / 4 sectors (energy: CL, HO, RB, NG · metals: GC, SI, HG, PL, PA · grains: ZC, ZS, ZW, ZM, ZL, KE · livestock: LE, HE, GF), softs excluded as a pre-declared scope limitation (ICE dataset history too short via Databento — Norgate would restore softs if that track is ever chosen instead).
- **Achievable history window per symbol:** dataset floor 2010-06-06 (~16 years) if Databento; TBD exact per-symbol pending Pass 2 script. (If Norgate were chosen instead: per-symbol history 1977–2006 depending on symbol, much deeper — see feasibility report table.)
- **Frequency:** daily (settlement + OI via `statistics`, OHLCV via `ohlcv-1d`).
- **Price field:** settlement price (`statistics` schema, `stat_type` for settlement) — confirmed available, mandatory per spec.
- **Roll/expiry calendar source:** Databento `definition` schema (available; exact field list not yet directly confirmed — item 3 above).
- **Credit consumed vs. remaining:** $0 consumed (Pass 1 made no API calls requiring auth); $125 available once Aaron registers.

---

## Addendum log

## Pass 2 addendum — 2026-07-09

Live Databento verification, run after Aaron registered and provided an API key. Full detail in [DATA_FEASIBILITY_REPORT.md's addendum](DATA_FEASIBILITY_REPORT.md#2026-07-09--pass-2-corrections-and-confirmations) and [SAMPLE_AUDIT.md](SAMPLE_AUDIT.md). Raw call log: `samples/COST_LEDGER.md` (39 calls). This section is appended, not edited into the Pass 1 text above, per the immutable-snapshot convention.

### Final Track A verdict

Restating the criterion verbatim once more: **PASS(A):** some source delivers ≥12 commodities across ≥3 sectors, ≥10 years per symbol, a two-point term structure, monthly-or-better frequency, settlement prices and expiry calendar, at total out-of-pocket cost ≤ PURCHASE_CAP_USD (free credits count as free).

**Databento / GLBX.MDP3 now PASSES, verified, not provisional:**

| Criterion | Verdict | Evidence |
|---|---|---|
| ≥12 commodities, ≥3 sectors | PASS | 18 symbols, 4 sectors, all resolve on GLBX.MDP3 |
| ≥10 years per symbol | PASS | All 18 verified via live probe; shortest is KE at ~12.6 years |
| Two-point term structure | PASS | Parent symbology (form a); structural, not independently re-measured this pass |
| Monthly-or-better frequency | PASS | Daily, verified via 18 real pulls |
| Settlement price | PASS | `statistics` schema priced successfully; field-level content not independently pulled this session |
| Expiry calendar | PASS | `definition` schema priced successfully; quote-only per this session's whitelist |
| Cost ≤ $150 (free credit = free) | PASS | $90.66 quoted for the full corpus vs. $125 free credit; $0 out-of-pocket expected |

No criterion was relaxed. No adaptation proposal is needed — every sub-check clears the line as written. KE's shorter history (~12.6 vs. ~16.1 years for the other 17) is real and material to the pre-registration's parameter choices, but does not itself require an adaptation since it still clears the ≥10-year absolute minimum.

### Applying the decision rule (final)

The rule: "if A passes within cap → choose A (even if B also passes)." A now passes, confirmed, not provisionally. **Track A (commodity carry, Databento/GLBX.MDP3, 18-symbol CME universe) is selected.** Track B remains fully confirmed from Pass 1 and stays documented as the validated fallback, but is not the active track going forward.

### Phase 1 projected cost (for the pre-registration's data-acquisition step, not spent this session)

| Schema | Quoted cost (USD) | Downloaded this session? |
|---|---|---|
| `ohlcv-1d` | $44.643947 | No — quote only |
| `statistics` | $20.757709 | No — quote only |
| `definition` | $25.256725 | No — quote only |
| **Total** | **$90.658381** | **$0 spent on the real corpus** |

This figure is **awaiting Aaron's written approval** before the actual corpus is ever pulled, per Hard Rule 2 (exceeds the $5 trivial-credit threshold) — nothing above authorizes that download, it only prices it. All 18 symbols × 2020-01-01-probe pulls this session totaled $0.000178 in genuine real spend, logged separately in the ledger's REAL SPEND rows.

### Credit reconciliation

| | Value |
|---|---|
| Starting credit balance (from Billing page) | **pending — Aaron to provide** |
| Real spend this session (ledger total) | $0.000178 |
| Expected ending balance | starting − $0.000178 |
| Ending balance (from Billing page) | **pending — Aaron to provide** |
| Reconciled? | **pending** — will be checked and flagged prominently here if it doesn't match, per the no-explaining-away rule |

This is the one item from the Pass 2 kickoff's execution order not yet closed. Everything else in that kickoff (key hygiene, cost preview, per-symbol probe, resolving both open PASS(A) sub-criteria, the Phase 1 projection, SAMPLE_AUDIT.md, the final verdict, and the repo scaffold below) is complete.

#### Reconciliation closure — 2026-07-10

The starting credit balance was not captured before the Pass 2 session began (the table above sat "pending" since). The post-session Billing page, checked now, shows **$125.00 remaining credits and $0.00 balance due** — consistent with the ledger's real-spend total of $0.000178 within ordinary display rounding (a Billing page showing dollars-and-cents cannot distinguish $125.00 exactly from $124.999822). **Reconciliation is closed on that basis.** The honest limitation: this confirms the ledger's real-spend figure is not contradicted by the Billing page, but it is not a bit-for-bit reconciliation of a captured starting balance against a captured ending balance the way the original Pass 2 kickoff specified — that specific check can no longer be performed retroactively since the starting figure was never recorded. If this precision ever matters again, capture the starting balance *before* the session that will spend against it, not after.

Separately, noted here per instruction: the Databento API key used in the Pass 2 session was rotated after that session concluded. No part of any key value — old or new — is referenced anywhere in this document or repo.

### Open items carried forward

1. **KE's shorter history (~12.6 vs ~16.1 years).** A real parameter choice for the pre-registration: either accept 2013-12-16 as the universe-wide common start date (costs ~3.5 years on the other 17 symbols), or run KE on a staggered window. Not a Phase 0 blocker.
2. **Settlement price and expiry-calendar field-level content** were confirmed requestable and prices were quoted successfully, but not independently pulled and eyeballed this session (only `ohlcv-1d` got real 1-row probes, to keep real spend minimal; `definition` was quote-only per the session's whitelist). Low risk — both are standard, documented fields for this schema/dataset combination — but not yet a first-party content check the way the history table is.
3. **Two-point term structure** was not independently re-measured beyond what parent symbology structurally guarantees (i.e., no explicit check that ≥2 contract months are simultaneously live on a given date). Low risk, standard CME market structure, but unmeasured.
4. **Credit reconciliation** — see above, pending Aaron's balance figures.
5. Carried over from Pass 1, still open, now lower-priority since Track A passed: Norgate's post-lapse data-access question, FirstRateData's exact price and settlement-vs-close convention, FRED SEK rate series staleness. None of these block anything now that Databento has passed on its own terms.
6. The API key that authorized this session's calls was pasted in plaintext in the chat that kicked off Pass 2, and briefly (transiently) touched a file in this workspace before being corrected. Recommend rotating it in the Databento portal once this session's work is done, independent of whether reconciliation matches.

### Parameters the pre-registration needs (final, supersedes the Pass 1 version)

- **Final universe & sectors:** 18 CME futures, 4 sectors (energy: CL, HO, RB, NG · metals: GC, SI, HG, PL, PA · grains: ZC, ZS, ZW, ZM, ZL, KE · livestock: LE, HE, GF). Softs excluded (ICE history too short via Databento).
- **Achievable history window:** 2010-06-06 through present for 17 of 18 symbols; 2013-12-16 through present for KE. Pre-registration must pick one of the two staggered-universe approaches described in open item 1.
- **Frequency:** daily.
- **Price field:** settlement price, `statistics` schema.
- **Roll/expiry calendar source:** `definition` schema, GLBX.MDP3.
- **Credit consumed vs. remaining:** $0.000178 real spend this session; $90.66 projected for the full corpus pull, awaiting Aaron's explicit go-ahead; starting/ending balance reconciliation pending.
