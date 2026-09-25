from risk.v2.risk_engine import RiskConfig, build_risk_decision


def base_analysis():
    return {
        "valid": True,
        "last_price": 26042,
        "indicators": {"vwap": 25980, "atr_14": 55},
        "levels": {"support": 26000, "resistance": 26100},
    }


def option():
    return {"option_type": "CE", "ltp": 150, "delta": 0.55, "spread": 1.0}


def test_risk_engine_calculates_one_or_more_lots_when_budget_allows():
    result = build_risk_decision(base_analysis(), option(), RiskConfig(capital=1_000_000, risk_per_trade_pct=1.0, lot_size=65))
    assert result["approved"] is True
    assert result["lots"] >= 1
    assert result["stop"] < result["entry"] < result["target"]
    assert result["rr"] >= 1.5


def test_risk_engine_rejects_expensive_option():
    expensive = {**option(), "ltp": 600}
    result = build_risk_decision(base_analysis(), expensive, RiskConfig(capital=1_000_000, max_premium=500))
    assert result["approved"] is False
    assert any("maximum" in r for r in result["rejection_reasons"])


def test_risk_engine_rejects_poor_delta():
    poor_delta = {**option(), "delta": 0.2}
    result = build_risk_decision(base_analysis(), poor_delta, RiskConfig(capital=1_000_000))
    assert result["approved"] is False
    assert any("Delta" in r for r in result["rejection_reasons"])


from risk.v2.risk_engine import calculate_trade_risk


def test_shared_trade_risk_matches_live_risk_decision():
    analysis = base_analysis()
    opt = option()
    cfg = RiskConfig(capital=1_000_000, risk_per_trade_pct=1.0, lot_size=65)
    decision = build_risk_decision(analysis, opt, cfg)
    shared = calculate_trade_risk(
        analysis, opt["ltp"], opt["delta"], opt["option_type"],
        capital=cfg.capital, risk_per_trade_pct=cfg.risk_per_trade_pct,
        min_rr=cfg.min_rr, lot_size=cfg.lot_size,
    )
    assert decision["approved"] is True
    assert shared["valid"] is True
    assert decision["stop"] == round(shared["premium_stop"], 2)
    assert decision["target"] == round(shared["target"], 2)
    assert decision["quantity"] == shared["quantity"]
    assert decision["lots"] == shared["lots"]


def test_shared_trade_risk_uses_nearest_meaningful_vwap_invalidation():
    analysis = {
        "valid": True, "last_price": 26042,
        "indicators": {"vwap": 26020, "atr_14": 55},
        "levels": {"support": 25900, "resistance": 26100},
    }
    result = calculate_trade_risk(
        analysis, 150, 0.55, "CALL", capital=1_000_000,
        risk_per_trade_pct=1.0, lot_size=65,
    )
    assert result["underlying_stop"] == 26020
