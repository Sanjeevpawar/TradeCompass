from __future__ import annotations

import os
from threading import Lock
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from data.providers.factory import get_market_data_provider
from production.decision import evaluate_tradecompass
from production.store import ProductionSignalStore
from production.data_quality import validate_snapshot_metadata

IST = ZoneInfo("Asia/Kolkata")


def _ts(value):
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone(IST)
    except (ValueError, TypeError):
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return (dt if dt.tzinfo else dt.replace(tzinfo=IST)).astimezone(IST)


def _completed(candles, interval):
    now = datetime.now(IST)
    return [c for c in candles if _ts(c.timestamp) + timedelta(minutes=interval) <= now]


class ProductionTradeCompassRuntime:
    """Phase 12 canonical read-only decision runtime.

    It evaluates only completed candles and produces one production decision.
    It does not place orders or calculate quantity/capital allocation.
    """

    def __init__(self, provider=None, store=None):
        self.provider = provider or get_market_data_provider()
        self.store = store or ProductionSignalStore(
            os.getenv(
                "TRADECOMPASS_PHASE12_DB",
                "data/live/tradecompass_phase12.db",
            )
        )
        self.security_id = os.getenv(
            "TRADECOMPASS_UNDERLYING_SECURITY_ID",
            "13",
        )
        self.segment = os.getenv(
            "TRADECOMPASS_UNDERLYING_SEGMENT",
            "IDX_I",
        )
        self.interval = int(
            os.getenv("TRADECOMPASS_LIVE_INTERVAL", "5")
        )
        self._last_candle = None
        self._previous_chain = None
        self._cached = None
        self._lock = Lock()

    def snapshot(self):
        with self._lock:
            candles = self.provider.get_intraday_candles(
                self.security_id,
                self.segment,
                "INDEX",
                self.interval,
                1,
            )

            candles = _completed(candles, self.interval)

            if len(candles) < 30:
                raise RuntimeError(
                    f"Need at least 30 completed candles; received {len(candles)}"
                )

            last = candles[-1]

            if last.timestamp == self._last_candle and self._cached is not None:
                return self._cached

            expiries = self.provider.get_expiries(
                self.security_id,
                self.segment,
            )

            if not expiries:
                raise RuntimeError(
                    "No active option expiry returned by provider"
                )

            chain = self.provider.get_option_chain(
                self.security_id,
                self.segment,
                expiries[0],
            )

            result = evaluate_tradecompass(
                candles,
                chain,
                self._previous_chain,
            )

            quality = validate_snapshot_metadata(
                last.timestamp,
                chain.fetched_at,
            )

            result["live_mode"] = "READ_ONLY_PAPER_OBSERVATION"
            result["execution_enabled"] = False
            result["provider"] = self.provider.__class__.__name__

            result["market"] = {
                "symbol": chain.underlying,
                "decision_price": last.close,
                "candle_close": last.close,
                "candle_timestamp": last.timestamp,
                "chain_spot": chain.underlying_ltp,
                "chain_fetched_at": chain.fetched_at,
            }

            result["data_quality"] = quality.as_dict()

            self.store.record_signal(result)

            self.store.record_event(
                result["signal_id"],
                "DECISION_CREATED",
                str(result.get("timestamp")),
                {
                    "decision": result["decision"],
                    "data_quality": quality.status,
                },
            )

            self._previous_chain = chain
            self._last_candle = last.timestamp
            self._cached = result

            return result

    def recent_signals(self, limit=50):
        return self.store.recent(limit)