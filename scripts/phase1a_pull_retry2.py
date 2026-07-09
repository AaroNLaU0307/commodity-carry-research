"""
Second retry. `definition` is attempted unchunked (small reference-data
schema, expected fast). `statistics` timed out 4/4 attempts as a single
16-year request (1 initial + 3 retries) while `ohlcv-1d` succeeded fine at
the same symbol/date scope -- so this splits `statistics` into yearly
chunks against the same locked whitelist (same dataset, schema, symbols,
overall date range; only the mechanical batching changes, which "batch or
streaming per your judgment" already covers). Each chunk is re-quoted via
get_cost before being pulled, so the ceiling guardrail applies per chunk as
well as in aggregate.
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
PULL_APPROVAL_CEILING = 100.00

CME_UNIVERSE = {
    "energy": ["CL.FUT", "HO.FUT", "RB.FUT", "NG.FUT"],
    "metals": ["GC.FUT", "SI.FUT", "HG.FUT", "PL.FUT", "PA.FUT"],
    "grains": ["ZC.FUT", "ZS.FUT", "ZW.FUT", "ZM.FUT", "ZL.FUT", "KE.FUT"],
    "livestock": ["LE.FUT", "HE.FUT", "GF.FUT"],
}
ALL_SYMBOLS = [s for syms in CME_UNIVERSE.values() for s in syms]

# Yearly chunk boundaries covering the same locked 2010-06-06..2026-07-01(excl) range
CHUNK_BOUNDARIES = (
    ["2010-06-06"] + [f"{y}-01-01" for y in range(2011, 2027)] + ["2026-07-01"]
)
STATISTICS_CHUNKS = list(zip(CHUNK_BOUNDARIES[:-1], CHUNK_BOUNDARIES[1:]))

# Continuing from row 44 (last row was the "STOP" note after retry #1)
CARRY_FORWARD_ROW_N = 44
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


class Row:
    def __init__(self):
        self.n = CARRY_FORWARD_ROW_N
        self.quote_cum = CARRY_FORWARD_QUOTE_CUMULATIVE
        self.real_cum = CARRY_FORWARD_REAL_SPEND_CUMULATIVE

    def quote(self, call_type, params, cost, note=""):
        self.n += 1
        self.quote_cum += cost
        self._write("QUOTE", call_type, params, cost, self.quote_cum, note)

    def real(self, call_type, params, cost, note=""):
        self.n += 1
        self.real_cum += cost
        self._write("REAL SPEND", call_type, params, cost, self.real_cum, note)

    def _write(self, track, call_type, params, cost, cumulative, note):
        ts = datetime.now(timezone.utc).isoformat()
        row = (f"| {self.n} | {ts} | {track} | {scrub(call_type)} | {scrub(params)} | "
               f"{cost:.6f} | {cumulative:.6f} | {scrub(note)} |\n")
        with LEDGER_PATH.open("a", encoding="utf-8") as f:
            f.write(row)

    def note(self, text):
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

    row = Row()
    row.note(f"### Phase 1a retry #2 (definition unchunked; statistics chunked yearly) -- {datetime.now(timezone.utc).isoformat()}")

    pull_results = {}

    # ---- definition: try unchunked first (expected small/fast) ----
    def_cost = 25.256725  # already quoted, ledger row 42, this session
    out_path = DATA_DIR / "definition.dbn.zst"
    try:
        client.timeseries.get_range(
            dataset=DATASET, symbols=ALL_SYMBOLS, stype_in="parent",
            schema="definition", start="2010-06-06", end="2026-07-01",
            path=out_path,
        )
        row.real("get_range (Phase 1a corpus pull, actual)",
                  "schema=definition symbols=18 start=2010-06-06 end=2026-07-01 path=definition.dbn.zst",
                  def_cost)
        checksum = sha256_of(out_path)
        pull_results["definition"] = {"path": str(out_path), "size_bytes": out_path.stat().st_size, "sha256": checksum}
        print(f"  pulled definition: {out_path.stat().st_size:,} bytes, sha256={checksum}")
    except BentoError as e:
        row.note(f"definition unchunked attempt failed: {scrub(str(e))} -- will need its own retry")
        print(f"definition failed: {scrub(str(e))}", file=sys.stderr)

    # ---- statistics: yearly chunks, each re-quoted before pulling ----
    chunk_files = []
    running_total_this_script = def_cost if "definition" in pull_results else 0.0
    for i, (start, end) in enumerate(STATISTICS_CHUNKS):
        try:
            cost = client.metadata.get_cost(
                dataset=DATASET, symbols=ALL_SYMBOLS, stype_in="parent",
                schema="statistics", start=start, end=end,
            )
        except BentoError as e:
            row.note(f"STOP: get_cost failed for statistics chunk {start}..{end}: {scrub(str(e))}")
            print(f"STOP: get_cost failed for chunk {start}..{end}: {scrub(str(e))}", file=sys.stderr)
            sys.exit(1)

        row.quote("get_cost (Phase 1a retry#2, statistics chunk)",
                   f"schema=statistics symbols=18 start={start} end={end}", cost)

        running_total_this_script += cost
        if CARRY_FORWARD_REAL_SPEND_CUMULATIVE + running_total_this_script > PULL_APPROVAL_CEILING:
            row.note(f"STOP: cumulative real spend would exceed ${PULL_APPROVAL_CEILING} ceiling at chunk {start}..{end}")
            print("STOP: ceiling would be exceeded", file=sys.stderr)
            sys.exit(1)

        chunk_path = DATA_DIR / f"statistics_{start}_{end}.dbn.zst"
        try:
            client.timeseries.get_range(
                dataset=DATASET, symbols=ALL_SYMBOLS, stype_in="parent",
                schema="statistics", start=start, end=end, path=chunk_path,
            )
        except BentoError as e:
            row.note(f"statistics chunk {start}..{end} failed: {scrub(str(e))}")
            print(f"  chunk {start}..{end} FAILED: {scrub(str(e))}", file=sys.stderr)
            continue  # keep going with remaining chunks; report failures at the end

        row.real("get_range (Phase 1a retry#2, statistics chunk, actual)",
                  f"schema=statistics symbols=18 start={start} end={end} path={chunk_path.name}", cost)
        checksum = sha256_of(chunk_path)
        chunk_files.append({"path": str(chunk_path), "start": start, "end": end,
                             "size_bytes": chunk_path.stat().st_size, "sha256": checksum, "cost_usd": cost})
        print(f"  pulled statistics chunk {start}..{end}: {chunk_path.stat().st_size:,} bytes (${cost:.4f})")

    pull_results["statistics_chunks"] = chunk_files
    row.note(f"Retry #2 complete. Ledger real-spend cumulative (all sessions): ${row.real_cum:.6f}.")

    if PULL_SUMMARY_PATH.exists():
        summary = json.loads(PULL_SUMMARY_PATH.read_text(encoding="utf-8"))
    else:
        summary = {"files": {}}
    summary.setdefault("files", {}).update(pull_results)
    summary["ledger_real_spend_cumulative_usd"] = row.real_cum
    summary["retry2_completed_utc"] = datetime.now(timezone.utc).isoformat()
    PULL_SUMMARY_PATH.write_text(scrub(json.dumps(summary, indent=2)), encoding="utf-8")

    print(f"\nRetry #2 complete. Ledger real-spend cumulative: ${row.real_cum:.6f}")
    n_chunks_ok = len(chunk_files)
    n_chunks_total = len(STATISTICS_CHUNKS)
    print(f"Statistics chunks: {n_chunks_ok}/{n_chunks_total} succeeded")
    if n_chunks_ok < n_chunks_total:
        print("SOME STATISTICS CHUNKS FAILED -- see ledger notes and stderr above", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
