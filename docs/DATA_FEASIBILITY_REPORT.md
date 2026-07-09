# Data Feasibility Report — Carry Risk Premium Research, Phase 0

**Status: Pass 1 (no-account research pass). Immutable snapshot once written — corrections go in the dated addendum at the bottom, never as silent edits.**
**Date written: 2026-07-09. Purchase cap: US$150. No accounts opened, no purchases made, no data downloaded — every line below is sourced from free public documentation, vendor marketing/docs pages, or free no-key API endpoints (FRED CSV/series pages, CFTC public reporting).**

No forward returns, carry-vs-return relationships, or asset rankings appear anywhere in this document — see the alpha-peeking bright line in the governing prompt. Everything here is coverage, cost, and integrity-of-availability only.

---

## Track A — Commodity carry

### A.1 Databento (primary candidate)

**Account/credit terms.** New accounts receive US$125 in free data credits, usable against historical data and subscription plans, expiring 6 months after signup, shared across a team (one set per team). A payment method is required at signup to verify account authenticity, but the card is not charged unless usage exceeds the credit. [Pricing](https://databento.com/pricing) · [Usage pricing & credits FAQ](https://databento.com/docs/faqs/usage-pricing-and-data-credits) · [GLBX.MDP3 dataset page](https://databento.com/datasets/GLBX.MDP3)

**Dataset.** `GLBX.MDP3` (CME Globex MDP 3.0). Dataset-level inception is **2010-06-06** (earliest timestamp referenced against this dataset in Databento's own public issue tracker). [Databento issue tracker references](https://issues.databento.com/b/6vrl98vl/feature-ideas/glbxmdp3-status-schema-unavilabile-for-extended-mdp2-history) — this is a corroborating source, not Databento's own dataset-coverage statement page, so treat as strong-but-secondary; Pass 2 must confirm via `metadata.get_dataset_range`. Marketing copy separately claims "up to 15 years of normalized data" for CME futures generally. [databento.com/futures](https://databento.com/futures)

**Schemas confirmed for GLBX.MDP3:** `mbo`, `mbp-10`, `mbp-1`, `trades`, `tbbo`, `ohlcv-*` (incl. `ohlcv-1d`), `statistics`, `definition`, `imbalance`. [Catalog page, GC futures](https://databento.com/catalog/cme/GLBX.MDP3/futures/GC)

**Settlement price + open interest.** Confirmed: official settlement prices and open interest are carried on the **statistics** schema, not the OHLCV bars — matches the brief's own caveat exactly. [Retrieving OI and settlement prices](https://databento.com/docs/examples/futures/retrieving-oi-and-settlement-prices)

**Candidate CME universe (18 symbols, 4 sectors)** — this is the study's target list, not yet individually verified against Databento's per-symbol coverage (that requires an API key; see Pass 2 script below):

| Sector | Symbols |
|---|---|
| Energy (4) | CL (WTI crude), HO (NY Harbor ULSD), RB (RBOB gasoline), NG (Henry Hub nat gas) |
| Metals (5) | GC (gold), SI (silver), HG (copper), PL (platinum), PA (palladium) |
| Grains (6) | ZC (corn), ZS (soybeans), ZW (SRW wheat), ZM (soybean meal), ZL (soybean oil), KE (KC HRW wheat) |
| Livestock (3) | LE (live cattle), HE (lean hogs), GF (feeder cattle) |

18 symbols / 4 sectors clears both the target (15–25 across ≥4 sectors) and the minimum viable (≥12 across ≥3 sectors) bars **on universe count alone** — subject to the per-symbol history check below.

**KE-specific check (done, favorable).** KE (KC HRW wheat, formerly KCBT) migrated to **electronic Globex trading in January 2008** (KCBT products moved to CME Globex when KCBT/CBOT/CME infrastructure merged), with the open-outcry floor closing in 2013 and trading continuing on Globex under CME/KCBT rules since. [CME Group: KCBT transition announcement, Feb 2013](https://www.prnewswire.com/news-releases/cme-group-announces-transition-of-kansas-city-wheat-futures-and-options-to-chicago-trading-floor-189691481.html) · [World Grain, Feb 2013](https://www.world-grain.com/articles/2928-cme-transitioning-kansas-city-wheat-futures-options) — since Globex-native KE trading predates GLBX.MDP3's own 2010-06-06 inception, KE should have **full dataset-era coverage**, not a truncated one. This was the single symbol on the candidate list with a plausible structural reason to be shorter than the rest; it checks out. Still subject to the same Pass-2 API verification as every other symbol — this is not a substitute for that check, just a reason not to expect KE to be the odd one out.

**ICE-listed softs (SB, KC, CC, CT).** Databento does carry ICE Futures US: `IFUS.IMPACT` dataset, covering coffee (KC), cocoa, cotton, sugar and more. **Historical coverage begins 2018-12-23** — roughly 7.6 years as of this report, which **fails** the study's 10-year absolute minimum outright. [IFUS.IMPACT dataset page](https://databento.com/datasets/IFUS.IMPACT) · [IFUS venue docs](https://databento.com/docs/venues-and-datasets/ifus-impact) · [IFUS KC catalog](https://databento.com/catalog/ifus/IFUS.IMPACT/futures/KC). Subscription starts at $199/mo or usage-based from $10/GB — moot given the history fails regardless of price.

**Consequence:** softs are excluded from Track A on this candidate architecture. Per the pre-declared fallback, this is a scope limitation, not a gate failure — the 18-symbol, 4-sector CME-only universe stands on its own against both the target and minimum-viable bars.

**Cost preview — NOT executed in Pass 1.** `metadata.get_cost` requires an authenticated `Historical` client (API key), which Pass 1's no-account rule prohibits calling. Confirmed signature: `client.metadata.get_cost(dataset=, symbols=, schema=, start=, end=)`, priced per byte of uncompressed binary, varies by dataset/schema. [get_cost docs](https://databento.com/docs/api-reference-historical/metadata/metadata-get-cost) · [Metered pricing](https://databento.com/docs/api-reference-historical/basics/metered-pricing). Daily bars + one low-frequency statistics record/day across 18 symbols over ~16 years is a small volume by Databento's own metered standards (their cost driver is intraday tick/book data, not EOD bars) — expected to land well inside the $125 credit, but this is an expectation, not a verified number, and must not be treated as one. Exact Pass 2 script is in the Appendix.

---

### A.2 Norgate Data

**Price.** Futures Package: **US$148.50 / 6 months**, or **US$270 / 12 months** (10% discount built into the 12-month term vs. 2× the 6-month price). [Pricing page](https://norgatedata.com/prices.php). The 6-month term is **$1.50 under** the $150 cap — binding, not comfortable; any FX conversion fee, card surcharge, or tax on a non-USD-denominated card could push it over. Record the number as instructed regardless of the cap fit.

**Coverage.** Individual futures contracts (all months, including delisted/expired) plus pre-built continuous series (unadjusted and back-adjusted), ~100 futures markets across 11 exchanges. [Futures package page](https://norgatedata.com/futurespackage.php). Full sector table pulled directly from Norgate's own content tables — every sector the study needs is covered, with per-symbol start dates far exceeding the study's 15-year target:

| Sector | Symbol (Norgate) | Exchange | Norgate history start |
|---|---|---|---|
| Energy | CL | NYMEX | 30 Mar 1983 |
| Energy | HO | NYMEX | 2 Feb 1979 |
| Energy | NG | NYMEX | 3 Apr 1990 |
| Energy | RB | NYMEX | 3 Oct 2005 |
| Metals | GC | NYMEX | 30 Oct 1979 |
| Metals | SI | NYMEX | 1 Mar 1978 |
| Metals | HG | NYMEX | 13 Mar 1978 |
| Metals | PA | NYMEX | 1 Nov 1982 |
| Metals | PL | NYMEX | 15 May 1978 |
| Grains | ZC | CBOT | 4 Jan 1978 |
| Grains | ZS | CBOT | 21 Nov 1977 |
| Grains | ZM | CBOT | 25 Jan 1978 |
| Grains | ZL | CBOT | 17 Jan 1978 |
| Grains | ZW | CBOT | 5 Jan 1978 |
| Grains | KE | KCBT | 23 Apr 1979 |
| Livestock | LE | CME | 23 Oct 1978 |
| Livestock | GF | CME | 22 Jan 1979 |
| Livestock | HE | CME | 14 Nov 1978 |
| Softs | CC, KC, SB, CT, OJ | ICE US | 1978–1979 (all five) |

[Data content tables](https://norgatedata.com/data-content-tables.php) — Norgate is the only source evaluated in Pass 1 that would pass Track A **with softs included**, since its history for CC/KC/SB/CT goes back to 1978–79, not 2018.

**Open items (unresolved by public docs, matter to the decision):**
- Subscriptions are **fixed-term and not cancellable early** — confirmed contractually binding. [Search of Norgate policy pages]
- Whether previously-downloaded/synced historical data remains usable after the subscription term lapses (vs. requiring an active subscription to even read the local database) is **not stated in any public page found**. This matters because the study needs one historical pull, not an ongoing feed — if data becomes unreadable post-lapse, the effective product is "6 months of usable access," not "permanent ownership of a historical dataset." Needs a direct question to Norgate support before any purchase.
- Python access (`norgatedata` PyPI package) is free and adds no extra cost, but requires the Windows-only Norgate Data Updater (NDU) running locally and an active subscription authenticating through it. [PyPI / search corroboration] — no issue for Aaron's Windows machine, noted for completeness.
- A **3-week free trial** exists, capped at 2 years of historical data per symbol — too short to validate the term-structure/history requirement outright, but long enough to sample field names, settlement-vs-close conventions, and file format for free before committing $148.50. [Free trial page](https://norgatedata.com/freetrial.php)

---

### A.3 FirstRateData

**Coverage.** Each futures dataset includes **both individual contract months and continuous series** (three continuous-adjustment methods: unadjusted, absolute-adjusted, ratio-adjusted) — passes the term-structure requirement structurally. [firstratedata.com/it/futures](https://firstratedata.com/it/futures) · [Most-active futures bundle](https://firstratedata.com/b/29/futures-most-active). Continuous series mostly start **January 2008** (~18 years as of 2026); per-symbol individual-contract start dates are not published and would need a direct sample to confirm.

**Fields.** Confirmed 1-day (EOD) bar format is `{DateTime, Open, High, Low, Close, Volume, Open Interest}` — open interest is present at daily frequency. [FirstRate Data FAQ, search-corroborated]. **Unresolved:** whether "Close" is the exchange's official settlement price or simply the last traded/quoted price in the session — the two can differ meaningfully for CME-style settlement algorithms, and the study's spec treats settlement as the mandatory, carry-relevant price. No public page states which convention FirstRateData uses. This is exactly the kind of thing a sample file resolves in one look (compare a known date's "Close" against the exchange's published settlement) — flagged for Pass 2 sample audit, not resolved here.

**Price.** Not found on any publicly reachable page for a futures-only bundle — pages show a "Buy Now" button with a dynamically-rendered price, and one 500-error on direct fetch. Indirect data points: update subscriptions run ~$59–99/month per bundle or ~$99/year for a single ticker; the unrelated "Complete Intraday Bundle" (stocks+ETFs+futures+indices) lists at $79.95/month. **No one-time futures-only bundle price is confirmed** — this is a genuine gap, not an inferred FAIL; if this source becomes relevant, Aaron would need to click through an actual checkout flow to get a number (a $0-cost action, no account needed to see a price).

---

### A.4 Stooq / Yahoo Finance — continuous futures

Both platforms' futures symbols (e.g., Yahoo `CL=F`, `GC=F`; Stooq `cl.f`, `gc.f`) are well-documented in the quant community as **single, auto-rolled front-month continuous series** — one series per symbol, no second contract-month available alongside it. This is consistent with general platform documentation and community write-ups (QuantInsti, IBKR Quant blog, QuantStart). Direct live verification was inconclusive in Pass 1: Yahoo's finance pages don't expose a back-month series in any documented way; Stooq's own pages returned empty/blocked responses to automated fetch (likely bot protection), so this finding rests on well-established secondary documentation rather than a first-party page read this session. [QuantInsti: Yahoo Finance futures](https://blog.quantinsti.com/download-futures-data-yahoo-finance-library-python/) · [QuantStart: Stooq intro](https://www.quantstart.com/articles/an-introduction-to-stooq-pricing-data/)

**Verdict: FAILS term structure** (front-month-only continuous, explicitly the disqualified form in the study spec). Per the brief's own instruction, this was verified quickly and not over-invested in — if Aaron wants a first-party confirmation, opening either site in a browser for 30 seconds settles it definitively.

---

### A.5 Nasdaq Data Link (formerly Quandl) — free tier

The `CHRIS` continuous-futures database (the one free source that historically offered front+back contract pairs) is **confirmed deprecated / no longer updated** — corroborated by a dated GitHub issue (2024-09-20) reporting the Chapter-1 example of a published cookbook no longer works because of it. [GitHub issue, Python-for-Algorithmic-Trading-Cookbook](https://github.com/PacktPublishing/Python-for-Algorithmic-Trading-Cookbook/issues/5). No free successor product offering term-structure futures data was found on Nasdaq Data Link's current free tier (free tier is capped at 10,000 rows/request and is oriented toward macro/alternative data, not futures term structure). [Nasdaq Data Link getting started](https://docs.data.nasdaq.com/docs/getting-started)

**Verdict: FAILS** (dead source, matches the brief's prior).

---

### A.6 CFTC Commitments of Traders — availability note only

Confirmed alive and free: the modern **Public Reporting Environment** at [publicreporting.cftc.gov](https://publicreporting.cftc.gov) serves CSV/RDF/RSS/TSV/XML exports and an API (no token currently required for light use), alongside legacy static file downloads. Legacy report history extends to 1986-01-15; other report types (Disaggregated, TFF) to 2006-06-13. [CFTC COT overview, search-corroborated]. **Not ingested this phase** — this is a scope note for a possible future hedging-pressure study family, per the governing brief. No further action taken.

---

## Track B — FX carry (G10)

### B.1 Spot — FRED `DEX*` daily series

All 9 candidate G10-vs-USD crosses confirmed present, free, no API key needed to view/download (public series pages + keyless `fredgraph.csv` export). Every series is currently updating (most recent observations in Jan–Jul 2026, i.e. live as of this report):

| Currency | FRED series | Coverage | Source |
|---|---|---|---|
| EUR | DEXUSEU | 1999-01-04 → present (Euro didn't exist before 1999) | [series page](https://fred.stlouisfed.org/series/DEXUSEU) |
| GBP | DEXUSUK | 1971-01-04 → 2026-06-26 | [series page](https://fred.stlouisfed.org/series/DEXUSUK) |
| JPY | DEXJPUS | 1971-01-04 → 2026-07-02 | [series page](https://fred.stlouisfed.org/series/DEXJPUS) |
| CAD | DEXCAUS | 1971-01-04 → 2026-07-02 | [series page](https://fred.stlouisfed.org/series/DEXCAUS) |
| CHF | DEXSZUS | 1971-01-04 → 2026-07-02 | [series page](https://fred.stlouisfed.org/series/DEXSZUS) |
| AUD | DEXUSAL | 1971-01-04 → 2026-06-26 | [series page](https://fred.stlouisfed.org/series/DEXUSAL) |
| NZD | DEXUSNZ | 1971-01-04 → 2026-07-02 | [series page](https://fred.stlouisfed.org/series/DEXUSNZ) |
| NOK | DEXNOUS | 1971-01-04 → 2026-06-26 | [series page](https://fred.stlouisfed.org/series/DEXNOUS) |
| SEK | DEXSDUS | 1971-01-04 → 2026-07-02 | [series page](https://fred.stlouisfed.org/series/DEXSDUS) |

9/9 vs. the ≥8 minimum viable and 9/9 vs. the full target. All ≥27 years (EUR) to ≥55 years (the rest) — comfortably clears the ≥20-year bar. **Verdict: PASS**, and unlike Track A this is a fully confirmed pass already in Pass 1 — no account gate, no cost uncertainty, nothing deferred to Pass 2 except a routine gap audit once files are actually pulled.

### B.2 Rates — OECD 3-month interbank via FRED, cross-checked against BIS policy rates

Primary candidate is the OECD `IR3TIB01` (3-month/90-day interbank rate) family as carried on FRED, monthly, all 9 currencies confirmed present and — contrary to the governing brief's stated worry about discontinued OECD MEI series — **currently live and updating**, not dead:

| Currency | FRED series | Coverage | Notes |
|---|---|---|---|
| EUR | IR3TIB01EZM156N | Jan 1994 → Jan 2026 | Euro-area aggregate; EUR spot only exists from 1999, so effective usable window matches DEXUSEU |
| GBP | IR3TIB01GBM156N | Jan 1957 → Jan 2026 | |
| JPY | IR3TIB01JPM156N | Apr 2002 → Mar 2026 | **Shortest of the nine at ~24 years** — still clears the ≥20yr bar but is the binding constraint if the study locks a common start date across all 9 |
| CAD | IR3TIB01CAM156N | Jan 1956 → Feb 2026 | |
| CHF | IR3TIB01CHM156N | Jul 1999 → Apr 2026 | |
| AUD | IR3TIB01AUM156N | Jan 1968 → Feb 2026 | |
| NZD | IR3TIB01NZM156N | Dec 1973 → Jan 2026 | |
| NOK | IR3TIB01NOM156N | Jan 1979 → May 2026 | |
| SEK | IR3TIB01SEM156N | Jan 1982 → **Aug 2025** | Only series of the nine trailing more than a few months behind "now" (2026-07-09) — worth a direct re-check at pre-registration time in case it has since lapsed rather than just being reporting-lagged |

[Series pages, search-corroborated per symbol — see individual FRED URLs, pattern `fred.stlouisfed.org/series/<ID>`]. All 9 clear ≥20 years; JPY is the tightest.

**Backup/cross-check source:** BIS [Central Bank Policy Rates](https://data.bis.org/topics/CBPOL/data) database — free, single CSV download, covers 40+ central banks including all G10, most daily series from the 1980s, some back to 1946, updated weekly. [BIS data documentation](https://www.bis.org/statistics/cbpol/cbpol_doc.pdf). Policy rate is a different definition than 3M interbank (matters for the pre-registration's rate-definition lock, not for feasibility), but as a **coverage/continuity backstop** for any of the 9 IR3TIB01 series it's a strong, independently-sourced fallback with no discontinuation risk of its own.

**Definitional caveat (recorded, not resolved, per instruction):** deposit/interbank-rate carry is not the same object as forward-implied carry after the 2008 breakdown of covered interest parity (CIP). Free data — both FRED and BIS — supports the rate-differential definition well. It does not, and cannot, resolve which definition the pre-registration should lock; that is a pre-registration decision, explicitly out of scope here.

**Verdict: PASS.** 9/9 currencies, all ≥24 years, monthly, free, live. SEK's staleness is the one line item worth a fresh check before locking anything.

---

## Integrity notes

No files have been retrieved in Pass 1 (only metadata/documentation pages), so there is nothing to checksum yet. Every factual claim above carries an inline citation to either a vendor documentation/pricing page, a FRED series page, or a corroborating secondary source (explicitly labeled as such where the primary source was unreachable, e.g. Stooq). Where Pass 1 could not verify something (Databento per-symbol start dates and exact cost, FirstRateData's exact price and settlement-price convention, Norgate's post-lapse data access), that is stated as an open item, not asserted either way.

---

## Appendix: Databento Pass 2 verification script

Not run in Pass 1 (requires an API key — registration is Aaron's action per Hard Rule 2). This is the exact script to run immediately after registering, before any data is pulled for real:

```python
import databento as db

client = db.Historical("")  # https://databento.com/portal/keys after signup

CME_UNIVERSE = [
    "CL.FUT", "HO.FUT", "RB.FUT", "NG.FUT",                    # energy
    "GC.FUT", "SI.FUT", "HG.FUT", "PL.FUT", "PA.FUT",          # metals
    "ZC.FUT", "ZS.FUT", "ZW.FUT", "ZM.FUT", "ZL.FUT", "KE.FUT", # grains
    "LE.FUT", "HE.FUT", "GF.FUT",                              # livestock
]

# 1. Cost preview FIRST — this call itself is metadata-only and does not
#    consume the data credit. Do not proceed to an actual download until
#    this has been reviewed. Per Hard Rule 2: if either total exceeds
#    US$5, stop and get Aaron's written approval before downloading,
#    even though it should be covered by the free credit.
for schema in ("ohlcv-1d", "statistics"):
    cost = client.metadata.get_cost(
        dataset="GLBX.MDP3",
        symbols=CME_UNIVERSE,
        stype_in="parent",       # all contract months per root symbol
        schema=schema,
        start="2010-06-06",      # dataset inception
        end="2026-07-09",        # today
    )
    print(schema, "-> $", cost)

# 2. Per-symbol first-available date — cheap (1 row per symbol, ~18 rows
#    total, trivial fraction of a cent), safe to run without separate
#    approval. Confirms actual per-symbol start vs. the dataset-level
#    2010-06-06 floor asserted in this report.
for sym in CME_UNIVERSE:
    df = client.timeseries.get_range(
        dataset="GLBX.MDP3",
        symbols=[sym],
        stype_in="parent",
        schema="ohlcv-1d",
        start="2010-06-06",
        end="2011-01-01",       # narrow probe window near the floor
        limit=1,
    ).to_df()
    print(sym, "first row:", df.index.min() if len(df) else "NO DATA IN PROBE WINDOW — widen the range")
```

If the probe window returns nothing for a symbol, widen `end` in that loop before concluding it's missing — this only tests whether the symbol has data *near* the dataset floor, not whether it exists at all later on.

---

## Addendum log

### 2026-07-09 — Pass 2 corrections and confirmations

**Correction to the A.1 "KE-specific check" claim.** Pass 1 predicted that KE (KC HRW wheat) would show full dataset-era coverage on the reasoning that KCBT products moved to electronic Globex trading in January 2008, predating GLBX.MDP3's 2010-06-06 inception. This prediction was **wrong**. A live `timeseries.get_range` probe against the actual dataset (Databento API, verified 2026-07-09, see `WORKSPACE/samples/per_symbol_probe_results.json` and `WORKSPACE/samples/COST_LEDGER.md` rows #32–33) shows KE's first record in GLBX.MDP3 is **2013-12-16**, not 2010-06-06 — a gap of roughly 3.5 years versus the other 17 symbols. KE still clears the study's ≥10-year absolute minimum (≈12.6 years as of this addendum) and does not change the Track A verdict, but the reasoning in the original A.1 section should be read as superseded by this measurement. Left in place above rather than edited, per the immutable-snapshot convention; this addendum is the correction of record. Plausible explanation (unconfirmed, not investigated further given scope/budget limits): the pre-2013 electronic KC-wheat volume may have traded under a different root/product symbol before a later migration to the modern "KE" root — this is a hypothesis, not a verified fact.

**Confirmed (not merely projected) full-corpus cost.** Pass 1 stated the Databento cost preview was "expected to land well inside the $125 credit... an expectation, not a verified number." That expectation is now confirmed correct, though the magnitude was off: a live `metadata.get_cost` quote for the entire 18-symbol candidate universe, full history (2010-06-06 to 2026-07-01), across all three needed schemas came back at:

| Schema | Quoted cost (USD) |
|---|---|
| `ohlcv-1d` | $44.643947 |
| `statistics` | $20.757709 |
| `definition` | $25.256725 |
| **Total** | **$90.658381** |

This is comfortably under the $125 free credit (≈$34 of margin), and well under the $150 purchase cap. Full detail and the resulting verdict are in [DECISION_MEMO.md](DECISION_MEMO.md#pass-2-addendum--2026-07-09).

**Per-symbol history, all 18 symbols (verified, not assumed):**

| Symbols | First record in GLBX.MDP3 | ~Years of history |
|---|---|---|
| CL, HO, RB, NG, GC, SI, HG, PL, PA, ZC, ZS, ZW, ZM, ZL (14) | 2010-06-06 (dataset floor) | ~16.1 |
| LE, HE, GF (3) | 2010-06-07 | ~16.1 |
| KE (1) | 2013-12-16 | ~12.6 |

All 18 clear the ≥10-year absolute minimum; 17 of 18 clear the ≥15-year strongly-preferred bar; KE alone does not, though it still passes the floor. This is a real, verified table — see the caveat above about the 2010-06-06 rows: the probe window itself starts at 2010-06-06 (the dataset's own asserted inception per Pass 1's issue-tracker citation), so those 14 rows mean "as far back as the dataset goes," not merely "as far back as this probe looked."
