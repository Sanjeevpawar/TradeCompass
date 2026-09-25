from data.dhan_sample_pipeline import normalize_options, normalize_underlying


def test_normalize_underlying_preserves_timestamp_and_ohlcv():
    rows = normalize_underlying({
        "timestamp": [0], "open": [100], "high": [101], "low": [99], "close": [100.5], "volume": [42]
    })
    assert rows[0]["timestamp_epoch"] == 0
    assert rows[0]["timestamp"].startswith("1970-01-01T05:30:00")
    assert rows[0]["close"] == 100.5


def test_normalize_options_keeps_dhan_metadata_without_inventing_expiry():
    response = {"data": {"ce": {
        "timestamp": [0], "open": [70], "high": [75], "low": [65], "close": [72],
        "iv": [17.2], "volume": [1000], "strike": [24050], "oi": [50000], "spot": [24040]
    }}}
    rows = normalize_options(response, "CALL", expiry_flag="WEEK", expiry_code=1, strike_mode="ATM")
    assert rows[0]["option_type"] == "CE"
    assert rows[0]["strike"] == 24050
    assert rows[0]["iv"] == 17.2
    assert rows[0]["expiry_code"] == 1
    assert "expiry" not in rows[0]
    assert "delta" not in rows[0]
