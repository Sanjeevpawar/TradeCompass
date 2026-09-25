from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from analysis.v2.quant_engine import analyze_market
from strategy.v2.buying_rules import evaluate_buying_setups
from production.chain import build_chain_evidence
from production.option_selector import select_suggested_option
from production.risk import build_production_risk


def _technical_evidence(analysis: dict, primary: dict) -> dict:
    ind = analysis.get("indicators", {})
    ema_relation = None
    if all(ind.get(k) is not None for k in ("ema_5", "ema_20", "ema_50")):
        if ind["ema_5"] > ind["ema_20"] > ind["ema_50"]:
            ema_relation = "5 > 20 > 50"
        elif ind["ema_5"] < ind["ema_20"] < ind["ema_50"]:
            ema_relation = "5 < 20 < 50"
        else:
            ema_relation = "Mixed"
    spot = analysis.get("last_price")
    vwap = ind.get("vwap")
    return {
        "setup": primary.get("setup", "NONE"),
        "direction": primary.get("direction"),
        "strength": primary.get("strength", "NONE"),
        "ema_relationship": ema_relation,
        "vwap": vwap,
        "vwap_distance": round(float(spot) - float(vwap), 2) if spot is not None and vwap is not None else None,
        "volume_ratio": ind.get("volume_ratio"),
        "rsi": ind.get("rsi_14"),
        "regime": analysis.get("regime"),
        "structure": analysis.get("structure"),
        "support": analysis.get("levels", {}).get("support"),
        "resistance": analysis.get("levels", {}).get("resistance"),
        "reasons": primary.get("reasons", []),
        "warnings": primary.get("warnings", []),
    }


def _strength(primary: dict, chain_evidence: dict) -> str:
    base = primary.get("strength", "NONE")
    if base in ("STRONG", "HIGH"):
        return "HIGH"
    if base in ("MODERATE", "MEDIUM"):
        return "MEDIUM"
    return "LOW" if primary.get("direction") else "NONE"


def evaluate_tradecompass(candles, chain, previous_chain=None, *, min_rr=1.5, max_premium=500.0) -> dict:
    analysis = analyze_market(candles)
    if not analysis.get("valid"):
        return {"decision": "WAIT", "wait_reason": "DATA WAIT", "reason": analysis.get("reason", "Invalid market data")}

    setups = evaluate_buying_setups(analysis)
    primary = setups[0] if setups else {"signal": "WAIT", "direction": None, "setup": "NONE", "strength": "NONE", "reasons": []}
    technical = _technical_evidence(analysis, primary)
    chain_evidence = build_chain_evidence(chain, previous_chain)

    if chain_evidence["data_quality"] != "COMPLETE":
        return _base_wait(analysis, technical, chain_evidence, "DATA WAIT", "Option-chain coverage is incomplete")

    direction = primary.get("direction")
    if primary.get("signal") not in ("BUY_CALL", "BUY_PUT") or direction not in ("CALL", "PUT"):
        return _base_wait(analysis, technical, chain_evidence, "CONFIRMATION WAIT", "No confirmed directional technical setup")

    # Chain evidence confirms context but does not create a trade by itself.
    chain_direction = None
    if chain_evidence.get("pcr_change") is not None:
        if chain_evidence["pcr_change"] > 0 and chain_evidence.get("put_concentration_zone"):
            chain_direction = "CALL"
        elif chain_evidence["pcr_change"] < 0 and chain_evidence.get("call_concentration_zone"):
            chain_direction = "PUT"
    if chain_direction is not None and chain_direction != direction:
        return _base_wait(analysis, technical, chain_evidence, "CONFLICT WAIT", "Technical direction conflicts with current chain context")

    option = select_suggested_option(chain, direction, max_premium=max_premium)
    if option is None:
        return _base_wait(analysis, technical, chain_evidence, "OPTION WAIT", "No option met the configured selection rules")

    risk = build_production_risk(analysis, option, direction, min_rr=min_rr, max_premium=max_premium)
    if not risk["approved"]:
        return _base_wait(analysis, technical, chain_evidence, "RISK WAIT", "; ".join(risk["rejection_reasons"])) | {"risk": risk, "suggested_option": option}

    decision = "BUY_CALL" if direction == "CALL" else "BUY_PUT"
    reasons = list(technical.get("reasons", []))
    if chain_evidence.get("oi_migration") not in (None, "UNCHANGED"):
        reasons.append(f"Open-interest concentration migration: {chain_evidence['oi_migration']}")
    if chain_evidence.get("pcr") is not None:
        reasons.append(f"Put/Call open-interest ratio: {chain_evidence['pcr']:.2f}")
    return {
        "signal_id": f"TC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}",
        "timestamp": analysis.get("timestamp"),
        "symbol": chain.underlying,
        "decision": decision,
        "direction": direction,
        "setup": primary.get("setup", "NONE"),
        "strength": _strength(primary, chain_evidence),
        "spot": chain.underlying_ltp,
        "suggested_option": option,
        "risk": risk,
        "technical_evidence": technical,
        "chain_evidence": chain_evidence,
        "reasons": reasons,
        "wait_reason": None,
        "engine_version": "phase12-v1",
        "config_version": "phase12-v1",
    }


def _base_wait(analysis, technical, chain_evidence, reason, message):
    return {
        "signal_id": f"TC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}",
        "timestamp": analysis.get("timestamp"),
        "symbol": chain_evidence.get("underlying", "NIFTY"),
        "decision": "WAIT",
        "direction": None,
        "setup": technical.get("setup", "NONE"),
        "strength": technical.get("strength", "NONE"),
        "spot": analysis.get("last_price"),
        "suggested_option": None,
        "risk": {"approved": False, "rejection_reasons": []},
        "technical_evidence": technical,
        "chain_evidence": chain_evidence,
        "reasons": [message],
        "wait_reason": reason,
        "engine_version": "phase12-v1",
        "config_version": "phase12-v1",
    }
