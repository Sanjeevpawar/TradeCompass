from datetime import datetime
from monitoring.feed_state import can_emit


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def build_feed_item(feed_type, severity, message):
    return {
        "timestamp": now(),
        "type": feed_type,
        "severity": severity,
        "message": message
    }


def generate_intelligence_feed(market_context):
    """
    market_context = {
        "oi_shift": "CALL_BUILDING | None",
        "support_move": "UP | DOWN | None",
        "premium_speed": "FAST | None",
        "volatility": "RISING | FALLING | None",
        "range": "TIGHT | EXPANDING | None",
        "theta": "POSITIVE | NEGATIVE | None",
        "event": "NEAR | None"
    }
    """

    feed = []

    # -------------------------
    # OI SHIFT
    # -------------------------
    if market_context.get("oi_shift") == "CALL_BUILDING":
        msg = "Call OI is building near resistance. More traders are selling calls here."
        if can_emit("OI", msg):
            feed.append(build_feed_item(
                "OI",
                "CAUTION",
                msg
            ))

    # -------------------------
    # SUPPORT / RESISTANCE MOVE
    # -------------------------
    if market_context.get("support_move") == "UP":
        msg = "Support is moving higher. The market is holding well on dips."
        if can_emit("SUPPORT", msg):
            feed.append(build_feed_item(
                "SUPPORT",
                "INFO",
                msg
            ))

    if market_context.get("support_move") == "DOWN":
        msg = "Support is slipping lower. Downside risk is increasing."
        if can_emit("SUPPORT", msg):
            feed.append(build_feed_item(
                "SUPPORT",
                "CAUTION",
                msg
            ))

    # -------------------------
    # PREMIUM SPEED
    # -------------------------
    if market_context.get("premium_speed") == "FAST":
        msg = "Option premium is rising fast. This usually happens during sudden volatility."
        if can_emit("PREMIUM", msg):
            feed.append(build_feed_item(
                "PREMIUM",
                "CAUTION",
                msg
            ))

    # -------------------------
    # VOLATILITY REGIME
    # -------------------------
    if market_context.get("volatility") == "RISING":
        msg = "Volatility (IV) is increasing. Option prices may move faster."
        if can_emit("VOLATILITY", msg):
            feed.append(build_feed_item(
                "VOLATILITY",
                "CAUTION",
                msg
            ))

    if market_context.get("volatility") == "FALLING":
        msg = "Volatility is cooling down. Option prices may stabilise."
        if can_emit("VOLATILITY", msg):
            feed.append(build_feed_item(
                "VOLATILITY",
                "INFO",
                msg
            ))

    # -------------------------
    # RANGE BEHAVIOUR
    # -------------------------
    if market_context.get("range") == "TIGHT":
        msg = "Market is moving in a tight range. No strong move yet."
        if can_emit("RANGE", msg):
            feed.append(build_feed_item(
                "RANGE",
                "INFO",
                msg
            ))

    if market_context.get("range") == "EXPANDING":
        msg = "Market range is expanding. Bigger price moves are possible."
        if can_emit("RANGE", msg):
            feed.append(build_feed_item(
                "RANGE",
                "CAUTION",
                msg
            ))

    # -------------------------
    # THETA (TIME DECAY)
    # -------------------------
    if market_context.get("theta") == "POSITIVE":
        msg = "Theta is working in your favour. Time decay is helping option sellers."
        if can_emit("THETA", msg):
            feed.append(build_feed_item(
                "THETA",
                "INFO",
                msg
            ))

    if market_context.get("theta") == "NEGATIVE":
        msg = "Theta advantage is reducing. Market movement is increasing."
        if can_emit("THETA", msg):
            feed.append(build_feed_item(
                "THETA",
                "CAUTION",
                msg
            ))

    # -------------------------
    # EVENT RISK
    # -------------------------
    if market_context.get("event") == "NEAR":
        msg = "Event risk ahead. Important news or data release may increase volatility."
        if can_emit("EVENT", msg):
            feed.append(build_feed_item(
                "EVENT",
                "CAUTION",
                msg
            ))

    return feed
