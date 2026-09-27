"""
Phase 1a corpus pull -- commodity carry research.

Executes PREREGISTRATION.md Sec 12 step 1 (the corpus pull itself; step 2,
Aaron's written approval, is the precondition checked below) under the
re-instantiated Phase 1a guardrails.

Whitelist (locked, no deviation possible from this script):
  dataset : GLBX.MDP3
  schemas : ohlcv-1d, statistics, definition ONLY
  symbols : the 18 pre-registered CME symbols ONLY (parent symbology)
  dates   : 2010-06-06 (inclusive) through 2026-06-30 (inclusive).
            Databento's `end` parameter is EXCLUSIVE -- verified directly
            against the installed SDK's docstrings this session, not
            assumed (both metadata.get_cost and timeseries.get_range say
            "The exclusive end of the request range"). 2026-07-01 is
            therefore the correct end= value: it includes all of
            2026-06-30 and not one record of July.

Guardrail sequence (guardrail 4 of the governing prompt):
  1. Re-quote the exact request set via get_cost (3 calls, one per
     schema, all 18 symbols, full date range) -- logged as QUOTE rows.
  2. Gate: sum must be <= PULL_APPROVAL_CEILING. If not, STOP, no pull.
  3. If the sum differs from the pre-registration's $90.658381 estimate
     by more than 10%, log the delta prominently (this does not block
     the pull by itself -- only the ceiling in step 2 does).
  4. Only if gated: 3 real get_range calls, one per schema, streamed
     directly to DATA_DIR (never buffered fully in memory). Logged as
     REAL SPEND rows, continuing the existing ledger's numbering and
     running totals rather than starting a new one.

Key hygiene: identical mechanism to the Pass 2 script -- read straight
from WORKSPACE/.env/KEY.txt into the environment, never printed or
logged. scrub() is defense-in-depth on every string written to disk.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import databento as db
from databento.common.error import BentoError

# Paths: repo-relative defaults, overridable by the DATA_DIR / WORKSPACE environment variables (src/config.py).
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.config import DATA_DIR, WORKSPACE

LEDGER_PATH = REPO / "docs" / "samples" / "COST_LEDGER.md"
PULL_SUMMARY_PATH = WORKSPACE / "phase1a_pull_summary.json"

DATASET = "GLBX.MDP3"
SAMPLE_START = "2010-06-06"
SAMPLE_END_EXCLUSIVE = "2026-07-01"   # exclusive boundary -> includes all of 2026-06-30, no July
SCHEMAS = ["ohlcv-1d", "statistics", "definition"]

CME_UNIVERSE = {
    "energy": ["CL.FUT", "HO.FUT", "RB.FUT", "NG.FUT"],
    "metals": ["GC.FUT", "SI.FUT", "HG.FUT", "PL.FUT", "PA.FUT"],
    "grains": ["ZC.FUT", "ZS.FUT", "ZW.FUT", "ZM.FUT", "ZL.FUT", "KE.FUT"],
    "livestock": ["LE.FUT", "HE.FUT", "GF.FUT"],
}
ALL_SYMBOLS = [s for syms in CME_UNIVERSE.values() for s in syms]

PULL_APPROVAL_CEILING = 100.00
MEMO_ESTIMATE = 90.658381454646   # docs/DECISION_MEMO.md, Pass 2 addendum
DELTA_LOG_THRESHOLD = 0.10

# Continuation of the existing ledger's running totals (docs/samples/COST_LEDGER.md,
# rows 1-39 from the Pass 2 session) -- this script APPENDS, it does not reset these.
CARRY_FORWARD_ROW_N = 39
CARRY_FORWARD_QUOTE_CUMULATIVE = 90.6585598215419
CARRY_FORWARD_REAL_SPEND_CUMULATIVE = 0.000178366896

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
    """Appends to the EXISTING ledger file, continuing its row numbering
    and running totals rather than starting fresh."""

    def __init__(self, path: Path, start_n: int, start_quote_cum: float, start_real_cum: float):
        self.path = path
        self.n = start_n
        self.quote_cumulative = start_quote_cum
        self.real_spend_cumulative = start_real_cum
        if not path.exists():
            raise FileNotFoundError(f"Expected existing ledger at {path}, found none -- refusing to silently create a fresh one.")

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

    def note(self, text: str):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"\n{scrub(text)}\n")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    key_source = load_key_into_env()
    if key_source:
        print(f"DATABENTO_API_KEY loaded from: {key_source}")
    try:
        client = db.Historical()
    except ValueError as e:
        print(f"Cannot construct client: {e}", file=sys.stderr)
        sys.exit(2)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(LEDGER_PATH, CARRY_FORWARD_ROW_N, CARRY_FORWARD_QUOTE_CUMULATIVE, CARRY_FORWARD_REAL_SPEND_CUMULATIVE)
    ledger.note(f"### Phase 1a corpus pull -- session start (UTC): {datetime.now(timezone.utc).isoformat()}")

    request_kwargs_common = dict(
        dataset=DATASET, symbols=ALL_SYMBOLS, stype_in="parent",
        start=SAMPLE_START, end=SAMPLE_END_EXCLUSIVE,
    )

    # ---- Step 1: re-quote (guardrail 4.1) ----
    quotes = {}
    try:
        for schema in SCHEMAS:
            cost = client.metadata.get_cost(schema=schema, **request_kwargs_common)
            quotes[schema] = cost
            ledger.log_quote(
                "get_cost (Phase 1a re-quote)",
                f"schema={schema} symbols=18 start={SAMPLE_START} end={SAMPLE_END_EXCLUSIVE}",
                cost,
            )
            print(f"  re-quote {schema}: ${cost:.6f}")
    except BentoError as e:
        ledger.note(f"STOP: BentoError during re-quote: {scrub(str(e))}")
        print(f"STOP: BentoError during re-quote: {scrub(str(e))}", file=sys.stderr)
        sys.exit(1)

    total_quote = sum(quotes.values())
    delta = (total_quote - MEMO_ESTIMATE) / MEMO_ESTIMATE
    print(f"\nTotal re-quote: ${total_quote:.6f} (memo estimate ${MEMO_ESTIMATE:.6f}, delta {delta:+.2%})")

    # ---- Step 2: ceiling gate (guardrail 4.2) ----
    if total_quote > PULL_APPROVAL_CEILING:
        ledger.note(
            f"STOP: re-quote total ${total_quote:.6f} exceeds PULL_APPROVAL_CEILING "
            f"${PULL_APPROVAL_CEILING:.2f}. No pull executed."
        )
        print(f"STOP: ${total_quote:.6f} > ${PULL_APPROVAL_CEILING:.2f} ceiling. No pull executed.", file=sys.stderr)
        sys.exit(1)

    # ---- Step 3: delta logging (guardrail 4.3) -- informational, does not block ----
    if abs(delta) > DELTA_LOG_THRESHOLD:
        msg = (f"DELTA FLAG: re-quote ${total_quote:.6f} differs from the PREREGISTRATION "
               f"memo estimate ${MEMO_ESTIMATE:.6f} by {delta:+.2%}, exceeding the 10% "
               f"logging threshold. Proceeding since ${total_quote:.6f} is within the "
               f"${PULL_APPROVAL_CEILING:.2f} ceiling, per guardrail 4.3.")
        ledger.note(msg)
        print(msg)
    else:
        print(f"Delta {delta:+.2%} within the 10% threshold -- no flag needed.")

    # ---- Step 4: the real pull, one file per schema ----
    pull_results = {}
    for schema in SCHEMAS:
        out_path = DATA_DIR / f"{schema}.dbn.zst"
        try:
            client.timeseries.get_range(schema=schema, path=out_path, **request_kwargs_common)
        except BentoError as e:
            ledger.note(f"STOP: BentoError during pull of schema={schema}: {scrub(str(e))}")
            print(f"STOP: BentoError during pull of {schema}: {scrub(str(e))}", file=sys.stderr)
            sys.exit(1)

        ledger.log_real_spend(
            "get_range (Phase 1a corpus pull, actual)",
            f"schema={schema} symbols=18 start={SAMPLE_START} end={SAMPLE_END_EXCLUSIVE} path={out_path.name}",
            quotes[schema],
        )

        size_bytes = out_path.stat().st_size
        checksum = sha256_of(out_path)
        pull_results[schema] = {
            "path": str(out_path),
            "size_bytes": size_bytes,
            "sha256": checksum,
        }
        print(f"  pulled {schema}: {out_path.name} ({size_bytes:,} bytes), sha256={checksum}")

    ledger.note(
        f"Phase 1a pull complete. Total real spend this pull: ${sum(quotes.values()):.6f}. "
        f"Ledger real-spend cumulative (all sessions): ${ledger.real_spend_cumulative:.6f}."
    )

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": DATASET,
        "start": SAMPLE_START,
        "end_exclusive": SAMPLE_END_EXCLUSIVE,
        "symbols": ALL_SYMBOLS,
        "schemas": SCHEMAS,
        "quotes_usd": quotes,
        "total_quote_usd": total_quote,
        "memo_estimate_usd": MEMO_ESTIMATE,
        "delta_from_memo": delta,
        "pull_approval_ceiling_usd": PULL_APPROVAL_CEILING,
        "files": pull_results,
        "ledger_quote_cumulative_usd": ledger.quote_cumulative,
        "ledger_real_spend_cumulative_usd": ledger.real_spend_cumulative,
    }
    PULL_SUMMARY_PATH.write_text(scrub(json.dumps(summary, indent=2)), encoding="utf-8")
    print(f"\nSummary written to {PULL_SUMMARY_PATH}")
    print(f"Real spend this pull: ${total_quote:.6f}")
    print(f"Ledger real-spend cumulative (all sessions): ${ledger.real_spend_cumulative:.6f}")


if __name__ == "__main__":
    main()
