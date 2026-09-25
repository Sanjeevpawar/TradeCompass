from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


REQUIRED_OPTION_COLUMNS = {
    "timestamp", "option_type", "open", "high", "low", "close",
    "strike", "spot", "derived_expiry", "dte_days", "model_delta",
    "identity_method", "identity_confidence",
}
REQUIRED_UNDERLYING_COLUMNS = {"timestamp", "open", "high", "low", "close"}

OUTPUT_FIELDS = [
    "timestamp",
    "timestamp_epoch",
    "underlying_open",
    "underlying_high",
    "underlying_low",
    "underlying_close",
    "underlying_volume",
    "option_type",
    "strike",
    "derived_expiry",
    "dte_days",
    "time_to_expiry_years",
    "model_delta",
    "delta_source",
    "option_open",
    "option_high",
    "option_low",
    "option_close",
    "iv",
    "option_volume",
    "oi",
    "option_spot",
    "expiry_flag",
    "expiry_code",
    "strike_mode",
    "identity_status",
    "identity_method",
    "identity_confidence",
    "identity_note",
    "timestamp_alignment",
    "backtest_eligible",
    "eligibility_reason",
]


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _identity_status(row: dict[str, str]) -> str:
    confidence = (row.get("identity_confidence") or "").upper()
    method = (row.get("identity_method") or "").lower()
    if confidence == "BROKER_VERIFIED" or "broker" in method:
        return "BROKER_VERIFIED"
    if row.get("derived_expiry") and confidence in {"HIGH", "MEDIUM"}:
        return "DERIVED"
    return "UNVERIFIED"


def _required_value_reasons(row: dict[str, str]) -> list[str]:
    reasons: list[str] = []
    for field in ("option_type", "derived_expiry"):
        if not row.get(field):
            reasons.append(f"missing_{field}")
    for field in ("open", "high", "low", "close", "strike", "spot"):
        if _float(row.get(field)) is None:
            reasons.append(f"invalid_{field}")
    if _float(row.get("dte_days")) is None:
        reasons.append("missing_dte")
    elif _float(row.get("dte_days")) < 0:
        reasons.append("negative_dte")
    if _float(row.get("model_delta")) is None:
        reasons.append("missing_model_delta")
    return reasons


def _build_row(option: dict[str, str], underlying: dict[str, str] | None) -> dict[str, object]:
    reasons: list[str] = []
    identity_status = _identity_status(option)
    if underlying is None:
        reasons.append("missing_exact_underlying_timestamp")
    reasons.extend(_required_value_reasons(option))
    if identity_status == "UNVERIFIED":
        reasons.append("unverified_contract_identity")

    eligible = not reasons
    return {
        "timestamp": option.get("timestamp", ""),
        "timestamp_epoch": _int(option.get("timestamp_epoch")),
        "underlying_open": _float((underlying or {}).get("open")),
        "underlying_high": _float((underlying or {}).get("high")),
        "underlying_low": _float((underlying or {}).get("low")),
        "underlying_close": _float((underlying or {}).get("close")),
        "underlying_volume": _float((underlying or {}).get("volume")),
        "option_type": option.get("option_type", ""),
        "strike": _float(option.get("strike")),
        "derived_expiry": option.get("derived_expiry", ""),
        "dte_days": _float(option.get("dte_days")),
        "time_to_expiry_years": _float(option.get("time_to_expiry_years")),
        "model_delta": _float(option.get("model_delta")),
        "delta_source": option.get("delta_source", ""),
        "option_open": _float(option.get("open")),
        "option_high": _float(option.get("high")),
        "option_low": _float(option.get("low")),
        "option_close": _float(option.get("close")),
        "iv": _float(option.get("iv")),
        "option_volume": _float(option.get("volume")),
        "oi": _float(option.get("oi")),
        "option_spot": _float(option.get("spot")),
        "expiry_flag": option.get("expiry_flag", ""),
        "expiry_code": _int(option.get("expiry_code")),
        "strike_mode": option.get("strike_mode", ""),
        "identity_status": identity_status,
        "identity_method": option.get("identity_method", ""),
        "identity_confidence": option.get("identity_confidence", ""),
        "identity_note": option.get("identity_note", ""),
        "timestamp_alignment": "EXACT" if underlying is not None else "MISSING",
        "backtest_eligible": eligible,
        "eligibility_reason": "eligible" if eligible else ";".join(reasons),
    }


def build_dataset(
    call_rows: Iterable[dict[str, str]],
    put_rows: Iterable[dict[str, str]],
    underlying_rows: Iterable[dict[str, str]],
) -> tuple[list[dict[str, object]], dict]:
    calls = list(call_rows)
    puts = list(put_rows)
    underlying = {r.get("timestamp", ""): r for r in underlying_rows if r.get("timestamp")}

    all_options = [("CALL", r) for r in calls] + [("PUT", r) for r in puts]
    all_options.sort(key=lambda x: x[1].get("timestamp", ""))

    output: list[dict[str, object]] = []
    for expected_type, row in all_options:
        normalized = dict(row)
        if not normalized.get("option_type"):
            normalized["option_type"] = "CE" if expected_type == "CALL" else "PE"
        output.append(_build_row(normalized, underlying.get(normalized.get("timestamp", ""))))

    output.sort(key=lambda r: (str(r["timestamp"]), str(r["option_type"])))
    eligible = sum(1 for r in output if r["backtest_eligible"])
    reason_counts = Counter(
        reason
        for r in output
        if not r["backtest_eligible"]
        for reason in str(r["eligibility_reason"]).split(";")
        if reason
    )
    report = {
        "status": "PASS",
        "rows": {
            "call": len(calls),
            "put": len(puts),
            "underlying": len(underlying),
            "combined": len(output),
            "eligible": eligible,
            "excluded": len(output) - eligible,
        },
        "identity": dict(Counter(str(r["identity_status"]) for r in output)),
        "option_types": dict(Counter(str(r["option_type"]) for r in output)),
        "expiry_segments": dict(Counter(str(r["derived_expiry"]) for r in output)),
        "exclusion_reasons": dict(reason_counts),
        "data_policy": {
            "timestamp_join": "exact",
            "missing_underlying": "exclude",
            "missing_values": "exclude",
            "contract_identity": "derived identity is retained and explicitly labelled",
            "lookahead": "builder only joins fields available at the same timestamp; no future fill",
        },
        "backtest_gate": {
            "allowed": False,
            "reason": "Phase 8.6 builds a clean research dataset. Production historical backtesting remains gated until contract identity policy and dataset quality are explicitly approved.",
        },
    }
    return output, report


def write_dataset(rows: list[dict[str, object]], path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_from_csv(
    call_path: str | Path,
    put_path: str | Path,
    underlying_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
) -> dict:
    rows, report = build_dataset(
        read_csv(call_path), read_csv(put_path), read_csv(underlying_path)
    )
    write_dataset(rows, output_path)
    report["output"] = str(output_path)
    report["report"] = str(report_path)
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
