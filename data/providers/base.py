from abc import ABC, abstractmethod
from typing import List

from data.market_models import MarketSnapshot, OptionChainSnapshot
from data.candle_models import Candle


class MarketDataProvider(ABC):
    """Provider-neutral read-only market data contract."""

    @abstractmethod
    def get_market_snapshot(self, security_id: str, exchange_segment: str) -> MarketSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_intraday_candles(self, security_id: str, exchange_segment: str, instrument: str = "INDEX", interval: int = 5, days: int = 1) -> List[Candle]:
        raise NotImplementedError

    @abstractmethod
    def get_expiries(self, underlying_security_id: str, underlying_segment: str) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def get_option_chain(
        self, underlying_security_id: str, underlying_segment: str, expiry: str
    ) -> OptionChainSnapshot:
        raise NotImplementedError
