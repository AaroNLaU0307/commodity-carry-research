"""
Phase 1a follow-up -- poll the batch jobs submitted by phase1a_batch_submit.py
and download whichever have reached 'done'. Safe to re-run repeatedly; does
nothing (no re-billing) for jobs already downloaded, and resumes cleanly if
interrupted -- every file already present at its expected size is skipped.
Downloading a batch job is not a separate charge -- cost was incurred at
submit_job() time.

Revision note (Phase 1a follow-up session, same day as the original bulk-
download version): a bulk `client.batch.download(job_id=...)` call for the
`definition` job (5,031 per-day data files, split_duration="day" is
Databento's batch-job default) itself hit a `504 gateway timeout` -- the
same failure mode session 1 saw on synchronous streaming, just relocated to
the download step of a job that had otherwise finished processing
server-side. Fix: download files INDIVIDUALLY via the SDK's documented
`filename_to_download` parameter (`GET /batch/download/{job_id}/{filename}`,
a much smaller request per call than the all-files bulk endpoint), with a
small thread pool and per-file retry -- the same "break a large transfer
into small, independently-retriable pieces" fix already used for
`statistics` in Step 1's yearly-chunk workaround, just applied one level
lower (per-file instead of per-year).

Per-day files are NOT concatenated into a single {schema}.dbn.zst -- naively
concatenating independently zstd-compressed DBN streams is not valid (each
carries its own DBN metadata header; nothing downstream should assume a
single header covers the whole file). Delivered files are kept under
DATA_DIR/{schema}/ with their original per-day filenames, and read back via
data_loader.load_dbn_partitioned(), which concatenates the decoded frames in
pandas, not the raw compressed bytes.
"""
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import databento as db
from databento.common.error import BentoError

WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")
DATA_DIR = Path(r"C:\Users\Aaron\quant-data\commodity-carry")
JOB_STATE_PATH = WORKSPACE / "phase1a_batch_jobs.json"
BATCH_STAGING_DIR = WORKSPACE / "batch_staging"

MAX_WORKERS = 16
MAX_ATTEMPTS_PER_FILE = 3
RETRY_BACKOFF_SECONDS = 2.0
PROGRESS_EVERY = 200

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


def _download_one(client, job_id: str, filename: str, staging_out: Path, expected_size):
    """Downloads a single file, retrying transient errors. Skips (returns
    'skipped') if a correctly-sized copy is already present -- resume
    support across repeated runs of this script."""
    dest = staging_out / job_id / filename
    if dest.exists() and (expected_size is None or dest.stat().st_size == expected_size):
        return filename, "skipped", None

    last_err = None
    for attempt in range(1, MAX_ATTEMPTS_PER_FILE + 1):
        try:
            client.batch.download(job_id=job_id, output_dir=staging_out, filename_to_download=filename)
            return filename, "ok", None
        except Exception as e:  # noqa: BLE001 -- narrow, contained retry boundary around one idempotent GET
            last_err = e
            if attempt < MAX_ATTEMPTS_PER_FILE:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    return filename, "failed", scrub(str(last_err))


def download_job_individually(client, job_id: str, schema: str, staging_out: Path) -> dict:
    file_list = client.batch.list_files(job_id)
    data_entries = [f for f in file_list if str(f.get("filename", "")).endswith((".dbn.zst", ".dbn"))]
    sidecar_entries = [f for f in file_list if f not in data_entries]
    print(f"  {len(file_list)} file(s) listed: {len(data_entries)} data file(s), {len(sidecar_entries)} sidecar file(s)")

    staging_out.mkdir(parents=True, exist_ok=True)

    results = {"ok": [], "skipped": [], "failed": []}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_download_one, client, job_id, f["filename"], staging_out, f.get("size")): f["filename"]
            for f in data_entries
        }
        done_count = 0
        for fut in as_completed(futures):
            filename, status, err = fut.result()
            results[status].append(filename if status != "failed" else (filename, err))
            done_count += 1
            if done_count % PROGRESS_EVERY == 0 or done_count == len(data_entries):
                print(f"  progress: {done_count}/{len(data_entries)} "
                      f"(ok={len(results['ok'])} skipped={len(results['skipped'])} failed={len(results['failed'])})")

    # Sidecar files (manifest.json/condition.json/metadata.json) -- best-effort,
    # not required for the data itself, so a failure here does not block finalization.
    for f in sidecar_entries:
        try:
            _download_one(client, job_id, f["filename"], staging_out, f.get("size"))
        except Exception:
            pass

    results["n_data_expected"] = len(data_entries)
    return results


def main():
    key_source = load_key_into_env()
    if key_source:
        print(f"DATABENTO_API_KEY loaded from: {key_source}")
    try:
        client = db.Historical()
    except ValueError as e:
        print(f"Cannot construct client: {e}", file=sys.stderr)
        sys.exit(2)

    if not JOB_STATE_PATH.exists():
        print(f"No job state file at {JOB_STATE_PATH} -- run phase1a_batch_submit.py first.", file=sys.stderr)
        sys.exit(1)

    jobs = json.loads(JOB_STATE_PATH.read_text(encoding="utf-8"))

    for schema, info in jobs.items():
        if info.get("downloaded"):
            print(f"{schema}: already downloaded, skipping ({info.get('final_dir') or info.get('final_path')})")
            continue

        job_id = info["job_id"]
        try:
            details = client.batch.get_job_details(job_id)
        except BentoError as e:
            print(f"{schema} ({job_id}): could not fetch job details: {scrub(str(e))}", file=sys.stderr)
            continue

        state = details.get("state", "unknown")
        print(f"{schema} ({job_id}): state={state}")

        if state != "done":
            continue

        try:
            results = download_job_individually(client, job_id, schema, BATCH_STAGING_DIR)
        except BentoError as e:
            print(f"{schema} ({job_id}): could not list files: {scrub(str(e))}", file=sys.stderr)
            continue

        if results["failed"]:
            print(f"  {schema}: {len(results['failed'])} file(s) still failing after "
                  f"{MAX_ATTEMPTS_PER_FILE} attempts each -- re-run this script to retry just those "
                  f"(already-downloaded files are skipped, no re-billing either way).")
            for fname, err in results["failed"][:10]:
                print(f"    FAILED: {fname} -- {err}")
            continue  # do not finalize a partial delivery

        n_ok_total = len(results["ok"]) + len(results["skipped"])
        if n_ok_total != results["n_data_expected"]:
            print(f"  WARNING: {schema}: expected {results['n_data_expected']} data files, "
                  f"accounted for {n_ok_total} -- not finalizing.", file=sys.stderr)
            continue

        # All data files confirmed present in staging -- finalize into
        # DATA_DIR/{schema}/ preserving original per-day filenames (move, not
        # copy: staging and DATA_DIR are on the same volume, so this is a fast
        # rename, and it avoids doubling ~1-2 GB of disk use per schema).
        staged_dir = BATCH_STAGING_DIR / job_id
        final_dir = DATA_DIR / schema
        final_dir.mkdir(parents=True, exist_ok=True)
        moved = 0
        for p in staged_dir.glob("*.dbn.zst"):
            dest = final_dir / p.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(p), str(dest))
            moved += 1
        for p in staged_dir.glob("*.dbn"):
            dest = final_dir / p.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(p), str(dest))
            moved += 1

        info["downloaded"] = True
        info["downloaded_utc"] = datetime.now(timezone.utc).isoformat()
        info["job_state"] = state
        info["n_files"] = moved
        info["final_dir"] = str(final_dir)
        print(f"  -> {moved} file(s) finalized at {final_dir}")

    JOB_STATE_PATH.write_text(scrub(json.dumps(jobs, indent=2, default=str)), encoding="utf-8")
    print(f"\nJob state updated: {JOB_STATE_PATH}")

    all_done = all(j.get("downloaded") for j in jobs.values())
    print("ALL_DOWNLOADED" if all_done else "STILL_WAITING")


if __name__ == "__main__":
    main()
