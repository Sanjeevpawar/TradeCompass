from __future__ import annotations

import argparse
from pathlib import Path

from data.sample_validation import validate_sample, write_report


def main() -> None:
    p = argparse.ArgumentParser(description="Validate enriched Dhan CALL/PUT sample before backtesting.")
    p.add_argument("--call", default="data/dhan_samples/nifty_options_call_enriched.csv")
    p.add_argument("--put", default="data/dhan_samples/nifty_options_put_enriched.csv")
    p.add_argument("--underlying", default="data/dhan_samples/nifty_underlying.csv")
    p.add_argument("--report", default="data/dhan_samples/validation_report.json")
    args = p.parse_args()
    report = validate_sample(args.call, args.put, args.underlying)
    write_report(report, args.report)
    print(f"Validation status: {report.status}")
    print(f"CALL rows: {report.rows_call}")
    print(f"PUT rows: {report.rows_put}")
    print(f"Paired timestamps: {report.paired_timestamps}")
    print(f"CALL derived expiry: {report.expiry_values_call}")
    print(f"PUT derived expiry: {report.expiry_values_put}")
    print("Checks:")
    for name, ok in report.checks.items():
        print(f"  {'PASS' if ok else 'FAIL'} - {name}")
    warnings = [i for i in report.issues if i.severity == "WARN"]
    errors = [i for i in report.issues if i.severity == "ERROR"]
    print(f"Warnings: {len(warnings)}")
    print(f"Errors: {len(errors)}")
    print(f"Report: {Path(args.report)}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
