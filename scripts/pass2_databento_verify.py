"""
Pass 2 Databento verification -- carry risk premium research, Phase 0.

Resolves the two open PASS(A) sub-criteria from Pass 1: per-symbol history
length, and actual cost. The full corpus is never downloaded here.

Guardrail interpretation, confirmed with Aaron after the first run stopped
on a $44.64 full-corpus quote: the $2-per-call / $5-cumulative caps bound
REAL SPEND (actual timeseries.get_range pulls) only. metadata.get_cost never
bills regardless of the number it returns, so quote calls -- including the
deliberate full-corpus projection this script is required to produce -- are
unrestricted and logged separately from the real-spend ledger.

Guardrails enforced in-code:
  - Dataset whitelist: GLBX.MDP3 only.
  - Schema whitelist for DOWNLOADS (real get_range calls): ohlcv-1d,
    statistics only. `definition` appears in get_cost quotes only -- grep
    this file for "definition" to confirm it's never passed to get_range.
  - get_cost is called immediately before every get_range call, no
    exceptions, and its result gates whether the get_range call is allowed
    to proceed (real-spend $2/call check).
  - Hard stop: any single real-spend amount > PER_CALL_LIMIT, or the running
    real-spend ledger total > CUMULATIVE_LIMIT, aborts the script
    immediately after writing the triggering row. No ask-and-continue.
  - The API key is loaded straight from disk into the environment and is
    never printed, returned, or logged -- see load_key_into_env(). Every
    string written to disk is passed through scrub() as defense in depth.

Run from a repo/workspace root containing a `.env` (file or folder with
KEY.txt inside) or with DATABENTO_API_KEY already set in the environment.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import databento as db
from databento.common.error import BentoError

WORKSPACE = Path(__file__).resolve().parent.parent
SAMPLES_DIR = WORKSPACE / "samples"
LEDGER_PATH = SAMPLES_DIR / "COST_LEDGER.md"
RESULTS_PATH = SAMPLES_DIR / "per_symbol_probe_results.json"

PER_CALL_LIMIT = 2.00      # applies to REAL SPEND only (a get_range about to execute)
CUMULATIVE_LIMIT = 5.00    # applies to REAL SPEND only, running total

DATASET = "GLBX.MDP3"
FULL_HISTORY_START = "2010-06-06"
PROJECTION_END = "2026-07-01"
PROBE_END = "2020-01-01"

CME_UNIVERSE = {
    "energy": ["CL.FUT", "HO.FUT", "RB.FUT", "NG.FUT"],
    "metals": ["GC.FUT", "SI.FUT", "HG.FUT", "PL.FUT", "PA.FUT"],
    "grains": ["ZC.FUT", "ZS.FUT", "ZW.FUT", "ZM.FUT", "ZL.FUT", "KE.FUT"],
    "livestock": ["LE.FUT", "HE.FUT", "GF.FUT"],
}
ALL_SYMBOLS = [s for syms in CME_UNIVERSE.values() for s in syms]
SYMBOL_SECTOR = {s: sector for sector, syms in CME_UNIVERSE.items() for s in syms}

KEY_PATTERN = re.compile(r"db-[A-Za-z0-9_-]{16,}")


def scrub(text: str) -> str:
    return KEY_PATTERN.sub("[REDACTED-KEY]", text)


def load_key_into_env() -> str:
    """Populate DATABENTO_API_KEY without ever printing/logging the value."""
    env_path = WORKSPACE / ".env"
    if env_path.is_file():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        if os.environ.get("DATABENTO_API_KEY"):
            return ".env file"

    key_txt = WORKSPACE / ".env" / "KEY.txt"
    if key_txt.is_file():
        raw = key_txt.read_text(encoding="utf-8")
        match = KEY_PATTERN.search(raw)
        if match:
            os.environ["DATABENTO_API_KEY"] = match.group(0)
            return ".env/KEY.txt (extracted via pattern match)"

    if os.environ.get("DATABENTO_API_KEY"):
        return "pre-existing process environment"

    return ""


class Ledger:
    """Two running totals: quotes (unrestricted, informational) and real
    spend (hard-capped at PER_CALL_LIMIT / CUMULATIVE_LIMIT)."""

    def __init__(self, path: Path):
        self.path = path
        self.real_spend_cumulative = 0.0
        self.quote_cumulative = 0.0
        self.n = 0
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            "# Cost Ledger -- Databento Pass 2\n\n"
            f"Session start (UTC): {datetime.now(timezone.utc).isoformat()}\n\n"
            "Two tracks: QUOTE rows (get_cost, never billed, unrestricted) and "
            "REAL SPEND rows (actual get_range pulls, capped at "
            f"${PER_CALL_LIMIT}/call and ${CUMULATIVE_LIMIT} cumulative).\n\n"
            "| # | UTC time | Track | Call type | Params | Cost (USD) | Cumulative (USD) | Note |\n"
            "|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )

    def log_quote(self, call_type: str, params: str, cost: float, note: str = "") -> float:
        self.n += 1
        self.quote_cumulative += cost
        self._write("QUOTE", call_type, params, cost, self.quote_cumulative, note)
        return cost

    def log_real_spend(self, call_type: str, params: str, cost: float, note: str = "") -> float:
        self.n += 1
        self.real_spend_cumulative += cost
        self._write("REAL SPEND", call_type, params, cost, self.real_spend_cumulative, note)
        return self.real_spend_cumulative

    def _write(self, track, call_type, params, cost, cumulative, note):
        ts = datetime.now(timezone.utc).isoformat()
        row = (f"| {self.n} | {ts} | {track} | {scrub(call_type)} | {scrub(params)} | "
               f"{cost:.6f} | {cumulative:.6f} | {scrub(note)} |\n")
        with self.path.open("a", encoding="utf-8") as f:
            f.write(row)

    def stop(self, reason: str):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"\n**STOPPED: {scrub(reason)}**\n")
        print(f"STOP: {reason}", file=sys.stderr)
        sys.exit(1)


def quote(client, ledger, *, label, **kwargs) -> float:
    """Unrestricted get_cost call -- never bills, logged to the quote track."""
    cost = client.metadata.get_cost(**kwargs)
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    ledger.log_quote("get_cost", f"{label}: {params}", cost)
    return cost


def gated_pull(client, ledger, *, label, **kwargs):
    """Quote first (free), then gate a REAL get_range call on that quote
    against PER_CALL_LIMIT and CUMULATIVE_LIMIT. Returns the DBNStore, or
    None if skipped for exceeding the per-call limit (does not abort)."""
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    cost = client.metadata.get_cost(**kwargs)
    ledger.log_quote("get_cost (pre-pull check)", f"{label}: {params}", cost)

    if cost > PER_CALL_LIMIT:
        ledger.log_real_spend("get_range SKIPPED", f"{label}: {params}", 0.0,
                               note=f"quoted ${cost:.4f} exceeds PER_CALL_LIMIT ${PER_CALL_LIMIT} -- pull not executed")
        print(f"SKIPPED (not a stop): {label} quoted ${cost:.4f} > ${PER_CALL_LIMIT} per-call limit -- no pull executed")
        return None

    if ledger.real_spend_cumulative + cost > CUMULATIVE_LIMIT:
        ledger.stop(f"executing {label} (${cost:.4f}) would push real-spend cumulative to "
                    f"${ledger.real_spend_cumulative + cost:.4f}, exceeding CUMULATIVE_LIMIT ${CUMULATIVE_LIMIT}")

    store = client.timeseries.get_range(**kwargs)
    ledger.log_real_spend("get_range (actual pull)", f"{label}: {params}", cost)
    return store


def main():
    key_source = load_key_into_env()
    if key_source:
        print(f"DATABENTO_API_KEY loaded from: {key_source}")
    try:
        client = db.Historical()
    except ValueError as e:
        print(f"Cannot construct client: {e}. DATABENTO_API_KEY is not visible to this process.", file=sys.stderr)
        sys.exit(2)

    ledger = Ledger(LEDGER_PATH)
    print(f"Ledger: {LEDGER_PATH}")

    # ---- Phase A: full-corpus cost projection (quotes only, unrestricted, nothing downloaded) ----
    projection = {}
    try:
        for schema in ("ohlcv-1d", "statistics", "definition"):
            cost = quote(
                client, ledger,
                label=f"full-corpus projection [{schema}]",
                dataset=DATASET, symbols=ALL_SYMBOLS, stype_in="parent",
                schema=schema, start=FULL_HISTORY_START, end=PROJECTION_END,
            )
            projection[schema] = cost
            print(f"  {schema}: ${cost:.4f}")
    except BentoError as e:
        ledger.stop(f"BentoError during full-corpus projection: {scrub(str(e))}")

    downloadable_subtotal = projection["ohlcv-1d"] + projection["statistics"]
    full_future_total = sum(projection.values())
    print(f"\nFull-corpus projection -- ohlcv-1d + statistics: ${downloadable_subtotal:.4f}")
    print(f"Full-corpus projection -- incl. definition: ${full_future_total:.4f}")
    print(f"(quotes only; nothing downloaded; free credit reference point: $125)\n")

    # ---- Phase B: per-symbol first-available-date probe (ohlcv-1d, real 1-row pulls, capped) ----
    probe_results = {}
    for sym in ALL_SYMBOLS:
        try:
            store = gated_pull(
                client, ledger,
                label=f"probe [{sym}]",
                dataset=DATASET, symbols=[sym], stype_in="parent",
                schema="ohlcv-1d", start=FULL_HISTORY_START, end=PROBE_END, limit=1,
            )
        except BentoError as e:
            probe_results[sym] = {"error": scrub(str(e))}
            print(f"{sym}: BentoError -- {scrub(str(e))}")
            continue

        if store is None:
            probe_results[sym] = {"skipped": "quoted cost exceeded per-call limit"}
            continue

        df = store.to_df()
        first_date = str(df.index.min()) if len(df) else None
        probe_results[sym] = {
            "sector": SYMBOL_SECTOR[sym],
            "first_row_in_probe_window": first_date,
            "probe_window": [FULL_HISTORY_START, PROBE_END],
        }
        print(f"{sym} ({SYMBOL_SECTOR[sym]}): first row in probe window = {first_date or 'NONE -- widen window manually'}")

    RESULTS_PATH.write_text(
        scrub(json.dumps({
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "dataset": DATASET,
            "dataset_floor_assumed": FULL_HISTORY_START,
            "full_corpus_projection_usd": projection,
            "downloadable_subtotal_usd": downloadable_subtotal,
            "full_future_total_usd": full_future_total,
            "per_symbol_probe": probe_results,
            "real_spend_cumulative_usd": ledger.real_spend_cumulative,
            "quote_cumulative_usd": ledger.quote_cumulative,
        }, indent=2, default=str)),
        encoding="utf-8",
    )

    print(f"\nReal spend this session: ${ledger.real_spend_cumulative:.6f} (limit ${CUMULATIVE_LIMIT})")
    print(f"Total quoted (never billed): ${ledger.quote_cumulative:.4f}")
    print(f"Results: {RESULTS_PATH}")
    print(f"Ledger: {LEDGER_PATH}")


if __name__ == "__main__":
    main()
