from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from data.nse_calendar import NSE_FO_HOLIDAYS

IST = ZoneInfo("Asia/Kolkata")
EXPIRY_CUTOFF = time(15, 30)


@dataclass(frozen=True)
class ExpiryResolution:
    observation_date: date
    expiry_flag: str
    expiry_code: int
    expiry: date | None
    method: str
    confidence: str
    note: str


def _last_tuesday(year: int, month: int) -> date:
    if month == 12:
        first_next = date(year + 1, 1, 1)
    else:
        first_next = date(year, month + 1, 1)
    d = first_next - timedelta(days=1)
    while d.weekday() != 1:  # Tuesday
        d -= timedelta(days=1)
    return d


def _weekly_nominal_dates(start: date, end: date) -> list[date]:
    # Weekly NIFTY expiry is Tuesday for contracts expiring on/after 2025-09-01.
    d = start - timedelta(days=(start.weekday() - 1) % 7)
    if d < start:
        d += timedelta(days=7)
    out = []
    while d <= end:
        out.append(d)
        d += timedelta(days=7)
    return out


def _is_nifty_tuesday_regime(d: date) -> bool:
    return d >= date(2025, 9, 1)


def adjusted_expiry(nominal: date, holidays: set[date] | None = None) -> date:
    holidays = NSE_FO_HOLIDAYS if holidays is None else holidays
    d = nominal
    while d.weekday() >= 5 or d in holidays:
        d -= timedelta(days=1)
    return d


def _expiry_dates_for_range(start: date, end: date, expiry_flag: str, holidays: set[date] | None) -> list[date]:
    holidays = NSE_FO_HOLIDAYS if holidays is None else holidays
    if expiry_flag == "WEEK":
        # For pre-Sep-2025 research we retain the old Thursday rule instead of
        # silently applying the modern Tuesday rule.
        out: list[date] = []
        cursor = start - timedelta(days=7)
        while cursor <= end + timedelta(days=7):
            cursor += timedelta(days=1)
            if cursor.weekday() == 3 and cursor < date(2025, 9, 1):
                out.append(adjusted_expiry(cursor, holidays))
        out.extend(adjusted_expiry(x, holidays) for x in _weekly_nominal_dates(max(start, date(2025, 9, 1)), end))
        return sorted(set(x for x in out if start - timedelta(days=7) <= x <= end + timedelta(days=7)))
    if expiry_flag == "MONTH":
        out = []
        y, m = start.year, start.month
        while date(y, m, 1) <= end + timedelta(days=31):
            nominal = _last_tuesday(y, m) if date(y, m, 1) >= date(2025, 9, 1) else None
            if nominal is not None:
                out.append(adjusted_expiry(nominal, holidays))
            if m == 12:
                y, m = y + 1, 1
            else:
                m += 1
        return sorted(set(out))
    raise ValueError("expiry_flag must be WEEK or MONTH")


def resolve_expiry(
    timestamp: str | datetime,
    *,
    expiry_flag: str,
    expiry_code: int,
    holidays: Iterable[str | date] | None = None,
) -> ExpiryResolution:
    """Resolve a Dhan rolling-series expiry as a *derived* contract identity.

    Dhan's rolling-options response exposes strike/spot/IV/OI/OHLC but not an
    explicit historical expiry date. Dhan documents expiryCode 0/1/2 as
    current/near, next, and far. We therefore derive the corresponding
    expiry from the exchange calendar. This is not broker-confirmed identity.
    """
    if expiry_code not in (0, 1, 2):
        raise ValueError("expiry_code must be 0, 1 or 2")
    if expiry_flag not in {"WEEK", "MONTH"}:
        raise ValueError("expiry_flag must be WEEK or MONTH")

    if isinstance(timestamp, str):
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    else:
        dt = timestamp
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    dt = dt.astimezone(IST)

    holiday_dates: set[date] = set(NSE_FO_HOLIDAYS if holidays is None else ())
    for h in holidays or []:
        holiday_dates.add(date.fromisoformat(h) if isinstance(h, str) else h)

    if dt.date() < date(2025, 9, 1):
        method = "exchange_expiry_calendar_pre_2025_09_01"
    else:
        method = "exchange_expiry_calendar_tuesday_regime"

    dates = _expiry_dates_for_range(
        dt.date() - timedelta(days=14),
        dt.date() + timedelta(days=60),
        expiry_flag,
        holiday_dates,
    )
    # On expiry day the current contract remains the near/current contract
    # through the trading session; after 15:30 it is considered expired.
    future = [x for x in dates if x > dt.date() or (x == dt.date() and dt.time() < EXPIRY_CUTOFF)]
    if len(future) <= expiry_code:
        return ExpiryResolution(dt.date(), expiry_flag, expiry_code, None, method, "LOW", "No calendar expiry available in resolution window")
    expiry = future[expiry_code]
    note = "Derived from Dhan expiryCode semantics + NSE expiry calendar; rolling endpoint does not return expiry explicitly."
    confidence = "MEDIUM"
    if expiry in holiday_dates:
        # Defensive assertion: adjusted_expiry should never return a holiday.
        return ExpiryResolution(dt.date(), expiry_flag, expiry_code, None, method, "LOW", "Resolved expiry unexpectedly falls on an NSE holiday")
    if dt.date() == expiry and dt.time() >= EXPIRY_CUTOFF:
        confidence = "MEDIUM"
    if expiry in holiday_dates:
        # Defensive assertion: adjusted_expiry should never return a holiday.
        return ExpiryResolution(dt.date(), expiry_flag, expiry_code, None, method, "LOW", "Resolved expiry unexpectedly falls on an NSE holiday")
    return ExpiryResolution(dt.date(), expiry_flag, expiry_code, expiry, method, confidence, note)


def time_to_expiry_years(timestamp: str | datetime, expiry: date | str, *, expiry_time: time = EXPIRY_CUTOFF) -> float:
    if isinstance(timestamp, str):
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    else:
        dt = timestamp
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    dt = dt.astimezone(IST)
    exp_date = date.fromisoformat(expiry) if isinstance(expiry, str) else expiry
    exp_dt = datetime.combine(exp_date, expiry_time, tzinfo=IST)
    return max((exp_dt - dt).total_seconds() / (365.0 * 24 * 3600), 0.0)


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes_delta(
    *,
    spot: float,
    strike: float,
    iv_percent: float,
    time_to_expiry_years: float,
    option_type: str,
    risk_free_rate: float = 0.0,
    dividend_yield: float = 0.0,
) -> float | None:
    """Approximate Black-Scholes delta from Dhan IV/spot/strike.

    This is a model-derived delta, not a historical broker-reported Greek.
    Rates/dividend yield default to zero because the rolling endpoint does not
    supply those inputs. Such deltas are suitable for contract selection
    research only after validation against an independent source.
    """
    if spot <= 0 or strike <= 0 or iv_percent is None or iv_percent <= 0 or time_to_expiry_years <= 0:
        return None
    sigma = iv_percent / 100.0
    t = time_to_expiry_years
    d1 = (math.log(spot / strike) + (risk_free_rate - dividend_yield + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    call_delta = math.exp(-dividend_yield * t) * _normal_cdf(d1)
    if option_type.upper() in {"PE", "PUT"}:
        return call_delta - math.exp(-dividend_yield * t)
    if option_type.upper() in {"CE", "CALL"}:
        return call_delta
    raise ValueError("option_type must be CE/CALL or PE/PUT")


def enrich_option_rows(rows: list[dict], *, holidays: Iterable[str | date] | None = None) -> list[dict]:
    out = []
    for row in rows:
        r = dict(row)
        resolved = resolve_expiry(
            r["timestamp"],
            expiry_flag=r["expiry_flag"],
            expiry_code=int(r["expiry_code"]),
            holidays=holidays,
        )
        r["derived_expiry"] = resolved.expiry.isoformat() if resolved.expiry else None
        r["identity_method"] = resolved.method
        r["identity_confidence"] = resolved.confidence
        r["identity_note"] = resolved.note
        if resolved.expiry:
            r["dte_days"] = (resolved.expiry - datetime.fromisoformat(r["timestamp"]).date()).days
            tte = time_to_expiry_years(r["timestamp"], resolved.expiry)
            r["time_to_expiry_years"] = tte
            try:
                delta = black_scholes_delta(
                    spot=float(r["spot"]), strike=float(r["strike"]), iv_percent=float(r["iv"]),
                    time_to_expiry_years=tte, option_type=r["option_type"],
                )
            except (TypeError, ValueError):
                delta = None
            r["model_delta"] = delta
            r["delta_source"] = "black_scholes_from_dhan_iv_spot_strike" if delta is not None else None
        else:
            r["dte_days"] = None
            r["time_to_expiry_years"] = None
            r["model_delta"] = None
            r["delta_source"] = None
        out.append(r)
    return out


def enrich_csv(input_path: str | Path, output_path: str | Path) -> int:
    with Path(input_path).open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    enriched = enrich_option_rows(rows)
    if not enriched:
        Path(output_path).write_text("", encoding="utf-8")
        return 0
    fields = list(enriched[0].keys())
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(output_path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(enriched)
    return len(enriched)
