from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


@dataclass
class ValidationIssue:
    severity: str
    code: str
    message: str
    timestamp: str | None = None


@dataclass
class ValidationReport:
    status: str
    rows_call: int
    rows_put: int
    paired_timestamps: int
    expiry_values_call: list[str]
    expiry_values_put: list[str]
    issues: list[ValidationIssue]
    checks: dict[str, bool]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["issues"] = [asdict(i) for i in self.issues]
        return data


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _float(row: dict, key: str) -> float | None:
    value = row.get(key)
    if value in (None, "", "None"):
        return None
    return float(value)


def _date(row: dict, key: str) -> date | None:
    value = row.get(key)
    return date.fromisoformat(value) if value else None


def _group(rows: Iterable[dict]) -> dict[str, dict]:
    return {r["timestamp"]: r for r in rows}


def validate_pair(call_rows: list[dict], put_rows: list[dict]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    c = _group(call_rows)
    p = _group(put_rows)
    common = sorted(set(c) & set(p))

    if len(c) != len(common):
        for ts in sorted(set(c) - set(p)):
            issues.append(ValidationIssue("ERROR", "CALL_TIMESTAMP_UNPAIRED", "CALL timestamp has no matching PUT row", ts))
    if len(p) != len(common):
        for ts in sorted(set(p) - set(c)):
            issues.append(ValidationIssue("ERROR", "PUT_TIMESTAMP_UNPAIRED", "PUT timestamp has no matching CALL row", ts))

    for ts in common:
        cr, pr = c[ts], p[ts]
        for key in ("strike", "spot", "derived_expiry", "dte_days"):
            if cr.get(key) != pr.get(key):
                issues.append(ValidationIssue("ERROR", f"PAIR_{key.upper()}_MISMATCH", f"CALL/PUT {key} mismatch: {cr.get(key)} vs {pr.get(key)}", ts))
        cd, pd = _float(cr, "model_delta"), _float(pr, "model_delta")
        if cd is not None and not (0.0 <= cd <= 1.0):
            issues.append(ValidationIssue("ERROR", "CALL_DELTA_RANGE", f"CALL delta outside [0,1]: {cd}", ts))
        if pd is not None and not (-1.0 <= pd <= 0.0):
            issues.append(ValidationIssue("ERROR", "PUT_DELTA_RANGE", f"PUT delta outside [-1,0]: {pd}", ts))
        if cd is not None and pd is not None and abs((cd - pd) - 1.0) > 0.08:
            issues.append(ValidationIssue("ERROR", "DELTA_PARITY", f"CALL delta - PUT delta should be near 1; got {cd - pd:.4f}", ts))

    return issues


def validate_series(rows: list[dict], label: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    rows = sorted(rows, key=lambda r: r["timestamp_epoch"])
    previous_dte = None
    previous_ts = None
    for r in rows:
        ts = r["timestamp"]
        dte = int(r["dte_days"]) if r.get("dte_days") not in (None, "") else None
        delta = _float(r, "model_delta")
        spot = _float(r, "spot")
        strike = _float(r, "strike")
        if dte is None:
            issues.append(ValidationIssue("ERROR", f"{label}_MISSING_DTE", "Missing derived DTE", ts))
        if previous_dte is not None and dte is not None and dte > previous_dte:
            issues.append(ValidationIssue("ERROR", f"{label}_DTE_INCREASE", f"DTE increased from {previous_dte} to {dte}", ts))
        if delta is None:
            issues.append(ValidationIssue("ERROR", f"{label}_MISSING_DELTA", "Missing model delta", ts))
        if spot is not None and strike is not None and abs(spot - strike) < 0.03 * spot and delta is not None:
            # ATM delta should be reasonably close to +/-0.5. This is a warning,
            # not a hard failure because dividend/rate/model differences exist.
            target = 0.5 if label == "CALL" else -0.5
            if abs(delta - target) > 0.15:
                issues.append(ValidationIssue("WARN", "ATM_DELTA_DEVIATION", f"ATM-like row has delta {delta:.4f}, expected roughly {target:+.2f}", ts))
        if previous_ts is not None and int(r["timestamp_epoch"]) <= previous_ts:
            issues.append(ValidationIssue("ERROR", f"{label}_TIMESTAMP_ORDER", "Timestamps are not strictly increasing", ts))
        previous_ts = int(r["timestamp_epoch"])
        previous_dte = dte
    return issues


def validate_expiry_consistency(rows: list[dict], label: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    values = sorted({r.get("derived_expiry") for r in rows if r.get("derived_expiry")})
    if len(values) != 1:
        issues.append(ValidationIssue("ERROR", f"{label}_EXPIRY_NOT_CONSTANT", f"Expected one derived expiry for this short sample, found {values}"))
    return issues


def validate_underlying(rows: list[dict], option_rows: list[dict]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    underlying = _group(rows)
    for r in option_rows:
        ur = underlying.get(r["timestamp"])
        if not ur:
            issues.append(ValidationIssue("ERROR", "UNDERLYING_TIMESTAMP_MISSING", "Option timestamp missing from underlying sample", r["timestamp"]))
            continue
        os = _float(r, "spot")
        us = _float(ur, "close")
        if os is not None and us is not None and abs(os - us) > 2.0:
            issues.append(ValidationIssue("WARN", "SPOT_CLOSE_DIFFERENCE", f"Option spot {os} differs from underlying close {us} by > 2 points", r["timestamp"]))
    return issues


def validate_sample(call_path: str | Path, put_path: str | Path, underlying_path: str | Path) -> ValidationReport:
    call_rows = read_csv(call_path)
    put_rows = read_csv(put_path)
    underlying_rows = read_csv(underlying_path)
    issues = []
    issues.extend(validate_pair(call_rows, put_rows))
    issues.extend(validate_series(call_rows, "CALL"))
    issues.extend(validate_series(put_rows, "PUT"))
    issues.extend(validate_expiry_consistency(call_rows, "CALL"))
    issues.extend(validate_expiry_consistency(put_rows, "PUT"))
    issues.extend(validate_underlying(underlying_rows, call_rows))
    issues.extend(validate_underlying(underlying_rows, put_rows))

    call_ts = {r["timestamp"] for r in call_rows}
    put_ts = {r["timestamp"] for r in put_rows}
    paired = len(call_ts & put_ts)
    errors = [i for i in issues if i.severity == "ERROR"]
    checks = {
        "call_put_timestamp_pairing": not any(i.code.endswith("TIMESTAMP_UNPAIRED") for i in issues),
        "call_put_identity_match": not any(i.code.startswith("PAIR_") for i in issues),
        "delta_ranges": not any(i.code.endswith("DELTA_RANGE") for i in issues),
        "delta_parity": not any(i.code == "DELTA_PARITY" for i in issues),
        "dte_non_increasing": not any(i.code.endswith("DTE_INCREASE") for i in issues),
        "timestamp_order": not any(i.code.endswith("TIMESTAMP_ORDER") for i in issues),
        "expiry_consistency": not any(i.code.endswith("EXPIRY_NOT_CONSTANT") for i in issues),
        "underlying_alignment": not any(i.code == "UNDERLYING_TIMESTAMP_MISSING" for i in issues),
    }
    return ValidationReport(
        status="PASS" if not errors else "FAIL",
        rows_call=len(call_rows),
        rows_put=len(put_rows),
        paired_timestamps=paired,
        expiry_values_call=sorted({r.get("derived_expiry") for r in call_rows if r.get("derived_expiry")}),
        expiry_values_put=sorted({r.get("derived_expiry") for r in put_rows if r.get("derived_expiry")}),
        issues=issues,
        checks=checks,
    )


def write_report(report: ValidationReport, path: str | Path) -> None:
    Path(path).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
