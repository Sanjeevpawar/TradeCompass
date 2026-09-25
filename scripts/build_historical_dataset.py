from __future__ import annotations

import argparse

from data.historical_dataset_builder import build_from_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the TradeCompass historical research dataset from validated Dhan samples.")
    parser.add_argument("--call", default="data/dhan_samples/nifty_options_call_enriched.csv")
    parser.add_argument("--put", default="data/dhan_samples/nifty_options_put_enriched.csv")
    parser.add_argument("--underlying", default="data/dhan_samples/nifty_underlying.csv")
    parser.add_argument("--output", default="data/dhan_samples/nifty_historical_research_dataset.csv")
    parser.add_argument("--report", default="data/dhan_samples/historical_dataset_report.json")
    args = parser.parse_args()

    report = build_from_csv(args.call, args.put, args.underlying, args.output, args.report)
    print("Historical dataset build: PASS")
    print(f"CALL rows: {report['rows']['call']}")
    print(f"PUT rows: {report['rows']['put']}")
    print(f"Combined rows: {report['rows']['combined']}")
    print(f"Eligible rows: {report['rows']['eligible']}")
    print(f"Excluded rows: {report['rows']['excluded']}")
    print(f"Identity: {report['identity']}")
    print(f"Output: {args.output}")
    print(f"Report: {args.report}")
    print("Backtest gate: BLOCKED (intentional)")


if __name__ == "__main__":
    main()
