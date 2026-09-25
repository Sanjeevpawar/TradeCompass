from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


OPTION_TYPE_ALIASES = {
    "CALL": "CE",
    "CE": "CE",
    "PUT": "PE",
    "PE": "PE",
}


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


def _timestamp(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _expiry(row: dict[str, str]) -> str:
    return (row.get("expiry") or row.get("derived_expiry") or "").strip()


def _option_type(row: dict[str, str]) -> str:
    raw = (row.get("option_type") or row.get("drv_option_type") or "").upper().strip()
    return OPTION_TYPE_ALIASES.get(raw, raw)


def _normalise_row(row: dict[str, str]) -> dict[str, object] | None:
    ts = _timestamp(row.get("timestamp"))
    strike = _float(row.get("strike"))
    expiry = _expiry(row)
    option_type = _option_type(row)
    if ts is None or strike is None or not expiry or option_type not in {"CE", "PE"}:
        return None

    # Accept both Phase 8.6 names and the raw/enriched Dhan names.
    out = dict(row)
    out["timestamp"] = ts.isoformat()
    out["_dt"] = ts
    out["strike"] = strike
    out["expiry"] = expiry
    out["option_type"] = option_type
    out["contract_key"] = f"{expiry}|{strike:g}|{option_type}"
    out["identity_status"] = row.get("identity_status") or "DERIVED"
    return out


def reconstruct_fixed_contracts(
    rows: Iterable[dict[str, str]],
    expected_interval_minutes: int = 5,
) -> tuple[list[dict[str, object]], dict]:
    """Group rolling observations into SAME-expiry + SAME-strike + SAME-type series.

    This function never rolls a contract forward to a new strike and never fills
    missing option prices. A gap inside the same trading date is retained and
    explicitly reported, because it may mean the requested rolling strike band
    stopped exposing the fixed contract.
    """
    if expected_interval_minutes <= 0:
        raise ValueError("expected_interval_minutes must be positive")

    source_rows = list(rows)
    normalised = [r for raw in source_rows if (r := _normalise_row(raw)) is not None]
    normalised.sort(key=lambda r: (str(r["contract_key"]), r["_dt"]))

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in normalised:
        grouped[str(row["contract_key"])].append(row)

    output: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    gap_counts = Counter()
    identity_counts = Counter()

    for key, series in sorted(grouped.items()):
        start = series[0]["_dt"]
        end = series[-1]["_dt"]
        same_day_gaps: list[dict[str, object]] = []
        duplicate_timestamps = 0
        seen: set[str] = set()

        for index, row in enumerate(series):
            ts = row["_dt"]
            ts_key = ts.isoformat()
            if ts_key in seen:
                duplicate_timestamps += 1
            seen.add(ts_key)

            if index > 0:
                previous = series[index - 1]["_dt"]
                delta_minutes = (ts - previous).total_seconds() / 60.0
                # Overnight/weekend gaps are expected. Only flag gaps within the
                # same calendar day; do not invent missing candles.
                if ts.date() == previous.date() and delta_minutes > expected_interval_minutes:
                    same_day_gaps.append(
                        {
                            "from": previous.isoformat(),
                            "to": ts.isoformat(),
                            "gap_minutes": delta_minutes,
                            "missing_intervals": max(
                                0, int(round(delta_minutes / expected_interval_minutes)) - 1
                            ),
                        }
                    )

        if duplicate_timestamps:
            continuity = "DUPLICATE_TIMESTAMP"
        elif len(series) == 1:
            continuity = "SINGLETON"
        elif same_day_gaps:
            continuity = "GAPPED"
        else:
            continuity = "CONTINUOUS"

        identity_statuses = {str(r.get("identity_status") or "UNVERIFIED") for r in series}
        identity_status = (
            "BROKER_VERIFIED"
            if identity_statuses == {"BROKER_VERIFIED"}
            else "DERIVED"
            if "DERIVED" in identity_statuses
            else "UNVERIFIED"
        )

        # Reconstruction is useful for research when identity is derived, but
        # this phase deliberately does not approve live/production backtesting.
        reconstruction_eligible = continuity == "CONTINUOUS" and identity_status != "UNVERIFIED"
        gap_counts[continuity] += 1
        identity_counts[identity_status] += 1

        for row_index, row in enumerate(series, start=1):
            enriched = dict(row)
            enriched.pop("_dt", None)
            enriched.update(
                {
                    "contract_row_index": row_index,
                    "contract_start": start.isoformat(),
                    "contract_end": end.isoformat(),
                    "contract_rows": len(series),
                    "contract_continuity": continuity,
                    "contract_identity_status": identity_status,
                    "same_day_gap_count": len(same_day_gaps),
                    "duplicate_timestamp_count": duplicate_timestamps,
                    "reconstruction_eligible": reconstruction_eligible,
                }
            )
            output.append(enriched)

        summaries.append(
            {
                "contract_key": key,
                "expiry": series[0]["expiry"],
                "strike": series[0]["strike"],
                "option_type": series[0]["option_type"],
                "start": start.isoformat(),
                "end": end.isoformat(),
                "rows": len(series),
                "continuity": continuity,
                "identity_status": identity_status,
                "same_day_gap_count": len(same_day_gaps),
                "duplicate_timestamp_count": duplicate_timestamps,
                "reconstruction_eligible": reconstruction_eligible,
                "gaps": same_day_gaps,
            }
        )

    report = {
        "status": "PASS",
        "policy": {
            "contract_key": "same expiry + same strike + same option type",
            "rolling_strike_policy": "never switch strike inside a fixed contract series",
            "missing_option_bars": "retain gap; never forward-fill prices",
            "overnight_gaps": "not treated as missing intraday bars",
            "identity": "derived identity remains explicitly labelled",
            "production_backtest": "not approved by Phase 9A",
        },
        "input": {
            "rows_received": len(source_rows),
            "rows_normalized": len(normalised),
            "rows_rejected": len(source_rows) - len(normalised),
        },
        "contracts": {
            "count": len(summaries),
            "continuity": dict(gap_counts),
            "identity": dict(identity_counts),
            "reconstruction_eligible": sum(1 for s in summaries if s["reconstruction_eligible"]),
        },
        "expected_interval_minutes": expected_interval_minutes,
        "contract_summaries": summaries,
    }
    return output, report


def write_csv(rows: list[dict[str, object]], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    fields = [f for f in fields if f != "_dt"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(report: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def reconstruct_from_csv(
    input_paths: Iterable[str | Path],
    output_path: str | Path,
    report_path: str | Path,
    expected_interval_minutes: int = 5,
) -> dict:
    paths = [Path(p) for p in input_paths]
    rows: list[dict[str, str]] = []
    rejected = 0
    for path in paths:
        source_rows = read_csv(path)
        rows.extend(source_rows)

    reconstructed, report = reconstruct_fixed_contracts(rows, expected_interval_minutes)
    report["input"]["files"] = [str(p) for p in paths]
    report["input"]["rows_received"] = len(rows)
    report["input"]["rows_normalized"] = len(reconstructed)
    report["input"]["rows_rejected"] = max(0, len(rows) - len(reconstructed))
    write_csv(reconstructed, output_path)
    report["output"] = str(output_path)
    report["report"] = str(report_path)
    write_report(report, report_path)
    return report
