from pathlib import Path

import pytest

from data.providers.mock_provider import MockMarketDataProvider
from production.runtime import ProductionTradeCompassRuntime
from production.store import ProductionSignalStore


class CountingMockProvider(MockMarketDataProvider):
    """Mock provider that records runtime provider calls."""

    def __init__(self):
        super().__init__()
        self.intraday_calls = 0
        self.expiry_calls = 0
        self.option_chain_calls = 0

    def get_intraday_candles(
        self,
        security_id,
        exchange_segment,
        instrument="INDEX",
        interval=5,
        days=1,
    ):
        self.intraday_calls += 1
        return super().get_intraday_candles(
            security_id,
            exchange_segment,
            instrument,
            interval,
            days,
        )

    def get_expiries(
        self,
        underlying_security_id,
        underlying_segment,
    ):
        self.expiry_calls += 1
        return super().get_expiries(
            underlying_security_id,
            underlying_segment,
        )

    def get_option_chain(
        self,
        underlying_security_id,
        underlying_segment,
        expiry,
    ):
        self.option_chain_calls += 1
        return super().get_option_chain(
            underlying_security_id,
            underlying_segment,
            expiry,
        )


class ShortCandleProvider(MockMarketDataProvider):
    """Mock provider returning fewer than the runtime minimum."""

    def get_intraday_candles(
        self,
        security_id,
        exchange_segment,
        instrument="INDEX",
        interval=5,
        days=1,
    ):
        candles = super().get_intraday_candles(
            security_id,
            exchange_segment,
            instrument,
            interval,
            days,
        )

        return candles[:29]


class NoExpiryProvider(MockMarketDataProvider):
    """Mock provider with no active expiry."""

    def get_expiries(
        self,
        underlying_security_id,
        underlying_segment,
    ):
        return []


def make_runtime(tmp_path, provider=None):
    db_path = tmp_path / "runtime_test.db"

    store = ProductionSignalStore(str(db_path))

    runtime = ProductionTradeCompassRuntime(
        provider=provider or MockMarketDataProvider(),
        store=store,
    )

    return runtime, store


def test_runtime_initializes_with_mock_provider(tmp_path):
    runtime, store = make_runtime(tmp_path)

    assert runtime.provider.__class__.__name__ == "MockMarketDataProvider"
    assert store.path.exists()


def test_runtime_requires_at_least_30_completed_candles(tmp_path):
    provider = ShortCandleProvider()

    runtime, _ = make_runtime(
        tmp_path,
        provider=provider,
    )

    with pytest.raises(
        RuntimeError,
        match="Need at least 30 completed candles",
    ):
        runtime.snapshot()


def test_runtime_requires_active_expiry(tmp_path):
    provider = NoExpiryProvider()

    runtime, _ = make_runtime(
        tmp_path,
        provider=provider,
    )

    with pytest.raises(
        RuntimeError,
        match="No active option expiry returned by provider",
    ):
        runtime.snapshot()


def test_runtime_creates_read_only_snapshot(tmp_path):
    provider = CountingMockProvider()

    runtime, store = make_runtime(
        tmp_path,
        provider=provider,
    )

    result = runtime.snapshot()

    assert isinstance(result, dict)

    assert result["live_mode"] == "READ_ONLY_PAPER_OBSERVATION"
    assert result["execution_enabled"] is False

    assert result["provider"] == "CountingMockProvider"

    assert "signal_id" in result
    assert result["signal_id"].startswith("TC-")

    assert result["decision"] in {
        "BUY_CALL",
        "BUY_PUT",
        "WAIT",
    }

    assert "market" in result
    assert "decision_price" in result["market"]
    assert "candle_timestamp" in result["market"]
    assert "chain_fetched_at" in result["market"]

    assert "data_quality" in result
    assert result["data_quality"]["status"] == "METADATA_AVAILABLE"

    assert provider.intraday_calls == 1
    assert provider.expiry_calls == 1
    assert provider.option_chain_calls == 1

    recent = store.recent()

    assert len(recent) == 1
    assert recent[0]["signal_id"] == result["signal_id"]


def test_runtime_persists_decision_created_event(tmp_path):
    provider = CountingMockProvider()

    runtime, store = make_runtime(
        tmp_path,
        provider=provider,
    )

    result = runtime.snapshot()

    with store._connect() as con:
        events = con.execute(
            """
            SELECT signal_id, event_type, event_timestamp, payload_json
            FROM signal_events
            WHERE signal_id = ?
            ORDER BY id
            """,
            (result["signal_id"],),
        ).fetchall()

    assert len(events) == 1

    event = events[0]

    assert event["signal_id"] == result["signal_id"]
    assert event["event_type"] == "DECISION_CREATED"
    assert event["event_timestamp"] == str(result.get("timestamp"))

    assert "decision" in event["payload_json"]
    assert "data_quality" in event["payload_json"]


def test_runtime_returns_cached_result_for_same_candle(tmp_path):
    provider = CountingMockProvider()

    runtime, store = make_runtime(
        tmp_path,
        provider=provider,
    )

    first = runtime.snapshot()

    first_intraday_calls = provider.intraday_calls
    first_expiry_calls = provider.expiry_calls
    first_option_chain_calls = provider.option_chain_calls

    second = runtime.snapshot()

    assert second is first

    assert provider.intraday_calls == first_intraday_calls + 1
    assert provider.expiry_calls == first_expiry_calls
    assert provider.option_chain_calls == first_option_chain_calls

    recent = store.recent()

    assert len(recent) == 1
    assert recent[0]["signal_id"] == first["signal_id"]


def test_runtime_recent_signals_returns_persisted_snapshot(tmp_path):
    runtime, _ = make_runtime(tmp_path)

    result = runtime.snapshot()

    recent = runtime.recent_signals(limit=10)

    assert len(recent) == 1

    signal = recent[0]

    assert signal["signal_id"] == result["signal_id"]
    assert signal["decision"] == result["decision"]
    assert signal["symbol"] == result["symbol"]


def test_runtime_uses_configured_provider_instance(tmp_path):
    provider = CountingMockProvider()

    runtime, _ = make_runtime(
        tmp_path,
        provider=provider,
    )

    assert runtime.provider is provider


def test_runtime_default_configuration_is_read_only(tmp_path, monkeypatch):
    monkeypatch.delenv(
        "TRADECOMPASS_DATA_PROVIDER",
        raising=False,
    )

    monkeypatch.delenv(
        "TRADECOMPASS_PHASE12_DB",
        raising=False,
    )

    runtime, _ = make_runtime(tmp_path)

    result = runtime.snapshot()

    assert result["live_mode"] == "READ_ONLY_PAPER_OBSERVATION"
    assert result["execution_enabled"] is False