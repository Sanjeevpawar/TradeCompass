from __future__ import annotations

from data.market_models import OptionChainSnapshot


def _peak_oi(options):
    usable = [o for o in options if o.oi is not None]
    return max(usable, key=lambda o: float(o.oi)) if usable else None


def _sum_oi(options):
    vals = [float(o.oi) for o in options if o.oi is not None]
    return sum(vals) if vals else None


def _sum_oi_change(options):
    vals = [float(o.oi_change) for o in options if o.oi_change is not None]
    return sum(vals) if vals else None


def build_live_chain_context(chain: OptionChainSnapshot) -> dict:
    """Create deterministic live chain evidence from the current broker snapshot.

    This is intentionally descriptive. OI is not labelled as 'writers'.
    """
    calls = chain.by_type("CE")
    puts = chain.by_type("PE")
    call_by_strike = {o.strike: o for o in calls}
    put_by_strike = {o.strike: o for o in puts}
    common = sorted(set(call_by_strike) & set(put_by_strike))
    common_calls = [call_by_strike[s] for s in common]
    common_puts = [put_by_strike[s] for s in common]

    call_oi = _sum_oi(common_calls)
    put_oi = _sum_oi(common_puts)
    pcr = put_oi / call_oi if call_oi else None

    call_peak = _peak_oi(calls)
    put_peak = _peak_oi(puts)
    call_delta = _sum_oi_change(calls)
    put_delta = _sum_oi_change(puts)

    atm = min(common or [o.strike for o in chain.options], key=lambda s: abs(s - chain.underlying_ltp)) if chain.options else None
    atm_call = call_by_strike.get(atm)
    atm_put = put_by_strike.get(atm)

    bullish = []
    bearish = []
    if pcr is not None:
        if pcr >= 1.0:
            bullish.append("Put/Call Interest >= 1.00")
        elif pcr <= 0.85:
            bearish.append("Put/Call Interest <= 0.85")

    if put_delta is not None and call_delta is not None:
        if put_delta > call_delta:
            bullish.append("Put OI Change is stronger than Call OI Change")
        elif call_delta > put_delta:
            bearish.append("Call OI Change is stronger than Put OI Change")

    if put_peak and put_peak.strike < chain.underlying_ltp:
        bullish.append("Largest Put OI is below NIFTY")
    if call_peak and call_peak.strike > chain.underlying_ltp:
        bearish.append("Largest Call OI is above NIFTY")

    if len(bullish) >= 2 and len(bullish) > len(bearish):
        signal = "BUY_CALL"
    elif len(bearish) >= 2 and len(bearish) > len(bullish):
        signal = "BUY_PUT"
    else:
        signal = "WAIT"

    score = max(len(bullish), len(bearish)) * 25
    return {
        "signal": signal,
        "evidence_score": min(score, 100),
        "spot": chain.underlying_ltp,
        "expiry": chain.expiry,
        "call_oi": call_oi,
        "put_oi": put_oi,
        "pcr": pcr,
        "call_oi_change": call_delta,
        "put_oi_change": put_delta,
        "call_oi_peak_strike": call_peak.strike if call_peak else None,
        "call_oi_peak": call_peak.oi if call_peak else None,
        "call_resistance_distance": (call_peak.strike - chain.underlying_ltp) if call_peak else None,
        "put_oi_peak_strike": put_peak.strike if put_peak else None,
        "put_oi_peak": put_peak.oi if put_peak else None,
        "put_support_distance": (chain.underlying_ltp - put_peak.strike) if put_peak else None,
        "atm_strike": atm,
        "atm_call_iv": atm_call.iv if atm_call else None,
        "atm_put_iv": atm_put.iv if atm_put else None,
        "bullish_evidence": bullish,
        "bearish_evidence": bearish,
        "coverage_complete": set(call_by_strike) == set(put_by_strike),
        "data_quality": "COMPLETE" if set(call_by_strike) == set(put_by_strike) else "ASYMMETRIC_STRIKE_COVERAGE",
    }
