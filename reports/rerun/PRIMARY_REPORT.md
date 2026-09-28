# Primary Report

Generated (UTC): 2026-09-28T15:46:55.658156+00:00 · code `70d1e0392f7112042d5855d57df9ca3e54bfda1a`

Runner-generated (`scripts/phase1c_primary_backtest.py`). PREREGISTRATION.md Sec 4/Sec 6, as amended by `preregistration/AMENDMENT_2026-09-27.md`. This run follows the 2026-09-27 corrections (`reports/ADDENDUM_2026-09-27.md`); the published pre-correction report, `reports/PRIMARY_REPORT.md`, stays unchanged.

**Premise gate (Sec 7, `results/premise_summary.json`):** XS mean IC +0.028270 (NW(3) t=1.3721), TS coefficient -0.000143 (t=-0.0690). Open arms: H1; closed at the premise: H2.

**Pipeline:** A1 roll rule and A2 carry-next (`DEVIATIONS.md` 2026-07-15); trade-date calendar and `StatType.OPEN_INTEREST` (2026-09-27); execution_lag = 0 (entry at the signal's own month-end settlement, the registered primary timing); leverage sized from the pre-cost series; every change in the levered position (monthly rebalance and daily leverage resize) and every roll leg charged on |position|. **N_trials for DSR: 16** (Sec 10's 14 plus the two execution-lag-1 series registered 2026-09-27). DSR inputs: each arm's sample skewness and excess kurtosis, and the empirical standard deviation of the 10 registered series' Sharpes (0.0709). Bootstrap: expected block 21 trading days, 10,000 replications, seeds (7, 13, 31) -- seed 7 decides the gates; all 3 seeds are reported (Sec 6).

**Tripwire firings this run:** none.

## H1 (XS, cross-sectional tercile)

- N (daily observations): 4,069
- Annualized net Sharpe (seed 7, point estimate): **0.0591**
- 95% bootstrap CI: [-0.4142, 0.5239]  (excludes zero: False)
- Bootstrap p-value (one-sided, P[Sharpe <= 0]): 0.4068
- Net Sharpe under 2x cost table: 0.0322
- Gross-of-cost Sharpe (same leverage path): 0.0860
- Net Sharpe with execution one trading day after the signal (sensitivity): 0.0140
- Deflated Sharpe Ratio (N_trials=16, skew=-0.111, excess kurtosis=2.257, trial Sharpe std=0.0709): 0.3915
- Annualized net Sharpe needed for DSR >= 0.95 under these inputs: 0.5381
- Annualized turnover (sum |monthly pre-leverage weight delta| / years): 36.11
- Trading cost drag, rebalance + daily leverage resize (annualized): 0.130316%
- Roll cost drag (annualized): 0.155368%
- Total cost drag (annualized; equals gross minus net mean daily return x 252): 0.285684%

**All 3 recorded seeds (Sec 6: "not just their average"):**

| Seed | Point estimate | CI low | CI high | Excludes zero |
|---|---|---|---|---|
| 7 | 0.0591 | -0.4142 | 0.5239 | False |
| 13 | 0.0591 | -0.4076 | 0.5149 | False |
| 31 | 0.0591 | -0.4130 | 0.5279 | False |

**Five promotion gates (Sec 6, all must pass):**

| Gate | Requirement | Value | Verdict |
|---|---|---|---|
| 1. BH-FDR | q=0.1, m=2 | p=0.4068 | FAIL |
| 2. CI excludes 0 | 95% bootstrap CI | [-0.4142, 0.5239] | FAIL |
| 3. Net Sharpe >= 0.3 | | 0.0591 | FAIL |
| 4. Net Sharpe > 0 under 2x cost | | 0.0322 | PASS |
| 5. DSR >= 0.95 | N_trials=16 | 0.3915 | FAIL |

**Promotion verdict: NOT PROMOTED**

### Annual returns

| Year | Net return |
|---|---|
| 2010 | 15.7116% |
| 2011 | -1.4258% |
| 2012 | -6.2261% |
| 2013 | 16.4732% |
| 2014 | -26.8510% |
| 2015 | 7.5539% |
| 2016 | -3.2484% |
| 2017 | 14.7054% |
| 2018 | -6.9382% |
| 2019 | 6.2493% |
| 2020 | -12.3244% |
| 2021 | 0.7003% |
| 2022 | 2.9657% |
| 2023 | -6.9432% |
| 2024 | -0.1214% |
| 2025 | 4.5620% |
| 2026 | 6.3354% |

Monthly net and gross returns: `results/primary_monthly_returns.csv`.

## H2 (TS, time-series sign)

**Closed at the premise stage (Sec 7): point estimate <= 0. No backtest run.**

## Summary

| Arm | Sharpe | CI | DSR | BH-FDR | Sharpe>=0.30 | 2x cost>0 | DSR>=0.95 | Promoted |
|---|---|---|---|---|---|---|---|---|
| H1 | 0.0591 | [-0.4142, 0.5239] | 0.3915 | FAIL | FAIL | PASS | FAIL | NO |
| H2 | -- | -- | -- | -- | -- | -- | -- | CLOSED AT PREMISE |

**No arm promoted.** Per Sec 6, promotion requires all five gates. Sec 8's robustness suite is still run as diagnostics of the primary series (robustness never gates promotion).