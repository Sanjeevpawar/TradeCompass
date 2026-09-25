from data.providers.factory import get_market_data_provider


def get_v2_snapshot(underlying_security_id: str = "13", underlying_segment: str = "IDX_I") -> dict:
    provider = get_market_data_provider()
    market = provider.get_market_snapshot(underlying_security_id, underlying_segment)
    expiries = provider.get_expiries(underlying_security_id, underlying_segment)
    if not expiries:
        raise RuntimeError("No active option expiry returned by market-data provider")
    chain = provider.get_option_chain(underlying_security_id, underlying_segment, expiries[0])
    return {"market": market, "chain": chain, "provider": provider.__class__.__name__}


def get_quant_analysis(underlying_security_id: str = "13", underlying_segment: str = "IDX_I", interval: int = 5) -> dict:
    from analysis.v2.quant_engine import analyze_market
    provider = get_market_data_provider()
    candles = provider.get_intraday_candles(underlying_security_id, underlying_segment, "INDEX", interval, 1)
    result = analyze_market(candles)
    result["provider"] = provider.__class__.__name__
    result["candle_count"] = len(candles)
    result["interval_minutes"] = interval
    return result
