# Cost Ledger -- Databento Pass 2

Session start (UTC): 2026-07-09T09:53:54.369097+00:00

Two tracks: QUOTE rows (get_cost, never billed, unrestricted) and REAL SPEND rows (actual get_range pulls, capped at $2.0/call and $5.0 cumulative).

| # | UTC time | Track | Call type | Params | Cost (USD) | Cumulative (USD) | Note |
|---|---|---|---|---|---|---|---|
| 1 | 2026-07-09T09:53:56.712552+00:00 | QUOTE | get_cost | full-corpus projection [ohlcv-1d]: dataset=GLBX.MDP3, symbols=['CL.FUT', 'HO.FUT', 'RB.FUT', 'NG.FUT', 'GC.FUT', 'SI.FUT', 'HG.FUT', 'PL.FUT', 'PA.FUT', 'ZC.FUT', 'ZS.FUT', 'ZW.FUT', 'ZM.FUT', 'ZL.FUT', 'KE.FUT', 'LE.FUT', 'HE.FUT', 'GF.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2026-07-01 | 44.643947 | 44.643947 |  |
| 2 | 2026-07-09T09:53:58.353261+00:00 | QUOTE | get_cost | full-corpus projection [statistics]: dataset=GLBX.MDP3, symbols=['CL.FUT', 'HO.FUT', 'RB.FUT', 'NG.FUT', 'GC.FUT', 'SI.FUT', 'HG.FUT', 'PL.FUT', 'PA.FUT', 'ZC.FUT', 'ZS.FUT', 'ZW.FUT', 'ZM.FUT', 'ZL.FUT', 'KE.FUT', 'LE.FUT', 'HE.FUT', 'GF.FUT'], stype_in=parent, schema=statistics, start=2010-06-06, end=2026-07-01 | 20.757709 | 65.401656 |  |
| 3 | 2026-07-09T09:53:59.727591+00:00 | QUOTE | get_cost | full-corpus projection [definition]: dataset=GLBX.MDP3, symbols=['CL.FUT', 'HO.FUT', 'RB.FUT', 'NG.FUT', 'GC.FUT', 'SI.FUT', 'HG.FUT', 'PL.FUT', 'PA.FUT', 'ZC.FUT', 'ZS.FUT', 'ZW.FUT', 'ZM.FUT', 'ZL.FUT', 'KE.FUT', 'LE.FUT', 'HE.FUT', 'GF.FUT'], stype_in=parent, schema=definition, start=2010-06-06, end=2026-07-01 | 25.256725 | 90.658381 |  |
| 4 | 2026-07-09T09:54:01.442438+00:00 | QUOTE | get_cost (pre-pull check) | probe [CL.FUT]: dataset=GLBX.MDP3, symbols=['CL.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658391 |  |
| 5 | 2026-07-09T09:54:07.655240+00:00 | REAL SPEND | get_range (actual pull) | probe [CL.FUT]: dataset=GLBX.MDP3, symbols=['CL.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000010 |  |
| 6 | 2026-07-09T09:54:09.249062+00:00 | QUOTE | get_cost (pre-pull check) | probe [HO.FUT]: dataset=GLBX.MDP3, symbols=['HO.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658401 |  |
| 7 | 2026-07-09T09:54:17.395631+00:00 | REAL SPEND | get_range (actual pull) | probe [HO.FUT]: dataset=GLBX.MDP3, symbols=['HO.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000020 |  |
| 8 | 2026-07-09T09:54:18.872600+00:00 | QUOTE | get_cost (pre-pull check) | probe [RB.FUT]: dataset=GLBX.MDP3, symbols=['RB.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658411 |  |
| 9 | 2026-07-09T09:54:25.688630+00:00 | REAL SPEND | get_range (actual pull) | probe [RB.FUT]: dataset=GLBX.MDP3, symbols=['RB.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000030 |  |
| 10 | 2026-07-09T09:54:27.010393+00:00 | QUOTE | get_cost (pre-pull check) | probe [NG.FUT]: dataset=GLBX.MDP3, symbols=['NG.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658421 |  |
| 11 | 2026-07-09T09:54:36.086414+00:00 | REAL SPEND | get_range (actual pull) | probe [NG.FUT]: dataset=GLBX.MDP3, symbols=['NG.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000040 |  |
| 12 | 2026-07-09T09:54:37.848694+00:00 | QUOTE | get_cost (pre-pull check) | probe [GC.FUT]: dataset=GLBX.MDP3, symbols=['GC.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658431 |  |
| 13 | 2026-07-09T09:55:08.202205+00:00 | REAL SPEND | get_range (actual pull) | probe [GC.FUT]: dataset=GLBX.MDP3, symbols=['GC.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000050 |  |
| 14 | 2026-07-09T09:55:09.679674+00:00 | QUOTE | get_cost (pre-pull check) | probe [SI.FUT]: dataset=GLBX.MDP3, symbols=['SI.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658441 |  |
| 15 | 2026-07-09T09:55:18.420425+00:00 | REAL SPEND | get_range (actual pull) | probe [SI.FUT]: dataset=GLBX.MDP3, symbols=['SI.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000059 |  |
| 16 | 2026-07-09T09:55:20.068125+00:00 | QUOTE | get_cost (pre-pull check) | probe [HG.FUT]: dataset=GLBX.MDP3, symbols=['HG.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658451 |  |
| 17 | 2026-07-09T09:55:28.951040+00:00 | REAL SPEND | get_range (actual pull) | probe [HG.FUT]: dataset=GLBX.MDP3, symbols=['HG.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000069 |  |
| 18 | 2026-07-09T09:55:30.693319+00:00 | QUOTE | get_cost (pre-pull check) | probe [PL.FUT]: dataset=GLBX.MDP3, symbols=['PL.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658461 |  |
| 19 | 2026-07-09T09:55:37.392301+00:00 | REAL SPEND | get_range (actual pull) | probe [PL.FUT]: dataset=GLBX.MDP3, symbols=['PL.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000079 |  |
| 20 | 2026-07-09T09:55:38.830522+00:00 | QUOTE | get_cost (pre-pull check) | probe [PA.FUT]: dataset=GLBX.MDP3, symbols=['PA.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658471 |  |
| 21 | 2026-07-09T09:55:43.997310+00:00 | REAL SPEND | get_range (actual pull) | probe [PA.FUT]: dataset=GLBX.MDP3, symbols=['PA.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000089 |  |
| 22 | 2026-07-09T09:55:45.730859+00:00 | QUOTE | get_cost (pre-pull check) | probe [ZC.FUT]: dataset=GLBX.MDP3, symbols=['ZC.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658481 |  |
| 23 | 2026-07-09T09:56:02.885437+00:00 | REAL SPEND | get_range (actual pull) | probe [ZC.FUT]: dataset=GLBX.MDP3, symbols=['ZC.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000099 |  |
| 24 | 2026-07-09T09:56:04.796795+00:00 | QUOTE | get_cost (pre-pull check) | probe [ZS.FUT]: dataset=GLBX.MDP3, symbols=['ZS.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658490 |  |
| 25 | 2026-07-09T09:56:12.093777+00:00 | REAL SPEND | get_range (actual pull) | probe [ZS.FUT]: dataset=GLBX.MDP3, symbols=['ZS.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000109 |  |
| 26 | 2026-07-09T09:56:15.125500+00:00 | QUOTE | get_cost (pre-pull check) | probe [ZW.FUT]: dataset=GLBX.MDP3, symbols=['ZW.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658500 |  |
| 27 | 2026-07-09T09:56:31.787982+00:00 | REAL SPEND | get_range (actual pull) | probe [ZW.FUT]: dataset=GLBX.MDP3, symbols=['ZW.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000119 |  |
| 28 | 2026-07-09T09:56:33.214843+00:00 | QUOTE | get_cost (pre-pull check) | probe [ZM.FUT]: dataset=GLBX.MDP3, symbols=['ZM.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658510 |  |
| 29 | 2026-07-09T09:56:40.670667+00:00 | REAL SPEND | get_range (actual pull) | probe [ZM.FUT]: dataset=GLBX.MDP3, symbols=['ZM.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000129 |  |
| 30 | 2026-07-09T09:56:43.946156+00:00 | QUOTE | get_cost (pre-pull check) | probe [ZL.FUT]: dataset=GLBX.MDP3, symbols=['ZL.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658520 |  |
| 31 | 2026-07-09T09:56:52.615825+00:00 | REAL SPEND | get_range (actual pull) | probe [ZL.FUT]: dataset=GLBX.MDP3, symbols=['ZL.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000139 |  |
| 32 | 2026-07-09T09:57:02.231509+00:00 | QUOTE | get_cost (pre-pull check) | probe [KE.FUT]: dataset=GLBX.MDP3, symbols=['KE.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658530 |  |
| 33 | 2026-07-09T09:57:08.342474+00:00 | REAL SPEND | get_range (actual pull) | probe [KE.FUT]: dataset=GLBX.MDP3, symbols=['KE.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000149 |  |
| 34 | 2026-07-09T09:57:10.379448+00:00 | QUOTE | get_cost (pre-pull check) | probe [LE.FUT]: dataset=GLBX.MDP3, symbols=['LE.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658540 |  |
| 35 | 2026-07-09T09:57:19.127408+00:00 | REAL SPEND | get_range (actual pull) | probe [LE.FUT]: dataset=GLBX.MDP3, symbols=['LE.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000159 |  |
| 36 | 2026-07-09T09:57:27.610676+00:00 | QUOTE | get_cost (pre-pull check) | probe [HE.FUT]: dataset=GLBX.MDP3, symbols=['HE.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658550 |  |
| 37 | 2026-07-09T09:57:36.297342+00:00 | REAL SPEND | get_range (actual pull) | probe [HE.FUT]: dataset=GLBX.MDP3, symbols=['HE.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000168 |  |
| 38 | 2026-07-09T09:57:37.999528+00:00 | QUOTE | get_cost (pre-pull check) | probe [GF.FUT]: dataset=GLBX.MDP3, symbols=['GF.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 90.658560 |  |
| 39 | 2026-07-09T09:57:44.913697+00:00 | REAL SPEND | get_range (actual pull) | probe [GF.FUT]: dataset=GLBX.MDP3, symbols=['GF.FUT'], stype_in=parent, schema=ohlcv-1d, start=2010-06-06, end=2020-01-01, limit=1 | 0.000010 | 0.000178 |  |

### Phase 1a corpus pull -- session start (UTC): 2026-07-09T23:00:36.319058+00:00
| 40 | 2026-07-09T23:00:37.775399+00:00 | QUOTE | get_cost (Phase 1a re-quote) | schema=ohlcv-1d symbols=18 start=2010-06-06 end=2026-07-01 | 44.643947 | 135.302507 |  |
| 41 | 2026-07-09T23:00:39.286419+00:00 | QUOTE | get_cost (Phase 1a re-quote) | schema=statistics symbols=18 start=2010-06-06 end=2026-07-01 | 20.757709 | 156.060216 |  |
| 42 | 2026-07-09T23:00:40.503327+00:00 | QUOTE | get_cost (Phase 1a re-quote) | schema=definition symbols=18 start=2010-06-06 end=2026-07-01 | 25.256725 | 181.316941 |  |
| 43 | 2026-07-09T23:03:47.660182+00:00 | REAL SPEND | get_range (Phase 1a corpus pull, actual) | schema=ohlcv-1d symbols=18 start=2010-06-06 end=2026-07-01 path=ohlcv-1d.dbn.zst | 44.643947 | 44.644125 |  |

STOP: BentoError during pull of schema=statistics: 504 The remote gateway timed out.

### Phase 1a retry (statistics, definition) -- 2026-07-09T23:06:38.395427+00:00

STOP: statistics failed 3 attempts, last error: 504 The remote gateway timed out.

### Phase 1a retry #2 (definition unchunked; statistics chunked yearly) -- 2026-07-09T23:11:43.494546+00:00

definition unchunked attempt failed: 504 The remote gateway timed out. -- will need its own retry
| 45 | 2026-07-09T23:12:47.419757+00:00 | QUOTE | get_cost (Phase 1a retry#2, statistics chunk) | schema=statistics symbols=18 start=2010-06-06 end=2011-01-01 | 0.432013 | 181.748954 |  |
| 46 | 2026-07-10T00:16:23.712900+00:00 | REAL SPEND | get_range (Phase 1a retry#2, statistics chunk, actual) | schema=statistics symbols=18 start=2010-06-06 end=2011-01-01 path=statistics_2010-06-06_2011-01-01.dbn.zst | 0.432013 | 45.076138 |  |
| 47 | 2026-07-10T00:16:25.635923+00:00 | QUOTE | get_cost (Phase 1a retry#2, statistics chunk) | schema=statistics symbols=18 start=2011-01-01 end=2012-01-01 | 0.790831 | 182.539785 |  |

statistics chunk 2011-01-01..2012-01-01 failed: Error streaming response: Response ended prematurely
| 48 | 2026-07-10T00:50:00.371136+00:00 | QUOTE | get_cost (Phase 1a retry#2, statistics chunk) | schema=statistics symbols=18 start=2012-01-01 end=2013-01-01 | 0.659588 | 183.199373 |  |
| 49 | 2026-07-10T01:52:41.171362+00:00 | REAL SPEND | get_range (Phase 1a retry#2, statistics chunk, actual) | schema=statistics symbols=18 start=2012-01-01 end=2013-01-01 path=statistics_2012-01-01_2013-01-01.dbn.zst | 0.659588 | 45.735726 |  |
| 50 | 2026-07-10T01:52:44.798277+00:00 | QUOTE | get_cost (Phase 1a retry#2, statistics chunk) | schema=statistics symbols=18 start=2013-01-01 end=2014-01-01 | 0.717631 | 183.917004 |  |
| 51 | 2026-07-10T02:46:30.459783+00:00 | REAL SPEND | get_range (Phase 1a retry#2, statistics chunk, actual) | schema=statistics symbols=18 start=2013-01-01 end=2014-01-01 path=statistics_2013-01-01_2014-01-01.dbn.zst | 0.717631 | 46.453357 |  |
| 52 | 2026-07-10T02:46:31.919397+00:00 | QUOTE | get_cost (Phase 1a retry#2, statistics chunk) | schema=statistics symbols=18 start=2014-01-01 end=2015-01-01 | 0.758321 | 184.675326 |  |

statistics chunk 2014-01-01..2015-01-01 failed: Error streaming response: Response ended prematurely
| 53 | 2026-07-10T03:45:22.347779+00:00 | QUOTE | get_cost (Phase 1a retry#2, statistics chunk) | schema=statistics symbols=18 start=2015-01-01 end=2016-01-01 | 0.911303 | 185.586629 |  |
| 54 | 2026-07-10T04:49:35.255073+00:00 | REAL SPEND | get_range (Phase 1a retry#2, statistics chunk, actual) | schema=statistics symbols=18 start=2015-01-01 end=2016-01-01 path=statistics_2015-01-01_2016-01-01.dbn.zst | 0.911303 | 47.364661 |  |
| 55 | 2026-07-10T04:49:57.169548+00:00 | QUOTE | get_cost (Phase 1a retry#2, statistics chunk) | schema=statistics symbols=18 start=2016-01-01 end=2017-01-01 | 1.373427 | 186.960056 |  |

statistics chunk 2016-01-01..2017-01-01 failed: 504 The remote gateway timed out.
| 56 | 2026-07-10T04:51:03.142494+00:00 | QUOTE | get_cost (Phase 1a retry#2, statistics chunk) | schema=statistics symbols=18 start=2017-01-01 end=2018-01-01 | 1.261575 | 188.221631 |  |

### Phase 1a follow-up session -- inventory & reconciliation, 2026-07-10T05:40:00+00:00 (approx, session start)

**Leftover process from session 1 was still alive** (PID 12920, matching the exact start timestamp of the "Phase 1a retry #2" run) and had continued working through statistics chunks unattended for ~6.5 hours after session 1 ended. Stopped cleanly this session (Stop-Process) once confirmed identified, since Step 2 of this session's brief mandates switching to the batch-job API for all remaining work -- running the old synchronous script concurrently with new batch jobs would risk ledger race conditions and billing ambiguity on top of what's already unresolved below.

**Inventory as found (before any deletion):**

| Chunk | File size (bytes) | Ledger status | Classification |
|---|---|---|---|
| ohlcv-1d (full range) | 107,229,003 | REAL SPEND row 43, $44.643947 | Confirmed complete; SHA-256 re-verified this session, matches data/MANIFEST.md exactly |
| statistics 2010-06-06..2011-01-01 | 114,164,811 | REAL SPEND row 46, $0.432013 | Confirmed complete and billed |
| statistics 2011-01-01..2012-01-01 | 95,283,524 | QUOTE row 47 ($0.790831) only -- client error "Response ended prematurely", no REAL SPEND logged | **Ambiguous**: real bytes clearly transferred (95MB), but transfer did not complete cleanly. Cannot determine from the client side alone whether Databento billed for the partial delivery. |
| statistics 2012-01-01..2013-01-01 | 165,856,063 | REAL SPEND row 49, $0.659588 | Confirmed complete and billed |
| statistics 2013-01-01..2014-01-01 | 173,505,255 | REAL SPEND row 51, $0.717631 | Confirmed complete and billed |
| statistics 2014-01-01..2015-01-01 | 176,919,370 | QUOTE row 52 ($0.758321) only -- same "Response ended prematurely" error, no REAL SPEND logged | **Ambiguous**, same reasoning as the 2011-2012 chunk |
| statistics 2015-01-01..2016-01-01 | 231,384,865 | REAL SPEND row 54, $0.911303 | Confirmed complete and billed |
| statistics 2016-01-01..2017-01-01 | *(no file created)* | QUOTE row 55 ($1.373427) only -- clean `504 gateway timeout`, zero bytes streamed | Confirmed NOT delivered, confirmed NOT billed (no data ever left Databento's side) |
| statistics 2017-01-01..2018-01-01 | 254,610,660 (frozen at kill) | QUOTE row 56 ($1.261575) only -- in-flight when the leftover process was stopped this session | **Ambiguous**, same reasoning as the other two partial-transfer chunks (real bytes transferred, transfer not completed cleanly, this time by a deliberate kill rather than a client-side error, which does not change what may have been billed server-side) |

**Reconciliation:**
- Confirmed billed (ledger REAL SPEND rows): **$47.364661** (ohlcv-1d $44.643947 + 4 complete statistics chunks $2.720535).
- Ambiguous, worst-case additional if all three partial transfers were in fact billed for bytes delivered: 2011-2012 ($0.790831) + 2014-2015 ($0.758321) + 2017-2018 ($1.261575) = **$2.810727**.
- Confirmed not billed: 2016-2017 ($1.373427, no data delivered).
- **Worst-case cumulative-billed-so-far: $50.175388.**

**Completion plan (Step 2): one fresh, comprehensive batch job per schema for the full locked range** (`statistics`: 2010-06-06 to 2026-07-01 exclusive; `definition`: same), rather than trying to salvage the 3 ambiguous partial files or stitch together the 4 confirmed chunks with a batch-job continuation. Per the governing brief's own "simplicity beats salvage at these dollar amounts": the incremental cost of re-pulling the ~4 years already confirmed-clean is a few dollars against a $100 ceiling, and a single atomic, verifiably-complete file per schema is safer than reconciling partial provenance across a patchwork of chunk files with mixed confidence. The 3 ambiguous partial files and the 4 confirmed-complete chunk files are all superseded by this plan and will be removed (see the deletion log immediately below for the partials; the confirmed-complete chunks are kept until the fresh full-range files are verified successful, then removed as redundant).

**Ceiling check:** worst-case cumulative-billed-so-far ($50.175388) + projected fresh full-range quotes (~$20.76 statistics + ~$25.26 definition, per the Pass 2-era estimate, to be re-confirmed via real get_cost calls before submission) ≈ **$96.20 worst case**, comfortably under the **$100 CUMULATIVE_CEILING**. Real get_cost quotes will be logged and re-checked against the ceiling before any batch job is actually submitted, per standing guardrails. Plan proceeds.

**Note on POST_PULL_BALANCE:** Step 1.2 permits asking Aaron for the portal's current remaining-credit figure "if needed to pin down what the partial chunks cost." Not asked mid-session here, since the worst-case bound above already fits the ceiling regardless of how the 3 ambiguous chunks resolve -- deferred to the standard end-of-pull POST_PULL_BALANCE reconciliation (Step 2.4), where it will also resolve this ambiguity definitively.

**Deletion log (stale/ambiguous partial files, checksummed before removal, per Step 1.4):**

| File | Size at deletion (bytes) | SHA-256 at deletion |
|---|---|---|
| `statistics_2011-01-01_2012-01-01.dbn.zst` | 95,283,524 | `70a90d1b78b75a9663083bd5cfb42e18d8df8c260d2909a682496b249d0a17d7` |
| `statistics_2014-01-01_2015-01-01.dbn.zst` | 176,919,370 | `bb86a88bcb690230e94f3c57b60221a93442d6a44ac1e0b823e2c5162e78fdf9` |
| `statistics_2017-01-01_2018-01-01.dbn.zst` | 254,610,660 | `012c1c212edf469402277e69ae3bf89d07e70a65475a6ac2bff71ef8cfb59405` |

These are recorded for the record only (in case the ambiguous-billing question ever needs revisiting); none are treated as usable data going forward -- superseded by the fresh full-range batch-job pull in Step 2.


### Phase 1a follow-up -- batch job submission, 2026-07-10T05:44:25.095802+00:00

| Schema | Quoted (USD) | Job ID | Submitted |
|---|---|---|---|
| statistics | 20.757709 | `GLBX-20260710-E8YMQQJMA7` | yes -- billed on submission per SDK docstring, logged as REAL SPEND now |
| definition | 25.256725 | `GLBX-20260710-BN6B8WQRWH` | yes -- billed on submission per SDK docstring, logged as REAL SPEND now |

Running cumulative after this session's batch submissions (worst-case basis): $96.189823
