# core/entry_engine.py

from core.risk_engine import calculate_iron_condor_risk
from execution.paper_trade_engine import open_paper_trade


def apply_entry_premiums(decision, premiums):
    """
    Validate and attach entry premiums.
    Activates trade ONLY when entry contract is fully satisfied.
    """

    # ---------------------------------
    # 1️⃣ STATE VALIDATION
    # ---------------------------------
    if not decision:
        return {
            "status": "ERROR",
            "reason": "No active trade found",
            "next_step": "GET_NEW_DECISION"
        }

    if decision.get("status") != "AWAITING_ENTRY_PREMIUMS":
        return {
            "status": "INVALID_STATE",
            "reason": "Trade is not waiting for entry premiums",
            "current_status": decision.get("status"),
            "next_step": "CHECK_TRADE_STATUS"
        }

    # ---------------------------------
    # 2️⃣ PAYLOAD VALIDATION
    # ---------------------------------
    if not premiums or not isinstance(premiums, dict):
        decision["status"] = "ENTRY_ERROR"
        decision["reason"] = "Premiums payload is empty or invalid"
        decision["next_step"] = "COLLECT_ENTRY_PREMIUMS"
        return decision

    try:
        normalized_premiums = {
            int(strike): float(premium)
            for strike, premium in premiums.items()
        }
    except (ValueError, TypeError):
        decision["status"] = "ENTRY_ERROR"
        decision["reason"] = "Strike prices and premiums must be numeric"
        decision["next_step"] = "COLLECT_ENTRY_PREMIUMS"
        return decision

    # ---------------------------------
    # 3️⃣ LEG VALIDATION
    # ---------------------------------
    legs = decision.get("legs")

    if not legs or not isinstance(legs, list):
        decision["status"] = "ENTRY_ERROR"
        decision["reason"] = "No valid option legs found for entry"
        decision["next_step"] = "RECALCULATE_DECISION"
        return decision

    for leg in legs:
        strike = leg.get("strike")

        if strike not in normalized_premiums:
            decision["status"] = "ENTRY_ERROR"
            decision["reason"] = f"Missing premium for strike {strike}"
            decision["next_step"] = "COLLECT_ENTRY_PREMIUMS"
            return decision

        premium = normalized_premiums[strike]

        if premium <= 0:
            decision["status"] = "ENTRY_ERROR"
            decision["reason"] = f"Invalid premium for strike {strike}"
            decision["next_step"] = "COLLECT_ENTRY_PREMIUMS"
            return decision

        leg["entry_premium"] = premium

    # ---------------------------------
    # 4️⃣ RISK CALCULATION
    # ---------------------------------
    if decision.get("strikes", {}).get("type") == "IRON CONDOR (WIDE)":
        risk = calculate_iron_condor_risk(legs)
        decision["max_profit"] = risk.get("max_profit")
        decision["max_loss"] = risk.get("max_loss")

    if decision.get("max_profit") is None or decision.get("max_loss") is None:
        decision["status"] = "ENTRY_ERROR"
        decision["reason"] = "Risk could not be calculated"
        decision["next_step"] = "RECALCULATE_DECISION"
        return decision

    # ---------------------------------
    # 5️⃣ STRUCTURAL VALIDATION
    # ---------------------------------
    support = decision.get("support")
    resistance = decision.get("resistance")

    if support is None or resistance is None:
        decision["status"] = "ENTRY_ERROR"
        decision["reason"] = "Support/Resistance missing. Cannot activate trade."
        decision["next_step"] = "RECALCULATE_DECISION"
        return decision

    # ---------------------------------
    # 6️⃣ FREEZE TRADE THESIS
    # ---------------------------------
    decision["trade_reason"] = {
        "type": "RANGE",
        "support": support,
        "resistance": resistance,
        "buffer": 30
    }

    # ---------------------------------
    # 7️⃣ ACTIVATE TRADE
    # ---------------------------------
    decision["status"] = "ACTIVE"
    decision["next_step"] = "START_MONITORING"

    # ---------------------------------
    # 8️⃣ PAPER TRADE ACTIVATION (CORRECTED)
    # ---------------------------------
    decision = open_paper_trade(decision)
    decision["execution_mode"] = "PAPER"

    return decision
