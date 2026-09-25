# ui/user_messages.py

def build_user_trade_message(strategy_ctx, strike_ctx):
    """
    Build final user-facing message
    (Dashboard / App / Telegram friendly)
    """

    if strategy_ctx["strategy"] == "NO TRADE":
        return (
            "ACTION     : NO TRADE\n"
            "REASON     : Market conditions are not safe today\n"
            "NEXT STEP  : Wait for next update"
        )

    lines = []
    lines.append("ACTION      : CONSIDER TRADE")
    lines.append(f"STRATEGY    : {strike_ctx['type']}")
    lines.append("")
    lines.append("TRADE SETUP")

    if strike_ctx["type"] == "IRON CONDOR (WIDE)":
        lines.append(f"• Sell {strike_ctx['put_sell']} PUT")
        lines.append(f"• Buy  {strike_ctx['put_buy']} PUT")
        lines.append(f"• Sell {strike_ctx['call_sell']} CALL")
        lines.append(f"• Buy  {strike_ctx['call_buy']} CALL")
    else:
        lines.append(f"• Sell {strike_ctx['sell_strike']}")
        lines.append(f"• Buy  {strike_ctx['buy_strike']}")

    lines.append("")
    lines.append("RISK        : Defined (Limited loss)")
    lines.append("NEXT STEP  : Do you want to take this trade? (YES / NO)")

    return "\n".join(lines)
