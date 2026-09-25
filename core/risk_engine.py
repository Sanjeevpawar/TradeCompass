# core/risk_engine.py

LOT_SIZE = 50  # NIFTY


def calculate_iron_condor_risk(legs):
    """
    Calculate max profit and max loss for Iron Condor
    using STRIKE WIDTH (not premiums).
    """

    put_sell_strike = put_buy_strike = None
    call_sell_strike = call_buy_strike = None

    put_sell_premium = put_buy_premium = None
    call_sell_premium = call_buy_premium = None

    for leg in legs:
        if leg["instrument"] == "PUT" and leg["side"] == "SELL":
            put_sell_strike = leg["strike"]
            put_sell_premium = leg["entry_premium"]

        elif leg["instrument"] == "PUT" and leg["side"] == "BUY":
            put_buy_strike = leg["strike"]
            put_buy_premium = leg["entry_premium"]

        elif leg["instrument"] == "CALL" and leg["side"] == "SELL":
            call_sell_strike = leg["strike"]
            call_sell_premium = leg["entry_premium"]

        elif leg["instrument"] == "CALL" and leg["side"] == "BUY":
            call_buy_strike = leg["strike"]
            call_buy_premium = leg["entry_premium"]

    # ---- Net Credit ----
    net_credit = (
        (put_sell_premium - put_buy_premium) +
        (call_sell_premium - call_buy_premium)
    )

    # ---- Spread Widths (STRIKES) ----
    put_width = abs(put_sell_strike - put_buy_strike)
    call_width = abs(call_buy_strike - call_sell_strike)

    max_width = max(put_width, call_width)

    max_profit = net_credit * LOT_SIZE
    max_loss = (max_width - net_credit) * LOT_SIZE

    return {
        "max_profit": max_profit,
        "max_loss": max_loss
    }
