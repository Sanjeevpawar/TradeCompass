from fastapi import HTTPException
from core.trade_state import ALLOWED_TRANSITIONS, TradeState

def assert_transition(current: TradeState, next_state: TradeState):
    allowed = ALLOWED_TRANSITIONS.get(current, [])

    if next_state not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {current} → {next_state}"
        )
