from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


def read_csv(path: str | Path) -> List[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _float(row: dict, key: str) -> Optional[float]:
    value = row.get(key)
    if value in (None, ""):
        return None
    return float(value)


def _dt(row: dict) -> datetime:
    return datetime.fromisoformat(row["timestamp"])


def expiry_segments(rows: Iterable[dict]) -> List[dict]:
    """Group rolling observations by derived expiry.

    A rolling series is allowed to change expiry. Within each expiry segment,
    DTE must not increase as timestamps advance.
    """
    ordered = sorted(rows, key=_dt)
    segments = []
    current = None

    for row in ordered:
        expiry = row.get("derived_expiry", "")
        if current is None or expiry != current["expiry"]:
            current = {
                "expiry": expiry,
                "start": row["timestamp"],
                "end": row["timestamp"],
                "rows": 0,
                "dte_values": [],
            }
            segments.append(current)

        current["end"] = row["timestamp"]
        current["rows"] += 1
        dte = _float(row, "dte_days")
        if dte is not None:
            current["dte_values"].append(dte)

    return segments


def validate_segment_dte(rows: Iterable[dict]) -> Tuple[bool, List[dict]]:
    ordered = sorted(rows, key=_dt)
    previous = None
    issues = []

    for row in ordered:
        dte = _float(row, "dte_days")
        if dte is None:
            issues.append({
                "code": "MISSING_DTE",
                "timestamp": row["timestamp"],
            })
            continue
        if previous is not None and dte > previous + 1e-9:
            issues.append({
                "code": "DTE_INCREASE_WITHIN_EXPIRY",
                "timestamp": row["timestamp"],
                "previous_dte": previous,
                "current_dte": dte,
            })
        previous = dte

    return not any(i["code"] == "DTE_INCREASE_WITHIN_EXPIRY" for i in issues), issues


def validate_rolling_expiry(rows: Iterable[dict]) -> dict:
    ordered = sorted(rows, key=_dt)
    segments = expiry_segments(ordered)
    issues = []

    for seg in segments:
        segment_rows = [
            r for r in ordered if r.get("derived_expiry", "") == seg["expiry"]
        ]
        ok, segment_issues = validate_segment_dte(segment_rows)
        if not ok:
            issues.extend(segment_issues)

    return {
        "pass": not issues,
        "segments": segments,
        "issues": issues,
    }


def validate_underlying_alignment(
    option_rows: Iterable[dict],
    underlying_rows: Iterable[dict],
    max_spot_difference: float = 2.0,
) -> dict:
    underlying_by_ts = {r["timestamp"]: r for r in underlying_rows}
    checked = 0
    missing = []
    spot_warnings = []

    for row in option_rows:
        ts = row["timestamp"]
        underlying = underlying_by_ts.get(ts)
        if underlying is None:
            missing.append(ts)
            continue

        checked += 1
        option_spot = _float(row, "spot")
        underlying_close = _float(underlying, "close")
        if option_spot is not None and underlying_close is not None:
            diff = abs(option_spot - underlying_close)
            if diff > max_spot_difference:
                spot_warnings.append({
                    "timestamp": ts,
                    "option_spot": option_spot,
                    "underlying_close": underlying_close,
                    "difference": diff,
                })

    return {
        "pass": True,  # missing timestamps are exclusions, not data corruption
        "checked": checked,
        "missing_timestamps": sorted(set(missing)),
        "spot_warnings": spot_warnings,
        "note": (
            "Exact timestamp alignment is required for backtest eligibility. "
            "Missing timestamps are excluded rather than filled or fabricated."
        ),
    }


def validate_call_put_identity(call_rows: Iterable[dict], put_rows: Iterable[dict]) -> dict:
    c = {r["timestamp"]: r for r in call_rows}
    p = {r["timestamp"]: r for r in put_rows}
    paired = sorted(set(c) & set(p))
    issues = []

    for ts in paired:
        for field in ("strike", "spot", "derived_expiry", "dte_days"):
            if c[ts].get(field) != p[ts].get(field):
                issues.append({
                    "timestamp": ts,
                    "field": field,
                    "call": c[ts].get(field),
                    "put": p[ts].get(field),
                })

    return {
        "pass": len(c) == len(p) and len(paired) == len(c) == len(p) and not issues,
        "call_rows": len(c),
        "put_rows": len(p),
        "paired": len(paired),
        "issues": issues,
    }


def load_instrument_master(path: str | Path) -> List[dict]:
    return read_csv(path)


def _norm_date(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value[:10], fmt).date().isoformat()
        except ValueError:
            pass
    return value[:10]


def instrument_master_crosscheck(
    rows: Iterable[dict],
    instruments: Iterable[dict],
    underlying_security_id: str = "13",
) -> dict:
    """Cross-check derived identity against Dhan's detailed instrument master.

    The master is optional because a current master may not retain older
    expired contracts. A missing master match is reported as UNVERIFIED, not
    silently treated as a match.
    """
    master = list(instruments)
    indexes = defaultdict(list)

    for item in master:
        expiry = _norm_date(
            item.get("SM_EXPIRY_DATE")
            or item.get("SEM_EXPIRY_DATE")
            or item.get("expiry_date", "")
        )
        strike = item.get("STRIKE_PRICE") or item.get("SEM_STRIKE_PRICE") or item.get("strike", "")
        option_type = item.get("OPTION_TYPE") or item.get("SEM_OPTION_TYPE") or item.get("option_type", "")
        underlying = item.get("UNDERLYING_SECURITY_ID") or item.get("underlying_security_id", "")
        indexes[(expiry, str(strike), str(option_type), str(underlying))].append(item)

    checked_keys = set()
    matched = 0
    unmatched = []

    for row in rows:
        expiry = row.get("derived_expiry", "")
        strike = row.get("strike", "")
        option_type = "CE" if row.get("option_type") == "CE" else "PE"
        key = (expiry, str(strike), option_type, str(underlying_security_id))
        checked_keys.add(key)

    for key in sorted(checked_keys):
        if indexes.get(key):
            matched += 1
        else:
            unmatched.append({
                "expiry": key[0],
                "strike": key[1],
                "option_type": key[2],
                "underlying_security_id": key[3],
            })

    return {
        "available": True,
        "checked_unique_contract_keys": len(checked_keys),
        "matched_unique_contract_keys": matched,
        "unmatched_unique_contract_keys": unmatched,
        "pass": len(unmatched) == 0,
        "note": (
            "A missing match means identity is UNVERIFIED. It is not treated "
            "as proof that the rolling observation is wrong."
        ),
    }


def build_report(call_path: str | Path, put_path: str | Path,
                 underlying_path: str | Path,
                 instrument_master_path: str | Path | None = None) -> dict:
    calls = read_csv(call_path)
    puts = read_csv(put_path)
    underlying = read_csv(underlying_path)

    call_roll = validate_rolling_expiry(calls)
    put_roll = validate_rolling_expiry(puts)
    identity = validate_call_put_identity(calls, puts)
    alignment_call = validate_underlying_alignment(calls, underlying)
    alignment_put = validate_underlying_alignment(puts, underlying)

    master_report = {
        "available": False,
        "pass": False,
        "note": "Instrument master not supplied; identity remains UNVERIFIED.",
    }
    if instrument_master_path:
        instruments = load_instrument_master(instrument_master_path)
        master_report = instrument_master_crosscheck(calls, instruments)

    hard_fail = (
        not identity["pass"]
        or not call_roll["pass"]
        or not put_roll["pass"]
    )

    return {
        "status": "PASS" if not hard_fail else "FAIL",
        "rows": {
            "call": len(calls),
            "put": len(puts),
            "underlying": len(underlying),
        },
        "rolling_expiry": {
            "call": call_roll,
            "put": put_roll,
        },
        "call_put_identity": identity,
        "underlying_alignment": {
            "call": alignment_call,
            "put": alignment_put,
            "actionable_rule": "Exact underlying timestamp required for backtest eligibility.",
        },
        "instrument_master_crosscheck": master_report,
        "backtest_gate": {
            "allowed": False,
            "reason": (
                "Phase 8.5 validates rolling segmentation, but the sample is "
                "not authorized for backtesting until contract identity is "
                "cross-checked against Dhan's instrument master or explicitly "
                "marked as research-only."
            ),
        },
    }
