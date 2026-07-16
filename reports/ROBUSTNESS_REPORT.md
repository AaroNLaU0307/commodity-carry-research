# Robustness Report

Generated (UTC): 2026-07-16T11:38:31.666034+00:00

Runner-generated, immutable once committed (dated addenda only for any future correction). PREREGISTRATION.md Sec 8, plus the F7 ex-PA/PL diagnostic. **Every item below is reported with sign and magnitude; none gates promotion.** The primary family's own promotion verdict (`reports/PRIMARY_REPORT.md`, commit f52602e: neither H1 nor H2 promoted) is unaffected by anything in this report and is not reconsidered here.

Primary Sharpe for reference: H1 -0.0031, H2 -0.1255 (matches `reports/PRIMARY_REPORT.md` exactly -- same construction, rebuilt fresh in this runner for the diagnostics below, not re-derived differently).

## Items 1-5, 7, 10: constructed variants (Sec 8)

| Item | Description | Arm(s) | Sharpe |
|---|---|---|---|
| 1 | Sector-neutral XS (rank within sector, equal sector risk) | XS | 0.0365 |
| 2 | Quintile cutoffs instead of terciles | XS | 0.0154 |
| 3 | Equal-weight legs instead of inverse-vol | XS | 0.0139 |
| 4 | 1-month-smoothed carry | XS | 0.1648 |
| 4 | 1-month-smoothed carry | TS | -0.0562 |
| 5 | 12-month-deferred carry (front vs ~1yr contract) | XS | 0.1829 |
| 5 | 12-month-deferred carry (front vs ~1yr contract) | TS | -0.0058 |
| 6 | 2x cost table (restated from Stage 2's gate 4 construction) | XS | -0.0122 |
| 6 | 2x cost table (restated from Stage 2's gate 4 construction) | TS | -0.1223 |
| 7 | Fixed-calendar roll rule (spec completion, `DEVIATIONS.md` 2026-07-16) | XS | 0.1248 |
| 7 | Fixed-calendar roll rule (spec completion, `DEVIATIONS.md` 2026-07-16) | TS | -0.0628 |
| 10 | KE excluded entirely from the universe | XS | -0.0271 |

### Item 7 detail: rule-independence cross-check for the amended (A1) roll rule

Per its upgraded role (this session's governing instruction): item 7 now also serves as an independent cross-check of A1's timing, using a completely different (calendar-driven, not OI-crossover) roll mechanism that shares only the existence filter with A2/A1.

| Symbol | Daily dates where fixed-calendar front differs from A1's front |
|---|---|
| NG | 4,263 |
| HO | 3,405 |
| CL | 3,275 |
| HG | 3,013 |
| RB | 2,992 |
| SI | 2,983 |
| GC | 2,930 |
| PL | 2,702 |
| ZL | 1,873 |
| ZM | 1,870 |
| KE | 1,838 |
| PA | 1,661 |
| HE | 1,456 |
| ZS | 1,370 |
| LE | 1,243 |
| ZC | 1,199 |
| GF | 1,041 |
| ZW | 753 |

**Fixed-calendar tripwire status:** zero unexpected stuck-front findings (NG's two already-known transient grazes, if they recur under this variant's own timing, are treated the same as elsewhere and are not counted as new findings).

## F7 ex-PA/PL diagnostic (non-gating; N_trials unaffected, per `DEVIATIONS.md` 2026-07-11)

| Arm | Sharpe (full 18-symbol universe) | Sharpe (ex-PA/PL) |
|---|---|---|
| H1 | -0.0031 | -0.0092 |
| H2 | -0.1255 | -0.2677 |

## Items 8-9: diagnostics of the primary series (no new construction)

### Sub-period halves

| Arm | First half | Sharpe | Second half | Sharpe |
|---|---|---|---|---|
| H1 | 2010-06-07 to 2018-06-19 | 0.0435 | 2018-06-20 to 2026-06-30 | -0.0485 |
| H2 | 2010-06-07 to 2018-06-19 | -0.0747 | 2018-06-20 to 2026-06-30 | -0.1765 |

### Per-year Sharpe (annual returns already in `reports/PRIMARY_REPORT.md`)

**H1:**

| Year | Sharpe (that year's daily returns only) |
|---|---|
| 2010 | 1.8964 |
| 2011 | 0.0156 |
| 2012 | -0.4506 |
| 2013 | 0.6435 |
| 2014 | -2.6787 |
| 2015 | 0.9821 |
| 2016 | -0.3288 |
| 2017 | 1.1523 |
| 2018 | -1.4242 |
| 2019 | 0.4842 |
| 2020 | -0.2219 |
| 2021 | -0.1083 |
| 2022 | 0.4677 |
| 2023 | -0.6560 |
| 2024 | -0.2985 |
| 2025 | 0.5463 |
| 2026 | 1.7202 |

**H2:**

| Year | Sharpe (that year's daily returns only) |
|---|---|
| 2010 | -2.7494 |
| 2011 | 0.5159 |
| 2012 | -0.5425 |
| 2013 | 0.8427 |
| 2014 | -0.7851 |
| 2015 | 1.9642 |
| 2016 | -1.0346 |
| 2017 | 0.1268 |
| 2018 | 0.1040 |
| 2019 | -0.0337 |
| 2020 | -0.7915 |
| 2021 | 0.1802 |
| 2022 | 0.4319 |
| 2023 | 0.1671 |
| 2024 | -0.3020 |
| 2025 | -1.2106 |
| 2026 | 0.4856 |

### Jackknife: drop-one-year

**H1** (Sharpe with the given year's daily returns excluded):

| Year dropped | Sharpe |
|---|---|
| 2010 | -0.0783 |
| 2011 | -0.0043 |
| 2012 | 0.0255 |
| 2013 | -0.0454 |
| 2014 | 0.1780 |
| 2015 | -0.0666 |
| 2016 | 0.0174 |
| 2017 | -0.0764 |
| 2018 | 0.0934 |
| 2019 | -0.0328 |
| 2020 | 0.0124 |
| 2021 | 0.0048 |
| 2022 | -0.0348 |
| 2023 | 0.0406 |
| 2024 | 0.0159 |
| 2025 | -0.0398 |
| 2026 | -0.0569 |

**H2** (Sharpe with the given year's daily returns excluded):

| Year dropped | Sharpe |
|---|---|
| 2010 | -0.0132 |
| 2011 | -0.1674 |
| 2012 | -0.0988 |
| 2013 | -0.1891 |
| 2014 | -0.0804 |
| 2015 | -0.2652 |
| 2016 | -0.0663 |
| 2017 | -0.1415 |
| 2018 | -0.1403 |
| 2019 | -0.1313 |
| 2020 | -0.0781 |
| 2021 | -0.1462 |
| 2022 | -0.1625 |
| 2023 | -0.1454 |
| 2024 | -0.1142 |
| 2025 | -0.0519 |
| 2026 | -0.1434 |

### Jackknife: drop-one-sector

| Sector dropped | Symbols dropped | H1 Sharpe | H2 Sharpe |
|---|---|---|---|
| energy | CL, HO, RB, NG | 0.2186 | -0.0718 |
| metals | GC, SI, HG, PL, PA | -0.0671 | -0.2108 |
| grains | ZC, ZS, ZW, ZM, ZL, KE | -0.1927 | -0.1787 |
| livestock | LE, HE, GF | 0.1024 | -0.0514 |

## Sanctioned attribution decompositions (of already-computed series; no new constructions)

### (a) Gross-of-cost Sharpe, restated alongside net

| Arm | Net Sharpe | Gross-of-cost Sharpe |
|---|---|---|
| H1 | -0.0031 | 0.0061 |
| H2 | -0.1255 | -0.1288 |

### (b) H1 long-leg vs short-leg contribution split

- Long-leg annualized mean contribution: 1.8665%
- Short-leg annualized mean contribution: -1.8180%
- Long-leg cumulative contribution (sum of daily contributions, full sample): 37.2562%
- Short-leg cumulative contribution (sum of daily contributions, full sample): -36.2883%

### (c) Per-year table annotated against the 2021-22 backwardation episode

| Year | H1 return | H2 return | Note |
|---|---|---|---|
| 2010 | 16.0005% | -21.5977% |  |
| 2011 | -0.4649% | 6.1813% |  |
| 2012 | -6.1675% | -7.2463% |  |
| 2013 | 7.9970% | 10.8094% |  |
| 2014 | -30.6974% | -10.7015% |  |
| 2015 | 12.6742% | 28.6642% |  |
| 2016 | -4.6247% | -13.0592% |  |
| 2017 | 14.9351% | 0.9654% |  |
| 2018 | -18.0362% | 0.6746% |  |
| 2019 | 5.4445% | -1.0311% |  |
| 2020 | -3.8141% | -11.1862% |  |
| 2021 | -2.4298% | 1.7054% | 2021: post-COVID demand recovery outpacing supply -- widely documented broad commodity backwardation. |
| 2022 | 5.6852% | 5.1026% | 2022: Russia/Ukraine war supply shock intensified backwardation across energy and several other commodities. |
| 2023 | -8.9908% | 1.5285% |  |
| 2024 | -4.3636% | -4.3676% |  |
| 2025 | 6.7596% | -15.5766% |  |
| 2026 | 11.3038% | 2.6519% |  |

No further interpretation attempted -- this is a factual annotation of already-computed, already-reported numbers against a well-documented macro episode, not a new claim about causality or an argument for or against promotion.