# analysis/option_chain.py

def analyze_option_chain(option_data):
    """
    Analyze option chain behavior.
    Must NEVER crash.
    """

    if not option_data or not isinstance(option_data, dict):
        return {
            "pcr": None,
            "max_pain": None,
            "support": None,
            "resistance": None,
            "market_state": "neutral",
            "instruction": "Insufficient option data",
            "oi_bias": "NEUTRAL",
            "premium_speed": "UNKNOWN",
            "iv_trend": "UNKNOWN"
        }

    pcr = option_data.get("pcr")
    max_pain = option_data.get("max_pain")
    support = option_data.get("support")
    resistance = option_data.get("resistance")

    # -------------------------
    # MARKET STATE (SAFE)
    # -------------------------
    if pcr is None:
        market_state = "neutral"
        instruction = "PCR unavailable"
        oi_bias = "NEUTRAL"
    elif pcr < 0.7:
        market_state = "capped"
        instruction = "Upside capped by call writers"
        oi_bias = "CALL"
    elif pcr > 1.2:
        market_state = "supported"
        instruction = "Downside protected by put writers"
        oi_bias = "PUT"
    else:
        market_state = "neutral"
        instruction = "No strong OI bias"
        oi_bias = "NEUTRAL"

    # -------------------------
    # PREMIUM SPEED (SAFE)
    # -------------------------
    premium_change_pct = option_data.get("premium_change_pct")
    if premium_change_pct is not None and premium_change_pct > 8:
        premium_speed = "FAST"
    else:
        premium_speed = "NORMAL"

    # -------------------------
    # IV TREND (SAFE)
    # -------------------------
    iv_trend = option_data.get("iv_trend", "STABLE")

    return {
        "pcr": pcr,
        "max_pain": max_pain,
        "support": support,
        "resistance": resistance,
        "market_state": market_state,
        "instruction": instruction,
        "oi_bias": oi_bias,
        "premium_speed": premium_speed,
        "iv_trend": iv_trend
    }
