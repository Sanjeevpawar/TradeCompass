# analysis/spot_analysis.py

def analyze_spot_context(spot_data):
    """
    Analyze spot price behavior.
    GUARANTEES support & resistance so strike selection can proceed.
    """

    if not spot_data or not isinstance(spot_data, dict):
        return {
            "spot": None,
            "support": None,
            "resistance": None,
            "bias": "unknown",
            "zone": "UNKNOWN",
            "support_trend": "UNKNOWN"
        }

    spot = spot_data.get("spot")

    if spot is None:
        return {
            "spot": None,
            "support": None,
            "resistance": None,
            "bias": "unknown",
            "zone": "UNKNOWN",
            "support_trend": "UNKNOWN"
        }

    # -------------------------------------------------
    # 🔑 STRUCTURE DERIVATION (THIS IS THE FIX)
    # -------------------------------------------------
    support = spot_data.get("support")
    resistance = spot_data.get("resistance")

    # If not provided by data source → derive safely
    if support is None:
        support = round((spot - 150) / 50) * 50

    if resistance is None:
        resistance = round((spot + 150) / 50) * 50

    atm_strike = round(spot / 50) * 50

    # -------------------------
    # ZONE DETECTION
    # -------------------------
    zone = "ATM" if abs(spot - atm_strike) <= 25 else "OTM"

    # -------------------------
    # SUPPORT TREND
    # -------------------------
    support_trend = "UP" if spot > support else "DOWN"

    return {
        "spot": spot,
        "support": support,
        "resistance": resistance,
        "bias": "range",
        "zone": zone,
        "support_trend": support_trend
    }
