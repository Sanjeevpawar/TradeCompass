# strategy/strategy_selector.py

def select_strategy(daily_ctx, spot_ctx, option_ctx):
    """
    Decide the safest strategy based on:
    - Daily environment
    - Spot location
    - Option seller positioning
    """

    # ---- Hard blocks ----
    if daily_ctx["risk"] == "HIGH":
        return {
            "strategy": "NO TRADE",
            "reason": "Daily chart indicates high risk environment"
        }

    if option_ctx["market_state"] == "dangerous":
        return {
            "strategy": "NO TRADE",
            "reason": "High volatility – option selling unsafe"
        }

    # ---- Core logic ----

    # 1. CAPPED market (call writers dominant)
    if option_ctx["market_state"] == "capped":
        # Daily bullish → avoid call selling, prefer neutral
        if daily_ctx["pattern"] == "bullish_continuation":
            return {
                "strategy": "IRON CONDOR (wide)",
                "reason": "Upside capped but higher-timeframe trend is bullish"
            }

        # Otherwise bearish / neutral
        return {
            "strategy": "CALL CREDIT SPREAD",
            "reason": "Call writers capping the upside"
        }

    # 2. SUPPORTED market (put writers dominant)
    if option_ctx["market_state"] == "supported":
        return {
            "strategy": "PUT CREDIT SPREAD",
            "reason": "Put writers supporting the downside"
        }

    # 3. RANGE market
    if option_ctx["market_state"] == "range":
        # Spot in middle → best for neutral selling
        if spot_ctx["bias"] == "range":
            return {
                "strategy": "IRON CONDOR",
                "reason": "Market in range with balanced option positioning"
            }

        # Spot near support/resistance → directional credit
        if spot_ctx["bias"] == "bullish":
            return {
                "strategy": "PUT CREDIT SPREAD",
                "reason": "Range market with price near support"
            }

        if spot_ctx["bias"] == "bearish":
            return {
                "strategy": "CALL CREDIT SPREAD",
                "reason": "Range market with price near resistance"
            }

    # ---- Fallback ----
    return {
        "strategy": "NO TRADE",
        "reason": "No clear low-risk setup available"
    }
