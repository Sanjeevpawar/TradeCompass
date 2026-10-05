"""Read-only DhanHQ market-data adapter.

Authentication is handled by DhanAuthManager using TOTP.
No order-placement methods are intentionally exposed here.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import List

from data.candle_models import Candle
from data.market_models import (
    MarketSnapshot,
    OptionChainSnapshot,
    OptionQuote,
)
from data.providers.base import MarketDataProvider
from data.providers.dhan_auth import (
    DhanAuthenticationError,
    DhanAuthManager,
)


class DhanAPIError(RuntimeError):
    pass


class DhanMarketDataProvider(MarketDataProvider):
    BASE_URL = "https://api.dhan.co/v2"

    def __init__(
        self,
        client_id: str | None = None,
        access_token: str | None = None,
    ):
        self.auth = DhanAuthManager(
            client_id=client_id,
        )

        self.client_id = self.auth.client_id

        # Optional compatibility path for callers that explicitly
        # provide an access token. Normal production usage should
        # use DhanAuthManager.
        self._explicit_access_token = access_token

    def _get_access_token(self) -> str:
        """Return an explicit token when supplied, otherwise use managed auth."""

        if self._explicit_access_token:
            return self._explicit_access_token

        try:
            return self.auth.get_access_token()

        except DhanAuthenticationError as exc:
            raise DhanAPIError(
                f"Dhan authentication failed: {exc}"
            ) from exc

    def _post(
        self,
        path: str,
        payload: dict,
    ) -> dict:
        access_token = self._get_access_token()

        body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            f"{self.BASE_URL}{path}",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "access-token": access_token,
                "client-id": self.client_id,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=10,
            ) as response:
                data = json.loads(
                    response.read().decode("utf-8")
                )

        except Exception as exc:
            raise DhanAPIError(
                f"Dhan request failed: {exc}"
            ) from exc

        if data.get("status") not in (
            None,
            "success",
        ):
            raise DhanAPIError(str(data))

        return data

    def get_market_snapshot(
        self,
        security_id: str,
        exchange_segment: str,
    ) -> MarketSnapshot:

        data = self._post(
            "/marketfeed/ohlc",
            {
                exchange_segment: [
                    int(security_id)
                ]
            },
        )

        node = (
            data.get("data", {})
            .get(exchange_segment, {})
            .get(str(security_id), {})
        )

        ohlc = node.get("ohlc", {})

        if not node.get("last_price"):
            raise DhanAPIError(
                "Dhan returned no LTP for the requested instrument"
            )

        return MarketSnapshot(
            symbol=str(
                node.get("trading_symbol")
                or security_id
            ),
            exchange_segment=exchange_segment,
            security_id=str(security_id),
            ltp=float(node["last_price"]),
            open=ohlc.get("open"),
            high=ohlc.get("high"),
            low=ohlc.get("low"),
            previous_close=ohlc.get("close"),
            fetched_at=datetime.now(
                timezone.utc
            ).isoformat(),
            source="dhan",
            raw=node,
        )

    def get_intraday_candles(
        self,
        security_id: str,
        exchange_segment: str,
        instrument: str = "INDEX",
        interval: int = 5,
        days: int = 1,
    ) -> List[Candle]:

        if interval not in (
            1,
            5,
            15,
            25,
            60,
        ):
            raise ValueError(
                "Dhan intraday interval must be "
                "1, 5, 15, 25 or 60 minutes"
            )

        from datetime import timedelta

        end = datetime.now()

        start = end - timedelta(
            days=max(
                1,
                min(days, 90),
            )
        )

        payload = {
            "securityId": str(security_id),
            "exchangeSegment": exchange_segment,
            "instrument": instrument,
            "interval": str(interval),
            "oi": False,
            "fromDate": start.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "toDate": end.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

        data = self._post(
            "/charts/intraday",
            payload,
        )

        root = data.get(
            "data",
            data,
        )

        ts = root.get(
            "timestamp",
            [],
        )

        opens = root.get(
            "open",
            [],
        )

        highs = root.get(
            "high",
            [],
        )

        lows = root.get(
            "low",
            [],
        )

        closes = root.get(
            "close",
            [],
        )

        volumes = root.get(
            "volume",
            [],
        )

        oi = root.get(
            "oi",
            [],
        )

        n = min(
            len(opens),
            len(highs),
            len(lows),
            len(closes),
            len(ts),
        )

        return [
            Candle(
                str(ts[i]),
                float(opens[i]),
                float(highs[i]),
                float(lows[i]),
                float(closes[i]),
                (
                    int(volumes[i])
                    if i < len(volumes)
                    else 0
                ),
                (
                    int(oi[i])
                    if i < len(oi)
                    else None
                ),
            )
            for i in range(n)
        ]

    def get_expiries(
        self,
        underlying_security_id: str,
        underlying_segment: str,
    ) -> List[str]:

        data = self._post(
            "/optionchain/expirylist",
            {
                "UnderlyingScrip": int(
                    underlying_security_id
                ),
                "UnderlyingSeg": underlying_segment,
            },
        )

        return data.get(
            "data",
            [],
        )

    def get_option_chain(
        self,
        underlying_security_id: str,
        underlying_segment: str,
        expiry: str,
    ) -> OptionChainSnapshot:

        data = self._post(
            "/optionchain",
            {
                "UnderlyingScrip": int(
                    underlying_security_id
                ),
                "UnderlyingSeg": underlying_segment,
                "Expiry": expiry,
            },
        )

        root = data.get(
            "data",
            {},
        )

        options = []

        for strike_text, pair in root.get(
            "oc",
            {},
        ).items():

            strike = float(
                strike_text
            )

            for option_type, node in (
                (
                    "CE",
                    pair.get("ce"),
                ),
                (
                    "PE",
                    pair.get("pe"),
                ),
            ):

                if not node:
                    continue

                greeks = node.get(
                    "greeks",
                    {},
                )

                options.append(
                    OptionQuote(
                        strike=strike,
                        option_type=option_type,
                        security_id=(
                            str(
                                node.get(
                                    "security_id"
                                )
                            )
                            if node.get(
                                "security_id"
                            )
                            is not None
                            else None
                        ),
                        ltp=node.get(
                            "last_price"
                        ),
                        bid=node.get(
                            "top_bid_price"
                        ),
                        ask=node.get(
                            "top_ask_price"
                        ),
                        volume=node.get(
                            "volume"
                        ),
                        oi=node.get(
                            "oi"
                        ),
                        previous_oi=node.get(
                            "previous_oi"
                        ),
                        iv=node.get(
                            "implied_volatility"
                        ),
                        delta=greeks.get(
                            "delta"
                        ),
                        gamma=greeks.get(
                            "gamma"
                        ),
                        theta=greeks.get(
                            "theta"
                        ),
                        vega=greeks.get(
                            "vega"
                        ),
                    )
                )

        return OptionChainSnapshot(
            underlying="NIFTY",
            underlying_ltp=float(
                root.get(
                    "last_price"
                )
            ),
            expiry=expiry,
            options=options,
            fetched_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )