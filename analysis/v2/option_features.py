from statistics import median

from data.market_models import OptionChainSnapshot, OptionQuote


def nearest_atm(chain: OptionChainSnapshot) -> float | None:
    if not chain.options:
        return None
    strikes = sorted({o.strike for o in chain.options})
    return min(strikes, key=lambda s: abs(s - chain.underlying_ltp))


def option_chain_features(chain: OptionChainSnapshot) -> dict:
    if not chain.options:
        return {"valid": False, "reason": "No option data"}

    calls = chain.by_type("CE")
    puts = chain.by_type("PE")
    call_oi = sum(o.oi or 0 for o in calls)
    put_oi = sum(o.oi or 0 for o in puts)
    pcr = round(put_oi / call_oi, 3) if call_oi else None
    atm = nearest_atm(chain)
    liquid = [o for o in chain.options if o.volume and o.volume > 0 and o.bid is not None and o.ask is not None]
    median_spread = median([o.spread for o in liquid if o.spread is not None]) if liquid else None
    return {
        "valid": True,
        "underlying": chain.underlying,
        "spot": chain.underlying_ltp,
        "expiry": chain.expiry,
        "atm_strike": atm,
        "pcr": pcr,
        "call_oi": call_oi,
        "put_oi": put_oi,
        "median_bid_ask_spread": median_spread,
        "option_count": len(chain.options),
    }


def select_liquid_candidates(chain: OptionChainSnapshot, option_type: str, min_delta: float = 0.45, max_delta: float = 0.65):
    candidates = []
    for option in chain.by_type(option_type):
        delta = abs(option.delta) if option.delta is not None else None
        if delta is None or not (min_delta <= delta <= max_delta):
            continue
        if option.ltp is None or option.bid is None or option.ask is None:
            continue
        if option.volume is not None and option.volume <= 0:
            continue
        candidates.append(option)
    return sorted(candidates, key=lambda o: (abs(abs(o.delta or 0) - 0.55), o.spread or 999))
