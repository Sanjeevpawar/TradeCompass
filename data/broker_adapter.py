"""
Broker Adapter (READ-ONLY)
--------------------------
Responsible ONLY for fetching live market prices.
NO order placement logic allowed here.
"""

# Toggle to switch between live & mock
USE_LIVE_BROKER = False


def get_live_option_ltp(legs):
    """
    Fetch live option LTPs for given legs.
    legs: list of {strike, instrument, side}
    """

    if not USE_LIVE_BROKER:
        # ---- MOCK FALLBACK (SAFE DEFAULT) ----
        return {
            f"{leg['instrument']}_{leg['strike']}": 50
            for leg in legs
        }

    # -----------------------------
    # 🔌 BROKER API INTEGRATION
    # -----------------------------
    # Example placeholder (Zerodha, Dhan, Angel, etc.)
    # Replace this section ONLY when broker credentials are ready

    live_prices = {}

    for leg in legs:
        symbol = f"NIFTY{leg['strike']}{leg['instrument'][0]}"
        # price = broker_api.get_ltp(symbol)
        price = 50  # placeholder
        live_prices[f"{leg['instrument']}_{leg['strike']}"] = price

    return live_prices
