# monitoring/feed_adapter.py

def detect_gamma_risk(spot_ctx, option_ctx):
    """
    Detect high gamma risk zone (interpreted, not numeric)
    """
    if (
        option_ctx.get("premium_speed") == "FAST"
        and option_ctx.get("iv_trend") == "RISING"
        and spot_ctx.get("zone") == "ATM"
    ):
        return "HIGH"

    return None


def build_market_snapshot(daily_ctx, spot_ctx, option_ctx):
    """
    Convert analysis contexts into feed-friendly signals
    """

    snapshot = {}

    # -------------------------
    # OI SHIFT (from option chain)
    # -------------------------
    oi_bias = option_ctx.get("oi_bias")

    if oi_bias == "CALL":
        snapshot["oi_shift"] = "CALL_BUILDUP"
    elif oi_bias == "PUT":
        snapshot["oi_shift"] = "PUT_BUILDUP"

    # -------------------------
    # SUPPORT MOVEMENT (from spot)
    # -------------------------
    if spot_ctx.get("support_trend") == "UP":
        snapshot["support_move"] = "UP"
    elif spot_ctx.get("support_trend") == "DOWN":
        snapshot["support_move"] = "DOWN"

    # -------------------------
    # VOLATILITY (from option chain)
    # -------------------------
    if option_ctx.get("iv_trend") == "RISING":
        snapshot["volatility"] = "RISING"
    elif option_ctx.get("iv_trend") == "FALLING":
        snapshot["volatility"] = "FALLING"

    # -------------------------
    # PREMIUM SPEED (heuristic)
    # -------------------------
    if option_ctx.get("premium_speed") == "FAST":
        snapshot["premium_speed"] = "FAST"

    # -------------------------
    # PRICE LEVELS (STRUCTURE)
    # -------------------------
    snapshot["support"] = spot_ctx.get("support")
    snapshot["resistance"] = spot_ctx.get("resistance")

    # 🔑 LIVE SPOT PRICE (REQUIRED FOR MONITORING)
    snapshot["spot"] = spot_ctx.get("spot")

    # -------------------------
    # GAMMA RISK (interpreted)
    # -------------------------
    gamma_risk = detect_gamma_risk(spot_ctx, option_ctx)
    if gamma_risk:
        snapshot["gamma_risk"] = gamma_risk

    # ✅ DEBUG (TEMPORARY – REMOVE AFTER VERIFY)
    print("DEBUG SNAPSHOT:", snapshot)

    return snapshot
