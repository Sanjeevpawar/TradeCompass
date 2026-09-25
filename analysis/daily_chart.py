# analysis/daily_chart.py

def analyze_daily_chart(d):
    """
    DAILY chart analysis (SPOT – Daily timeframe)
    Acts as a SAFETY FILTER, not a trade trigger.
    Must NEVER crash.
    """

    if not d or not isinstance(d, dict):
        return {
            "trend": "unknown",
            "pattern": "unknown",
            "risk": "HIGH",
            "allowed_strategies": [],
            "instruction": "NO TRADE"
        }

    close = d.get("close")
    ema20 = d.get("ema20")
    ema50 = d.get("ema50")
    sma200 = d.get("sma200")

    high_20 = d.get("high_20")
    low_20 = d.get("low_20")

    volume_today = d.get("volume_today")
    volume_avg_20 = d.get("volume_avg_20")

    # -------------------------
    # If critical data missing → NO TRADE
    # -------------------------
    required = [close, ema20, ema50, sma200, high_20, low_20, volume_today, volume_avg_20]
    if any(v is None for v in required):
        return {
            "trend": "unknown",
            "pattern": "unknown",
            "risk": "HIGH",
            "allowed_strategies": [],
            "instruction": "NO TRADE"
        }

    # -------------------------
    # Trend detection
    # -------------------------
    if close > ema20 > ema50 > sma200:
        trend = "bullish"
    elif close < ema20 < ema50 < sma200:
        trend = "bearish"
    else:
        trend = "sideways"

    # -------------------------
    # Range detection
    # -------------------------
    is_range = (high_20 - low_20) <= 300

    # -------------------------
    # Volume check
    # -------------------------
    volume_state = (
        "expansion"
        if volume_today > volume_avg_20
        else "normal"
    )

    # -------------------------
    # Permissions logic
    # -------------------------
    if is_range and volume_state == "normal":
        return {
            "trend": trend,
            "pattern": "range",
            "risk": "LOW",
            "allowed_strategies": ["neutral_credit"],
            "instruction": "Option selling allowed"
        }

    if trend == "bullish":
        return {
            "trend": trend,
            "pattern": "bullish_continuation",
            "risk": "MEDIUM",
            "allowed_strategies": ["bullish_credit"],
            "instruction": "Avoid call selling"
        }

    if trend == "bearish":
        return {
            "trend": trend,
            "pattern": "bearish_continuation",
            "risk": "MEDIUM",
            "allowed_strategies": ["bearish_credit"],
            "instruction": "Avoid put selling"
        }

    return {
        "trend": trend,
        "pattern": "unclear",
        "risk": "HIGH",
        "allowed_strategies": [],
        "instruction": "NO TRADE"
    }
