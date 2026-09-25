"""Paper execution layer.

No broker order is ever sent from this module. It creates a virtual position
and records the entry in the ledger automatically.
"""

from copy import deepcopy
from execution.paper_ledger import record_entry


def open_paper_trade(decision):
    positions = []
    for leg in decision.get("legs", []):
        positions.append({
            "strike": leg["strike"],
            "instrument": leg["instrument"],
            "side": leg["side"],
            "entry_price": leg["entry_premium"],
            "quantity": leg.get("quantity", 1),
            "status": "OPEN",
        })

    decision["paper_positions"] = positions
    decision["execution_mode"] = "PAPER"
    decision["paper_entry_snapshot"] = deepcopy({
        "spot": decision.get("spot"),
        "support": decision.get("support"),
        "resistance": decision.get("resistance"),
        "strategy": decision.get("strategy"),
        "legs": decision.get("legs", []),
    })
    record_entry(decision)
    return decision
