from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import json

DEFAULT_OPTIONS = "data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv"
DEFAULT_REPORT = "data/dhan_history/reconstructed/option_chain_history_validation_report.json"


def _read_csv(path: str):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _first(row, *names):
    for name in names:
        if name in row and row[name] not in ("", None):
            return row[name]
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Inspect exceptional timestamps in the historical option-chain dataset."
    )
    parser.add_argument("--options", default=DEFAULT_OPTIONS)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--max-timestamps", type=int, default=20)
    args = parser.parse_args()

    # Read the report so the diagnostic remains tied to the validated dataset.
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    rows = _read_csv(args.options)

    by_ts = defaultdict(lambda: {"CE": defaultdict(list), "PE": defaultdict(list)})

    for row in rows:
        ts = _first(row, "timestamp", "datetime", "time")
        opt = (_first(row, "option_type", "type", "optionType") or "").upper()
        strike_raw = _first(row, "strike", "strike_price", "strikePrice")
        expiry = _first(row, "expiry", "expiry_date")

        if ts is None or opt not in ("CE", "PE") or strike_raw is None:
            continue

        try:
            strike = float(strike_raw)
        except ValueError:
            continue

        by_ts[str(ts)][opt][(expiry, strike)].append(row)

    exceptional = []
    for ts, sides in by_ts.items():
        ce_keys = set(sides["CE"])
        pe_keys = set(sides["PE"])
        if ce_keys != pe_keys:
            exceptional.append((ts, sides["CE"], sides["PE"]))

    exceptional.sort(key=lambda x: x[0])

    print("Option-chain exceptional timestamp inspection")
    print(f"Dataset: {args.options}")
    print(f"Exceptional timestamps found: {len(exceptional)}")
    print()

    for ts, ce, pe in exceptional[:args.max_timestamps]:
        ce_keys = set(ce)
        pe_keys = set(pe)

        print(f"TIMESTAMP: {ts}")
        print(f"  CE contracts: {len(ce_keys)}")
        print(f"  PE contracts: {len(pe_keys)}")

        only_ce = sorted(ce_keys - pe_keys, key=lambda x: (str(x[0]), x[1]))
        only_pe = sorted(pe_keys - ce_keys, key=lambda x: (str(x[0]), x[1]))

        if only_ce:
            print(f"  CE-only contracts: {only_ce}")
        if only_pe:
            print(f"  PE-only contracts: {only_pe}")

        common = sorted(ce_keys & pe_keys, key=lambda x: (str(x[0]), x[1]))
        print("  Common contracts:")
        for expiry, strike in common:
            ce_rows = ce.get((expiry, strike), [])
            pe_rows = pe.get((expiry, strike), [])

            # Defensive check: never manufacture a row merely to print diagnostics.
            if not ce_rows or not pe_rows:
                print(f"    {expiry} {strike:g}: missing side row (diagnostic only)")
                continue

            ce_row = ce_rows[0]
            pe_row = pe_rows[0]

            ce_oi = _first(ce_row, "oi", "open_interest", "openInterest")
            pe_oi = _first(pe_row, "oi", "open_interest", "openInterest")
            ce_vol = _first(ce_row, "volume")
            pe_vol = _first(pe_row, "volume")

            print(
                f"    {expiry} {strike:g}: "
                f"CE OI={ce_oi} Vol={ce_vol}; "
                f"PE OI={pe_oi} Vol={pe_vol}"
            )
        print()

    if len(exceptional) > args.max_timestamps:
        print(f"... {len(exceptional) - args.max_timestamps} additional timestamps omitted.")

    print(
        "Integrity report status:",
        report.get("status", "UNKNOWN"),
    )
    print("No trading rules or datasets were modified.")


if __name__ == "__main__":
    main()
