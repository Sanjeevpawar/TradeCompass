"""
Decision Builder
----------------
Responsible for constructing the final trade decision object.
Also normalizes strikes → legs so downstream engines are consistent.
"""

# -------------------------------------------------
# CONFIDENCE CALCULATION
# -------------------------------------------------
def calculate_confidence(daily_ctx, spot_ctx, option_ctx):
    score = 0
    total = 0

    total += 1
    if daily_ctx.get("trend") == "UP":
        score += 1

    total += 1
    if spot_ctx.get("zone") == "ATM":
        score += 1

    total += 1
    if option_ctx.get("pcr") and option_ctx.get("pcr") > 1:
        score += 1

    if total == 0:
        return 0.25

    return max(round(score / total, 2), 0.25)


# -------------------------------------------------
# REASONING BUILDER
# -------------------------------------------------
def build_reasoning(daily_ctx, spot_ctx, option_ctx):
    reasons = []

    if daily_ctx.get("trend") == "UP":
        reasons.append("Daily trend is bullish")
    elif daily_ctx.get("trend") == "DOWN":
        reasons.append("Daily trend is bearish")

    if option_ctx.get("pcr"):
        if option_ctx["pcr"] > 1:
            reasons.append("Put-Call Ratio indicates bullish bias")
        elif option_ctx["pcr"] < 0.8:
            reasons.append("Put-Call Ratio indicates bearish bias")

    return reasons or ["Market signals are mixed"]


# -------------------------------------------------
# RISK IDENTIFICATION
# -------------------------------------------------
def identify_risks(daily_ctx, option_ctx):
    risks = []

    if option_ctx.get("volatility") == "RISING":
        risks.append("HIGH_VOLATILITY")

    if option_ctx.get("market_state") == "dangerous":
        risks.append("UNSTABLE_MARKET")

    return risks or ["NORMAL_MARKET_RISK"]


# -------------------------------------------------
# 🧩 STRIKES → LEGS BUILDER
# -------------------------------------------------
def build_legs_from_strikes(strikes):
    """
    Convert strike structure into executable option legs.
    Compatible with risk_engine.
    """

    if not strikes or strikes.get("status") != "OK":
        return []

    legs = []

    if "call_sell" in strikes:
        legs.append({
            "strike": strikes["call_sell"],
            "instrument": "CALL",
            "side": "SELL"
        })

    if "call_buy" in strikes:
        legs.append({
            "strike": strikes["call_buy"],
            "instrument": "CALL",
            "side": "BUY"
        })

    if "put_sell" in strikes:
        legs.append({
            "strike": strikes["put_sell"],
            "instrument": "PUT",
            "side": "SELL"
        })

    if "put_buy" in strikes:
        legs.append({
            "strike": strikes["put_buy"],
            "instrument": "PUT",
            "side": "BUY"
        })

    return legs


# -------------------------------------------------
# MAIN DECISION BUILDER
# -------------------------------------------------
def build_decision(daily_ctx, spot_ctx, option_ctx, strategy_ctx, strike_ctx):
    confidence = calculate_confidence(daily_ctx, spot_ctx, option_ctx)
    reasoning = build_reasoning(daily_ctx, spot_ctx, option_ctx)
    risk_tags = identify_risks(daily_ctx, option_ctx)

    # 🔑 CRITICAL FIX:
    # strategy_selector returns "strategy", not "name"
    strategy = strategy_ctx.get("strategy") or "NO TRADE"

    action = "TRADE" if strategy != "NO TRADE" else "NO_TRADE"

    legs = build_legs_from_strikes(strike_ctx)

    decision = {
        "action": action,
        "strategy": strategy,
        "strikes": strike_ctx,
        "legs": legs,

        # Structure (filled in api/app.py)
        "support": None,
        "resistance": None,
        "spot": None,

        "status": "AWAITING_CONFIRMATION",
        "confidence": confidence,
        "reasoning": reasoning,
        "risk_tags": risk_tags,
    }

    return decision
