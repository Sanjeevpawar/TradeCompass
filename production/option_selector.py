from __future__ import annotations

from data.market_models import OptionChainSnapshot


def select_suggested_option(
    chain: OptionChainSnapshot,
    direction: str,
    *,
    min_delta: float = 0.45,
    max_delta: float = 0.65,
    target_delta: float = 0.55,
    max_premium: float = 500.0,
) -> dict | None:
    option_type = "CE" if direction == "CALL" else "PE"
    candidates = []
    for o in chain.by_type(option_type):
        if o.ltp is None or o.ltp <= 0 or o.delta is None:
            continue
        delta = abs(float(o.delta))
        if not min_delta <= delta <= max_delta:
            continue
        if float(o.ltp) > max_premium:
            continue
        if o.volume is not None and o.volume <= 0:
            continue
        candidates.append(o)
    if not candidates:
        return None

    # This is a deterministic selection rule, not a claim that one option is universally best.
    # Delta fit is primary; liquidity is only a tie-breaker.
    candidates.sort(key=lambda o: (abs(abs(o.delta) - target_delta), -(o.volume or 0)))
    selected = candidates[0]
    alternatives = []
    for o in candidates[1:4]:
        alternatives.append({
            "strike": o.strike,
            "option_type": o.option_type,
            "ltp": o.ltp,
            "delta": o.delta,
            "gamma": o.gamma,
            "theta": o.theta,
            "iv": o.iv,
            "volume": o.volume,
            "oi": o.oi,
            "expiry": chain.expiry,
        })
    return {
        "strike": selected.strike,
        "option_type": selected.option_type,
        "security_id": selected.security_id,
        "expiry": chain.expiry,
        "ltp": selected.ltp,
        "bid": selected.bid,
        "ask": selected.ask,
        "volume": selected.volume,
        "oi": selected.oi,
        "iv": selected.iv,
        "delta": selected.delta,
        "gamma": selected.gamma,
        "theta": selected.theta,
        "vega": selected.vega,
        "spread": selected.spread,
        "selection_basis": f"Delta within {min_delta:.2f}-{max_delta:.2f}; closest to configured reference {target_delta:.2f}; volume used only as tie-breaker",
        "alternatives": alternatives,
    }
