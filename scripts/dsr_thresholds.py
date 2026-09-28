"""
The Sharpe the DSR gate demands, per arm, at N_trials = 16 (registered, preregistration/AMENDMENT_2026-09-27.md
§2.3) and at N_trials = 14 (the count before that amendment), from the DSR inputs the primary stage stored in
results/primary_summary.json (sample length, skewness, excess kurtosis, dispersion of the trial Sharpes).
Only n_trials differs between the two. Uses src/stats.py::dsr_sharpe_threshold().

    python scripts/dsr_thresholds.py      # writes results/dsr_thresholds.json

Reads and writes only files under results/; no licensed data.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import config, stats

SUMMARY = REPO / "results" / "primary_summary.json"
OUT = REPO / "results" / "dsr_thresholds.json"


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    out = {"source": "results/primary_summary.json", "dsr_gate": config.DSR_GATE_MIN,
           "code_version": summary.get("code_version"), "arms": {}}
    for arm, a in summary["arms"].items():
        inputs = a.get("dsr_inputs")
        if not inputs:
            out["arms"][arm] = {"note": "arm closed at the premise gate; no DSR inputs"}
            continue
        at = {}
        for n in (16, 14):
            at[str(n)] = stats.dsr_sharpe_threshold(**{**inputs, "n_trials": n})
        assert abs(at["16"] - a["dsr_sharpe_threshold"]) < 1e-12 or inputs["n_trials"] != 16
        out["arms"][arm] = {"dsr_inputs": inputs, "sharpe_threshold_by_n_trials": at}
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
