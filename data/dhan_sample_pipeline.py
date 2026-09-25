from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from data.dhan_historical import DhanHistoricalClient, epoch_to_ist, rolling_option_records


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_underlying(response: dict[str, Any]) -> list[dict[str, Any]]:
    timestamps = response.get("timestamp") or []
    rows = []
    for i, ts in enumerate(timestamps):
        rows.append({
            "timestamp_epoch": int(ts),
            "timestamp": epoch_to_ist(ts),
            "open": response.get("open", [])[i],
            "high": response.get("high", [])[i],
            "low": response.get("low", [])[i],
            "close": response.get("close", [])[i],
            "volume": (response.get("volume") or [None] * len(timestamps))[i],
        })
    return rows


def normalize_options(response: dict[str, Any], option_type: str, *, expiry_flag: str, expiry_code: int, strike_mode: str) -> list[dict[str, Any]]:
    rows = []
    for r in rolling_option_records(response, option_type=option_type):
        r = dict(r)
        r["timestamp_epoch"] = r.pop("timestamp")
        r["timestamp"] = epoch_to_ist(r["timestamp_epoch"])
        r["expiry_flag"] = expiry_flag
        r["expiry_code"] = expiry_code
        r["strike_mode"] = strike_mode
        rows.append(r)
    return rows


def capture_sample(
    client: DhanHistoricalClient,
    *,
    from_date: str,
    to_date: str,
    out_dir: str | Path,
    security_id: str = "13",
    interval: int = 5,
    expiry_flag: str = "WEEK",
    expiry_code: int = 1,
    strike_mode: str = "ATM",
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    underlying = client.intraday_candles(
        security_id=security_id,
        exchange_segment="IDX_I",
        instrument="INDEX",
        interval=interval,
        from_date=from_date,
        to_date=to_date,
    )
    call = client.rolling_expired_options(
        security_id=security_id, strike=strike_mode, option_type="CALL",
        from_date=from_date, to_date=to_date, expiry_flag=expiry_flag,
        expiry_code=expiry_code, interval=interval,
    )
    put = client.rolling_expired_options(
        security_id=security_id, strike=strike_mode, option_type="PUT",
        from_date=from_date, to_date=to_date, expiry_flag=expiry_flag,
        expiry_code=expiry_code, interval=interval,
    )

    underlying_rows = normalize_underlying(underlying)
    call_rows = normalize_options(call, "CALL", expiry_flag=expiry_flag, expiry_code=expiry_code, strike_mode=strike_mode)
    put_rows = normalize_options(put, "PUT", expiry_flag=expiry_flag, expiry_code=expiry_code, strike_mode=strike_mode)

    _write_csv(out / "nifty_underlying.csv", underlying_rows,
               ["timestamp_epoch", "timestamp", "open", "high", "low", "close", "volume"])
    option_fields = ["timestamp_epoch", "timestamp", "option_type", "open", "high", "low", "close", "iv", "volume", "strike", "oi", "spot", "expiry_flag", "expiry_code", "strike_mode"]
    _write_csv(out / "nifty_options_call.csv", call_rows, option_fields)
    _write_csv(out / "nifty_options_put.csv", put_rows, option_fields)

    metadata = {
        "provider": "Dhan",
        "security_id": str(security_id),
        "from_date": from_date,
        "to_date": to_date,
        "interval_minutes": interval,
        "expiry_flag": expiry_flag,
        "expiry_code": expiry_code,
        "strike_mode": strike_mode,
        "counts": {"underlying": len(underlying_rows), "call": len(call_rows), "put": len(put_rows)},
        "contract_identity_note": "Dhan rolling expired-options data is relative to spot. This capture intentionally does not invent a historical expiry date or Delta.",
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata
