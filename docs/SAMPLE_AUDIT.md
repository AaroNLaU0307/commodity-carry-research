# Sample Audit — Databento GLBX.MDP3, Pass 2

**Date: 2026-07-09. Source: live Databento API calls (`metadata.get_cost` quotes + 18 real 1-row `timeseries.get_range` probes), not documentation.** Raw outputs: [`samples/COST_LEDGER.md`](samples/COST_LEDGER.md) (39 logged calls, full parameters) and [`samples/per_symbol_probe_results.json`](samples/per_symbol_probe_results.json). No raw Databento data is committed anywhere — these two files are metadata/cost records and a set of 18 single-row date probes, not the licensed dataset itself.

This audit maps the verified findings against the Track A study requirements from the governing brief, requirement by requirement. No forward returns, carry values, or rankings were computed at any point — every call below is a cost quote or a 1-row existence probe.

---

## Universe & sectors

**Requirement:** target 15–25 commodities across ≥4 sectors; minimum viable ≥12 across ≥3 sectors.

**Result: MEETS TARGET, not just minimum viable.** 18 symbols, 4 sectors (energy 4, metals 5, grains 6, livestock 3). All 18 resolved successfully against Databento's parent symbology (`stype_in=parent`, `SYM.FUT` form) — no symbol errored or came back empty at the quote stage, meaning all 18 are real, tradeable, currently-known instrument roots on GLBX.MDP3.

Softs (SB, KC, CC, CT) remain excluded per the Pass 1 finding (IFUS.IMPACT coverage only from 2018-12-23, fails the 10-year minimum) — not re-tested this pass since that finding didn't depend on account access and Databento's own dataset page was authoritative.

## Term structure

**Requirement:** at least two simultaneous contract prices per commodity; individual contract-month series is the preferred form (a).

**Result: MEETS, structurally confirmed.** All requests used `stype_in="parent"`, which resolves to every individual contract-month instrument under each root symbol — this is form (a), the best of the three acceptable forms, not a continuous-series proxy. Not independently re-verified in this sample audit beyond what parent symbology inherently provides (i.e., no explicit check was made that ≥2 contract months are simultaneously live for a given calendar date), because doing so would require pulling real multi-row data, which is out of scope for a probe-only sample audit. This is a low-risk gap: CME futures markets structurally always have multiple listed contract months trading simultaneously by design, so this isn't expected to be a real risk, but it wasn't independently measured here either — flag as a formality to confirm once the real corpus is pulled, not a suspected problem.

## History length (per symbol)

**Requirement:** ≥15 years strongly preferred; ≥10 years absolute minimum; record exact per-symbol start date, don't assume.

**Result: ALL 18 MEET THE ABSOLUTE MINIMUM. 17 of 18 clear the preferred bar; KE does not.**

| Symbol | Sector | First record (probe, UTC) | Years as of 2026-07-09 | vs. 15yr preferred | vs. 10yr minimum |
|---|---|---|---|---|---|
| CL | energy | 2010-06-06 | ~16.1 | meets | meets |
| HO | energy | 2010-06-06 | ~16.1 | meets | meets |
| RB | energy | 2010-06-06 | ~16.1 | meets | meets |
| NG | energy | 2010-06-06 | ~16.1 | meets | meets |
| GC | metals | 2010-06-06 | ~16.1 | meets | meets |
| SI | metals | 2010-06-06 | ~16.1 | meets | meets |
| HG | metals | 2010-06-06 | ~16.1 | meets | meets |
| PL | metals | 2010-06-06 | ~16.1 | meets | meets |
| PA | metals | 2010-06-06 | ~16.1 | meets | meets |
| ZC | grains | 2010-06-06 | ~16.1 | meets | meets |
| ZS | grains | 2010-06-06 | ~16.1 | meets | meets |
| ZW | grains | 2010-06-06 | ~16.1 | meets | meets |
| ZM | grains | 2010-06-06 | ~16.1 | meets | meets |
| ZL | grains | 2010-06-06 | ~16.1 | meets | meets |
| **KE** | **grains** | **2013-12-16** | **~12.6** | **does not meet** | **meets** |
| LE | livestock | 2010-06-07 | ~16.1 | meets | meets |
| HE | livestock | 2010-06-07 | ~16.1 | meets | meets |
| GF | livestock | 2010-06-07 | ~16.1 | meets | meets |

Method: `timeseries.get_range(dataset=GLBX.MDP3, symbols=[SYM.FUT], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1)`, one real (metered, ~$0.00001 each) pull per symbol, reading `df.index.min()`. The 2010-06-06/07 rows reflect the probe window's own start boundary; since 2010-06-06 is independently asserted as GLBX.MDP3's own overall inception (Pass 1, Databento issue-tracker citation), those results mean "as far back as the dataset goes," not an artifact of the probe not looking further back. This interpretation is reasonable but not itself independently re-verified via `metadata.get_dataset_range` this session (that call was not in the pre-approved whitelist of this run).

**Consequence for the universe test:** all 18 individually pass the absolute-minimum criterion, so the ≥12-symbol/≥3-sector bar is met either with or without KE. KE's shorter history is a real fact for the pre-registration to weigh (uniform start date across the universe would mean either accepting 2013-12-16 as the common start for all 18 — losing ~3.5 years on the other 17 — or running KE on a staggered/shorter window) but it is not a Phase 0 gate failure.

## Fields: settlement price, open interest, expiry calendar

**Requirement:** settlement price mandatory; volume + open interest strongly preferred; expiry calendar mandatory.

**Result: settlement + OI confirmed available and priceable; expiry calendar confirmed requestable, field-level content not independently verified this session.**

- **Settlement + open interest** (`statistics` schema): full-corpus quote succeeded ($20.757709 for all 18 symbols, full history) — confirms the schema is valid and requestable for this exact symbol set. Field-level content (i.e., pulling one real row and confirming a `stat_type` value corresponding to settlement is populated) was not done in this sample audit — the `statistics` schema was whitelisted for quotes in this session but per-symbol real probes were only run against `ohlcv-1d`, to keep the real-spend footprint minimal. This is a reasonable, low-risk gap (Databento's own docs, cited in Pass 1, are explicit that settlement + OI live here) but is not yet a first-party-confirmed data point the way the `ohlcv-1d` history table above is.
- **Expiry calendar** (`definition` schema): full-corpus quote succeeded ($25.256725). Per the Pass 2 kickoff's explicit whitelist, `definition` is quote-only this session — no download, even a 1-row probe, was executed against it. The quote succeeding confirms the request is well-formed and priced; it does not confirm the returned records actually carry a populated expiration field. This is expected to be fine (Databento's definition schema is documented, in general, to carry instrument reference data including expiration for derivatives) but is the one requirement in this audit that rests on documentation plus a successful price quote, not a first-party content check.

## Frequency

**Requirement:** daily preferred, monthly acceptable.

**Result: MEETS.** `ohlcv-1d` is daily; confirmed both by successful quoting and by 18 successful real 1-row pulls returning dated rows.

## Cost

**Requirement:** total out-of-pocket cost ≤ US$150 (free credits count as free).

**Result: MEETS, with margin.** Full candidate corpus (18 symbols × `ohlcv-1d` + `statistics` + `definition` × full history 2010-06-06 to 2026-07-01): **$90.66**, against a $125 free credit — a real, live quote, not a projection. Out-of-pocket exposure is $0 as long as Aaron's credit balance is intact (starting-balance confirmation from the Billing page is still an open item for the session's final reconciliation, tracked in the decision memo, but the margin here is wide enough — ~$34 — that this is very unlikely to change the verdict even accounting for some prior incidental usage).

This session's actual real spend across all quoting + probing: **$0.000178** (18 one-row pulls at ~$0.00001 each). Full ledger in `samples/COST_LEDGER.md`.

## Integrity

**Requirement:** checksums on everything retrieved; gap audit; documented/reproducible roll construction if used.

**Result: N/A for this pass, correctly.** No bulk data was retrieved this session (only cost quotes and 18 single-row probes), so there is nothing substantial to checksum yet — Hard Rule 7 (raw licensed data never committed; checksums and provenance manifests are) applies once the real corpus is actually pulled, which has not happened. A gap audit and roll-construction documentation are Phase-1-download-time activities, not Phase-0 activities, and remain correctly out of scope here.

The 18-row probe results and the cost ledger are themselves reproducible: both are generated by [`scripts/pass2_databento_verify.py`](scripts/pass2_databento_verify.py), which is deterministic given the same account state (same free-credit balance, same dataset), and which is committed to the scaffolded repo (see below) so the exact request parameters are auditable, not just their output.

---

## Summary verdict feeding into the decision memo

Every PASS(A) sub-criterion resolves favorably against the pre-declared criteria as written:

| Criterion | Status |
|---|---|
| ≥12 commodities, ≥3 sectors | MEETS (18, 4) |
| ≥10 years per symbol | MEETS (all 18, verified; KE tightest at ~12.6yr) |
| Two-point term structure | MEETS (parent symbology, structurally; not independently re-measured this pass) |
| Monthly-or-better frequency | MEETS (daily, verified via real pulls) |
| Settlement price | MEETS (schema confirmed + priced; field-level content not independently pulled this session) |
| Expiry calendar | MEETS (schema confirmed + priced; quote-only per this session's whitelist, field-level content not pulled) |
| Cost ≤ $150 (free credit counts as free) | MEETS ($90.66 quoted, $125 credit available, $0 out-of-pocket expected) |

No criterion required relaxation or an adaptation proposal. See [DECISION_MEMO.md](DECISION_MEMO.md#pass-2-addendum--2026-07-09) for the formal verdict statement and what happens next.
