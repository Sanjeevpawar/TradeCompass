from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from analysis.v2.option_chain_intelligence import build_historical_snapshots


def load_rows(path: str) -> list[dict]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser(description="Research-only historical near-ATM option-chain intelligence.")
    parser.add_argument("--options", default="data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv")
    parser.add_argument("--output", default="data/dhan_history/reconstructed/option_chain_intelligence_1y.json")
    args = parser.parse_args()

    rows = load_rows(args.options)
    snapshots = build_historical_snapshots(rows)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "status": "PASS",
        "purpose": "Independent near-ATM option-chain evidence layer; not integrated into trade decisions.",
        "rows": len(rows),
        "snapshots": len(snapshots),
        "identity_statuses": sorted({s["identity_status"] for s in snapshots}),
        "coverage_incomplete_snapshots": sum(1 for s in snapshots if not s["coverage_complete"]),
        "snapshots_data": snapshots,
        "research_limitations": [
            "Historical Dhan rolling data is near-ATM, not a full option chain.",
            "Expiry identity remains derived where supplied by reconstruction; it is not repaired here.",
            "PCR uses only the Call/Put common-strike intersection.",
            "OI change uses only the immediately preceding processed timestamp and the same fixed contract identity.",
            "Large OI is reported as concentration/potential positioning, not proof of option writers.",
            "No trading signal, score, BUY/PUT/CALL decision, or backtest result is produced by this layer.",
        ],
    }, indent=2), encoding="utf-8")

    print("Option-chain intelligence build: PASS")
    print(f"Rows: {len(rows)}")
    print(f"Snapshots: {len(snapshots)}")
    print(f"Coverage-incomplete snapshots: {sum(1 for s in snapshots if not s['coverage_complete'])}")
    print(f"Report: {args.output}")
    print("Trading decision integration: NOT ENABLED")


if __name__ == "__main__":
    main()
