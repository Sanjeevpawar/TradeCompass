from __future__ import annotations

from data.market_models import OptionChainSnapshot, OptionQuote


def _safe_sum(values):
    vals = [float(v) for v in values if v is not None]
    return sum(vals) if vals else None


def _strike_step(chain: OptionChainSnapshot) -> float:
    strikes = sorted({float(o.strike) for o in chain.options})
    diffs = [b - a for a, b in zip(strikes, strikes[1:]) if b > a]
    return min(diffs) if diffs else 50.0


def _zone(strike: float | None, step: float) -> dict | None:
    if strike is None:
        return None
    return {"low": strike - step, "high": strike + step, "center": strike}


def _peak(options: list[OptionQuote]) -> OptionQuote | None:
    usable = [o for o in options if o.oi is not None]
    return max(usable, key=lambda o: float(o.oi)) if usable else None


def _buildup(option: OptionQuote | None) -> str:
    if option is None or option.oi_change is None or option.ltp is None:
        return "UNKNOWN"
    # Classification describes a price/OI relationship; it does not claim trader intent.
    previous = option.previous_oi
    if previous is None or previous == 0:
        return "UNKNOWN"
    if option.oi_change > 0 and option.ltp > 0:
        # Without a previous premium, do not invent a price-change classification.
        return "OI_INCREASED"
    if option.oi_change < 0:
        return "OI_DECREASED"
    return "UNCHANGED"


def build_chain_evidence(current: OptionChainSnapshot, previous: OptionChainSnapshot | None = None) -> dict:
    calls = current.by_type("CE")
    puts = current.by_type("PE")
    call_map = {float(o.strike): o for o in calls}
    put_map = {float(o.strike): o for o in puts}
    common = sorted(set(call_map) & set(put_map))

    call_oi = _safe_sum(call_map[s].oi for s in common)
    put_oi = _safe_sum(put_map[s].oi for s in common)
    pcr = put_oi / call_oi if call_oi else None

    prev_pcr = None
    pcr_change = None
    call_oi_change = _safe_sum(call_map[s].oi_change for s in common)
    put_oi_change = _safe_sum(put_map[s].oi_change for s in common)
    if previous is not None:
        pcalls = {float(o.strike): o for o in previous.by_type("CE")}
        pputs = {float(o.strike): o for o in previous.by_type("PE")}
        prev_common = sorted(set(pcalls) & set(pputs))
        pcoi = _safe_sum(pcalls[s].oi for s in prev_common)
        ppoi = _safe_sum(pputs[s].oi for s in prev_common)
        if pcoi:
            prev_pcr = ppoi / pcoi
            if pcr is not None:
                pcr_change = pcr - prev_pcr

    call_peak = _peak(calls)
    put_peak = _peak(puts)
    step = _strike_step(current)
    call_zone = _zone(float(call_peak.strike) if call_peak else None, step)
    put_zone = _zone(float(put_peak.strike) if put_peak else None, step)

    migration = "UNCHANGED"
    migration_details = None
    if previous is not None:
        pcall_peak = _peak(previous.by_type("CE"))
        pput_peak = _peak(previous.by_type("PE"))
        moves = []
        if pcall_peak and call_peak:
            delta = float(call_peak.strike) - float(pcall_peak.strike)
            moves.append(("CALL_RESISTANCE", delta))
        if pput_peak and put_peak:
            delta = float(put_peak.strike) - float(pput_peak.strike)
            moves.append(("PUT_SUPPORT", delta))
        meaningful = [m for m in moves if abs(m[1]) >= step]
        if meaningful:
            directions = {"HIGHER" if d > 0 else "LOWER" for _, d in meaningful}
            migration = next(iter(directions)) if len(directions) == 1 else "MIXED"
            migration_details = [{"zone": z, "strike_change": round(d, 2)} for z, d in meaningful]

    return {
        "data_quality": "COMPLETE" if common and set(call_map) == set(put_map) else "ASYMMETRIC_STRIKE_COVERAGE",
        "spot": current.underlying_ltp,
        "expiry": current.expiry,
        "call_open_interest": call_oi,
        "put_open_interest": put_oi,
        "change_in_call_open_interest": call_oi_change,
        "change_in_put_open_interest": put_oi_change,
        "pcr": pcr,
        "previous_pcr": prev_pcr,
        "pcr_change": pcr_change,
        "call_concentration_zone": call_zone,
        "put_concentration_zone": put_zone,
        "call_concentration_oi": call_peak.oi if call_peak else None,
        "put_concentration_oi": put_peak.oi if put_peak else None,
        "oi_migration": migration,
        "oi_migration_details": migration_details,
        "call_peak_buildup_state": _buildup(call_peak),
        "put_peak_buildup_state": _buildup(put_peak),
        "coverage_strikes": len(common),
    }
