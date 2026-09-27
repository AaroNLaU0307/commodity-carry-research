# Amendment 2026-09-27 — execution timing (§3) and a registered execution-lag sensitivity

**Status.** Dated amendment to [`PREREGISTRATION.md`](PREREGISTRATION.md). That document is not edited; its body and its Amendments log stay as they are. Authority: the repository owner, 2026-09-27.

**Timing.** This amendment is written after the results of 2026-07-16 were published (`reports/*.md` at commit `f0847d7`), so it is a post-results amendment. It is written before any computation under it. The corrected re-run ([`RERUN_RUNBOOK.md`](../RERUN_RUNBOOK.md)) has not been executed, and no number exists under the lag-1 variant.

## 1. What §3 says and what the code does

§3, *Signal timing*, says two things:

1. Positions "are established at the first trading day of month `t+1`, at that day's settlement price", and "a full trading day separates signal observation from position entry".
2. The timing is "consistent with `positions = weights.shift(1)` convention used in `multi-asset-tsmom-research`".

These describe different timings.

The code (`src/primary.py::expand_monthly_to_daily`) applies month-end `t`'s weight to the daily returns dated `(t, t_next]`, where `r(d) = settle(d) / settle(d−1) − 1`. The premise panel (`src/pipeline.py::month_end_next_month_return_panel`) uses the same window. So the first return a month-end-`t` signal earns is `settle(t) → settle(t+1)`. In effect the position is entered at `settle(t)`, the same settlement the signal is computed from. That is the `weights.shift(1)` convention of statement 2. It is not statement 1: no trading day separates signal and entry.

Every number published on 2026-07-16 was computed with this same-settlement timing. The test that encoded it was named "no same-day signal-to-trade". It is now `tests/test_primary.py::test_default_execution_lag_enters_at_the_signal_settlement`, and its docstring describes what it tests.

## 2. The amendment

1. **Registered primary timing, both arms, premise and portfolio: the same-settlement convention.** This is `execution_lag = 0` as implemented. The signal is computed from `settle(t)`, the position is entered at `settle(t)`, and the first return is `settle(t) → settle(t+1)`. For this study, §3's timing is the `weights.shift(1)` convention. The sentences about a full trading day between signal and entry do not describe the registered construction. The code already did this, so this item changes no computation.

2. **Registered sensitivity: `execution_lag = 1`.** Entry is at `settle(t+1)`, and the first return is `settle(t+1) → settle(t+2)`. This is the literal reading of "the first trading day of month `t+1`, at that day's settlement". It applies to:
   - **Both primary arms (H1, H2).** Every other element of the construction is unchanged: signal, weights, vol targeting, leverage and costs.
   - **Both premise statistics (XS mean IC, TS coefficient).** They are reported next to the registered values. The §7 gate is decided at `execution_lag = 0` only.

   Like every §8 item, the sensitivity is reported with sign and magnitude and never gates promotion.

3. **§10 consequence.** The two lag-1 portfolio series are constructed strategy-return series. So `N_trials = 14 + 2 = 16` for every DSR computed from the re-run on (`src/config.py::N_TRIALS`). The lag-1 premise statistics are not strategy-return series and do not count.

## 3. Why this is not result-motivated

- Item 1 ratifies what the code has always done.
- Item 2 registers a variant that has never been computed on the data. It can only add evidence, and it is reported whichever way it points. Which timing favours the hypothesis is not known in advance.
- Item 3 makes the DSR gate stricter, never looser.

## 4. Implementation and tests

- `src/primary.py`: an `execution_lag` parameter on `expand_monthly_to_daily` and `compute_arm_daily_returns`.
- `src/pipeline.py`: `month_end_next_month_return_panel(execution_lag=...)`.
- `src/config.py`: `EXECUTION_LAG_PRIMARY = 0`, `EXECUTION_LAG_SENSITIVITY = 1`, `N_TRIALS = 16`.
- `src/study.py::registered_series`: the series `LAG1_H1` and `LAG1_H2`.
- `scripts/phase1b_premise_test.py`: the lag-1 premise table.
- Tests:
  - `tests/test_primary.py::test_execution_lag_1_first_earns_settle_t_plus_1_to_t_plus_2`
  - `tests/test_pipeline.py::test_month_end_next_month_return_panel_execution_lag_shifts_window_one_trading_row`

Other code corrections made the same day restore the registered definitions rather than amend them:

- the trade-date calendar;
- the open-interest field;
- costs on every change in the levered position, kept out of the vol estimator;
- the DSR inputs.

They are recorded in [`reports/ADDENDUM_2026-09-27.md`](../reports/ADDENDUM_2026-09-27.md). No other part of `PREREGISTRATION.md` changes.
