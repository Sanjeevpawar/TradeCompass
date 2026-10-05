from data.market_models import OptionChainSnapshot, OptionQuote
from data.providers.mock_provider import MockMarketDataProvider
from production.chain import build_chain_evidence
from production.decision import evaluate_tradecompass
from production.risk import build_production_risk
from production.runtime import ProductionTradeCompassRuntime


def _candles():
    provider = MockMarketDataProvider()
    return provider.get_intraday_candles(
        "13",
        "IDX_I",
        "INDEX",
        5,
        1,
    )


def _chain():
    provider = MockMarketDataProvider()
    return provider.get_option_chain(
        "13",
        "IDX_I",
        "2026-09-24",
    )


def _option(
    *,
    strike=26000,
    option_type="CE",
    ltp=100,
    delta=0.55,
    volume=5000,
    oi=5000,
    previous_oi=4500,
):
    return OptionQuote(
        strike=strike,
        option_type=option_type,
        security_id=f"{option_type}-{strike}",
        ltp=ltp,
        bid=ltp - 1,
        ask=ltp + 1,
        volume=volume,
        oi=oi,
        previous_oi=previous_oi,
        iv=18,
        delta=delta if option_type == "CE" else -delta,
        gamma=0.02,
        theta=-1,
        vega=0.1,
    )


def _complete_chain(
    *,
    underlying_ltp=26000,
    expiry="2026-09-24",
    options=None,
):
    if options is None:
        options = [
            _option(strike=25950, option_type="CE", ltp=90, delta=0.48),
            _option(strike=26000, option_type="CE", ltp=100, delta=0.55),
            _option(strike=26050, option_type="CE", ltp=110, delta=0.62),
            _option(strike=25950, option_type="PE", ltp=90, delta=0.48),
            _option(strike=26000, option_type="PE", ltp=100, delta=0.55),
            _option(strike=26050, option_type="PE", ltp=110, delta=0.62),
        ]

    return OptionChainSnapshot(
        "NIFTY",
        underlying_ltp,
        expiry,
        options,
    )


def _directional_analysis():
    return {
        "valid": True,
        "timestamp": "2026-09-16T10:00:00+00:00",
        "last_price": 26042,
        "indicators": {
            "ema_5": 26030,
            "ema_20": 26010,
            "ema_50": 25980,
            "vwap": 26000,
            "atr_14": 50,
            "volume_ratio": 1.5,
            "rsi_14": 62,
        },
        "levels": {
            "support": 25950,
            "resistance": 26200,
        },
        "regime": "TRENDING",
        "structure": "BULLISH",
    }


def test_phase12_chain_has_no_pcr_standalone_trade_signal():
    provider = MockMarketDataProvider()
    chain = provider.get_option_chain(
        "13",
        "IDX_I",
        "2026-09-24",
    )

    evidence = build_chain_evidence(chain)

    assert "signal" not in evidence
    assert evidence["pcr"] is not None
    assert "pcr_change" in evidence


def test_phase12_risk_contains_no_quantity_or_capital():
    analysis = {
        "valid": True,
        "last_price": 26042,
        "levels": {
            "support": 25950,
            "resistance": 26200,
        },
        "indicators": {
            "vwap": 26000,
            "atr_14": 50,
        },
    }

    option = {
        "ltp": 100,
        "delta": 0.55,
        "option_type": "CE",
    }

    risk = build_production_risk(
        analysis,
        option,
        "CALL",
    )

    assert "quantity" not in risk
    assert "capital" not in risk
    assert "risk" in risk
    assert "reward" in risk
    assert "risk_reward" in risk


def test_phase12_runtime_emits_single_production_decision():
    runtime = ProductionTradeCompassRuntime(
        provider=MockMarketDataProvider()
    )

    result = runtime.snapshot()

    assert result["decision"] in {
        "BUY_CALL",
        "BUY_PUT",
        "WAIT",
    }
    assert "approaches" not in result
    assert result["execution_enabled"] is False
    assert result["live_mode"] == "READ_ONLY_PAPER_OBSERVATION"


def test_phase12_wait_reasons_are_controlled():
    result = evaluate_tradecompass(
        _candles(),
        _chain(),
    )

    assert result["decision"] in {
        "BUY_CALL",
        "BUY_PUT",
        "WAIT",
    }

    if result["decision"] == "WAIT":
        assert result["wait_reason"] in {
            "DATA WAIT",
            "CONFIRMATION WAIT",
            "CONFLICT WAIT",
            "OPTION WAIT",
            "RISK WAIT",
        }


def test_decision_invalid_market_data_returns_data_wait(monkeypatch):
    monkeypatch.setattr(
        "production.decision.analyze_market",
        lambda candles: {
            "valid": False,
            "reason": "Invalid market data",
        },
    )

    result = evaluate_tradecompass(
        _candles(),
        _chain(),
    )

    assert result["decision"] == "WAIT"
    assert result["wait_reason"] == "DATA WAIT"
    assert result["reason"] == "Invalid market data"


def test_decision_incomplete_chain_returns_data_wait(monkeypatch):
    monkeypatch.setattr(
        "production.decision.analyze_market",
        lambda candles: _directional_analysis(),
    )

    monkeypatch.setattr(
        "production.decision.evaluate_buying_setups",
        lambda analysis: [
            {
                "signal": "BUY_CALL",
                "direction": "CALL",
                "setup": "TREND_CONTINUATION",
                "strength": "STRONG",
                "reasons": ["Bullish trend"],
                "warnings": [],
            }
        ],
    )

    incomplete_chain = _complete_chain(
        options=[
            _option(strike=26000, option_type="CE"),
            _option(strike=26050, option_type="CE"),
            _option(strike=26000, option_type="PE"),
        ]
    )

    result = evaluate_tradecompass(
        _candles(),
        incomplete_chain,
    )

    assert result["decision"] == "WAIT"
    assert result["wait_reason"] == "DATA WAIT"
    assert result["chain_evidence"]["data_quality"] == "ASYMMETRIC_STRIKE_COVERAGE"


def test_decision_without_directional_setup_returns_confirmation_wait(monkeypatch):
    monkeypatch.setattr(
        "production.decision.analyze_market",
        lambda candles: _directional_analysis(),
    )

    monkeypatch.setattr(
        "production.decision.evaluate_buying_setups",
        lambda analysis: [
            {
                "signal": "WAIT",
                "direction": None,
                "setup": "NONE",
                "strength": "NONE",
                "reasons": [],
                "warnings": [],
            }
        ],
    )

    result = evaluate_tradecompass(
        _candles(),
        _complete_chain(),
    )

    assert result["decision"] == "WAIT"
    assert result["wait_reason"] == "CONFIRMATION WAIT"
    assert result["suggested_option"] is None


def test_decision_conflicting_chain_context_returns_conflict_wait(monkeypatch):
    monkeypatch.setattr(
        "production.decision.analyze_market",
        lambda candles: _directional_analysis(),
    )

    monkeypatch.setattr(
        "production.decision.evaluate_buying_setups",
        lambda analysis: [
            {
                "signal": "BUY_CALL",
                "direction": "CALL",
                "setup": "TREND_CONTINUATION",
                "strength": "STRONG",
                "reasons": ["Bullish trend"],
                "warnings": [],
            }
        ],
    )

    # Current chain:
    # - Strong call OI concentration
    # - Lower total PCR than the previous snapshot
    #
    # The production decision engine interprets:
    #   pcr_change < 0 + call concentration
    # as PUT chain context.
    current = _complete_chain(
        options=[
            _option(
                strike=25950,
                option_type="CE",
                oi=12000,
                previous_oi=1000,
            ),
            _option(
                strike=26000,
                option_type="CE",
                oi=12000,
                previous_oi=1000,
            ),
            _option(
                strike=26050,
                option_type="CE",
                oi=12000,
                previous_oi=1000,
            ),
            _option(
                strike=25950,
                option_type="PE",
                oi=1000,
                previous_oi=1000,
            ),
            _option(
                strike=26000,
                option_type="PE",
                oi=1000,
                previous_oi=1000,
            ),
            _option(
                strike=26050,
                option_type="PE",
                oi=1000,
                previous_oi=1000,
            ),
        ]
    )

    previous = _complete_chain(
        options=[
            _option(
                strike=25950,
                option_type="CE",
                oi=1000,
                previous_oi=1000,
            ),
            _option(
                strike=26000,
                option_type="CE",
                oi=1000,
                previous_oi=1000,
            ),
            _option(
                strike=26050,
                option_type="CE",
                oi=1000,
                previous_oi=1000,
            ),
            _option(
                strike=25950,
                option_type="PE",
                oi=12000,
                previous_oi=1000,
            ),
            _option(
                strike=26000,
                option_type="PE",
                oi=12000,
                previous_oi=1000,
            ),
            _option(
                strike=26050,
                option_type="PE",
                oi=12000,
                previous_oi=1000,
            ),
        ]
    )

    result = evaluate_tradecompass(
        _candles(),
        current,
        previous,
    )

    assert result["decision"] == "WAIT"
    assert result["wait_reason"] == "CONFLICT WAIT"


def test_decision_without_qualifying_option_returns_option_wait(monkeypatch):
    monkeypatch.setattr(
        "production.decision.analyze_market",
        lambda candles: _directional_analysis(),
    )

    monkeypatch.setattr(
        "production.decision.evaluate_buying_setups",
        lambda analysis: [
            {
                "signal": "BUY_CALL",
                "direction": "CALL",
                "setup": "TREND_CONTINUATION",
                "strength": "STRONG",
                "reasons": ["Bullish trend"],
                "warnings": [],
            }
        ],
    )

    monkeypatch.setattr(
        "production.decision.select_suggested_option",
        lambda *args, **kwargs: None,
    )

    result = evaluate_tradecompass(
        _candles(),
        _complete_chain(),
    )

    assert result["decision"] == "WAIT"
    assert result["wait_reason"] == "OPTION WAIT"
    assert result["suggested_option"] is None


def test_decision_rejected_risk_returns_risk_wait(monkeypatch):
    monkeypatch.setattr(
        "production.decision.analyze_market",
        lambda candles: _directional_analysis(),
    )

    monkeypatch.setattr(
        "production.decision.evaluate_buying_setups",
        lambda analysis: [
            {
                "signal": "BUY_CALL",
                "direction": "CALL",
                "setup": "TREND_CONTINUATION",
                "strength": "STRONG",
                "reasons": ["Bullish trend"],
                "warnings": [],
            }
        ],
    )

    selected = {
        "strike": 26000,
        "option_type": "CE",
        "ltp": 100,
        "delta": 0.55,
    }

    monkeypatch.setattr(
        "production.decision.select_suggested_option",
        lambda *args, **kwargs: selected,
    )

    monkeypatch.setattr(
        "production.decision.build_production_risk",
        lambda *args, **kwargs: {
            "approved": False,
            "rejection_reasons": ["Risk/reward below minimum"],
        },
    )

    result = evaluate_tradecompass(
        _candles(),
        _complete_chain(),
    )

    assert result["decision"] == "WAIT"
    assert result["wait_reason"] == "RISK WAIT"
    assert result["suggested_option"] == selected
    assert result["risk"]["approved"] is False


def test_decision_approved_call_returns_buy_call(monkeypatch):
    monkeypatch.setattr(
        "production.decision.analyze_market",
        lambda candles: _directional_analysis(),
    )

    monkeypatch.setattr(
        "production.decision.evaluate_buying_setups",
        lambda analysis: [
            {
                "signal": "BUY_CALL",
                "direction": "CALL",
                "setup": "TREND_CONTINUATION",
                "strength": "STRONG",
                "reasons": ["Bullish trend"],
                "warnings": [],
            }
        ],
    )

    selected = {
        "strike": 26000,
        "option_type": "CE",
        "ltp": 100,
        "delta": 0.55,
    }

    risk = {
        "approved": True,
        "risk": 50,
        "reward": 100,
        "risk_reward": 2.0,
    }

    monkeypatch.setattr(
        "production.decision.select_suggested_option",
        lambda *args, **kwargs: selected,
    )

    monkeypatch.setattr(
        "production.decision.build_production_risk",
        lambda *args, **kwargs: risk,
    )

    result = evaluate_tradecompass(
        _candles(),
        _complete_chain(),
    )

    assert result["decision"] == "BUY_CALL"
    assert result["direction"] == "CALL"
    assert result["suggested_option"] == selected
    assert result["risk"] == risk
    assert result["wait_reason"] is None
    assert result["strength"] == "HIGH"


def test_decision_approved_put_returns_buy_put(monkeypatch):
    monkeypatch.setattr(
        "production.decision.analyze_market",
        lambda candles: _directional_analysis(),
    )

    monkeypatch.setattr(
        "production.decision.evaluate_buying_setups",
        lambda analysis: [
            {
                "signal": "BUY_PUT",
                "direction": "PUT",
                "setup": "TREND_REVERSAL",
                "strength": "MODERATE",
                "reasons": ["Bearish reversal"],
                "warnings": [],
            }
        ],
    )

    selected = {
        "strike": 26000,
        "option_type": "PE",
        "ltp": 100,
        "delta": -0.55,
    }

    risk = {
        "approved": True,
        "risk": 40,
        "reward": 80,
        "risk_reward": 2.0,
    }

    monkeypatch.setattr(
        "production.decision.select_suggested_option",
        lambda *args, **kwargs: selected,
    )

    monkeypatch.setattr(
        "production.decision.build_production_risk",
        lambda *args, **kwargs: risk,
    )

    result = evaluate_tradecompass(
        _candles(),
        _complete_chain(),
    )

    assert result["decision"] == "BUY_PUT"
    assert result["direction"] == "PUT"
    assert result["suggested_option"] == selected
    assert result["risk"] == risk
    assert result["wait_reason"] is None
    assert result["strength"] == "MEDIUM"