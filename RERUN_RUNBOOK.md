# Re-run runbook — after the 2026-09-27 corrections

This is for a fresh session on the machine that holds the licensed Databento corpus. Every number published on 2026-07-16 predates these corrections:

- the trade-date calendar and the open-interest field (`StatType.OPEN_INTEREST`, not stat_type 6);
- the execution-timing amendment, which adds the lag-1 sensitivity and sets N_trials to 16;
- costs and leverage;
- the DSR inputs;
- the single-name sector short.

Details are in [`reports/ADDENDUM_2026-09-27.md`](reports/ADDENDUM_2026-09-27.md) and [`preregistration/AMENDMENT_2026-09-27.md`](preregistration/AMENDMENT_2026-09-27.md). Do the steps in order and do not skip step 2.

## 1. Prerequisites

- **Python 3.13.** This is what CI runs; see the header of `requirements.txt`.
- **Pinned environment.**

  ```
  python -m venv .venv && . .venv/bin/activate
  pip install -r requirements.txt
  pytest -q
  ```

  `pytest -q` must pass in full, with the count stated in `README.md`. The pins include `databento==0.81.0` and `databento-dbn==0.62.0`. The open-interest fix relies on that package's `StatType` enum: `SETTLEMENT_PRICE = 3`, `CLEARED_VOLUME = 6`, `OPEN_INTEREST = 9`.
- **Checkout.** Use a clean checkout (`git status` empty) of the commit that holds this runbook. Every report and result is stamped with `git rev-parse HEAD`, and `-dirty` is appended when the tree has uncommitted changes. A dirty stamp is not publishable.
- **Data.** You need the Databento `GLBX.MDP3` delivery listed in `data/MANIFEST.md`:
  - `ohlcv-1d.dbn.zst`
  - `definition/` (5,031 per-day files)
  - `statistics/` (5,026 per-day files)
- **Environment variables.**
  - `DATA_DIR` points at that directory. The default is `data/raw/` inside the checkout, which is git-ignored.
  - `WORKSPACE` is optional; the default is `data/workspace/`, also git-ignored. Only the optional Figure 4 reads it, from `WORKSPACE/stuck_episodes_full.csv`.
  - No API key is needed. Nothing calls the Databento API.

## 2. Data check — before any computation

```
DATA_DIR=/path/to/commodity-carry python scripts/run_all.py check-data
```

This hashes about 9.4 GB. Add `--skip-checksums` to re-print only the comparisons. The command prints three blocks; all three must pass.

1. **Checksums.** Every line must read `OK`:
   - `ohlcv-1d.dbn.zst` = `333095164e55…`
   - `definition/` aggregate = `76da3a39a727…`, over 5,031 files
   - `statistics/` aggregate = `ee7dee4dc1c2…`, over 5,026 files

   The aggregate rule is the one `scripts/phase1a_build_manifest.py` wrote. Any `FAIL` means the corpus is not the one the manifest describes, so stop.

2. **Open-interest field, CLK0 (May 2020 WTI), trade dates 2020-04-13 to 2020-04-20.** The table shows, per trade date (`ts_ref`):
   - `SETTLEMENT_PRICE`;
   - `CLEARED_VOLUME` (stat_type 6);
   - `OPEN_INTEREST` (stat_type 9);
   - the UTC time the open interest first arrived.

   Compare each date with CME-published open interest and volume for NYMEX CL, contract month May 2020 (CME Group's daily volume and open interest report or Daily Bulletin archive).

   - **Pass:** `OPEN_INTEREST` matches CME's open interest, `CLEARED_VOLUME` matches CME's volume, and each date's open interest arrives before the next trade date's settlement.
   - **Stop:** if stat_type 6 is the one that matches CME open interest, the enum mapping does not hold for this corpus. Record that in the addendum and do not run.

3. **Settlement spot-check.** There are six defaults: CLK0 on 2020-04-20 and 2020-04-17; GCM0, ZCN0 and LEM0 on 2020-04-17; and NGG1 on 2021-01-15, a winter Friday. For each, the check lists every `SETTLEMENT_PRICE` record for that trade date, by file, plus the value the pipeline keeps (the last one received). A Friday settlement appears twice: in the Friday file and in the Sunday-dated file (for example `…20200419…` for 2020-04-17).
   - **Pass:** at least five exact matches with CME's published final settlements. One of them must be a Friday value read from a Sunday-dated file. CLK0 on 2020-04-20 must be −37.63.
   - If a raw symbol is not found, the output lists that day's outrights. Re-run with, for example, `--spot GCM0:2020-04-17`.

Keep the printed output and the CME figures you compared. Both go into the addendum (step 5).

## 3. Run

```
DATA_DIR=/path/to/commodity-carry python scripts/run_all.py
```

This loads the corpus once and then runs premise → primary → robustness → figures. The first lines print the statistics diagnostics:

- `n_weekend_trade_date_dropped` must be 0. Anything else means `ts_ref` is not the trade date this pipeline assumes, so stop.
- `n_undefined_ts_ref` and `n_deleted` are reported for the record.

Single stages, in dependency order:

```
python scripts/run_all.py premise
python scripts/run_all.py primary      # needs results/premise_summary.json
python scripts/run_all.py robustness   # needs results/primary_summary.json
python scripts/run_all.py figures      # needs the three results files below
```

**Halts, and what to do:**

- **`STUCK FRONT`, the permanent tripwire.** A held front was still held after its own expiry, and it is not one of NG's two known transient grazes (`src/study.py::KNOWN_ALLOWED_TRANSIENT_GRAZES`). The corrected OI field and trade-date keying move roll dates, so a known graze may vanish or a new one may appear. Stop, diagnose it the way F11 was diagnosed (`docs/DATA_QA_REPORT.md`), and record the finding in the addendum. Do not widen the allow-list unless a dated record, written before re-running, justifies it.
- **`ZERO-PRICE GUARD`.** A held front settled at or below zero; CLK0 on 2020-04-20 must never be front. Stop and investigate.
- **Truncation-invariance failure.** This means look-ahead. Stop.
- **Premise gate.** An arm whose premise point estimate is at or below zero closes there (§7). The primary stage skips it and reports it as closed; BH gives it p = 1. If both arms close, `run_all` stops after the premise stage. That is a complete outcome, not an error.

## 4. What each stage writes, and what it feeds

Line numbers refer to this commit.

**premise**

- Writes:
  - `reports/PREMISE_REPORT.md`
  - `results/premise_summary.json` (`xs`, `ts`, `sensitivity_execution_lag_1`, `gate`)
- Feeds:
  - `README.md` verdicts table, "Premise (point est.)" column (lines 36–37)
  - `DESIGN_DECISIONS.md` "Why a sign-only premise gate?" (line 15)
  - `results/headline.json` `ts-carry` "premise t"
  - the premise line in the primary report's header

**primary**

- Writes:
  - `reports/PRIMARY_REPORT.md`
  - `results/primary_summary.json` (per arm: net Sharpe, CI by seed, p-value, 2× cost Sharpe, gross Sharpe, lag-1 Sharpe, DSR with its inputs and threshold, gates, annual returns, cost drags; plus N_trials and the trial Sharpes)
  - `results/primary_monthly_returns.csv`
- Feeds, in `README.md`:
  - Verdict paragraph, "0 of 2 promoted" (lines 5–10)
  - headline block (lines 18–21)
  - verdicts table (lines 34–37)
  - "Headline stats with CIs" (lines 45–48)
  - Figure 2 caption, net Sharpes (lines 68–74)
  - Power statement: SEs from the CI widths, the MDE and the DSR threshold (lines 151–161)
- Feeds elsewhere:
  - `DESIGN_DECISIONS.md` "Why report a confidence interval this wide…" (line 82)
  - `results/headline.json`: every net Sharpe and CI stat

**robustness**

- Writes:
  - `reports/ROBUSTNESS_REPORT.md`
  - `results/robustness_variants.csv` (every registered series, including the lag-1 pair, and every diagnostic slice, with `kind` and `in_n_trials`)
- Feeds, in `README.md`:
  - Verdict paragraph, "none of the 12 registered variants reaches 0.30" (lines 8–10; now 14 registered with the lag-1 pair)
  - Figure 2 caption, gross vs net (lines 68–74)
  - Mechanism section, including the long/short split (lines 76–88)
  - Figure 3 caption (line 92)
- Feeds elsewhere:
  - `docs/MECHANISM_NOTES.md` rows 1–5 (lines 20–24), the row-1 caption (line 31) and "Where did H1's P&L come from?" (line 36)
  - `DESIGN_DECISIONS.md` "Why 12 registered variants…"
  - `results/headline.json` `xs-carry` mechanism: "all 12 registered variants below the 0.30 gate; long-leg gains offset by short-leg losses"

**figures**

- Writes:
  - `reports/figures/gates_forest.png`
  - `reports/figures/equity_curves.png`
  - `reports/figures/per_year_returns.png`
  - `reports/figures/f11_deadlock.png`, only when the census CSV is in `WORKSPACE`
- Feeds: `README.md` Figures 1–3, their alt text and captions (lines 41–43, 66–74, 89–93), and the `docs/MECHANISM_NOTES.md` row-1 figure.

Several prose claims depend on the numbers and must be re-read against the new results, not carried over:

- "0 of 2 promoted" and "none of the registered variants reaches 0.30";
- "both arms positive in 2022 but not either arm's best year" (Figure 3 alt text and `MECHANISM_NOTES.md` row 1);
- "gross tracks net closely" (Figure 2);
- each `MECHANISM_NOTES.md` verdict;
- the long/short sentence (README, `MECHANISM_NOTES.md`, `results/headline.json`);
- the "≈0.6" MDE and the "≈0.76" DSR threshold;
- the `ts-carry` mechanism in `results/headline.json`.

## 5. Record and commit

1. **Addendum.** Append a new dated section to `reports/ADDENDUM_2026-09-27.md`, "## 10. Re-run results (YYYY-MM-DD)". It must contain:
   - the code commit stamped in the report headers (not `-dirty`);
   - the step-2 outputs and the CME figures they were compared against;
   - the statistics diagnostics;
   - for each headline number, the old value, the new value and the new artifact path;
   - the premise gates, the promotion verdicts, the lag-1 sensitivity and the DSR threshold;
   - any halt and its diagnosis.

   Do not edit the earlier sections.
2. **README.** Update every number listed in step 4. Replace the dated notice at lines 12–16 with one saying the numbers are from the re-run of that date, linking addendum §10. Update the Figure 1 caption (lines 41–43) and the test count if it changed.
3. **`results/headline.json`.**
   - Point each stat at `results/primary_summary.json` or `results/premise_summary.json`, with a `json: …` locator such as `json: arms.H1.net_sharpe`, `json: arms.H1.ci_by_seed.0.ci_low` or `json: ts.tstat`. `tests/test_headline.py` recomputes JSON-backed stats.
   - Set `provenance` to `reproduced` only for values recomputed from those committed files in that session.
   - Set `source_commit` to the commit that contains the regenerated artifacts: commit them first, then fill in the sha. Re-check `verdict`, `mechanism` and `caveats`.
4. **Commit** these, with `pytest -q` green:
   - `reports/*.md` and `reports/figures/*.png`
   - `results/*.json` and `results/*.csv`
   - `README.md`, `docs/MECHANISM_NOTES.md` and `DESIGN_DECISIONS.md` where their numbers changed
   - the addendum

   Never commit anything from `DATA_DIR` or `WORKSPACE`. The replaced reports stay in history at `f0847d7`.
5. **Do not touch** `preregistration/PREREGISTRATION.md` or the existing `DEVIATIONS.md` entries. Any new specification decision gets a dated record written before the computation it governs.
