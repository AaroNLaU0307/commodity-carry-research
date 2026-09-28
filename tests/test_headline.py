"""results/headline.json: the machine-readable headline rows other pages
render from. Checks the schema, that every cited artifact exists, and that
every stat's value is what its artifact holds -- printed on the cited line
of a markdown report ("line N: ..."), at the cited key path of a results
JSON ("json: arms.H1.net_sharpe"), or, for a count shown as "k/n", recounted
from the cited table rows ("lines A-B: ...") -- and matches the displayed
string. Runs without licensed data."""
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from src import config

REPO = Path(__file__).resolve().parents[1]
HEADLINE = json.loads((REPO / "results" / "headline.json").read_text(encoding="utf-8"))
TOP_KEYS = {"schema", "repo", "source_commit", "as_of", "rows"}
ROW_KEYS = {"id", "section", "hypothesis", "verdict", "verdict_detail", "mechanism", "stats", "caveats"}
STAT_KEYS = {"label", "display", "value", "artifact", "locator", "provenance"}
PROVENANCE = {"reproduced", "repo-reported, not reproduced", "predates fix; pending re-run"}
MINUS = "\u2212"  # the typographic minus used in display strings
STATS = [(row["id"], stat) for row in HEADLINE["rows"] for stat in row["stats"]]


def test_schema_keys_and_values():
    assert set(HEADLINE) == TOP_KEYS
    assert HEADLINE["schema"] == "headline/v1"
    assert HEADLINE["repo"] == "AaroNLaU0307/commodity-carry-research"
    assert re.fullmatch(r"[0-9a-f]{40}|PENDING", HEADLINE["source_commit"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", HEADLINE["as_of"])
    assert [row["id"] for row in HEADLINE["rows"]] == ["xs-carry", "ts-carry"]
    for row in HEADLINE["rows"]:
        assert set(row) == ROW_KEYS
        assert row["section"] in {"archive", "other"}
        assert all(isinstance(c, str) for c in row["caveats"])
        for stat in row["stats"]:
            assert set(stat) == STAT_KEYS
            assert stat["provenance"] in PROVENANCE


@pytest.mark.parametrize("row_id,stat", STATS, ids=[f"{r}:{s['label']}" for r, s in STATS])
def test_stat_is_printed_on_the_cited_line_and_matches_its_display(row_id, stat):
    path = REPO / stat["artifact"]
    assert path.is_file()
    if re.fullmatch(r"\d+/\d+", stat["display"]):
        if path.suffix == ".csv":
            _check_variant_count_csv(path, stat)
        else:
            _check_variant_count(path, stat)
        return
    display = stat["display"].replace(MINUS, "-")
    places = Decimal(display).as_tuple().exponent
    if path.suffix == ".json":
        node = json.loads(path.read_text(encoding="utf-8"))
        for key in re.match(r"json: ([\w.]+)", stat["locator"]).group(1).split("."):
            node = node[int(key)] if isinstance(node, list) else node[key]
        assert stat["value"] == pytest.approx(node, abs=1e-12)
        value = Decimal(repr(node))
    else:
        line_no = int(re.match(r"line (\d+)", stat["locator"]).group(1))
        line = path.read_text(encoding="utf-8").splitlines()[line_no - 1]
        assert f"{stat['value']:.4f}" in line
        value = Decimal(f"{stat['value']:.4f}")  # the reported 4-dp decimal
    # display = that decimal rounded half away from zero to the displayed places
    assert value.quantize(Decimal(1).scaleb(places), rounding=ROUND_HALF_UP) == Decimal(display)


REGISTERED_ROW = re.compile(r"^\| (\d+) \| [^|]+ \| (XS|TS) \| (-?\d+\.\d{4}) \|$")


def _check_variant_count(path, stat):
    """"k/n registered variants reaching the gate": the cited lines must be
    exactly the 12 registered variant rows of Sec 8 (items 1-7 and 10, per
    PREREGISTRATION.md Sec 10), and k must be how many have Sharpe >= the
    0.30 gate."""
    first, last = map(int, re.match(r"lines (\d+)-(\d+)", stat["locator"]).groups())
    rows = [REGISTERED_ROW.match(line) for line in path.read_text(encoding="utf-8").splitlines()[first - 1:last]]
    assert all(rows), "every cited line must be a registered-variant table row"
    assert len(rows) == 12
    assert sorted({int(r.group(1)) for r in rows}) == [1, 2, 3, 4, 5, 6, 7, 10]
    reaching = sum(float(r.group(3)) >= config.SHARPE_GATE_MIN for r in rows)
    assert stat["value"] == reaching
    assert stat["display"] == f"{reaching}/{len(rows)}"


def _check_variant_count_csv(path, stat):
    """"k/n registered variants reaching the gate", counted from the re-run's
    results/robustness_variants.csv: n is the rows with kind == registered,
    k those with Sharpe >= the 0.30 gate. In the 2026-09-28 re-run H2 closed
    at the premise gate, so these are H1's 8 Sec 8 items and its
    execution-lag-1 series (preregistration/AMENDMENT_2026-09-27.md)."""
    import csv
    with path.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["kind"] == "registered"]
    assert rows, "no registered rows"
    reaching = sum(float(r["sharpe"]) >= config.SHARPE_GATE_MIN for r in rows)
    assert stat["value"] == reaching
    assert stat["display"] == f"{reaching}/{len(rows)}"
