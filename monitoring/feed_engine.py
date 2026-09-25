# monitoring/feed_engine.py

from datetime import datetime
from monitoring.feed_state import has_changed


def _now():
    return datetime.now().strftime("%H:%M")


def generate_feed(market_snapshot: dict):
    """
    Generates market intelligence feed safely
    """

    feed = []

    if not market_snapshot:
        return feed

    # -------------------------
    # OI SHIFT
    # -------------------------
    oi_shift = market_snapshot.get("oi_shift")
    resistance = market_snapshot.get("resistance")

    if oi_shift and has_changed("oi_shift", oi_shift):
        if oi_shift == "CALL_BUILDUP":
            feed.append({
                "time": _now(),
                "type": "OI",
                "severity": "CAUTION",
                "message": (
                    f"Call writers active near {resistance}. "
                    "Upside may be limited."
                )
            })

        elif oi_shift == "PUT_BUILDUP":
            feed.append({
                "time": _now(),
                "type": "OI",
                "severity": "INFO",
                "message": (
                    "Put writers are active. Downside looks protected."
                )
            })

    # -------------------------
    # SUPPORT MOVE
    # -------------------------
    support_move = market_snapshot.get("support_move")
    support = market_snapshot.get("support")

    if support_move and has_changed("support_move", support_move):
        if support_move == "UP":
            feed.append({
                "time": _now(),
                "type": "SUPPORT",
                "severity": "INFO",
                "message": (
                    f"Support has moved up to {support}. "
                    "Buyers are stepping in earlier."
                )
            })

        elif support_move == "DOWN":
            feed.append({
                "time": _now(),
                "type": "SUPPORT",
                "severity": "CAUTION",
                "message": (
                    f"Support is weakening near {support}. "
                    "Downside risk is increasing."
                )
            })

    # -------------------------
    # VOLATILITY
    # -------------------------
    volatility = market_snapshot.get("volatility")

    if volatility and has_changed("volatility", volatility):
        if volatility == "RISING":
            feed.append({
                "time": _now(),
                "type": "VOLATILITY",
                "severity": "CAUTION",
                "message": (
                    "Volatility is rising. Option prices may move fast."
                )
            })

        elif volatility == "FALLING":
            feed.append({
                "time": _now(),
                "type": "VOLATILITY",
                "severity": "INFO",
                "message": (
                    "Volatility is cooling down."
                )
            })

    # -------------------------
    # PREMIUM SPEED
    # -------------------------
    premium_speed = market_snapshot.get("premium_speed")

    if premium_speed and has_changed("premium_speed", premium_speed):
        if premium_speed == "FAST":
            feed.append({
                "time": _now(),
                "type": "PREMIUM",
                "severity": "CAUTION",
                "message": (
                    "Option premiums are rising fast. "
                    "Avoid aggressive entries."
                )
            })

    return feed
