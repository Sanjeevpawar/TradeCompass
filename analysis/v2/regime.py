def classify_regime(ind, struct):
    e5,e20,e50=ind.get("ema_5"),ind.get("ema_20"),ind.get("ema_50")
    rsi=ind.get("rsi_14"); vr=ind.get("volume_ratio")
    trend=struct.get("trend")
    if e5 and e20 and e50 and e5>e20>e50 and trend in ("BULLISH","MIXED_BULLISH"):
        return "BULLISH_TREND"
    if e5 and e20 and e50 and e5<e20<e50 and trend in ("BEARISH","MIXED_BEARISH"):
        return "BEARISH_TREND"
    if trend == "RANGE" or (rsi is not None and 45 <= rsi <= 55): return "RANGE_BOUND"
    return "TRANSITION"
