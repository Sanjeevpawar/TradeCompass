# monitoring/trailing_engine.py

def get_profit_lock(max_profit, profit_pct):
    """
    Returns locked profit amount based on profit achieved
    """

    if profit_pct >= 85:
        return 0.70 * max_profit
    elif profit_pct >= 70:
        return 0.50 * max_profit
    elif profit_pct >= 50:
        return 0.25 * max_profit
    elif profit_pct >= 30:
        return 0.10 * max_profit
    else:
        return 0


def evaluate_trailing_exit(max_profit, max_loss, current_pnl):
    """
    Decide HOLD / EXIT based on trailing stop logic
    """

    if max_profit <= 0 or max_loss <= 0:
        return {
            "action": "HOLD",
            "reason": "Invalid risk parameters"
        }

    profit_pct = (current_pnl / max_profit) * 100
    loss_pct = (abs(current_pnl) / max_loss) * 100 if current_pnl < 0 else 0

    locked_profit = get_profit_lock(max_profit, profit_pct)

    # 🔴 EXIT CONDITIONS
    if loss_pct >= 30:
        return {
            "action": "EXIT",
            "reason": "Max loss threshold breached",
            "loss_pct": round(loss_pct, 2)
        }

    if current_pnl < locked_profit:
        return {
            "action": "EXIT",
            "reason": "Trailing profit stop hit",
            "locked_profit": round(locked_profit, 2)
        }

    return {
        "action": "HOLD",
        "reason": "Trade within trailing limits",
        "profit_pct": round(profit_pct, 2),
        "locked_profit": round(locked_profit, 2)
    }
