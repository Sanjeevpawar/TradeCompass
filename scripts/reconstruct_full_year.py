from __future__ import annotations

import argparse
from data.full_year_reconstruction import run_full_year


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the 1-year fixed-contract research dataset from validated Dhan raw chunks.")
    parser.add_argument("--raw-root", default="data/dhan_history/raw")
    parser.add_argument("--output-dir", default="data/dhan_history/reconstructed")
    args = parser.parse_args()
    report = run_full_year(args.raw_root, args.output_dir)
    print(f"Full-year reconstruction: {report['status']}")
    print(f"Option rows after boundary dedupe: {report['input']['rows_received']}")
    print(f"Fixed-contract rows written: {report['input']['rows_normalized']}")
    print(f"Contracts: {report['contracts']['count']}")
    print(f"Continuity: {report['contracts']['continuity']}")
    print(f"Identity: {report['contracts']['identity']}")
    print(f"Reconstruction eligible: {report['contracts']['reconstruction_eligible']}")
    print(f"Conflicting duplicates: {len(report['ingest']['option_dedupe']['conflicting_duplicates']) + len(report['ingest']['underlying_conflicting_duplicates'])}")
    print(f"Report: {report['outputs']['report']}")


if __name__ == "__main__":
    main()
