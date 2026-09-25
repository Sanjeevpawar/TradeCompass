from core.pnl_engine import calculate_pnl
from execution.paper_ledger import record_pnl, record_exit


# -----------------------------
# CONFIG
# -----------------------------
PROFIT_LOCK_THRESHOLD = 0.5
TRAILING_EXIT_RATIO   = 0.7
HARD_STOP_RATIO       = 0.7
TARGET_RATIO          = 0.8


def explain_status(action, total_pnl, decision):
    """
    Convert machine state into trader-friendly explanation.
    """

    max_profit = decision.get("max_profit", 1)
    max_loss = decision.get("max_loss", 1)

    pnl_pct = round((total_pnl / max_profit) * 100, 1) if max_profit else 0

    if action == "HOLD":
        return {
            "headline": "Trade is stable",
            "plain_english": "Price is moving inside the expected range. Option decay is working in your favour.",
            "trader_note": "Theta positive. No threat from either side yet.",
            "what_to_do": "Hold position. No action required."
        }

    if action == "ALERT":
        return {
            "headline": "Position needs attention",
            "plain_english": "Price is moving closer to one of your sold strikes.",
            "trader_note": "Range is getting tested. Gamma risk increasing.",
            "what_to_do": "Watch closely. Be ready to adjust or exit if momentum continues."
        }

    if action == "EXIT":
        if total_pnl > 0:
            return {
                "headline": "Profit booked",
                "plain_english": "Target or trailing profit level reached. Trade exited safely.",
                "trader_note": f"Captured ~{pnl_pct}% of max profit.",
                "what_to_do": "No action. Look for next setup."
            }
        else:
            return {
                "headline": "Loss controlled",
                "plain_english": "Stop loss triggered to prevent further damage.",
                "trader_note": "Risk management worked. Capital protected.",
                "what_to_do": "Stay disciplined. Avoid revenge trades."
            }

    return {
        "headline": "Status update",
        "plain_english": "Monitoring trade conditions.",
        "trader_note": "",
        "what_to_do": ""
    }


def monitor_trade(decision, market_snapshot):
    """
    Monitor ACTIVE trade using stateful trailing logic
    """

    if decision.get("status") != "ACTIVE":
        return {
            "action": "NO_MONITORING",
            "message": "Trade is not active yet."
        }

    pnl_result = calculate_pnl(decision, market_snapshot["option_ltp"])
    total_pnl = pnl_result["total_pnl"]

    max_profit = decision.get("max_profit", market_snapshot.get("max_profit"))
    max_loss   = decision.get("max_loss", market_snapshot.get("max_loss"))

    # A zero/negative reward is invalid for threshold-based monitoring.
    # Keep the position observable rather than immediately exiting because
    # mock/partial pricing cannot establish a valid target.
    thresholds_valid = (max_profit is not None and max_profit > 0 and
                        max_loss is not None and max_loss > 0)

    if "peak_pnl" not in decision:
        decision["peak_pnl"] = total_pnl

    if "locked_profit" not in decision:
        decision["locked_profit"] = 0

    if total_pnl > decision["peak_pnl"]:
        decision["peak_pnl"] = total_pnl

    action = "HOLD"

    if thresholds_valid and decision["peak_pnl"] >= PROFIT_LOCK_THRESHOLD * max_profit and decision["locked_profit"] == 0:
        decision["locked_profit"] = decision["peak_pnl"]

    if thresholds_valid and total_pnl <= -HARD_STOP_RATIO * max_loss:
        decision["status"] = "EXITED"
        action = "EXIT"

    elif thresholds_valid and total_pnl >= TARGET_RATIO * max_profit:
        decision["status"] = "EXITED"
        action = "EXIT"

    elif decision["locked_profit"] > 0:
        trailing_floor = decision["locked_profit"] * TRAILING_EXIT_RATIO
        if total_pnl <= trailing_floor:
            decision["status"] = "EXITED"
            action = "EXIT"

    elif thresholds_valid and abs(total_pnl) >= 0.4 * max_profit:
        action = "ALERT"

    trade_id = decision.get("trade_id")
    if trade_id is not None:
        record_pnl(trade_id, total_pnl, market_snapshot)
    explanation = explain_status(action, total_pnl, decision)

    if trade_id is not None and action == "EXIT":
        record_exit(trade_id, total_pnl, "TARGET" if total_pnl > 0 else "STOP")

    return {
        "action": action,
        "pnl": total_pnl,
        "peak_pnl": decision["peak_pnl"],
        "locked_profit": decision["locked_profit"],
        "explanation": explanation,
        "legs": pnl_result["legs"]
    }
