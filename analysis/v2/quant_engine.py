from analysis.v2.indicators import calculate_indicators
from analysis.v2.market_structure import support_resistance, structure
from analysis.v2.regime import classify_regime
from analysis.v2.setups import detect_setups

def analyze_market(candles):
    if len(candles) < 30:
        return {"valid":False,"reason":f"Need at least 30 candles; received {len(candles)}"}
    ind=calculate_indicators(candles)
    struct=structure(candles)
    sr=support_resistance(candles)
    regime=classify_regime(ind,struct)
    setups=detect_setups(candles,ind,sr,struct,regime)
    return {"valid":True,"last_price":candles[-1].close,"timestamp":candles[-1].timestamp,"indicators":ind,"structure":struct,"levels":sr,"regime":regime,"setups":setups}
