import os

from data.providers.base import MarketDataProvider
from data.providers.dhan_provider import DhanMarketDataProvider
from data.providers.mock_provider import MockMarketDataProvider


def get_market_data_provider() -> MarketDataProvider:
    provider = os.getenv("TRADECOMPASS_DATA_PROVIDER", "mock").lower()
    if provider == "dhan":
        return DhanMarketDataProvider()
    if provider == "mock":
        return MockMarketDataProvider()
    raise ValueError(f"Unsupported TRADECOMPASS_DATA_PROVIDER: {provider}")
