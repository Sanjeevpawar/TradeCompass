from __future__ import annotations

import csv
import json
import time as time_module
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Protocol

from data.dhan_historical import DhanHistoricalClient, month_chunks, epoch_to_ist


DEFAULT_REQUIRED_DATA = ["open", "high", "low", "close", "iv", "volume", "strike", "oi", "spot"]


class RollingClient(Protocol):
    def rolling_expired_options(self, **kwargs: Any) -> dict[str, Any]: ...


@dataclass(frozen=True)
class StrikeBandConfig:
    security_id: str = "13"
    expiry_flag: str = "WEEK"
    expiry_codes: tuple[int, ...] = (1,)
    interval: int = 5
    offsets: tuple[int, ...] = tuple(range(-10, 11))
    exchange_segment: str = "NSE_FNO"
    instrument: str = "OPTIDX"
    pause_seconds: float = 0.5
    max_retries: int = 5
    retry_backoff_seconds: float = 1.0

    def validate(self) -> None:
        if self.interval not in {1, 5, 15, 25, 60}:
            raise ValueError("interval must be one of 1, 5, 15, 25, 60")
        if self.expiry_flag not in {"WEEK", "MONTH"}:
            raise ValueError("expiry_flag must be WEEK or MONTH")
        if not self.expiry_codes or any(code not in {0, 1, 2} for code in self.expiry_codes):
            raise ValueError("expiry_codes must contain only 0, 1 or 2")
        if not self.offsets:
            raise ValueError("offsets cannot be empty")
        if any(offset < -10 or offset > 10 for offset in self.offsets):
            raise ValueError("index strike offsets must be between -10 and +10")
        if len(set(self.offsets)) != len(self.offsets):
            raise ValueError("offsets must be unique")
        if self.pause_seconds < 0:
            raise ValueError("pause_seconds cannot be negative")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.retry_backoff_seconds <= 0:
            raise ValueError("retry_backoff_seconds must be positive")


def offset_to_strike(offset: int) -> str:
    if offset == 0:
        return "ATM"
    return f"ATM{offset:+d}"


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def normalize_rolling_response(
    response: dict[str, Any],
    *,
    option_type: str,
    requested_offset: int,
    expiry_flag: str,
    expiry_code: int,
    source_from_date: str,
    source_to_date: str,
) -> list[dict[str, Any]]:
    """Normalize one Dhan rolling-option response into row records.

    The returned strike is the strike Dhan reported at each timestamp. The
    requested ATM offset is retained only as provenance; it is never treated as
    a fixed contract identity.
    """
    option_type = option_type.upper()
    if option_type not in {"CALL", "PUT"}:
        raise ValueError("option_type must be CALL or PUT")
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict):
        return []

    key = "ce" if option_type == "CALL" else "pe"
    series = data.get(key)
    if series is None:
        # Some responses may use a neutral data object for a requested option.
        series = data if isinstance(data, dict) and "timestamp" in data else None
    if not isinstance(series, dict):
        return []

    timestamps = _as_list(series.get("timestamp"))
    columns = {
        "open": _as_list(series.get("open")),
        "high": _as_list(series.get("high")),
        "low": _as_list(series.get("low")),
        "close": _as_list(series.get("close")),
        "iv": _as_list(series.get("iv")),
        "volume": _as_list(series.get("volume")),
        "strike": _as_list(series.get("strike")),
        "oi": _as_list(series.get("oi")),
        "spot": _as_list(series.get("spot")),
    }
    rows: list[dict[str, Any]] = []
    for i, ts in enumerate(timestamps):
        row: dict[str, Any] = {
            "timestamp": epoch_to_ist(ts),
            "option_type": "CE" if option_type == "CALL" else "PE",
            "open": columns["open"][i] if i < len(columns["open"]) else None,
            "high": columns["high"][i] if i < len(columns["high"]) else None,
            "low": columns["low"][i] if i < len(columns["low"]) else None,
            "close": columns["close"][i] if i < len(columns["close"]) else None,
            "iv": columns["iv"][i] if i < len(columns["iv"]) else None,
            "volume": columns["volume"][i] if i < len(columns["volume"]) else None,
            "strike": columns["strike"][i] if i < len(columns["strike"]) else None,
            "oi": columns["oi"][i] if i < len(columns["oi"]) else None,
            "spot": columns["spot"][i] if i < len(columns["spot"]) else None,
            "expiry_flag": expiry_flag,
            "expiry_code": expiry_code,
            "requested_strike_offset": requested_offset,
            "requested_strike": offset_to_strike(requested_offset),
            "source_from_date": source_from_date,
            "source_to_date": source_to_date,
            "identity_status": "DERIVED",
        }
        rows.append(row)
    return rows


def _dedupe_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("timestamp"),
        row.get("option_type"),
        row.get("strike"),
        row.get("expiry_flag"),
        row.get("expiry_code"),
    )


def collect_strike_band(
    client: RollingClient,
    *,
    start_date: str,
    end_date: str,
    config: StrikeBandConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collect a wide ATM-relative strike band without inventing contract identity."""
    config.validate()
    if date.fromisoformat(end_date) <= date.fromisoformat(start_date):
        raise ValueError("end_date must be after start_date")

    rows: list[dict[str, Any]] = []
    requests_made = 0
    request_attempts = 0
    request_errors: list[dict[str, Any]] = []
    retry_events: list[dict[str, Any]] = []
    response_counts: Counter[str] = Counter()

    for chunk_start, chunk_end in month_chunks(start_date, end_date, max_days=30):
        for expiry_code in config.expiry_codes:
            for offset in config.offsets:
                strike = offset_to_strike(offset)
                for option_type in ("CALL", "PUT"):
                    requests_made += 1
                    attempts = 0
                    while True:
                        attempts += 1
                        request_attempts += 1
                        try:
                            response = client.rolling_expired_options(
                                security_id=config.security_id,
                                strike=strike,
                                option_type=option_type,
                                from_date=chunk_start,
                                to_date=chunk_end,
                                expiry_flag=config.expiry_flag,
                                expiry_code=expiry_code,
                                interval=config.interval,
                                exchange_segment=config.exchange_segment,
                                instrument=config.instrument,
                                required_data=DEFAULT_REQUIRED_DATA,
                            )
                            normalized = normalize_rolling_response(
                                response,
                                option_type=option_type,
                                requested_offset=offset,
                                expiry_flag=config.expiry_flag,
                                expiry_code=expiry_code,
                                source_from_date=chunk_start,
                                source_to_date=chunk_end,
                            )
                            rows.extend(normalized)
                            response_counts[f"{option_type}:{offset}"] += len(normalized)
                            break
                        except Exception as exc:
                            status_code = getattr(getattr(exc, "response", None), "status_code", None)
                            is_rate_limited = status_code == 429
                            if not is_rate_limited or attempts > config.max_retries:
                                request_errors.append({
                                    "from_date": chunk_start,
                                    "to_date": chunk_end,
                                    "expiry_code": expiry_code,
                                    "offset": offset,
                                    "option_type": option_type,
                                    "attempts": attempts,
                                    "error": f"{type(exc).__name__}: {exc}",
                                })
                                break

                            retry_after = getattr(getattr(exc, "response", None), "headers", {}).get("Retry-After")
                            try:
                                wait_seconds = float(retry_after) if retry_after is not None else config.retry_backoff_seconds * (2 ** (attempts - 1))
                            except (TypeError, ValueError):
                                wait_seconds = config.retry_backoff_seconds * (2 ** (attempts - 1))
                            retry_events.append({
                                "from_date": chunk_start,
                                "to_date": chunk_end,
                                "expiry_code": expiry_code,
                                "offset": offset,
                                "option_type": option_type,
                                "attempt": attempts,
                                "wait_seconds": wait_seconds,
                                "reason": "HTTP 429 rate limit",
                            })
                            time_module.sleep(wait_seconds)

                    if config.pause_seconds:
                        time_module.sleep(config.pause_seconds)

    before = len(rows)
    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        deduped[_dedupe_key(row)] = row
    rows = sorted(deduped.values(), key=lambda r: (r["timestamp"], r["option_type"], float(r["strike"] or 0), int(r["expiry_code"])))

    report = {
        "status": "PASS" if not request_errors else "FAIL",
        "request": {
            "security_id": config.security_id,
            "start_date": start_date,
            "end_date": end_date,
            "expiry_flag": config.expiry_flag,
            "expiry_codes": list(config.expiry_codes),
            "interval_minutes": config.interval,
            "strike_offsets": list(config.offsets),
            "strike_mode": "ATM plus/minus requested offsets",
            "pause_seconds": config.pause_seconds,
            "max_retries": config.max_retries,
            "retry_backoff_seconds": config.retry_backoff_seconds,
        },
        "requests": {
            "made": requests_made,
            "attempts": request_attempts,
            "errors": len(request_errors),
            "error_details": request_errors,
            "retry_events": retry_events,
            "retry_count": len(retry_events),
        },
        "rows": {
            "before_deduplication": before,
            "after_deduplication": len(rows),
            "duplicates_removed": before - len(rows),
        },
        "response_counts": dict(response_counts),
        "policy": {
            "fixed_contract_identity": "not inferred by collector",
            "returned_strike": "preserved exactly as reported by Dhan",
            "requested_offset": "retained as provenance only",
            "expiry": "not invented by collector; expiry_code retained",
            "missing_prices": "not forward-filled",
        },
    }
    return rows, report


def write_csv(rows: Iterable[dict[str, Any]], path: str | Path) -> None:
    rows = list(rows)
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
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def collect_with_dhan(
    *,
    start_date: str,
    end_date: str,
    config: StrikeBandConfig,
    output_call: str | Path,
    output_put: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    from data.dhan_historical import DhanHistoricalConfig
    client = DhanHistoricalClient(DhanHistoricalConfig.from_env())
    rows, report = collect_strike_band(client, start_date=start_date, end_date=end_date, config=config)
    write_csv((r for r in rows if r["option_type"] == "CE"), output_call)
    write_csv((r for r in rows if r["option_type"] == "PE"), output_put)
    report["outputs"] = {"call": str(output_call), "put": str(output_put), "report": str(report_path)}
    write_report(report, report_path)
    return report
