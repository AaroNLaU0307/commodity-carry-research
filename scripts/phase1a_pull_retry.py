"""
Retry of the two schemas that failed on the first Phase 1a pull attempt
(statistics, definition -- both hit a transient 504 gateway timeout;
ohlcv-1d already pulled successfully). Reuses the get_cost quotes already
logged in COST_LEDGER.md rows 41-42 (fresh, same session, minutes old) --
does not re-quote, since nothing about frozen historical data has changed
and get_cost calls add no new information the second time.
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

WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")
REPO = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\commodity-carry-research")
DATA_DIR = Path(r"C:\Users\Aaron\quant-data\commodity-carry")
LEDGER_PATH = REPO / "docs" / "samples" / "COST_LEDGER.md"
PULL_SUMMARY_PATH = WORKSPACE / "phase1a_pull_summary.json"

DATASET = "GLBX.MDP3"
SAMPLE_START = "2010-06-06"
SAMPLE_END_EXCLUSIVE = "2026-07-01"

CME_UNIVERSE = {
    "energy": ["CL.FUT", "HO.FUT", "RB.FUT", "NG.FUT"],
    "metals": ["GC.FUT", "SI.FUT", "HG.FUT", "PL.FUT", "PA.FUT"],
    "grains": ["ZC.FUT", "ZS.FUT", "ZW.FUT", "ZM.FUT", "ZL.FUT", "KE.FUT"],
    "livestock": ["LE.FUT", "HE.FUT", "GF.FUT"],
}
ALL_SYMBOLS = [s for syms in CME_UNIVERSE.values() for s in syms]

# Already-quoted costs, ledger rows 41-42, this same session
ALREADY_QUOTED = {"statistics": 20.757709, "definition": 25.256725}
REMAINING_SCHEMAS = ["statistics", "definition"]

# Continuing from row 43 (the last row written: the successful ohlcv-1d REAL SPEND)
CARRY_FORWARD_ROW_N = 43
CARRY_FORWARD_QUOTE_CUMULATIVE = 181.316941
CARRY_FORWARD_REAL_SPEND_CUMULATIVE = 44.644125

KEY_PATTERN = re.compile(r"db-[A-Za-z0-9_-]{16,}")


def scrub(text: str) -> str:
    return KEY_PATTERN.sub("[REDACTED-KEY]", text)


def load_key_into_env() -> str:
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


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def append_ledger_row(n, track, call_type, params, cost, cumulative, note=""):
    ts = datetime.now(timezone.utc).isoformat()
    row = (f"| {n} | {ts} | {track} | {scrub(call_type)} | {scrub(params)} | "
           f"{cost:.6f} | {cumulative:.6f} | {scrub(note)} |\n")
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(row)


def append_ledger_note(text: str):
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n{scrub(text)}\n")


def main():
    key_source = load_key_into_env()
    if key_source:
        print(f"DATABENTO_API_KEY loaded from: {key_source}")
    try:
        client = db.Historical()
    except ValueError as e:
        print(f"Cannot construct client: {e}", file=sys.stderr)
        sys.exit(2)

    append_ledger_note(f"### Phase 1a retry (statistics, definition) -- {datetime.now(timezone.utc).isoformat()}")

    row_n = CARRY_FORWARD_ROW_N
    real_spend_cum = CARRY_FORWARD_REAL_SPEND_CUMULATIVE
    pull_results = {}

    for schema in REMAINING_SCHEMAS:
        out_path = DATA_DIR / f"{schema}.dbn.zst"
        attempt = 0
        while True:
            attempt += 1
            try:
                client.timeseries.get_range(
                    dataset=DATASET, symbols=ALL_SYMBOLS, stype_in="parent",
                    schema=schema, start=SAMPLE_START, end=SAMPLE_END_EXCLUSIVE,
                    path=out_path,
                )
                break
            except BentoError as e:
                print(f"Attempt {attempt} for {schema} failed: {scrub(str(e))}", file=sys.stderr)
                if attempt >= 3:
                    append_ledger_note(f"STOP: {schema} failed {attempt} attempts, last error: {scrub(str(e))}")
                    print(f"STOP: giving up on {schema} after {attempt} attempts", file=sys.stderr)
                    sys.exit(1)
                if out_path.exists():
                    out_path.unlink()  # remove any partial file before retrying

        cost = ALREADY_QUOTED[schema]
        row_n += 1
        real_spend_cum += cost
        append_ledger_row(
            row_n, "REAL SPEND", "get_range (Phase 1a corpus pull, retry, actual)",
            f"schema={schema} symbols=18 start={SAMPLE_START} end={SAMPLE_END_EXCLUSIVE} path={out_path.name} attempts={attempt}",
            cost, real_spend_cum,
        )

        size_bytes = out_path.stat().st_size
        checksum = sha256_of(out_path)
        pull_results[schema] = {"path": str(out_path), "size_bytes": size_bytes, "sha256": checksum, "attempts": attempt}
        print(f"  pulled {schema}: {out_path.name} ({size_bytes:,} bytes), sha256={checksum}, attempts={attempt}")

    append_ledger_note(
        f"Phase 1a retry complete. Real spend this retry: ${sum(ALREADY_QUOTED[s] for s in REMAINING_SCHEMAS):.6f}. "
        f"Ledger real-spend cumulative (all sessions): ${real_spend_cum:.6f}."
    )

    # Merge into the existing summary JSON (ohlcv-1d was already recorded there)
    if PULL_SUMMARY_PATH.exists():
        summary = json.loads(PULL_SUMMARY_PATH.read_text(encoding="utf-8"))
    else:
        summary = {"files": {}}
    summary.setdefault("files", {}).update(pull_results)
    summary["ledger_real_spend_cumulative_usd"] = real_spend_cum
    summary["retry_completed_utc"] = datetime.now(timezone.utc).isoformat()
    PULL_SUMMARY_PATH.write_text(scrub(json.dumps(summary, indent=2)), encoding="utf-8")

    print(f"\nRetry complete. Ledger real-spend cumulative: ${real_spend_cum:.6f}")


if __name__ == "__main__":
    main()
