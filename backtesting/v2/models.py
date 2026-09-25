from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HistoricalOptionBar:
    timestamp: str
    expiry: str
    strike: float
    option_type: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    iv: Optional[float] = None
    delta: Optional[float] = None
    theta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spot: Optional[float] = None
