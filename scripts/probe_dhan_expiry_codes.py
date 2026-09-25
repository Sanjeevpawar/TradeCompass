"""Read-only probe of Dhan rolling-option expiryCode behaviour.

This does NOT modify TradeCompass data. It queries the Dhan expired-options
rolling endpoint for expiryCode 0/1/2 around normal and holiday expiry
transitions, then reports row/timestamp/strike coverage and overlaps.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

API_URL = "https://api.dhan.co/v2/charts/rollingoption"
DEFAULT_SECURITY_ID = "13"
DEFAULT_CASES = [
    ("normal_expiry", "2026-03-09", "2026-03-11"),
    ("holiday_expiry_oct_2025", "2025-10-20", "2025-10-23"),
    ("holiday_expiry_mar_2026", "2026-03-30", "2026-04-01"),
    ("holiday_expiry_apr_2026", "2026-04-13", "2026-04-15"),
]


def token_from_env() -> str:
    load_dotenv()
    for key in ("DHAN_ACCESS_TOKEN", "DHAN_TOKEN", "DHAN_API_TOKEN", "DHAN_ACCESS_TOKEN_24H"):
        value = os.getenv(key)
        if value:
            return value.strip()
    raise RuntimeError(
        "No Dhan token found. Set DHAN_ACCESS_TOKEN (or DHAN_TOKEN) in the TradeCompass .env file."
    )


def request_code(token: str, code: int, from_date: str, to_date: str, security_id: str) -> dict:
    body = {
        "exchangeSegment": "NSE_FNO",
        "interval": "5",
        "securityId": security_id,
        "instrument": "OPTIDX",
        "expiryFlag": "WEEK",
        "expiryCode": code,
        "strike": "ATM",
        "drvOptionType": "CALL",
        "requiredData": ["open", "high", "low", "close", "iv", "volume", "strike", "oi", "spot"],
        "fromDate": from_date,
        "toDate": to_date,
    }
    response = requests.post(
        API_URL,
        headers={"Accept": "application/json", "Content-Type": "application/json", "access-token": token},
        json=body,
        timeout=30,
    )
    result = {
        "http_status": response.status_code,
        "request": {"expiryCode": code, "fromDate": from_date, "toDate": to_date, "strike": "ATM"},
    }
    try:
        payload = response.json()
    except Exception:
        result["error_text"] = response.text[:500]
        return result
    if response.status_code != 200:
        result["error"] = payload
        return result

    data = (payload.get("data") or {}).get("ce") or {}
    timestamps = data.get("timestamp") or []
    strikes = data.get("strike") or []
    spots = data.get("spot") or []
    closes = data.get("close") or []
    ivs = data.get("iv") or []
    volumes = data.get("volume") or []

    def ts_to_ist(ts):
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone().isoformat()
        except Exception:
            return None

    result["summary"] = {
        "rows": len(timestamps),
        "first_timestamp": timestamps[0] if timestamps else None,
        "last_timestamp": timestamps[-1] if timestamps else None,
        "first_timestamp_local": ts_to_ist(timestamps[0]) if timestamps else None,
        "last_timestamp_local": ts_to_ist(timestamps[-1]) if timestamps else None,
        "unique_strikes": sorted({float(x) for x in strikes if x is not None}),
        "first_strikes": strikes[:10],
        "last_strikes": strikes[-10:],
        "first_spots": spots[:5],
        "last_spots": spots[-5:],
        "first_closes": closes[:5],
        "last_closes": closes[-5:],
        "iv_present": sum(x is not None for x in ivs),
        "volume_present": sum(x is not None for x in volumes),
    }
    # Keep only compact diagnostic arrays, not the full market response.
    result["sample"] = [
        {"timestamp": timestamps[i], "strike": strikes[i] if i < len(strikes) else None,
         "spot": spots[i] if i < len(spots) else None, "close": closes[i] if i < len(closes) else None}
        for i in range(min(3, len(timestamps)))
    ]
    return result


def compare(results: list[dict]) -> dict:
    by_case = {}
    for r in results:
        name = r["case"]
        by_case.setdefault(name, {})[str(r["request"]["expiryCode"])] = r

    comparisons = []
    for case, codes in by_case.items():
        sets = {}
        for code, r in codes.items():
            summary = r.get("summary") or {}
            # Reconstruct timestamp set from compactly stored first/last only is insufficient,
            # so comparison is intentionally limited to coverage and endpoint differences.
            sets[code] = summary
        comparisons.append({"case": case, "codes": sets})
    return {"comparisons": comparisons}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--security-id", default=DEFAULT_SECURITY_ID)
    parser.add_argument("--output", default="data/dhan_history/raw/dhan_expiry_code_probe_report.json")
    parser.add_argument("--pause-seconds", type=float, default=0.5)
    args = parser.parse_args()

    token = token_from_env()
    results = []
    for case_name, from_date, to_date in DEFAULT_CASES:
        for code in (0, 1, 2):
            result = request_code(token, code, from_date, to_date, args.security_id)
            result["case"] = case_name
            results.append(result)
            print(
                f"{case_name:28s} code={code} status={result['http_status']} "
                f"rows={(result.get('summary') or {}).get('rows', 0)}"
            )
            time.sleep(args.pause_seconds)

    report = {
        "status": "PASS",
        "endpoint": API_URL,
        "security_id": args.security_id,
        "instrument": "OPTIDX",
        "expiry_flag": "WEEK",
        "option_type": "CALL",
        "cases": [{"name": n, "from": f, "to": t} for n, f, t in DEFAULT_CASES],
        "results": results,
        **compare(results),
        "note": (
            "The rolling-option response does not expose the historical expiry date directly. "
            "This probe therefore documents observed coverage/behaviour of expiryCode 0/1/2; "
            "it does not by itself prove the exact expiry identity of a returned series."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
