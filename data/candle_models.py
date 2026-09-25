from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Candle:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    oi: Optional[int] = None
