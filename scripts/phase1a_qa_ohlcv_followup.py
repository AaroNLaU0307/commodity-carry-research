"""Follow-up check: do zero/negative-close rows correlate with zero volume
(benign "listed but untraded that day" placeholder) or not (a real data
concern)? Integrity check only, per Hard Rule 1."""
import json
from datetime import datetime, timezone
from pathlib import Path

import databento as db

DATA_DIR = Path(r"C:\Users\Aaron\quant-data\commodity-carry")
WORKSPACE = Path(r"C:\Users\Aaron\OneDrive\Desktop\Quant trade\_carry-research-workspace")
OUT_PATH = WORKSPACE / "phase1a_qa_ohlcv_followup_findings.json"


def main():
    store = db.DBNStore.from_file(DATA_DIR / "ohlcv-1d.dbn.zst")
    df = store.to_df()

    zero_close = df[df["close"] <= 0]
    zero_close_and_zero_volume = zero_close[zero_close["volume"] == 0]
    zero_close_nonzero_volume = zero_close[zero_close["volume"] != 0]

    nonzero_close = df[df["close"] > 0]
    nonzero_close_zero_volume = nonzero_close[nonzero_close["volume"] == 0]

    findings = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(df),
        "zero_or_negative_close_total": len(zero_close),
        "zero_close_AND_zero_volume": len(zero_close_and_zero_volume),
        "zero_close_but_NONZERO_volume": len(zero_close_nonzero_volume),
        "nonzero_close_but_zero_volume": len(nonzero_close_zero_volume),
        "negative_close_count": int((df["close"] < 0).sum()),
    }
    if len(zero_close_nonzero_volume) > 0:
        sample = zero_close_nonzero_volume.head(10)[["symbol", "open", "high", "low", "close", "volume"]]
        findings["zero_close_nonzero_volume_sample"] = sample.reset_index().astype(str).to_dict(orient="records")

    OUT_PATH.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    print(json.dumps(findings, indent=2, default=str))


if __name__ == "__main__":
    main()
