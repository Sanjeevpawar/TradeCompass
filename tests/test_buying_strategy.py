from data.providers.mock_provider import MockMarketDataProvider
from data.market_models import OptionChainSnapshot, OptionQuote
from analysis.v2.quant_engine import analyze_market
from strategy.v2.buying_rules import evaluate_buying_setups
from strategy.v2.option_buying import select_buying_option


def test_buying_strategy_returns_signal_or_wait_without_execution():
    p = MockMarketDataProvider()
    candles = p.get_intraday_candles("13", "IDX_I", interval=5)
    result = analyze_market(candles)
    signals = evaluate_buying_setups(result)
    assert signals[0]["signal"] in {"BUY_CALL", "BUY_PUT", "WAIT"}
    assert "score" in signals[0]


def test_option_selector_prefers_delta_near_target():
    chain = OptionChainSnapshot("NIFTY", 26000, "2026-09-24", [
        OptionQuote(25950,"PE","1",100,99,101,1000,5000,4000,18,0.42,0.02,-1,0.1),
        OptionQuote(26000,"PE","2",120,119,121,1200,6000,5000,18,0.55,0.02,-1,0.1),
        OptionQuote(26050,"PE","3",90,89,91,2000,7000,6000,18,0.63,0.02,-1,0.1),
    ])
    selected = select_buying_option(chain, "PUT")
    assert selected["strike"] == 26000
