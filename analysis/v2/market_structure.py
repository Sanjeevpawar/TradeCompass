from data.candle_models import Candle

def support_resistance(candles, lookback=20):
    window=candles[-lookback:] if candles else []
    if not window: return {"support":None,"resistance":None}
    return {"support":min(c.low for c in window), "resistance":max(c.high for c in window)}

def structure(candles, lookback=5):
    if len(candles) < lookback*2: return {"trend":"UNKNOWN","higher_high":False,"higher_low":False,"lower_high":False,"lower_low":False}
    a,b=candles[-lookback*2:-lookback], candles[-lookback:]
    ah=max(c.high for c in a); al=min(c.low for c in a); bh=max(c.high for c in b); bl=min(c.low for c in b)
    hh,hl,lh,ll=bh>ah, bl>al, bh<ah, bl<al
    if hh and hl: trend="BULLISH"
    elif lh and ll: trend="BEARISH"
    elif candles[-1].close > candles[-lookback*2].close: trend="MIXED_BULLISH"
    elif candles[-1].close < candles[-lookback*2].close: trend="MIXED_BEARISH"
    else: trend="RANGE"
    return {"trend":trend,"higher_high":hh,"higher_low":hl,"lower_high":lh,"lower_low":ll}
