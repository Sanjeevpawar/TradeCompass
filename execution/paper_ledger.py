"""Paper trade ledger.

V1 is intentionally in-memory.  The ledger records the complete decision
snapshot, entry, every monitoring snapshot, and final exit so the same data
can later feed analytics/backtesting validation.
"""

from copy import deepcopy
from datetime import datetime, timezone

PAPER_TRADES = []


def _now():
    return datetime.now(timezone.utc).isoformat()


def _find_trade(trade_id):
    return next((t for t in PAPER_TRADES if t["trade_id"] == trade_id), None)


def record_entry(decision):
    """Create one paper trade and return its id.

    A decision can only create one paper trade.  The full decision is frozen
    at entry so later market changes cannot rewrite the original thesis.
    """
    if decision.get("trade_id") is not None:
        existing = _find_trade(decision["trade_id"])
        if existing:
            return existing["trade_id"]

    trade_id = (max((t["trade_id"] for t in PAPER_TRADES), default=0) + 1)
    entry = {
        "trade_id": trade_id,
        "strategy": decision.get("strategy"),
        "action": decision.get("action"),
        "signal": decision.get("signal"),
        "legs": deepcopy(decision.get("paper_positions", [])),
        "decision_snapshot": deepcopy(decision),
        "entry_time": _now(),
        "status": "OPEN",
        "max_profit": decision.get("max_profit"),
        "max_loss": decision.get("max_loss"),
        "pnl_snapshots": [],
        "exit_time": None,
        "exit_reason": None,
        "realized_pnl": None,
    }
    PAPER_TRADES.append(entry)
    decision["trade_id"] = trade_id
    return trade_id


def record_pnl(trade_id, pnl, snapshot=None):
    trade = _find_trade(trade_id)
    if not trade or trade["status"] != "OPEN":
        return False
    item = {"time": _now(), "pnl": float(pnl)}
    if snapshot is not None:
        item["market_snapshot"] = deepcopy(snapshot)
    trade["pnl_snapshots"].append(item)
    return True


def record_exit(trade_id, pnl, reason):
    trade = _find_trade(trade_id)
    if not trade:
        return False
    if trade["status"] == "CLOSED":
        return True
    trade["status"] = "CLOSED"
    trade["exit_time"] = _now()
    trade["exit_reason"] = reason
    trade["realized_pnl"] = float(pnl)
    return True


def _calculate_trade_metrics(trade):
    snapshots = trade.get("pnl_snapshots", [])
    current_pnl = snapshots[-1]["pnl"] if snapshots else 0.0
    peak_pnl = max((s["pnl"] for s in snapshots), default=0.0)

    running_peak = 0.0
    max_drawdown = 0.0
    for snap in snapshots:
        running_peak = max(running_peak, snap["pnl"])
        max_drawdown = max(max_drawdown, running_peak - snap["pnl"])

    entry_time = datetime.fromisoformat(trade["entry_time"])
    end_time = datetime.fromisoformat(trade["exit_time"]) if trade["exit_time"] else datetime.now(timezone.utc)
    duration_minutes = int((end_time - entry_time).total_seconds() / 60)

    max_profit = trade.get("max_profit") or 0
    max_loss = trade.get("max_loss") or 0
    risk_reward = round(max_profit / max_loss, 2) if max_loss > 0 else None

    return {
        "current_pnl": current_pnl,
        "peak_pnl": peak_pnl,
        "max_drawdown": max_drawdown,
        "duration_minutes": duration_minutes,
        "risk_reward": risk_reward,
        "status_label": trade["status"],
    }


def get_all_trades():
    return [{**deepcopy(t), **_calculate_trade_metrics(t)} for t in PAPER_TRADES]


def get_trade_by_id(trade_id: int):
    trade = _find_trade(trade_id)
    if not trade:
        return None
    return {**deepcopy(trade), **_calculate_trade_metrics(trade)}


def clear_trades():
    """Test/dev helper; production persistence will replace the in-memory store."""
    PAPER_TRADES.clear()
