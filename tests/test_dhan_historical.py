from datetime import datetime

import pytest

from data.dhan_historical import (
    DhanHistoricalClient,
    DhanHistoricalConfig,
    epoch_to_ist,
    month_chunks,
    rolling_option_records,
)


def test_month_chunks_respect_30_day_limit():
    chunks = month_chunks("2025-01-01", "2025-03-15")
    assert chunks == [
        ("2025-01-01", "2025-01-31"),
        ("2025-01-31", "2025-03-02"),
        ("2025-03-02", "2025-03-15"),
    ]
    assert all(
        (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days <= 30
        for a, b in chunks
    )


def test_invalid_option_type_rejected_without_network():
    client = DhanHistoricalClient(DhanHistoricalConfig("x"))
    with pytest.raises(ValueError):
        client.rolling_expired_options(
            security_id="13", strike="ATM", option_type="BAD",
            from_date="2025-01-01", to_date="2025-01-02"
        )


def test_epoch_conversion():
    assert epoch_to_ist(0).startswith("1970-01-01T05:30:00")


def test_rolling_option_records_normalize_dhan_arrays():
    response = {
        "data": {
            "ce": {
                "timestamp": [100, 105],
                "open": [10.0, 11.0],
                "high": [12.0, 13.0],
                "low": [9.0, 10.0],
                "close": [11.0, 12.0],
                "iv": [15.0, 16.0],
                "volume": [100, 200],
                "strike": [25000, 25050],
                "oi": [1000, 1100],
                "spot": [25020, 25060],
            },
            "pe": None,
        }
    }
    rows = rolling_option_records(response, option_type="CALL")
    assert len(rows) == 2
    assert rows[0]["option_type"] == "CE"
    assert rows[0]["strike"] == 25000
    assert rows[1]["oi"] == 1100
