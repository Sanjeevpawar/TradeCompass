def detect_setups(candles, ind, sr, struct, regime):
    if not candles: return []
    last=candles[-1]; setups=[]
    vr=ind.get("volume_ratio") or 0; vwap=ind.get("vwap")
    resistance=sr.get("resistance"); support=sr.get("support")
    prior=candles[-21:-1] if len(candles) > 21 else candles[:-1]
    prior_resistance=max((c.high for c in prior), default=None)
    prior_support=min((c.low for c in prior), default=None)
    if regime == "BULLISH_TREND" and vwap and last.close > vwap:
        setups.append({"name":"TREND_CONTINUATION","direction":"CALL","conditions":["bullish regime","price above VWAP","bullish structure"]})
    if prior_resistance and last.close > prior_resistance and vr >= 1.2:
        setups.append({"name":"BREAKOUT","direction":"CALL","conditions":["resistance broken","volume expansion"]})
    if regime == "BEARISH_TREND" and vwap and last.close < vwap:
        setups.append({"name":"TREND_CONTINUATION","direction":"PUT","conditions":["bearish regime","price below VWAP","bearish structure"]})
    if prior_support and last.close < prior_support and vr >= 1.2:
        setups.append({"name":"BREAKDOWN","direction":"PUT","conditions":["support broken","volume expansion"]})
    return setups
