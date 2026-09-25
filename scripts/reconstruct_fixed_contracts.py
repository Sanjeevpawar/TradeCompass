from __future__ import annotations

import argparse
from pathlib import Path

from data.fixed_contract_reconstruction import reconstruct_from_csv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconstruct fixed expiry+strike+option-type series from Dhan rolling data."
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="CSV input; repeat for CALL/PUT or multiple rolling strike captures.",
    )
    parser.add_argument(
        "--output",
        default="data/dhan_samples/nifty_fixed_contracts.csv",
    )
    parser.add_argument(
        "--report",
        default="data/dhan_samples/fixed_contract_reconstruction_report.json",
    )
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()

    report = reconstruct_from_csv(args.input, args.output, args.report, args.interval)
    print("Fixed-contract reconstruction: PASS")
    print(f"Input rows: {report['input']['rows_received']}")
    print(f"Normalized rows: {report['input']['rows_normalized']}")
    print(f"Contracts: {report['contracts']['count']}")
    print(f"Continuity: {report['contracts']['continuity']}")
    print(f"Reconstruction-eligible contracts: {report['contracts']['reconstruction_eligible']}")
    print(f"Output: {Path(args.output)}")
    print(f"Report: {Path(args.report)}")
    print("Backtest gate: BLOCKED (Phase 9A only reconstructs and validates contract series)")


if __name__ == "__main__":
    main()
