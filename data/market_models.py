from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class OptionQuote:
    strike: float
    option_type: str
    security_id: Optional[str]
    ltp: Optional[float]
    bid: Optional[float]
    ask: Optional[float]
    volume: Optional[int]
    oi: Optional[int]
    previous_oi: Optional[int]
    iv: Optional[float]
    delta: Optional[float]
    gamma: Optional[float]
    theta: Optional[float]
    vega: Optional[float]

    @property
    def spread(self) -> Optional[float]:
        if self.bid is None or self.ask is None:
            return None
        return round(max(self.ask - self.bid, 0), 4)

    @property
    def oi_change(self) -> Optional[int]:
        if self.oi is None or self.previous_oi is None:
            return None
        return self.oi - self.previous_oi


@dataclass
class OptionChainSnapshot:
    underlying: str
    underlying_ltp: float
    expiry: str
    options: List[OptionQuote] = field(default_factory=list)
    fetched_at: Optional[str] = None

    def by_type(self, option_type: str) -> List[OptionQuote]:
        return [o for o in self.options if o.option_type == option_type]


@dataclass
class MarketSnapshot:
    symbol: str
    exchange_segment: str
    security_id: str
    ltp: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = None
    volume: Optional[int] = None
    oi: Optional[int] = None
    fetched_at: Optional[str] = None
    source: str = "unknown"
    raw: Dict[str, Any] = field(default_factory=dict)
