from enum import Enum

class TradeState(str, Enum):
    INIT = "INIT"
    DECISION_CREATED = "DECISION_CREATED"
    CONFIRMED = "CONFIRMED"
    ENTRY_READY = "ENTRY_READY"
    ENTERED = "ENTERED"
    MONITORING = "MONITORING"
    EXITED = "EXITED"
    FAILED = "FAILED"

ALLOWED_TRANSITIONS = {
    TradeState.INIT: [TradeState.DECISION_CREATED],

    TradeState.DECISION_CREATED: [
        TradeState.CONFIRMED,
        TradeState.FAILED
    ],

    TradeState.CONFIRMED: [
        TradeState.ENTRY_READY,
        TradeState.FAILED
    ],

    TradeState.ENTRY_READY: [
        TradeState.ENTERED,
        TradeState.FAILED
    ],

    TradeState.ENTERED: [
        TradeState.MONITORING,
        TradeState.EXITED
    ],

    TradeState.MONITORING: [
        TradeState.EXITED,
        TradeState.FAILED
    ],
}
