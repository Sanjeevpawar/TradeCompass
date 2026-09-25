from datetime import datetime
from core.trade_state import TradeState

class TradeContext:
    def __init__(self, trade_id: str):
        self.trade_id = trade_id
        self.state = TradeState.INIT
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.data = {}

    def transition(self, new_state: TradeState):
        self.state = new_state
        self.updated_at = datetime.utcnow()
