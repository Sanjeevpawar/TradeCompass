# strategy/strike_selector.py

def select_strikes(strategy_ctx, option_ctx):
    """
    Select strikes based on:
    - Chosen strategy
    - Option OI support / resistance

    Must NEVER crash.
    """

    if not strategy_ctx or not option_ctx:
        return {
            "status": "NO TRADE",
            "reason": "Missing strategy or option context"
        }

    strategy = strategy_ctx.get("strategy")

    # ---- NO TRADE ----
    if strategy == "NO TRADE" or not strategy:
        return {
            "status": "NO TRADE",
            "reason": "No safe strategy available"
        }

    support = option_ctx.get("support")
    resistance = option_ctx.get("resistance")

    # ---- CALL CREDIT SPREAD ----
    if strategy == "CALL CREDIT SPREAD":
        if resistance is None:
            return {
                "status": "NO TRADE",
                "reason": "Resistance unavailable for call spread"
            }

        sell = resistance
        buy = sell + 200

        return {
            "status": "OK",
            "type": "CALL CREDIT SPREAD",
            "sell_strike": sell,
            "buy_strike": buy,
            "risk": "Defined"
        }

    # ---- PUT CREDIT SPREAD ----
    if strategy == "PUT CREDIT SPREAD":
        if support is None:
            return {
                "status": "NO TRADE",
                "reason": "Support unavailable for put spread"
            }

        sell = support
        buy = sell - 200

        return {
            "status": "OK",
            "type": "PUT CREDIT SPREAD",
            "sell_strike": sell,
            "buy_strike": buy,
            "risk": "Defined"
        }

    # ---- IRON CONDOR ----
    if "IRON CONDOR" in strategy:
        if support is None or resistance is None:
            return {
                "status": "NO TRADE",
                "reason": "Support/Resistance unavailable for iron condor"
            }

        call_sell = resistance
        call_buy = call_sell + 300

        put_sell = support
        put_buy = put_sell - 300

        return {
            "status": "OK",
            "type": "IRON CONDOR (WIDE)",
            "call_sell": call_sell,
            "call_buy": call_buy,
            "put_sell": put_sell,
            "put_buy": put_buy,
            "risk": "Defined"
        }

    return {
        "status": "NO TRADE",
        "reason": "Unsupported strategy"
    }
