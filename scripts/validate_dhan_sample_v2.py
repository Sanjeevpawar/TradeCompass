from __future__ import annotations

import argparse
import json
from pathlib import Path

from data.rolling_contract_validation import build_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Dhan rolling option sample.")
    parser.add_argument("--call", default="data/dhan_samples/nifty_options_call_enriched.csv")
    parser.add_argument("--put", default="data/dhan_samples/nifty_options_put_enriched.csv")
    parser.add_argument("--underlying", default="data/dhan_samples/nifty_underlying.csv")
    parser.add_argument("--instrument-master", default=None)
    parser.add_argument("--output", default="data/dhan_samples/validation_report_v2.json")
    args = parser.parse_args()

    report = build_report(
        args.call, args.put, args.underlying, args.instrument_master
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Validation status: {report['status']}")
    print(f"CALL rows: {report['rows']['call']}")
    print(f"PUT rows: {report['rows']['put']}")
    print(f"Underlying rows: {report['rows']['underlying']}")

    print("CALL expiry segments:")
    for s in report["rolling_expiry"]["call"]["segments"]:
        print(f"  {s['expiry']}: {s['start']} -> {s['end']} ({s['rows']} rows)")

    print("PUT expiry segments:")
    for s in report["rolling_expiry"]["put"]["segments"]:
        print(f"  {s['expiry']}: {s['start']} -> {s['end']} ({s['rows']} rows)")

    print(
        "Underlying missing timestamps:",
        len(report["underlying_alignment"]["call"]["missing_timestamps"]),
    )
    print(
        "Instrument master:",
        "MATCHED" if report["instrument_master_crosscheck"]["available"]
        and report["instrument_master_crosscheck"]["pass"]
        else "NOT VERIFIED",
    )
    print(f"Report: {out}")


if __name__ == "__main__":
    main()
