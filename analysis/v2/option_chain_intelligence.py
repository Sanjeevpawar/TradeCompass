from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from math import isfinite
from typing import Iterable, Mapping, Optional


@dataclass(frozen=True)
class ChainMetric:
    timestamp: str
    spot: Optional[float]
    call_contracts: int
    put_contracts: int
    common_strikes: int
    call_only_strikes: int
    put_only_strikes: int
    coverage_complete: bool
    identity_status: str
    call_oi: Optional[float]
    put_oi: Optional[float]
    pcr_oi: Optional[float]
    call_peak_strike: Optional[float]
    call_peak_oi: Optional[float]
    call_peak_oi_pct: Optional[float]
    put_peak_strike: Optional[float]
    put_peak_oi: Optional[float]
    put_peak_oi_pct: Optional[float]
    call_peak_distance: Optional[float]
    put_peak_distance: Optional[float]
    call_delta_oi: Optional[float]
    put_delta_oi: Optional[float]
    call_delta_oi_peak_strike: Optional[float]
    put_delta_oi_peak_strike: Optional[float]
    atm_strike: Optional[float]
    atm_call_iv: Optional[float]
    atm_put_iv: Optional[float]
    atm_call_oi: Optional[float]
    atm_put_oi: Optional[float]

    def to_dict(self) -> dict:
        return asdict(self)


def _float(value) -> Optional[float]:
    if value in (None, "", "null", "None"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _text(value) -> str:
    return "" if value is None else str(value)


def _option_type(value) -> str:
    """Normalize broker/reconstructed option-type labels to CALL/PUT."""
    text = _text(value).strip().upper()
    return {
        "CALL": "CALL",
        "CE": "CALL",
        "PUT": "PUT",
        "PE": "PUT",
    }.get(text, text)


def _contract_key(row: Mapping) -> tuple:
    """Fixed identity: expiry + strike + option type.

    Identity is intentionally kept as supplied by the reconstruction layer.
    The engine never tries to repair or infer expiry dates.
    """
    return (
        _text(row.get("expiry")),
        _float(row.get("strike")),
        _option_type(row.get("option_type")),
    )


def _dedupe(rows: Iterable[Mapping]) -> list[dict]:
    """Remove exact market duplicates only.

    Acquisition-boundary duplicates are expected. If two rows with the same
    timestamp/contract disagree on market fields, keep both so the caller can
    detect the conflict rather than silently choosing one.
    """
    seen = set()
    result = []
    market_fields = ("open", "high", "low", "close", "iv", "volume", "oi", "spot")
    for row in rows:
        key = (
            _text(row.get("timestamp")),
            *_contract_key(row),
            tuple(_text(row.get(k)) for k in market_fields),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(row))
    return result


def _timestamp_value(value) -> str:
    return _text(value)


def _previous_contract_oi(
    previous_rows: Iterable[Mapping],
) -> dict[tuple, float]:
    result = {}
    for row in previous_rows:
        key = _contract_key(row)
        oi = _float(row.get("oi"))
        if oi is not None:
            result[key] = oi
    return result


def build_snapshot(
    rows: Iterable[Mapping],
    *,
    timestamp: Optional[str] = None,
    spot: Optional[float] = None,
    previous_rows: Optional[Iterable[Mapping]] = None,
) -> ChainMetric:
    """Build one deterministic historical option-chain snapshot.

    Only rows belonging to the requested timestamp are used. Previous OI is
    supplied explicitly from the immediately preceding completed snapshot;
    therefore no future/EOD information can leak into the calculation.
    """
    rows = _dedupe(rows)
    if timestamp is not None:
        rows = [r for r in rows if _timestamp_value(r.get("timestamp")) == timestamp]
    if not rows:
        raise ValueError("No option-chain rows available for the requested timestamp")

    by_type: dict[str, dict[tuple, dict]] = {"CALL": {}, "PUT": {}}
    conflicts = []
    for row in rows:
        option_type = _option_type(row.get("option_type"))
        if option_type not in by_type:
            continue
        key = _contract_key(row)
        if key in by_type[option_type]:
            existing = by_type[option_type][key]
            if tuple(existing.get(k) for k in ("open", "high", "low", "close", "iv", "volume", "oi", "spot")) != tuple(row.get(k) for k in ("open", "high", "low", "close", "iv", "volume", "oi", "spot")):
                conflicts.append(key)
            continue
        by_type[option_type][key] = row

    if conflicts:
        raise ValueError(f"Conflicting duplicate option rows at timestamp: {conflicts[:3]}")

    calls = list(by_type["CALL"].values())
    puts = list(by_type["PUT"].values())
    call_strikes = {k[1] for k in by_type["CALL"] if k[1] is not None}
    put_strikes = {k[1] for k in by_type["PUT"] if k[1] is not None}
    common = call_strikes & put_strikes

    # PCR is deliberately based on the common strike intersection so an
    # asymmetric rolling ATM window cannot create a fake PCR advantage.
    common_calls = [r for r in calls if _float(r.get("strike")) in common]
    common_puts = [r for r in puts if _float(r.get("strike")) in common]

    call_oi = sum(_float(r.get("oi")) or 0.0 for r in common_calls) if common_calls else None
    put_oi = sum(_float(r.get("oi")) or 0.0 for r in common_puts) if common_puts else None
    pcr = put_oi / call_oi if call_oi not in (None, 0) and put_oi is not None else None

    def peak(items):
        usable = [r for r in items if _float(r.get("oi")) is not None and _float(r.get("strike")) is not None]
        return max(usable, key=lambda r: (_float(r.get("oi")) or 0.0)) if usable else None

    call_peak = peak(calls)
    put_peak = peak(puts)

    def oi_pct(row, total):
        oi = _float(row.get("oi")) if row else None
        return oi / total * 100.0 if oi is not None and total else None

    prev_oi = _previous_contract_oi(previous_rows or [])

    def delta_for(items):
        values = []
        for r in items:
            key = _contract_key(r)
            current = _float(r.get("oi"))
            previous = prev_oi.get(key)
            if current is not None and previous is not None:
                values.append((r, current - previous))
        return values

    call_deltas = delta_for(calls)
    put_deltas = delta_for(puts)

    call_delta_total = sum(d for _, d in call_deltas) if call_deltas else None
    put_delta_total = sum(d for _, d in put_deltas) if put_deltas else None
    call_delta_peak = max(call_deltas, key=lambda x: x[1]) if call_deltas else None
    put_delta_peak = max(put_deltas, key=lambda x: x[1]) if put_deltas else None

    inferred_spot = spot
    if inferred_spot is None:
        spots = [_float(r.get("spot")) for r in rows]
        spots = [x for x in spots if x is not None]
        inferred_spot = spots[0] if spots else None

    all_strikes = sorted(common if common else (call_strikes | put_strikes))
    atm_strike = min(all_strikes, key=lambda s: abs(s - inferred_spot)) if all_strikes and inferred_spot is not None else None

    def at_strike(items, strike):
        for r in items:
            if _float(r.get("strike")) == strike:
                return r
        return None

    atm_call = at_strike(calls, atm_strike)
    atm_put = at_strike(puts, atm_strike)

    identity_values = {_text(r.get("identity_status")) for r in rows if r.get("identity_status")}
    identity_status = ",".join(sorted(identity_values)) if identity_values else "UNKNOWN"

    call_total_all = sum(_float(r.get("oi")) or 0.0 for r in calls) if calls else None
    put_total_all = sum(_float(r.get("oi")) or 0.0 for r in puts) if puts else None

    return ChainMetric(
        timestamp=_timestamp_value(rows[0].get("timestamp")),
        spot=inferred_spot,
        call_contracts=len(calls),
        put_contracts=len(puts),
        common_strikes=len(common),
        call_only_strikes=len(call_strikes - put_strikes),
        put_only_strikes=len(put_strikes - call_strikes),
        coverage_complete=call_strikes == put_strikes,
        identity_status=identity_status,
        call_oi=call_oi,
        put_oi=put_oi,
        pcr_oi=pcr,
        call_peak_strike=_float(call_peak.get("strike")) if call_peak else None,
        call_peak_oi=_float(call_peak.get("oi")) if call_peak else None,
        call_peak_oi_pct=oi_pct(call_peak, call_total_all),
        put_peak_strike=_float(put_peak.get("strike")) if put_peak else None,
        put_peak_oi=_float(put_peak.get("oi")) if put_peak else None,
        put_peak_oi_pct=oi_pct(put_peak, put_total_all),
        call_peak_distance=(inferred_spot - _float(call_peak.get("strike"))) if call_peak and inferred_spot is not None else None,
        put_peak_distance=(_float(put_peak.get("strike")) - inferred_spot) if put_peak and inferred_spot is not None else None,
        call_delta_oi=call_delta_total,
        put_delta_oi=put_delta_total,
        call_delta_oi_peak_strike=_float(call_delta_peak[0].get("strike")) if call_delta_peak else None,
        put_delta_oi_peak_strike=_float(put_delta_peak[0].get("strike")) if put_delta_peak else None,
        atm_strike=atm_strike,
        atm_call_iv=_float(atm_call.get("iv")) if atm_call else None,
        atm_put_iv=_float(atm_put.get("iv")) if atm_put else None,
        atm_call_oi=_float(atm_call.get("oi")) if atm_call else None,
        atm_put_oi=_float(atm_put.get("oi")) if atm_put else None,
    )


def build_historical_snapshots(rows: Iterable[Mapping], underlying_spot_by_timestamp: Optional[Mapping[str, float]] = None) -> list[dict]:
    """Build snapshots chronologically without look-ahead.

    `rows` may contain boundary duplicates. Exact duplicates are removed. Each
    timestamp is processed once, and the previous timestamp's rows are the
    only source for ΔOI.
    """
    rows = _dedupe(rows)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[_timestamp_value(row.get("timestamp"))].append(row)

    result = []
    previous_rows = []
    for ts in sorted(grouped):
        spot = None
        if underlying_spot_by_timestamp:
            spot = underlying_spot_by_timestamp.get(ts)
        snapshot = build_snapshot(grouped[ts], timestamp=ts, spot=spot, previous_rows=previous_rows)
        result.append(snapshot.to_dict())
        previous_rows = grouped[ts]
    return result
