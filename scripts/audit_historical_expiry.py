from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

from data.contract_identity import _expiry_dates_for_range
from data.nse_calendar import NSE_FO_HOLIDAYS

EXPIRY_CUTOFF = time(15, 30)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def future_expiries(ts: datetime, *, count: int = 3) -> list[date]:
    d = ts.date()
    dates = _expiry_dates_for_range(
        d - timedelta(days=14),
        d + timedelta(days=60),
        "WEEK",
        NSE_FO_HOLIDAYS,
    )
    return [
        x for x in dates
        if x > d or (x == d and ts.time() < EXPIRY_CUTOFF)
    ][:count]


def audit(path: str | Path) -> dict:
    path = Path(path)
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for the expiry audit") from exc

    usecols = ["timestamp", "derived_expiry", "expiry_code", "expiry_flag"]
    df = pd.read_csv(path, usecols=usecols)
    rows = len(df)
    parsed_ts = pd.to_datetime(df["timestamp"], errors="coerce")
    parsed_expiry = pd.to_datetime(df["derived_expiry"], errors="coerce")
    codes = pd.to_numeric(df["expiry_code"], errors="coerce")
    invalid_mask = parsed_ts.isna() | parsed_expiry.isna() | codes.isna()
    invalid_rows = int(invalid_mask.sum())

    valid = df.loc[~invalid_mask, ["timestamp", "derived_expiry", "expiry_code"]].copy()
    valid["ts"] = parsed_ts.loc[~invalid_mask]
    valid["expiry"] = parsed_expiry.loc[~invalid_mask].dt.date
    valid["code"] = codes.loc[~invalid_mask].astype(int)
    valid["dte"] = (valid["expiry"] - valid["ts"].dt.date).map(lambda x: x.days)

    expiry_code_counts = {str(int(k)): int(v) for k, v in valid["code"].value_counts().sort_index().items()}
    expiry_counts = valid["expiry"].value_counts()
    weekday_counts = Counter(x.strftime("%A") for x in valid["expiry"])
    holiday_counts = Counter(x.isoformat() for x in valid["expiry"] if x in NSE_FO_HOLIDAYS)
    weekend_counts = Counter(x.isoformat() for x in valid["expiry"] if x.weekday() >= 5)
    dte_counts = Counter(int(x) for x in valid["dte"])

    # Only evaluate unique timestamp/code/expiry combinations. The raw dataset
    # repeats the same identity across many strikes and option types.
    combos = valid[["timestamp", "ts", "expiry", "code"]].drop_duplicates()
    mismatches = []
    code1_classification = Counter()
    for row in combos.itertuples(index=False):
        candidates = future_expiries(row.ts)
        if not candidates:
            mismatches.append({
                "timestamp": row.timestamp,
                "expiry_code": int(row.code),
                "derived_expiry": row.expiry.isoformat(),
                "reason": "no_calendar_expiry_candidate",
            })
            continue
        expected = candidates[int(row.code)] if int(row.code) < len(candidates) else None
        if expected is not None and row.expiry != expected:
            mismatches.append({
                "timestamp": row.timestamp,
                "expiry_code": int(row.code),
                "derived_expiry": row.expiry.isoformat(),
                "expected_by_calendar_ordinal": expected.isoformat(),
                "calendar_candidates": [x.isoformat() for x in candidates],
            })
        if int(row.code) == 1 and len(candidates) >= 2:
            if row.expiry == candidates[0]:
                code1_classification["stored_as_current_near"] += 1
            elif row.expiry == candidates[1]:
                code1_classification["stored_as_next"] += 1
            else:
                code1_classification["stored_as_other"] += 1

    ordered = (
        valid[["expiry", "timestamp"]]
        .drop_duplicates("expiry")
        .sort_values("timestamp")
    )
    transitions = []
    previous = None
    for row in ordered.itertuples(index=False):
        transitions.append({
            "first_seen": row.timestamp,
            "expiry": row.expiry.isoformat(),
            "previous_expiry": previous,
        })
        previous = row.expiry.isoformat()
        if len(transitions) >= 12:
            break

    return {
        "status": "PASS" if invalid_rows == 0 else "FAIL",
        "input": {"path": str(path), "rows": rows, "invalid_rows": invalid_rows},
        "expiry_code_counts": expiry_code_counts,
        "unique_expiries": int(valid["expiry"].nunique()),
        "expiry_weekdays": dict(weekday_counts),
        "holiday_expiry_rows": dict(holiday_counts),
        "weekend_expiry_rows": dict(weekend_counts),
        "dte": {
            "min": int(valid["dte"].min()) if len(valid) else None,
            "max": int(valid["dte"].max()) if len(valid) else None,
            "negative_rows": sum(v for k, v in dte_counts.items() if k < 0),
            "zero_rows": dte_counts.get(0, 0),
            "one_to_fourteen_rows": sum(v for k, v in dte_counts.items() if 1 <= k <= 14),
            "over_fourteen_rows": sum(v for k, v in dte_counts.items() if k > 14),
        },
        "documented_expiry_code_check": {
            "source": "DhanHQ Annexure: 0=Current/Near, 1=Next, 2=Far",
            "unique_timestamp_identity_combinations_checked": len(combos),
            "mismatch_rows": len(mismatches),
            "sample_mismatches": mismatches[:20],
            "code1_classification": dict(code1_classification),
        },
        "expiry_transitions_sample": transitions,
        "research_note": (
            "Read-only audit. It does not rewrite expiry identity. Dhan's rolling historical endpoint "
            "does not return historical expiry directly, so any documented expiry-code mismatch must be "
            "investigated before rebuilding the research dataset."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit historical NIFTY expiry/DTE identity without modifying data.")
    parser.add_argument(
        "--input",
        default="data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv",
    )
    parser.add_argument(
        "--report",
        default="data/dhan_history/reconstructed/historical_expiry_audit_report.json",
    )
    args = parser.parse_args()

    report = audit(args.input)
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Historical expiry audit: {report['status']}")
    print(f"Rows: {report['input']['rows']}")
    print(f"Unique expiries: {report['unique_expiries']}")
    print(f"Expiry codes: {report['expiry_code_counts']}")
    print(f"Expiry weekdays: {report['expiry_weekdays']}")
    print(f"Holiday expiry rows: {report['holiday_expiry_rows']}")
    print(f"Weekend expiry rows: {report['weekend_expiry_rows']}")
    print(f"DTE range: {report['dte']['min']} to {report['dte']['max']}")
    print(f"Negative DTE rows: {report['dte']['negative_rows']}")
    print(f"Dhan documented expiry-code mismatches: {report['documented_expiry_code_check']['mismatch_rows']}")
    print(f"Code-1 classification: {report['documented_expiry_code_check']['code1_classification']}")
    print(f"Report: {out}")


if __name__ == "__main__":
    main()
