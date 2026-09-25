from analysis.v2.option_features import select_liquid_candidates
from data.market_models import OptionChainSnapshot, OptionQuote


def select_buying_option(chain: OptionChainSnapshot, direction: str, min_delta: float = 0.45, max_delta: float = 0.65) -> dict | None:
    option_type = "CE" if direction == "CALL" else "PE"
    candidates = select_liquid_candidates(chain, option_type, min_delta, max_delta)
    if not candidates:
        return None
    # Prefer Delta near 0.55, then tighter spread, then higher volume.
    def key(o: OptionQuote):
        delta_distance = abs(abs(o.delta or 0) - 0.55)
        spread_pct = (o.spread / o.ltp) if o.spread is not None and o.ltp else 999
        return (delta_distance, spread_pct, -(o.volume or 0))
    selected = sorted(candidates, key=key)[0]
    return {
        "strike": selected.strike,
        "option_type": selected.option_type,
        "security_id": selected.security_id,
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
        "expiry": chain.expiry,
    }
