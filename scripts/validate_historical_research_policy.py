from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from data.nse_calendar import NSE_FO_HOLIDAYS

DEFAULT_INPUT = Path("data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv")
DEFAULT_OUTPUT = Path("data/dhan_history/reconstructed/historical_research_policy_report.json")


def _bool(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def validate(path: Path, *, fail_on_holiday_expiry: bool = False) -> dict:
    required = {"timestamp", "expiry", "strike", "option_type", "open", "close"}
    rows = 0
    eligible_rows = 0
    identity = Counter()
    continuity = Counter()
    expiry_counts = Counter()
    holiday_expiry = Counter()
    negative_dte = 0
    invalid_dte = 0
    missing_identity = 0
    dtes: list[int] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        for row in reader:
            rows += 1
            status = str(
                row.get("contract_identity_status")
                or row.get("identity_status")
                or "DERIVED"
            ).upper()
            identity[status] += 1
            continuity[str(row.get("contract_continuity") or "UNKNOWN").upper()] += 1
            if _bool(row.get("reconstruction_eligible")):
                eligible_rows += 1

            expiry_text = str(row.get("expiry") or row.get("derived_expiry") or "").strip()
            timestamp = str(row.get("timestamp") or "").strip()
            if not expiry_text or not timestamp:
                invalid_dte += 1
                continue
            try:
                expiry = date.fromisoformat(expiry_text[:10])
                obs = _date(timestamp)
                dte = (expiry - obs).days
                dtes.append(dte)
                expiry_counts[expiry.isoformat()] += 1
                if dte < 0:
                    negative_dte += 1
                if expiry in NSE_FO_HOLIDAYS:
                    holiday_expiry[expiry.isoformat()] += 1
            except (TypeError, ValueError):
                invalid_dte += 1

            if status not in {"DERIVED"}:
                missing_identity += 1

    warnings: list[str] = []
    if holiday_expiry:
        warnings.append(
            "Existing reconstructed rows contain expiry dates that are NSE F&O holidays; "
            "this is a data-provenance warning and is not auto-corrected because Dhan rolling-option "
            "responses do not expose the historical expiry date directly."
        )
    if identity and set(identity) != {"DERIVED"}:
        warnings.append("Dataset contains identity statuses other than DERIVED.")
    if negative_dte:
        warnings.append("Negative DTE rows detected.")
    if invalid_dte:
        warnings.append("Rows with invalid/missing expiry or timestamp detected.")

    status = "PASS_WITH_WARNINGS" if warnings else "PASS"
    if fail_on_holiday_expiry and holiday_expiry:
        status = "BLOCKED"

    report = {
        "status": status,
        "input": str(path),
        "rows": rows,
        "reconstruction_eligible_rows": eligible_rows,
        "identity": dict(identity),
        "continuity": dict(continuity),
        "expiry_count": len(expiry_counts),
        "dte": {
            "min": min(dtes) if dtes else None,
            "max": max(dtes) if dtes else None,
            "negative_rows": negative_dte,
            "invalid_rows": invalid_dte,
        },
        "holiday_expiry_rows": dict(holiday_expiry),
        "research_policy": {
            "expiry_identity": "DERIVED",
            "broker_verified_expiry": False,
            "dte_is_research_attribute": True,
            "nse_calendar_applied_by_current_identity_code": True,
            "rolling_response_exposes_expiry_directly": False,
            "auto_repair_existing_dataset": False,
        },
        "warnings": warnings,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate historical option dataset research-integrity policy.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--fail-on-holiday-expiry", action="store_true")
    args = parser.parse_args()

    report = validate(Path(args.input), fail_on_holiday_expiry=args.fail_on_holiday_expiry)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Historical research-policy validation: {report['status']}")
    print(f"Rows: {report['rows']}")
    print(f"Reconstruction-eligible rows: {report['reconstruction_eligible_rows']}")
    print(f"Identity: {report['identity']}")
    print(f"Continuity: {report['continuity']}")
    print(f"DTE: {report['dte']}")
    print(f"Holiday expiry rows: {report['holiday_expiry_rows']}")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
