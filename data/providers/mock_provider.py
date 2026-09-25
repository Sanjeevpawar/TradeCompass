from datetime import datetime, timezone
from typing import List

from data.market_models import MarketSnapshot, OptionChainSnapshot, OptionQuote
from data.candle_models import Candle
from datetime import timedelta
from data.providers.base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic provider for local development and tests."""

    def get_market_snapshot(self, security_id: str, exchange_segment: str) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="NIFTY",
            exchange_segment=exchange_segment,
            security_id=str(security_id),
            ltp=26042.0,
            open=25980.0,
            high=26120.0,
            low=25960.0,
            previous_close=26010.0,
            volume=1_250_000,
            oi=None,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="mock",
        )

    def get_intraday_candles(self, security_id: str, exchange_segment: str, instrument: str = "INDEX", interval: int = 5, days: int = 1) -> List[Candle]:
        # Deterministic rising-then-pullback series for local development.
        start = datetime(2026, 9, 16, 9, 15, tzinfo=timezone.utc)
        prices = [25980 + i*2.2 + (4 if i%7 in (3,4) else -2 if i%11==0 else 0) for i in range(80)]
        candles = []
        for i, close in enumerate(prices):
            prev = prices[i-1] if i else close - 8
            o = prev
            h = max(o, close) + 5
            l = min(o, close) - 4
            candles.append(Candle((start + timedelta(minutes=interval*i)).isoformat(), o, h, l, close, 100000 + i*2500))
        return candles

    def get_expiries(self, underlying_security_id: str, underlying_segment: str) -> List[str]:
        return ["2026-09-24"]

    def get_option_chain(self, underlying_security_id: str, underlying_segment: str, expiry: str) -> OptionChainSnapshot:
        spot = 26042.0
        strikes = [25800, 25900, 26000, 26100, 26200, 26300, 26400]
        options = []
        for strike in strikes:
            distance = abs(strike - spot)
            call_delta = max(0.15, min(0.85, 0.55 - (strike - spot) / 900))
            put_delta = call_delta - 1
            call_ltp = max(25, 210 - distance * 0.38)
            put_ltp = max(25, 210 - distance * 0.38)
            for option_type, delta, ltp in (("CE", call_delta, call_ltp), ("PE", put_delta, put_ltp)):
                oi = 100000 + int(distance * 800) + (50000 if option_type == "CE" and strike >= 26200 else 0)
                options.append(OptionQuote(
                    strike=float(strike), option_type=option_type, security_id=None,
                    ltp=round(ltp, 2), bid=round(ltp - 0.5, 2), ask=round(ltp + 0.5, 2),
                    volume=250000, oi=oi, previous_oi=oi - 12000,
                    iv=14.5 + distance / 3000,
                    delta=round(delta, 4), gamma=0.0012, theta=-8.5, vega=11.0,
                ))
        return OptionChainSnapshot(
            underlying="NIFTY", underlying_ltp=spot, expiry=expiry,
            options=options, fetched_at=datetime.now(timezone.utc).isoformat()
        )
