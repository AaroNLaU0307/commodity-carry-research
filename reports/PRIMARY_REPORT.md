# Primary Report

Generated (UTC): 2026-07-16T10:28:30.765723+00:00

Runner-generated, immutable once committed (dated addenda only for any future correction). PREREGISTRATION.md Sec 4/Sec 6. First real-data primary-family backtest in this project's history -- both arms passed Sec 7's premise gate (`reports/PREMISE_REPORT.md`, commit 543d271): XS mean IC +0.028489 (NW(3) t=1.4650), TS coefficient +0.000672 (t=0.3000). No design reaction to those numbers occurred; they are quoted here only for the run record.

**Pipeline confirmation:** amended pipeline throughout (A1 multi-candidate OI-max roll rule, A2 next-OI-bearing carry-next, `DEVIATIONS.md` 2026-07-15). **N_trials used for DSR: 14** (Sec 10's frozen computation ledger, cited directly, never locally recomputed). Bootstrap: expected block 21 trading days, 10,000 replications, seeds (7, 13, 31) -- seed 7 (the stats.py default) decides the gate verdicts below; all 3 seeds' individual outcomes are reported per Sec 6 ("not just their average").

**Tripwire firings this run** (same known, non-permanent NG grazes as Phase 1b):

- NG: known allowed transient graze(s) ['192047__2010-06-28', '192053__2010-12-28']

## H1 (XS, cross-sectional tercile)

- N (daily observations): 5,030
- Annualized net Sharpe (seed 7, point estimate): **-0.0031**
- 95% bootstrap CI: [-0.4417, 0.4287]  (excludes zero: False)
- Bootstrap p-value (one-sided, P[Sharpe <= 0]): 0.5003
- Net Sharpe under 2x cost table: -0.0122
- Deflated Sharpe Ratio (N_trials=14): 0.0399
- Annualized turnover (sum |monthly weight delta| / years): 41.65
- Rebalance cost drag (annualized): 0.420870%
- Total cost drag, rebalance + roll (annualized, gross-vs-net mean daily return): 0.097163%

**All 3 recorded seeds (Sec 6: "not just their average"):**

| Seed | Point estimate | CI low | CI high | Excludes zero |
|---|---|---|---|---|
| 7 | -0.0031 | -0.4417 | 0.4287 | False |
| 13 | -0.0031 | -0.4463 | 0.4241 | False |
| 31 | -0.0031 | -0.4423 | 0.4263 | False |

**Five promotion gates (Sec 6, verbatim, all must pass):**

| Gate | Requirement | Value | Verdict |
|---|---|---|---|
| 1. BH-FDR | q=0.1, m=2 | p=0.5003 | FAIL |
| 2. CI excludes 0 | 95% bootstrap CI | [-0.4417, 0.4287] | FAIL |
| 3. Net Sharpe >= 0.3 | | -0.0031 | FAIL |
| 4. Net Sharpe > 0 under 2x cost | | -0.0122 | FAIL |
| 5. DSR >= 0.95 | N_trials=14 | 0.0399 | FAIL |

**Promotion verdict: NOT PROMOTED**

### Annual returns

| Year | Net return |
|---|---|
| 2010 | 16.0005% |
| 2011 | -0.4649% |
| 2012 | -6.1675% |
| 2013 | 7.9970% |
| 2014 | -30.6974% |
| 2015 | 12.6742% |
| 2016 | -4.6247% |
| 2017 | 14.9351% |
| 2018 | -18.0362% |
| 2019 | 5.4445% |
| 2020 | -3.8141% |
| 2021 | -2.4298% |
| 2022 | 5.6852% |
| 2023 | -8.9908% |
| 2024 | -4.3636% |
| 2025 | 6.7596% |
| 2026 | 11.3038% |

Full daily equity curve saved to `_carry-research-workspace/phase1c_equity_curve_H1.csv` (not committed, reproducible).

## H2 (TS, time-series sign)

- N (daily observations): 5,030
- Annualized net Sharpe (seed 7, point estimate): **-0.1255**
- 95% bootstrap CI: [-0.5580, 0.3227]  (excludes zero: False)
- Bootstrap p-value (one-sided, P[Sharpe <= 0]): 0.7118
- Net Sharpe under 2x cost table: -0.1223
- Deflated Sharpe Ratio (N_trials=14): 0.0107
- Annualized turnover (sum |monthly weight delta| / years): 39.12
- Rebalance cost drag (annualized): 0.370597%
- Total cost drag, rebalance + roll (annualized, gross-vs-net mean daily return): -0.034331%

**All 3 recorded seeds (Sec 6: "not just their average"):**

| Seed | Point estimate | CI low | CI high | Excludes zero |
|---|---|---|---|---|
| 7 | -0.1255 | -0.5580 | 0.3227 | False |
| 13 | -0.1255 | -0.5784 | 0.3215 | False |
| 31 | -0.1255 | -0.5665 | 0.3104 | False |

**Five promotion gates (Sec 6, verbatim, all must pass):**

| Gate | Requirement | Value | Verdict |
|---|---|---|---|
| 1. BH-FDR | q=0.1, m=2 | p=0.7118 | FAIL |
| 2. CI excludes 0 | 95% bootstrap CI | [-0.5580, 0.3227] | FAIL |
| 3. Net Sharpe >= 0.3 | | -0.1255 | FAIL |
| 4. Net Sharpe > 0 under 2x cost | | -0.1223 | FAIL |
| 5. DSR >= 0.95 | N_trials=14 | 0.0107 | FAIL |

**Promotion verdict: NOT PROMOTED**

### Annual returns

| Year | Net return |
|---|---|
| 2010 | -21.5977% |
| 2011 | 6.1813% |
| 2012 | -7.2463% |
| 2013 | 10.8094% |
| 2014 | -10.7015% |
| 2015 | 28.6642% |
| 2016 | -13.0592% |
| 2017 | 0.9654% |
| 2018 | 0.6746% |
| 2019 | -1.0311% |
| 2020 | -11.1862% |
| 2021 | 1.7054% |
| 2022 | 5.1026% |
| 2023 | 1.5285% |
| 2024 | -4.3676% |
| 2025 | -15.5766% |
| 2026 | 2.6519% |

Full daily equity curve saved to `_carry-research-workspace/phase1c_equity_curve_H2.csv` (not committed, reproducible).

## Summary

| Arm | Sharpe | CI | DSR | BH-FDR | Sharpe>=0.30 | 2x cost>0 | DSR>=0.95 | Promoted |
|---|---|---|---|---|---|---|---|---|
| H1 | -0.0031 | [-0.4417, 0.4287] | 0.0399 | FAIL | FAIL | FAIL | FAIL | NO |
| H2 | -0.1255 | [-0.5580, 0.3227] | 0.0107 | FAIL | FAIL | FAIL | FAIL | NO |

**No arm promoted.** Per Sec 6, promotion requires all five gates. Sec 8's robustness suite is still run as diagnostics of the primary series regardless of promotion (robustness never gates promotion either way).