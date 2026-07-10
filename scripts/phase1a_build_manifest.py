"""
Builds data/MANIFEST.md from whatever is actually in DATA_DIR. Run only
after all expected files for a schema are present -- this script does not
pull anything itself, it only inventories and checksums what has already
landed.

Handles two delivery shapes per schema:
  - single file:      DATA_DIR/{schema}.dbn.zst           (ohlcv-1d)
  - per-day directory: DATA_DIR/{schema}/*.dbn.zst          (definition --
    Databento's batch-job default is to split by day; concatenating the
    compressed per-day files into one is not valid DBN, so they are kept
    as delivered -- see scripts/phase1a_batch_poll_download.py's docstring)

For a per-day directory, every individual file is still checksummed (real
per-file integrity), but data/MANIFEST.md records an aggregate "manifest
hash" -- SHA-256 of the sorted "filename:sha256\\n" lines joined -- rather
than a 5,000+ row markdown table. The full per-file list is written
alongside it in WORKSPACE (not committed; reproducible from DATA_DIR at any
time) for anyone who needs to verify one specific day's file.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")
REPO = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\commodity-carry-research")
DATA_DIR = Path(r"C:\Users\Aaron\quant-data\commodity-carry")
MANIFEST_PATH = REPO / "data" / "MANIFEST.md"

# Schemas confirmed fully delivered as of this manifest generation -- see
# docs/DATA_QA_REPORT.md Sec 0 / addendum for what's actually complete.
# "statistics" is deliberately absent: still processing server-side
# (Databento batch job GLBX-20260710-E8YMQQJMA7) as of this snapshot.
CONFIRMED_COMPLETE_SCHEMAS = {
    "ohlcv-1d": "single_file",
    "definition": "per_day_dir",
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_single_file(schema: str):
    path = DATA_DIR / f"{schema}.dbn.zst"
    if not path.exists():
        return None
    checksum = sha256_of(path)
    return {
        "schema": schema, "kind": "single_file", "n_files": 1,
        "total_bytes": path.stat().st_size,
        "files": [{"name": path.name, "size": path.stat().st_size, "sha256": checksum}],
    }


def manifest_per_day_dir(schema: str):
    d = DATA_DIR / schema
    if not d.is_dir():
        return None
    files = sorted(d.glob("*.dbn.zst"))
    if not files:
        return None
    entries = []
    for f in files:
        entries.append({"name": f.name, "size": f.stat().st_size, "sha256": sha256_of(f)})
    joined = "\n".join(f"{e['name']}:{e['sha256']}" for e in entries)
    aggregate_hash = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return {
        "schema": schema, "kind": "per_day_dir", "n_files": len(entries),
        "total_bytes": sum(e["size"] for e in entries),
        "aggregate_sha256": aggregate_hash, "files": entries,
    }


def main():
    results = []
    for schema, kind in CONFIRMED_COMPLETE_SCHEMAS.items():
        r = manifest_single_file(schema) if kind == "single_file" else manifest_per_day_dir(schema)
        if r is None:
            print(f"WARNING: {schema} ({kind}) expected but not found in {DATA_DIR} -- skipping")
            continue
        results.append(r)

    if not results:
        raise SystemExit(f"No confirmed-complete schemas found in {DATA_DIR} -- has any pull completed?")

    lines = [
        "# Data Provenance Manifest",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "Raw files live in `DATA_DIR` (see `src/config.py` / README's Data storage "
        "section) -- outside this repo and outside OneDrive. Never committed. This "
        "manifest is the committed record of what was pulled, when, and its checksums.",
        "",
        "## Request parameters (locked, PREREGISTRATION.md Sec 2)",
        "",
        "- Dataset: `GLBX.MDP3`",
        "- Symbols: 18 pre-registered CME symbols (parent symbology)",
        "- Date range: `2010-06-06` (inclusive) to `2026-07-01` (exclusive) == through "
        "2026-06-30 inclusive",
        "- Schemas: `ohlcv-1d`, `statistics`, `definition`",
        "",
        "## Cost",
        "",
        "See `docs/samples/COST_LEDGER.md` for every quote and every real charge, in order.",
        "",
        "## Files",
        "",
    ]

    for r in results:
        lines.append(f"### `{r['schema']}`")
        lines.append("")
        if r["kind"] == "single_file":
            f = r["files"][0]
            lines.append("| File | Size (bytes) | SHA-256 |")
            lines.append("|---|---|---|")
            lines.append(f"| `{f['name']}` | {f['size']:,} | `{f['sha256']}` |")
        else:
            lines.append(
                f"Delivered as {r['n_files']:,} per-day files (Databento batch-job default "
                f"split_duration=\"day\"; concatenating independently-compressed DBN streams "
                f"is not valid, so they are kept as delivered -- see "
                f"`scripts/phase1a_batch_poll_download.py`)."
            )
            lines.append("")
            lines.append(f"- Total files: {r['n_files']:,}")
            lines.append(f"- Total bytes: {r['total_bytes']:,}")
            lines.append(
                f"- Aggregate SHA-256 (of the sorted `filename:sha256` lines for every "
                f"individual file, newline-joined): `{r['aggregate_sha256']}`"
            )
            lines.append(
                f"- Full per-file checksum list: `{schema_perfile_path(r['schema']).name}` "
                f"(WORKSPACE, not committed -- reproducible from `DATA_DIR` at any time; "
                f"the aggregate hash above is what's committed here as the tamper-evident record)"
            )
            perfile_path = schema_perfile_path(r["schema"])
            perfile_path.write_text(json.dumps(r["files"], indent=2), encoding="utf-8")
        lines.append("")

    total_files = sum(r["n_files"] for r in results)
    total_bytes = sum(r["total_bytes"] for r in results)
    lines += [
        f"Total confirmed-complete: {len(results)} schema(s), {total_files:,} file(s), {total_bytes:,} bytes.",
        "",
        "## Not yet manifested",
        "",
        "- `statistics` -- submitted as a Databento batch job (`GLBX-20260710-E8YMQQJMA7`), "
        "billed at submission, still processing server-side as of this manifest generation. "
        "See `docs/DATA_QA_REPORT.md`'s addendum Sec 0 for the current progress reading and "
        "honest ETA assessment.",
        "- 4 pre-batch `statistics` yearly-chunk files remain in `DATA_DIR` "
        "(`statistics_2010-06-06_2011-01-01.dbn.zst` and 3 others) -- confirmed billed "
        "(`docs/samples/COST_LEDGER.md` rows 46/49/51/54) but superseded by the pending "
        "full-range batch job per the Step 1 reconciliation plan; kept until that job "
        "completes and is verified, then removed as redundant. Not manifested here since "
        "they cover only partial date ranges, not the full locked window.",
        "",
        "## Notes",
        "",
        "- Raw data integrity findings (settlement/OI coverage, gaps, expiry "
        "calendar completeness, spot-checks) are in `docs/DATA_QA_REPORT.md`, not here "
        "-- this manifest is provenance only.",
    ]

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {MANIFEST_PATH} covering {len(results)} schema(s), {total_files:,} file(s).")


def schema_perfile_path(schema: str) -> Path:
    return WORKSPACE / f"manifest_perfile_{schema}.json"


if __name__ == "__main__":
    main()
