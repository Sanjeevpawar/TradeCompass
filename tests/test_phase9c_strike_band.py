from __future__ import annotations

from data.dhan_strike_band import StrikeBandConfig, normalize_rolling_response, offset_to_strike


def test_offset_names_are_deterministic():
    assert offset_to_strike(0) == "ATM"
    assert offset_to_strike(1) == "ATM+1"
    assert offset_to_strike(-10) == "ATM-10"


def test_normalize_preserves_returned_strike_and_provenance():
    response = {
        "data": {
            "ce": {
                "timestamp": [1788234300, 1788234600],
                "open": [47.4, 46.0],
                "high": [48.0, 47.0],
                "low": [45.0, 44.0],
                "close": [47.2, 45.5],
                "iv": [17.2, 17.1],
                "volume": [100, 110],
                "strike": [24050, 24000],
                "oi": [1000, 1100],
                "spot": [24042.5, 24010.0],
            }
        }
    }
    rows = normalize_rolling_response(
        response,
        option_type="CALL",
        requested_offset=0,
        expiry_flag="WEEK",
        expiry_code=1,
        source_from_date="2026-09-01",
        source_to_date="2026-09-05",
    )
    assert len(rows) == 2
    assert rows[0]["strike"] == 24050
    assert rows[1]["strike"] == 24000
    assert rows[0]["requested_strike"] == "ATM"
    assert rows[0]["expiry_code"] == 1
    assert rows[0]["identity_status"] == "DERIVED"


def test_config_rejects_out_of_range_offset():
    config = StrikeBandConfig(offsets=(-11, 0, 10))
    try:
        config.validate()
    except ValueError as exc:
        assert "between -10 and +10" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


class Fake429Response:
    status_code = 429
    headers = {}


class Fake429Error(Exception):
    def __init__(self):
        super().__init__("429 rate limit")
        self.response = Fake429Response()


class RetryClient:
    def __init__(self):
        self.calls = 0

    def rolling_expired_options(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise Fake429Error()
        return {"data": {"ce": {
            "timestamp": [1788234300], "open": [47.4], "high": [48.0],
            "low": [45.0], "close": [47.2], "iv": [17.2], "volume": [100],
            "strike": [24050], "oi": [1000], "spot": [24042.5]
        }}}


def test_config_has_safe_rate_limit_defaults():
    config = StrikeBandConfig()
    config.validate()
    assert config.pause_seconds > 0
    assert config.max_retries >= 1


def test_collect_retries_http_429(monkeypatch):
    import data.dhan_strike_band as module
    from data.dhan_strike_band import collect_strike_band

    sleeps = []
    monkeypatch.setattr(module.time_module, "sleep", sleeps.append)
    client = RetryClient()
    config = StrikeBandConfig(offsets=(0,), pause_seconds=0.0, max_retries=2, retry_backoff_seconds=0.01)

    rows, report = collect_strike_band(client, start_date="2026-09-01", end_date="2026-09-05", config=config)
    assert len(rows) == 1
    assert report["requests"]["errors"] == 0
    assert report["requests"]["made"] == 2
    assert report["requests"]["attempts"] == 3
    assert report["requests"]["retry_count"] == 1
    assert report["requests"]["retry_events"][0]["reason"] == "HTTP 429 rate limit"
    assert sleeps == [0.01]
