"""
Builds data/MANIFEST.md from whatever is actually in DATA_DIR plus the
Phase 1a pull summary JSON (request parameters, per-file SHA-256, sizes).
Run only after all expected files are present -- this script does not pull
anything itself, it only inventories and checksums what has already landed.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")
REPO = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\commodity-carry-research")
DATA_DIR = Path(r"C:\Users\Aaron\quant-data\commodity-carry")
PULL_SUMMARY_PATH = WORKSPACE / "phase1a_pull_summary.json"
MANIFEST_PATH = REPO / "data" / "MANIFEST.md"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# Only files confirmed complete (a matching REAL SPEND ledger row exists for
# them) are manifested with a checksum. In-progress downloads are excluded --
# checksumming a file that's still being written to is a race condition and
# would record a meaningless, unstable hash. See docs/DATA_QA_REPORT.md Sec 0
# for which schemas are actually complete as of this snapshot.
CONFIRMED_COMPLETE_FILES = ["ohlcv-1d.dbn.zst"]


def main():
    all_files = sorted(DATA_DIR.glob("*.dbn.zst"))
    files = [f for f in all_files if f.name in CONFIRMED_COMPLETE_FILES]
    in_progress = [f for f in all_files if f.name not in CONFIRMED_COMPLETE_FILES]
    if not files:
        raise SystemExit(f"No confirmed-complete .dbn.zst files found in {DATA_DIR} -- has any pull completed?")

    summary = {}
    if PULL_SUMMARY_PATH.exists():
        summary = json.loads(PULL_SUMMARY_PATH.read_text(encoding="utf-8"))

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
        f"- Dataset: `{summary.get('dataset', 'GLBX.MDP3')}`",
        f"- Symbols: 18 pre-registered CME symbols (parent symbology)",
        f"- Date range: `{summary.get('start', '2010-06-06')}` (inclusive) to "
        f"`{summary.get('end_exclusive', '2026-07-01')}` (exclusive) == through "
        f"2026-06-30 inclusive",
        f"- Schemas: `ohlcv-1d`, `statistics`, `definition`",
        "",
        "## Cost",
        "",
        f"- Total quoted: ${summary.get('total_quote_usd', 'see COST_LEDGER.md'):.6f}"
        if isinstance(summary.get("total_quote_usd"), float) else
        "- Total quoted: see `docs/samples/COST_LEDGER.md`",
        f"- Memo estimate: ${summary.get('memo_estimate_usd', 90.658381):.6f} "
        f"(delta {summary.get('delta_from_memo', 0):+.2%})"
        if isinstance(summary.get("delta_from_memo"), float) else "",
        f"- Full ledger: `docs/samples/COST_LEDGER.md` (continued from the Pass 2 session's rows 1-39)",
        "",
        "## Files",
        "",
        "| File | Size (bytes) | SHA-256 |",
        "|---|---|---|",
    ]

    for f in files:
        checksum = sha256_of(f)
        lines.append(f"| `{f.name}` | {f.stat().st_size:,} | `{checksum}` |")

    lines += [
        "",
        f"Total confirmed-complete: {len(files)} files, {sum(f.stat().st_size for f in files):,} bytes.",
        "",
    ]

    if in_progress:
        lines += [
            "## In progress / not yet manifested",
            "",
            "These files exist in `DATA_DIR` but are NOT yet confirmed complete "
            "(no matching REAL SPEND row in `docs/samples/COST_LEDGER.md` as of this "
            "manifest generation) and are therefore deliberately excluded above -- "
            "checksumming a file still being written to would record an unstable, "
            "meaningless hash. See `docs/DATA_QA_REPORT.md` Sec 0 for the full status.",
            "",
        ]
        for f in in_progress:
            lines.append(f"- `{f.name}` — {f.stat().st_size:,} bytes as of manifest generation, size not final")
        lines.append("")

    lines += [
        "## Notes",
        "",
        "- `statistics` was split into yearly (or finer) date-range chunks after the "
        "single full-range request consistently hit a server-side gateway timeout "
        "(`504`) across multiple attempts; `ohlcv-1d` succeeded as a single request. "
        "This is a mechanical delivery detail, not a change to what was requested -- "
        "every chunk covers the same locked whitelist (dataset, schema, symbols), "
        "just a narrower date sub-range per request. See `docs/samples/COST_LEDGER.md` "
        "for every chunk's individual quote and actual cost.",
        "- Raw data integrity findings (settlement/OI coverage, gaps, expiry "
        "calendar completeness, spot-checks) are in `docs/DATA_QA_REPORT.md`, not here "
        "-- this manifest is provenance only.",
    ]

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {MANIFEST_PATH} covering {len(files)} files.")


if __name__ == "__main__":
    main()
