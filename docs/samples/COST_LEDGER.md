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
