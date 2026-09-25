from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.dhan.co/v2"


@dataclass(frozen=True)
class DhanHistoricalConfig:
    access_token: str
    timeout_seconds: int = 30
    default_expiry_code: int = 1

    @classmethod
    def from_env(cls) -> "DhanHistoricalConfig":
        load_dotenv()
        token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
        if not token:
            raise ValueError("DHAN_ACCESS_TOKEN is not configured")
        expiry_code = int(os.getenv("TRADECOMPASS_DHAN_EXPIRY_CODE", "1"))
        if expiry_code not in (0, 1, 2):
            raise ValueError("TRADECOMPASS_DHAN_EXPIRY_CODE must be 0, 1 or 2")
        return cls(access_token=token, default_expiry_code=expiry_code)


class DhanHistoricalClient:
    """Read-only client for Dhan historical market/expired-option data."""

    def __init__(self, config: DhanHistoricalConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "access-token": config.access_token,
        })

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            f"{BASE_URL}{path}", json=payload, timeout=self.config.timeout_seconds
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Unexpected Dhan response for {path}")
        return data

    def intraday_candles(
        self,
        *,
        security_id: str,
        exchange_segment: str = "IDX_I",
        instrument: str = "INDEX",
        interval: int = 5,
        from_date: str,
        to_date: str,
        oi: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange_segment,
            "instrument": instrument,
            "interval": str(interval),
            "oi": oi,
            "fromDate": from_date,
            "toDate": to_date,
        }
        return self._post("/charts/intraday", payload)

    def rolling_expired_options(
        self,
        *,
        security_id: str,
        strike: str,
        option_type: str,
        from_date: str,
        to_date: str,
        expiry_flag: str = "WEEK",
        expiry_code: int | None = None,
        interval: int = 1,
        exchange_segment: str = "NSE_FNO",
        instrument: str = "OPTIDX",
        required_data: list[str] | None = None,
    ) -> dict[str, Any]:
        option_type = option_type.upper()
        if option_type not in {"CALL", "PUT"}:
            raise ValueError("option_type must be CALL or PUT")
        if expiry_flag not in {"WEEK", "MONTH"}:
            raise ValueError("expiry_flag must be WEEK or MONTH")
        code = self.config.default_expiry_code if expiry_code is None else expiry_code
        if code not in (0, 1, 2):
            raise ValueError("expiry_code must be 0, 1 or 2")
        payload = {
            "exchangeSegment": exchange_segment,
            "interval": int(interval),
            "securityId": str(security_id),
            "instrument": instrument,
            "expiryFlag": expiry_flag,
            "expiryCode": code,
            "strike": strike,
            "drvOptionType": option_type,
            "requiredData": required_data or [
                "open", "high", "low", "close", "iv", "volume", "strike", "oi", "spot"
            ],
            "fromDate": from_date,
            "toDate": to_date,
        }
        return self._post("/charts/rollingoption", payload)


def rolling_option_records(
    response: dict[str, Any],
    *,
    option_type: str,
) -> list[dict[str, Any]]:
    """Normalize Dhan rolling-option arrays into timestamped records.

    Dhan's rolling endpoint does not return an explicit expiry-date field.
    This function therefore deliberately does NOT invent an expiry date.
    The returned records retain the actual strike/spot/IV/OI supplied by Dhan.
    """
    option_type = option_type.upper()
    if option_type not in {"CALL", "PUT"}:
        raise ValueError("option_type must be CALL or PUT")

    leg_key = "ce" if option_type == "CALL" else "pe"
    leg = (response.get("data") or {}).get(leg_key) or {}
    timestamps = leg.get("timestamp") or []
    fields = ("open", "high", "low", "close", "iv", "volume", "strike", "oi", "spot")

    records: list[dict[str, Any]] = []
    for i, ts in enumerate(timestamps):
        row: dict[str, Any] = {
            "timestamp": int(ts),
            "option_type": "CE" if option_type == "CALL" else "PE",
        }
        for field in fields:
            values = leg.get(field) or []
            row[field] = values[i] if i < len(values) else None
        records.append(row)
    return records


def month_chunks(start: str, end: str, max_days: int = 30) -> list[tuple[str, str]]:
    """Split a research range into Dhan-safe <=30-day requests."""
    if max_days < 1:
        raise ValueError("max_days must be positive")
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    if end_d <= start_d:
        raise ValueError("end must be after start")
    chunks = []
    cursor = start_d
    while cursor < end_d:
        chunk_end = min(cursor + timedelta(days=max_days), end_d)
        chunks.append((cursor.isoformat(), chunk_end.isoformat()))
        cursor = chunk_end
    return chunks


def epoch_to_ist(timestamp: int | float) -> str:
    """Convert Dhan epoch seconds to an ISO timestamp in Asia/Kolkata."""
    from zoneinfo import ZoneInfo
    return datetime.fromtimestamp(float(timestamp), tz=ZoneInfo("Asia/Kolkata")).isoformat()
