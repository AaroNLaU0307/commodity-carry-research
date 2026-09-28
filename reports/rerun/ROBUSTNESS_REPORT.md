# Robustness Report

Generated (UTC): 2026-09-28T15:46:57.109867+00:00 · code `70d1e0392f7112042d5855d57df9ca3e54bfda1a`

Runner-generated (`scripts/phase1c_robustness.py`). PREREGISTRATION.md Sec 8, the F7 ex-PA/PL diagnostic and the execution-lag-1 sensitivity (`preregistration/AMENDMENT_2026-09-27.md`). This run follows the 2026-09-27 corrections (`reports/ADDENDUM_2026-09-27.md`); the published pre-correction report, `reports/ROBUSTNESS_REPORT.md`, stays unchanged. **Every item below is reported with sign and magnitude; none gates promotion.** The primary family's promotion verdict (`reports/rerun/PRIMARY_REPORT.md`: H1: NOT PROMOTED, H2: closed at premise (Sec 7)) is unaffected by anything in this report.

Primary Sharpe for reference: H1 0.0591 (matches `results/primary_summary.json`).

## Items 1-7, 10: constructed variants (Sec 8)

| Item | Description | Arm(s) | Sharpe |
|---|---|---|---|
| 1 | Sector-neutral XS (rank within sector, equal sector risk) | XS | 0.1587 |
| 2 | Quintile cutoffs instead of terciles | XS | 0.0584 |
| 3 | Equal-weight legs instead of inverse-vol | XS | 0.0520 |
| 4 | 1-month-smoothed carry | XS | 0.2313 |
| 5 | 12-month-deferred carry (front vs ~1yr contract) | XS | 0.1750 |
| 6 | 2x cost table | XS | 0.0322 |
| 7 | Fixed-calendar roll rule | XS | 0.1013 |
| 10 | KE excluded entirely from the universe | XS | 0.0603 |

## Execution-timing sensitivity (registered 2026-09-27; counted in N_trials)

The primary construction with execution one trading day after the signal: entry at settle(t+1), first return settle(t+1) -> settle(t+2).

| Arm | Sharpe, execution at the signal settlement (registered) | Sharpe, execution one day later |
|---|---|---|
| H1 | 0.0591 | 0.0140 |

### Item 7 detail: rule-independence cross-check for the amended (A1) roll rule

Calendar-driven roll timing (last business day of the month before the front's expiry month) sharing only the existence filter with A1/A2.

| Symbol | Daily dates where fixed-calendar front differs from A1's front |
|---|---|
| HG | 3,239 |
| SI | 2,986 |
| PL | 2,948 |
| GC | 2,850 |
| CL | 2,163 |
| ZL | 2,100 |
| ZM | 2,040 |
| PA | 2,026 |
| HO | 1,942 |
| NG | 1,927 |
| HE | 1,908 |
| RB | 1,773 |
| ZS | 1,715 |
| KE | 1,712 |
| ZC | 1,475 |
| LE | 1,294 |
| GF | 1,289 |
| ZW | 1,074 |

**Fixed-calendar tripwire status:** zero unexpected stuck-front findings (NG's two known transient grazes are not counted as new findings).

## F7 ex-PA/PL diagnostic (non-gating; not counted in N_trials)

| Arm | Sharpe (full universe) | Sharpe (ex-PA/PL) |
|---|---|---|
| H1 | 0.0591 | -0.1027 |

## Items 8-9: diagnostics of the primary series (no new construction)

### Sub-period halves

| Arm | First half | Sharpe | Second half | Sharpe |
|---|---|---|---|---|
| H1 | 2010-06-08 to 2018-06-14 | 0.1173 | 2018-06-15 to 2026-06-30 | 0.0016 |

### Per-year Sharpe (annual returns are in `reports/rerun/PRIMARY_REPORT.md`)

**H1:**

| Year | Sharpe (that year's daily returns only) |
|---|---|
| 2010 | 2.0356 |
| 2011 | -0.0839 |
| 2012 | -0.6102 |
| 2013 | 1.5138 |
| 2014 | -2.8300 |
| 2015 | 0.7443 |
| 2016 | -0.2799 |
| 2017 | 1.4016 |
| 2018 | -0.5897 |
| 2019 | 0.6808 |
| 2020 | -1.1278 |
| 2021 | 0.1180 |
| 2022 | 0.3249 |
| 2023 | -0.6040 |
| 2024 | 0.0383 |
| 2025 | 0.4527 |
| 2026 | 1.3180 |

### Jackknife: drop-one-year

**H1** (Sharpe with the given year's daily returns excluded):

| Year dropped | Sharpe |
|---|---|
| 2010 | -0.0302 |
| 2011 | 0.0685 |
| 2012 | 0.0996 |
| 2013 | -0.0353 |
| 2014 | 0.2545 |
| 2015 | 0.0143 |
| 2016 | 0.0801 |
| 2017 | -0.0255 |
| 2018 | 0.1043 |
| 2019 | 0.0223 |
| 2020 | 0.1415 |
| 2021 | 0.0549 |
| 2022 | 0.0412 |
| 2023 | 0.1043 |
| 2024 | 0.0604 |
| 2025 | 0.0315 |
| 2026 | 0.0225 |

### Jackknife: drop-one-sector

| Sector dropped | Symbols dropped | H1 Sharpe | H2 Sharpe |
|---|---|---|---|
| energy | CL, HO, RB, NG | 0.1808 | -- |
| metals | GC, SI, HG, PL, PA | -0.1260 | -- |
| grains | ZC, ZS, ZW, ZM, ZL, KE | -0.2194 | -- |
| livestock | LE, HE, GF | 0.1848 | -- |

## Attribution decompositions (of already-computed series; no new constructions)

### (a) Gross-of-cost Sharpe, restated alongside net

Same positions and leverage path; only the costs are removed.

| Arm | Net Sharpe | Gross-of-cost Sharpe |
|---|---|---|
| H1 | 0.0591 | 0.0860 |

### (b) H1 long-leg vs short-leg contribution split

Each leg's levered daily contribution net of its own trading and roll costs.

- Long-leg annualized mean contribution: 1.9621%
- Short-leg annualized mean contribution: -1.3069%
- Long-leg cumulative contribution (sum of daily contributions, full sample): 31.6817%
- Short-leg cumulative contribution (sum of daily contributions, full sample): -21.1022%

### (c) Per-year table annotated against the 2021-22 backwardation episode

| Year | H1 return | H2 return | Note |
|---|---|---|---|
| 2010 | 15.7116% | -- |  |
| 2011 | -1.4258% | -- |  |
| 2012 | -6.2261% | -- |  |
| 2013 | 16.4732% | -- |  |
| 2014 | -26.8510% | -- |  |
| 2015 | 7.5539% | -- |  |
| 2016 | -3.2484% | -- |  |
| 2017 | 14.7054% | -- |  |
| 2018 | -6.9382% | -- |  |
| 2019 | 6.2493% | -- |  |
| 2020 | -12.3244% | -- |  |
| 2021 | 0.7003% | -- | 2021: post-COVID demand recovery outpacing supply -- widely documented broad commodity backwardation. |
| 2022 | 2.9657% | -- | 2022: Russia/Ukraine war supply shock intensified backwardation across energy and several other commodities. |
| 2023 | -6.9432% | -- |  |
| 2024 | -0.1214% | -- |  |
| 2025 | 4.5620% | -- |  |
| 2026 | 6.3354% | -- |  |

No further interpretation attempted -- a factual annotation of already-computed numbers against a well-documented macro episode, not a claim about causality.

Every Sharpe above: `results/robustness_variants.csv`.