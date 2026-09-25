from data.providers.mock_provider import MockMarketDataProvider
from analysis.v2.quant_engine import analyze_market

def test_quant_engine_produces_indicators_and_regime():
    p=MockMarketDataProvider()
    candles=p.get_intraday_candles("13","IDX_I",interval=5)
    result=analyze_market(candles)
    assert result["valid"] is True
    assert result["indicators"]["ema_20"] is not None
    assert result["indicators"]["ema_50"] is not None
    assert result["indicators"]["rsi_14"] is not None
    assert result["indicators"]["vwap"] is not None
    assert result["regime"] in {"BULLISH_TREND","BEARISH_TREND","RANGE_BOUND","TRANSITION"}
    assert isinstance(result["setups"], list)

def test_quant_engine_rejects_insufficient_data():
    p=MockMarketDataProvider()
    candles=p.get_intraday_candles("13","IDX_I")[:10]
    result=analyze_market(candles)
    assert result["valid"] is False
