"""
Phase 1a follow-up -- submit statistics and definition as Databento batch
jobs (client.batch.submit_job), replacing the synchronous streaming
approach that hit persistent 504 gateway timeouts in session 1. Same
locked whitelist: GLBX.MDP3, the 18 pre-registered symbols (parent
symbology), 2010-06-06 (inclusive) to 2026-07-01 (exclusive) -- through
2026-06-30 inclusive.

submit_job() itself incurs the cost (per the SDK's own docstring warning),
same as get_range() did for streaming -- so REAL SPEND is logged
immediately on a successful submission response, not deferred to download
time. get_cost is called first as a free preview and gate, same guardrail
pattern as every other pull this project has done.

This script only submits and logs job IDs to a local state file for the
companion poll/download script to pick up -- it does not block waiting for
completion, since batch job processing time is unknown and potentially
long (that's the entire point of using batch over synchronous streaming).
"""
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
LEDGER_PATH = REPO / "docs" / "samples" / "COST_LEDGER.md"
JOB_STATE_PATH = WORKSPACE / "phase1a_batch_jobs.json"

DATASET = "GLBX.MDP3"
SAMPLE_START = "2010-06-06"
SAMPLE_END_EXCLUSIVE = "2026-07-01"
SCHEMAS_TO_SUBMIT = ["statistics", "definition"]

CME_UNIVERSE = {
    "energy": ["CL.FUT", "HO.FUT", "RB.FUT", "NG.FUT"],
    "metals": ["GC.FUT", "SI.FUT", "HG.FUT", "PL.FUT", "PA.FUT"],
    "grains": ["ZC.FUT", "ZS.FUT", "ZW.FUT", "ZM.FUT", "ZL.FUT", "KE.FUT"],
    "livestock": ["LE.FUT", "HE.FUT", "GF.FUT"],
}
ALL_SYMBOLS = [s for syms in CME_UNIVERSE.values() for s in syms]

CUMULATIVE_CEILING = 100.00
# Worst-case cumulative billed so far this project, per the reconciliation
# logged in COST_LEDGER.md this session (confirmed $47.364661 + worst-case
# ambiguous $2.810727 that may or may not actually have been billed).
WORST_CASE_PRIOR_CUMULATIVE = 50.175388

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


def append_ledger(text: str):
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(scrub(text))


def main():
    key_source = load_key_into_env()
    if key_source:
        print(f"DATABENTO_API_KEY loaded from: {key_source}")
    try:
        client = db.Historical()
    except ValueError as e:
        print(f"Cannot construct client: {e}", file=sys.stderr)
        sys.exit(2)

    append_ledger(f"\n\n### Phase 1a follow-up -- batch job submission, {datetime.now(timezone.utc).isoformat()}\n\n")
    append_ledger("| Schema | Quoted (USD) | Job ID | Submitted |\n|---|---|---|---|\n")

    running_cumulative = WORST_CASE_PRIOR_CUMULATIVE
    jobs = {}

    for schema in SCHEMAS_TO_SUBMIT:
        try:
            cost = client.metadata.get_cost(
                dataset=DATASET, symbols=ALL_SYMBOLS, stype_in="parent",
                schema=schema, start=SAMPLE_START, end=SAMPLE_END_EXCLUSIVE,
            )
        except BentoError as e:
            append_ledger(f"| {schema} | ERROR | -- | get_cost failed: {scrub(str(e))} |\n")
            print(f"STOP: get_cost failed for {schema}: {scrub(str(e))}", file=sys.stderr)
            sys.exit(1)

        print(f"{schema}: quoted ${cost:.6f}")

        projected = running_cumulative + cost
        if projected > CUMULATIVE_CEILING:
            append_ledger(f"| {schema} | {cost:.6f} | -- | STOP: projected cumulative ${projected:.6f} exceeds ${CUMULATIVE_CEILING} ceiling, NOT submitted |\n")
            print(f"STOP: ${projected:.6f} > ${CUMULATIVE_CEILING} ceiling. {schema} NOT submitted.", file=sys.stderr)
            sys.exit(1)

        try:
            job_info = client.batch.submit_job(
                dataset=DATASET, symbols=ALL_SYMBOLS, stype_in="parent",
                schema=schema, start=SAMPLE_START, end=SAMPLE_END_EXCLUSIVE,
                encoding="dbn", compression="zstd",
            )
        except BentoError as e:
            append_ledger(f"| {schema} | {cost:.6f} | -- | submit_job FAILED: {scrub(str(e))} |\n")
            print(f"STOP: submit_job failed for {schema}: {scrub(str(e))}", file=sys.stderr)
            sys.exit(1)

        job_id = job_info.get("id") or job_info.get("job_id")
        running_cumulative += cost
        append_ledger(f"| {schema} | {cost:.6f} | `{job_id}` | yes -- billed on submission per SDK docstring, logged as REAL SPEND now |\n")

        jobs[schema] = {
            "job_id": job_id,
            "quoted_cost_usd": cost,
            "submitted_utc": datetime.now(timezone.utc).isoformat(),
            "raw_job_info": job_info,
        }
        print(f"{schema}: submitted, job_id={job_id}, cost=${cost:.6f}")

    append_ledger(f"\nRunning cumulative after this session's batch submissions (worst-case basis): ${running_cumulative:.6f}\n")

    JOB_STATE_PATH.write_text(scrub(json.dumps(jobs, indent=2, default=str)), encoding="utf-8")
    print(f"\nJob state written to {JOB_STATE_PATH}")
    print(f"Running cumulative (worst-case basis): ${running_cumulative:.6f} / ${CUMULATIVE_CEILING} ceiling")


if __name__ == "__main__":
    main()
