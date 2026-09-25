from data.providers.mock_provider import MockMarketDataProvider
from production.chain import build_chain_evidence
from production.decision import evaluate_tradecompass
from production.risk import build_production_risk
from production.runtime import ProductionTradeCompassRuntime


def test_phase12_chain_has_no_pcr_standalone_trade_signal():
    provider = MockMarketDataProvider()
    chain = provider.get_option_chain("13", "IDX_I", "2026-09-24")
    evidence = build_chain_evidence(chain)
    assert "signal" not in evidence
    assert evidence["pcr"] is not None
    assert "pcr_change" in evidence


def test_phase12_risk_contains_no_quantity_or_capital():
    analysis = {
        "valid": True, "last_price": 26042,
        "levels": {"support": 25950, "resistance": 26200},
        "indicators": {"vwap": 26000, "atr_14": 50},
    }
    option = {"ltp": 100, "delta": .55, "option_type": "CE"}
    risk = build_production_risk(analysis, option, "CALL")
    assert "quantity" not in risk
    assert "capital" not in risk
    assert "risk" in risk and "reward" in risk and "risk_reward" in risk


def test_phase12_runtime_emits_single_production_decision():
    runtime = ProductionTradeCompassRuntime(provider=MockMarketDataProvider())
    result = runtime.snapshot()
    assert result["decision"] in {"BUY_CALL", "BUY_PUT", "WAIT"}
    assert "approaches" not in result
    assert result["execution_enabled"] is False
    assert result["live_mode"] == "READ_ONLY_PAPER_OBSERVATION"


def test_phase12_wait_reasons_are_controlled():
    provider = MockMarketDataProvider()
    candles = provider.get_intraday_candles("13", "IDX_I", "INDEX", 5, 1)
    chain = provider.get_option_chain("13", "IDX_I", "2026-09-24")
    result = evaluate_tradecompass(candles, chain)
    assert result["decision"] in {"BUY_CALL", "BUY_PUT", "WAIT"}
    if result["decision"] == "WAIT":
        assert result["wait_reason"] in {"DATA WAIT", "CONFIRMATION WAIT", "CONFLICT WAIT", "OPTION WAIT", "RISK WAIT"}
