from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_keys(path: Path, option: bool):
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ts = r.get("timestamp", "")
            if option:
                yield (ts, r.get("strike", ""), r.get("option_type", ""))
            else:
                yield (ts,)


def _date_from_ts(ts: str) -> str:
    """Return the exchange-local (IST) calendar date for ISO or Unix timestamps."""
    value = str(ts).strip()
    if not value:
        raise ValueError("empty timestamp")

    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt.astimezone(IST).date().isoformat()
    except ValueError:
        epoch = float(value)
        if epoch > 1_000_000_000_000:
            epoch /= 1000.0
        return datetime.fromtimestamp(epoch, tz=IST).date().isoformat()


def boundary_duplicates_detail(
    left: Path, right: Path, option: bool, expected_boundary_date: str
):
    left_keys = set(read_keys(left, option))
    unexpected = []
    expected = 0

    for k in read_keys(right, option):
        if k in left_keys:
            if _date_from_ts(k[0]) == expected_boundary_date:
                expected += 1
            else:
                unexpected.append(k)

    return expected, unexpected


def validate_raw_acquisition(root: str = "data/dhan_history/raw") -> dict[str, Any]:
    rootp = Path(root)
    manifest = load_manifest(rootp / "acquisition_manifest.json")
    chunks = manifest.get("chunks", {})

    underlying = sorted(
        [v for v in chunks.values() if v.get("type") == "underlying" and v.get("status") == "PASS"],
        key=lambda x: x["from_date"],
    )
    options = sorted(
        [v for v in chunks.values() if v.get("type") == "options" and v.get("status") == "PASS"],
        key=lambda x: x["from_date"],
    )

    errors = []
    boundary_checks = []

    for a, b in zip(underlying, underlying[1:]):
        pa, pb = Path(a["output"]), Path(b["output"])
        expected, unexpected = boundary_duplicates_detail(pa, pb, False, a["to_date"])
        boundary_checks.append({
            "type": "underlying",
            "left": a["output"],
            "right": b["output"],
            "expected_boundary_duplicates": expected,
            "unexpected_duplicates": len(unexpected),
        })
        if unexpected:
            errors.append(
                f"underlying unexpected boundary duplicates {len(unexpected)}: {a['to_date']}"
            )

    for a, b in zip(options, options[1:]):
        for side in ("call_output", "put_output"):
            pa, pb = Path(a[side]), Path(b[side])
            expected, unexpected = boundary_duplicates_detail(
                pa, pb, True, a["to_date"]
            )
            boundary_checks.append({
                "type": side,
                "left": a[side],
                "right": b[side],
                "expected_boundary_duplicates": expected,
                "unexpected_duplicates": len(unexpected),
            })
            if unexpected:
                errors.append(
                    f"{side} unexpected boundary duplicates {len(unexpected)}: {a['to_date']}"
                )

    return {
        "status": "PASS" if not errors else "FAIL",
        "manifest_last_run": manifest.get("last_run", {}),
        "passed_chunks": sum(v.get("status") == "PASS" for v in chunks.values()),
        "failed_chunks": sum(v.get("status") == "FAIL" for v in chunks.values()),
        "underlying_chunks_verified": len(underlying),
        "option_chunks_verified": len(options),
        "boundary_checks": boundary_checks,
        "errors": errors,
        "policy": {
            "timestamp_timezone": "Asia/Kolkata",
            "boundary_duplicates": "duplicates on the intentional shared boundary date are allowed; duplicates outside that date are errors",
            "raw_data": "unchanged; validator only checks files",
            "forward_fill": "never",
        },
    }


if __name__ == "__main__":
    root = "data/dhan_history/raw"
    result = validate_raw_acquisition(root)
    out = Path(root) / "raw_acquisition_validation_report.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    expected = sum(x["expected_boundary_duplicates"] for x in result["boundary_checks"])
    unexpected = sum(x["unexpected_duplicates"] for x in result["boundary_checks"])

    print(f"Raw acquisition validation: {result['status']}")
    print(f"Underlying chunks verified: {result['underlying_chunks_verified']}")
    print(f"Option chunks verified: {result['option_chunks_verified']}")
    print(f"Boundary checks: {len(result['boundary_checks'])}")
    print(f"Expected boundary overlap rows: {expected}")
    print(f"Unexpected boundary duplicates: {unexpected}")
    print(f"Report: {out}")

    for e in result["errors"]:
        print("ERROR:", e)
