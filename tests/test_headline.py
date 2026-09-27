"""results/headline.json: the machine-readable headline rows other pages
render from. Checks the schema, that every cited artifact exists, and that
every stat's value is printed on the cited line of its (markdown) artifact
and rounds to the displayed string. Runs without licensed data."""
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

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
