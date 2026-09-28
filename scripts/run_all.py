"""
Single entry point for the study.

    python scripts/run_all.py check-data [--skip-checksums] [--spot RAW_SYMBOL:YYYY-MM-DD ...]
    python scripts/run_all.py [all]          # premise -> primary -> robustness -> figures
    python scripts/run_all.py premise|primary|robustness|figures

`check-data` verifies DATA_DIR against data/MANIFEST.md's checksums and
prints, straight from the raw statistics files, the values a person must
compare with CME's published figures before trusting a run: stat_type 6
(CLEARED_VOLUME) vs 9 (OPEN_INTEREST) for CLK0 over 2020-04-13..20, and a
settlement spot-check that includes a Sunday-UTC-dated file. It writes
nothing. RERUN_RUNBOOK.md says what to compare against.

`all` loads the corpus once (src/study.py) and runs the four stages in
order; each stage writes its report and figures under reports/rerun/ and its
machine-readable results under results/. The published reports/*.md and
reports/figures/*.png are never written. Paths come from src/config.py (repo-relative
defaults; DATA_DIR and WORKSPACE environment variables).
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd
from databento_dbn import StatType

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))

from src import config, study

MANIFEST_PATH = REPO / "data" / "MANIFEST.md"
SETTLE, CLEARED_VOLUME, OPEN_INTEREST = (int(StatType.SETTLEMENT_PRICE), int(StatType.CLEARED_VOLUME),
                                         int(StatType.OPEN_INTEREST))
OI_CHECK = ("CLK0", "2020-04-13", "2020-04-20")
# Friday trade dates are re-sent at the Sunday 22:00 UTC session open, so
# each of them is printed from its Friday file AND its Sunday-dated file.
DEFAULT_SPOT_CHECKS = (
    ("CLK0", "2020-04-20"),
    ("CLK0", "2020-04-17"),
    ("GCM0", "2020-04-17"),
    ("ZCN0", "2020-04-17"),
    ("LEM0", "2020-04-17"),
    ("NGG1", "2021-01-15"),
)


# ---------------------------------------------------------------------------
# check-data
# ---------------------------------------------------------------------------
def parse_manifest(text: str) -> dict:
    """data/MANIFEST.md -> {schema: {"files": [(name, size, sha256)]} or
    {"n_files": int, "aggregate_sha256": str}} for the working-set schemas
    (the "Superseded" section is ignored)."""
    files_section = text.split("## Files", 1)[1].split("## Superseded", 1)[0]
    parts = re.split(r"^### `([^`]+)`\s*$", files_section, flags=re.MULTILINE)
    out = {}
    for schema, body in zip(parts[1::2], parts[2::2]):
        agg = re.search(r"Aggregate SHA-256.*`([0-9a-f]{64})`", body)
        if agg:
            n = re.search(r"Total files: ([\d,]+)", body)
            out[schema] = {"n_files": int(n.group(1).replace(",", "")), "aggregate_sha256": agg.group(1)}
        else:
            rows = re.findall(r"\| `([^`]+)` \| ([\d,]+) \| `([0-9a-f]{64})` \|", body)
            out[schema] = {"files": [(name, int(size.replace(",", "")), sha) for name, size, sha in rows]}
    return out


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def aggregate_sha256(files) -> str:
    """The manifest's per-directory hash: sha256 of the name-sorted
    "filename:sha256" lines joined by newlines (scripts/phase1a_build_manifest.py)."""
    lines = [f"{p.name}:{sha256_of(p)}" for p in sorted(files, key=lambda p: p.name)]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def verify_manifest(data_dir: Path, manifest_text: str) -> list:
    """[(schema, expected, actual, ok)] for every working-set schema."""
    results = []
    for schema, spec in parse_manifest(manifest_text).items():
        if "files" in spec:
            for name, _size, sha in spec["files"]:
                path = data_dir / name
                actual = sha256_of(path) if path.exists() else "missing"
                results.append((f"{schema}/{name}", sha, actual, actual == sha))
        else:
            files = sorted((data_dir / schema).glob("*.dbn.zst"))
            actual = aggregate_sha256(files) if files else "missing"
            ok = actual == spec["aggregate_sha256"] and len(files) == spec["n_files"]
            results.append((f"{schema}/ ({len(files):,} of {spec['n_files']:,} files)", spec["aggregate_sha256"],
                            actual, ok))
    return results


def _day_files(data_dir: Path, schema: str, day: pd.Timestamp) -> list:
    return sorted((data_dir / schema).glob(f"*{day:%Y%m%d}*.dbn.zst"))


def _instrument_ids(data_dir: Path, raw_symbol: str, day: pd.Timestamp) -> tuple:
    import databento as db
    for f in _day_files(data_dir, "definition", day):
        d = db.DBNStore.from_file(f).to_df()
        hit = d[(d["raw_symbol"] == raw_symbol) & (d["instrument_class"] == "F")]
        if len(hit):
            return sorted(set(hit["instrument_id"].astype(int))), None
        root = raw_symbol[:2]
        near = sorted(set(d.loc[d["raw_symbol"].str.startswith(root) & (d["instrument_class"] == "F"), "raw_symbol"]))
        return [], near[:20]
    return [], None


def _stat_records(data_dir: Path, ids: list, days) -> pd.DataFrame:
    import databento as db
    frames = []
    for day in days:
        for f in _day_files(data_dir, "statistics", day):
            d = db.DBNStore.from_file(f).to_df().reset_index()
            d = d[d["instrument_id"].isin(ids)].copy()
            d["file"] = f.name
            frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _stat_name(value) -> str:
    try:
        return StatType(int(value)).name
    except ValueError:
        return str(value)


def check_open_interest_field(data_dir: Path, raw_symbol: str, start: str, end: str) -> None:
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    ids, near = _instrument_ids(data_dir, raw_symbol, first)
    print(f"\n== Open-interest field check: {raw_symbol}, trade dates {start}..{end} ==")
    if not ids:
        print(f"  {raw_symbol} not found in the {first.date()} definition file; outrights listed: {near}")
        return
    days = pd.date_range(first - pd.DateOffset(days=1), last + pd.DateOffset(days=3), freq="D")
    rec = _stat_records(data_dir, ids, days)
    rec = rec[rec["stat_type"].isin([SETTLE, CLEARED_VOLUME, OPEN_INTEREST])].copy()
    rec["trade_date"] = pd.to_datetime(rec["ts_ref"], utc=True).dt.tz_convert(None).dt.normalize()
    rec = rec[(rec["trade_date"] >= first) & (rec["trade_date"] <= last)]
    rec["stat"] = rec["stat_type"].map(_stat_name)
    rec["value"] = rec["price"].where(rec["stat_type"] == SETTLE, rec["quantity"])
    table = (rec.sort_values("ts_recv").groupby(["trade_date", "stat"])["value"].last()
             .unstack("stat").reindex(columns=["SETTLEMENT_PRICE", "CLEARED_VOLUME", "OPEN_INTEREST"]))
    oi = rec[rec["stat_type"] == OPEN_INTEREST]
    table["OPEN_INTEREST first received (UTC)"] = oi.groupby("trade_date")["ts_recv"].min()
    print(f"  instrument_id(s): {ids}. Last-received value per trade date (ts_ref):")
    print(table.to_string())
    print("  Compare OPEN_INTEREST (stat_type 9) and CLEARED_VOLUME (stat_type 6) with CME's published "
          "open interest and volume for this contract; the pipeline uses OPEN_INTEREST. Each trade date's "
          "OPEN_INTEREST must arrive before the next trade date's settlement (the roll uses it the next day).")


def spot_check_settlements(data_dir: Path, checks) -> None:
    print("\n== Settlement spot-check (every SETTLEMENT_PRICE record for the trade date, by file) ==")
    for raw_symbol, day in checks:
        trade_date = pd.Timestamp(day)
        ids, near = _instrument_ids(data_dir, raw_symbol, trade_date)
        print(f"\n-- {raw_symbol} trade date {trade_date.date()} ({trade_date.day_name()})")
        if not ids:
            print(f"   not found in that day's definition file; outrights listed: {near}")
            continue
        rec = _stat_records(data_dir, ids, pd.date_range(trade_date, trade_date + pd.DateOffset(days=3), freq="D"))
        if rec.empty:
            print("   no statistics records found")
            continue
        rec = rec[rec["stat_type"] == SETTLE].copy()
        rec["trade_date"] = pd.to_datetime(rec["ts_ref"], utc=True).dt.tz_convert(None).dt.normalize()
        rec = rec[rec["trade_date"] == trade_date].sort_values("ts_recv")
        for _, r in rec.iterrows():
            weekday = pd.Timestamp(r["ts_recv"]).day_name()
            print(f"   {r['file']}  ts_recv={r['ts_recv']} ({weekday})  ts_ref={r['ts_ref']}  price={r['price']}  "
                  f"stat_flags={r['stat_flags']}  update_action={r['update_action']}")
        if len(rec):
            print(f"   -> pipeline value (last received): {rec['price'].iloc[-1]}")


def check_data(skip_checksums: bool, spot) -> int:
    data_dir = Path(config.DATA_DIR)
    print(f"DATA_DIR = {data_dir}")
    status = 0
    if not skip_checksums:
        print("\n== Checksums against data/MANIFEST.md ==")
        for name, expected, actual, ok in verify_manifest(data_dir, MANIFEST_PATH.read_text(encoding="utf-8")):
            print(f"  {'OK  ' if ok else 'FAIL'} {name}  expected {expected}  got {actual}")
            status |= 0 if ok else 1
    check_open_interest_field(data_dir, *OI_CHECK)
    spot_check_settlements(data_dir, spot or DEFAULT_SPOT_CHECKS)
    return status


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------
def run_stages(stages) -> int:
    import generate_readme_figures as figures_stage
    import phase1b_premise_test as premise_stage
    import phase1c_primary_backtest as primary_stage
    import phase1c_robustness as robustness_stage

    print(f"code version (pinned for every stage of this run): {study.pin_code_version()}", flush=True)
    ctx = None
    if any(s in stages for s in ("premise", "primary", "robustness")):
        try:
            ctx = study.load_context(log=lambda m: print(m, flush=True))
        except study.StudyHalt as halt:
            premise_stage.handle_halt(halt)
            return 1
    if "premise" in stages:
        summary = premise_stage.run(ctx)
        if summary is None:
            return 1
        if not any(summary["gate"].values()):
            print("Both arms closed at the premise stage (Sec 7): no backtest is run.", flush=True)
            return 0
    if "primary" in stages:
        primary_stage.run(ctx)
    if "robustness" in stages:
        robustness_stage.run(ctx)
    if "figures" in stages:
        figures_stage.main()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", default="all",
                        choices=["all", "check-data", "premise", "primary", "robustness", "figures"])
    parser.add_argument("--skip-checksums", action="store_true", help="check-data: skip the ~9.4 GB hash pass")
    parser.add_argument("--spot", nargs="*", metavar="RAW_SYMBOL:YYYY-MM-DD",
                        help="check-data: settlement spot-checks instead of the defaults")
    args = parser.parse_args(argv)
    if args.command == "check-data":
        spot = [tuple(item.split(":", 1)) for item in args.spot] if args.spot else None
        return check_data(args.skip_checksums, spot)
    stages = ("premise", "primary", "robustness", "figures") if args.command == "all" else (args.command,)
    return run_stages(stages)


if __name__ == "__main__":
    sys.exit(main())
